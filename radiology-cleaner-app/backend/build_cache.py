# --- START OF FILE build_cache.py (Corrected & Simplified) ---

import os
import logging
import sys
import json
import pickle
import faiss
import numpy as np

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
    Computes the FAISS index for a given model and uploads it to R2 with a predictable key.
    """
    logger.info(f"\n=== Building and uploading cache for {model_key} model ===")
    
    # Initialize dependencies
    base_dir = os.path.dirname(os.path.abspath(__file__))
    nhs_json_path = os.path.join(base_dir, 'core', 'NHS.json')
    with open(nhs_json_path, 'r') as f:
        nhs_authority = {item.get('primary_source_name'): item for item in json.load(f)}
    abbreviation_expander = AbbreviationExpander()
    initialize_preprocessor(abbreviation_expander)
    anatomy_extractor = AnatomyExtractor(nhs_authority)
    laterality_detector = LateralityDetector()
    contrast_mapper = ContrastMapper()
    semantic_parser = RadiologySemanticParser(nlp_processor, anatomy_extractor, laterality_detector, contrast_mapper)
    engine = NHSLookupEngine(nhs_json_path, nlp_processor, semantic_parser)

    # Compute the index
    primary_names = [e["_clean_primary_name_for_embedding"] for e in engine.nhs_data]
    fsn_names = [e["_clean_fsn_for_embedding"] for e in engine.nhs_data]
    primary_embeddings = np.array(nlp_processor.batch_get_embeddings(primary_names), dtype='float32')
    fsn_embeddings = np.array(nlp_processor.batch_get_embeddings(fsn_names), dtype='float32')
    ensemble_embeddings = np.concatenate([primary_embeddings, fsn_embeddings], axis=1)
    faiss.normalize_L2(ensemble_embeddings)
    vector_index = faiss.IndexFlatIP(ensemble_embeddings.shape[1])
    vector_index.add(ensemble_embeddings)
    index_to_snomed_id = [e.get('snomed_concept_id') for e in engine.nhs_data]

    cache_content = {
        'index_data': faiss.serialize_index(vector_index),
        'id_mapping': index_to_snomed_id
    }
    
    # Create a predictable, non-versioned object key
    object_key = f"caches/{model_key}/faiss_index.cache"

    logger.info(f"Uploading index to R2 with key: {object_key}")
    success = r2_manager.upload_object(object_key, pickle.dumps(cache_content))
    
    if success:
        logger.info(f"SUCCESS: Uploaded {object_key} to R2.")
    else:
        logger.error(f"FAILURE: Could not upload {object_key} to R2.")
    
    return success

def main_build():
    r2_manager = R2CacheManager()
    if not r2_manager.is_available(): sys.exit(1)
        
    available_models = NLPProcessor.get_available_models()
    success_count = 0
    for model_key in available_models.keys():
        nlp_processor = NLPProcessor(model_key=model_key)
        if build_and_upload_cache_for_model(model_key, nlp_processor, r2_manager):
            success_count += 1
    
    if success_count < len(available_models): sys.exit(1)
    logger.info("Build completed successfully.")

if __name__ == '__main__':
    main_build()
