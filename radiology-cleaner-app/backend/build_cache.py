# --- START OF FILE build_cache.py (Corrected) ---

import os
import logging
import sys
import json
import pickle
import faiss
import numpy as np
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [BuildCache] - %(message)s')
logger = logging.getLogger(__name__)

from nlp_processor import NLPProcessor
from r2_cache_manager import R2CacheManager
from nhs_lookup_engine import NHSLookupEngine
from parser import RadiologySemanticParser
from parsing_utils import AbbreviationExpander, AnatomyExtractor, LateralityDetector, ContrastMapper
from preprocessing import initialize_preprocessor

def build_and_upload_cache_for_model(model_key: str, nlp_processor, r2_manager):
    """
    Computes the FAISS index for a given model and uploads it to R2 with a timestamped filename.
    """
    logger.info(f"\n=== Building and uploading cache for {model_key} model ===")
    
    # 1. Initialize dependencies to create an engine instance
    base_dir = os.path.dirname(os.path.abspath(__file__))
    nhs_json_path = os.path.join(base_dir, 'core', 'NHS.json')
    with open(nhs_json_path, 'r', encoding='utf-8') as f:
        nhs_authority_data = json.load(f)
    nhs_authority = {item.get('primary_source_name'): item for item in nhs_authority_data}
    abbreviation_expander = AbbreviationExpander()
    initialize_preprocessor(abbreviation_expander)
    anatomy_extractor = AnatomyExtractor(nhs_authority)
    laterality_detector = LateralityDetector()
    contrast_mapper = ContrastMapper()
    semantic_parser = RadiologySemanticParser(nlp_processor, anatomy_extractor, laterality_detector, contrast_mapper)
    engine = NHSLookupEngine(nhs_json_path, nlp_processor, semantic_parser)

    # 2. Compute the ensemble embeddings and FAISS index
    logger.info("Computing ensemble embeddings...")
    primary_names = [e["_clean_primary_name_for_embedding"] for e in engine.nhs_data]
    fsn_names = [e["_clean_fsn_for_embedding"] for e in engine.nhs_data]
    primary_embeddings = np.array(nlp_processor.batch_get_embeddings(primary_names), dtype='float32')
    fsn_embeddings = np.array(nlp_processor.batch_get_embeddings(fsn_names), dtype='float32')
    ensemble_embeddings = np.concatenate([primary_embeddings, fsn_embeddings], axis=1)
    faiss.normalize_L2(ensemble_embeddings)
    
    logger.info("Building FAISS index...")
    dimension = ensemble_embeddings.shape[1]
    vector_index = faiss.IndexFlatIP(dimension)
    vector_index.add(ensemble_embeddings)
    index_to_snomed_id = [e.get('snomed_concept_id') for e in engine.nhs_data]

    cache_content = {
        'index_data': faiss.serialize_index(vector_index),
        'id_mapping': index_to_snomed_id
    }
    
    # 3. Create a versioned filename and upload to R2
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    filename = f"{model_key}_{timestamp}_faiss_index.cache"
    object_key = f"caches/{model_key}/{filename}"

    logger.info(f"Uploading index to R2 with key: {object_key}")
    success = r2_manager.upload_object(object_key, pickle.dumps(cache_content)) # <-- THIS CALL IS NOW CORRECT
    
    if success:
        logger.info(f"SUCCESS: Uploaded {object_key} to R2.")
        r2_manager.cleanup_old_caches(model_key, keep_latest=3)
    else:
        logger.error(f"FAILURE: Could not upload {object_key} to R2.")
    
    return success

def main_build():
    logger.info("--- Starting Build and Upload Process ---")
    r2_manager = R2CacheManager()
    if not r2_manager.is_available():
        logger.error("R2 manager not available. Aborting build.")
        sys.exit(1)
        
    available_models = NLPProcessor.get_available_models()
    success_count = 0
    for model_key in available_models.keys():
        nlp_processor = NLPProcessor(model_key=model_key)
        if build_and_upload_cache_for_model(model_key, nlp_processor, r2_manager):
            success_count += 1
    
    logger.info(f"\n=== Build Summary: {success_count}/{len(available_models)} caches built and uploaded. ===")
    if success_count < len(available_models):
        logger.error("Build failed: Not all caches were created.")
        sys.exit(1)

if __name__ == '__main__':
    main_build()