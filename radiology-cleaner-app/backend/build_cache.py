# --- START OF FILE build_cache.py (Timestamp-based version) ---

import os
import logging
import sys
import json
import numpy as np
import faiss
import pickle
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from nlp_processor import NLPProcessor
from r2_cache_manager import R2CacheManager

def build_and_upload_for_model(model_key: str, engine_instance, r2_manager):
    logger.info(f"--- Building index for model '{model_key}' ---")
    
    nlp_proc = engine_instance.nlp_processor
    
    # 1. Compute Embeddings
    primary_names = [e["_clean_primary_name_for_embedding"] for e in engine_instance.nhs_data]
    fsn_names = [e["_clean_fsn_for_embedding"] for e in engine_instance.nhs_data]
    
    logger.info(f"Step 1/2: Generating embeddings for {len(primary_names)} Primary Names...")
    primary_embeddings_raw = nlp_proc.batch_get_embeddings(primary_names, context_label="Primary Names")
    
    logger.info(f"Step 2/2: Generating embeddings for {len(fsn_names)} FSNs...")
    fsn_embeddings_raw = nlp_proc.batch_get_embeddings(fsn_names, context_label="FSNs")

    # 2. Filter out failed embeddings and corresponding data
    valid_indices = [i for i, (p, f) in enumerate(zip(primary_embeddings_raw, fsn_embeddings_raw)) if p is not None and f is not None]
    
    if len(valid_indices) != len(primary_embeddings_raw):
        failed_count = len(primary_embeddings_raw) - len(valid_indices)
        logger.warning(f"Failed to generate {failed_count} embedding pairs. They will be excluded from the cache.")

    if not valid_indices:
        logger.error(f"No valid embeddings were generated. Aborting cache build for model '{model_key}'.")
        return False

    primary_embeddings = np.array([primary_embeddings_raw[i] for i in valid_indices], dtype='float32')
    fsn_embeddings = np.array([fsn_embeddings_raw[i] for i in valid_indices], dtype='float32')
    filtered_nhs_data = [engine_instance.nhs_data[i] for i in valid_indices]
    index_to_snomed_id = [e.get('snomed_concept_id') for e in filtered_nhs_data]

    # 3. Build FAISS Index
    ensemble_embeddings = np.concatenate([primary_embeddings, fsn_embeddings], axis=1)
    faiss.normalize_L2(ensemble_embeddings)
    dimension = ensemble_embeddings.shape[1]
    vector_index = faiss.IndexFlatIP(dimension)
    vector_index.add(ensemble_embeddings)
    logger.info(f"Built FAISS index with {vector_index.ntotal} vectors.")

    # 4. Prepare Cache Content and Filename
    cache_content = {
        'index_data': faiss.serialize_index(vector_index),
        'id_mapping': index_to_snomed_id
    }
    cache_bytes = pickle.dumps(cache_content)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    object_key = f"caches/{model_key}/{timestamp}.cache"

    # 5. Upload to R2
    if not r2_manager.upload_cache(object_key, cache_bytes):
        logger.error(f"CRITICAL: Failed to upload cache for model '{model_key}'.")
        return False
        
    # 6. Cleanup old caches in R2
    r2_manager.cleanup_old_caches(model_key, keep=3)
    return True

def main_build():
    from nhs_lookup_engine import NHSLookupEngine
    from parser import RadiologySemanticParser
    from parsing_utils import AbbreviationExpander, AnatomyExtractor, LateralityDetector, ContrastMapper
    from preprocessing import initialize_preprocessor

    logger.info("--- Starting Pre-computation of NHS Embeddings Cache for R2 (Timestamp Method) ---")
    
    r2_manager = R2CacheManager()
    if not r2_manager.is_available():
        logger.error("R2 cache manager not available. Check R2_* environment variables.")
        sys.exit(1)
        
    for model_key in NLPProcessor.get_available_models().keys():
        logger.info(f"\n=== Processing model: {model_key} ===")
        nlp_processor = NLPProcessor(model_key=model_key)
        # Initialize dependencies...
        base_dir = os.path.dirname(os.path.abspath(__file__))
        nhs_json_path = os.path.join(base_dir, 'core', 'NHS.json')
        with open(nhs_json_path, 'r') as f: nhs_authority = {item.get('primary_source_name'): item for item in json.load(f)}
        abbreviation_expander = AbbreviationExpander()
        initialize_preprocessor(abbreviation_expander)
        anatomy_extractor = AnatomyExtractor(nhs_authority)
        laterality_detector = LateralityDetector()
        contrast_mapper = ContrastMapper()
        semantic_parser = RadiologySemanticParser(nlp_processor, anatomy_extractor, laterality_detector, contrast_mapper)
        
        # We only need the engine for its pre-parsing of NHS data
        engine = NHSLookupEngine(nhs_json_path, nlp_processor, semantic_parser)
        
        build_and_upload_for_model(model_key, engine, r2_manager)

if __name__ == '__main__':
    main_build()