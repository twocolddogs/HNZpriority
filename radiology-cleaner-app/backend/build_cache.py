# --- START OF FILE build_cache.py (Refactored for Reusability) ---

import os
import logging
import sys
import json
import numpy as np
import faiss
import pickle

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from nlp_processor import NLPProcessor
from r2_cache_manager import R2CacheManager

# This function will now be the core logic, callable from other places.
def compute_and_cache_index_for_model(model_key: str, engine_instance, r2_manager):
    """Computes ensemble embeddings, builds a FAISS index, and uploads it to R2."""
    logger.info(f"--- Building index for model '{model_key}' ---")
    
    nlp_proc = engine_instance.nlp_processor
    
    primary_names_to_embed = [e["_clean_primary_name_for_embedding"] for e in engine_instance.nhs_data]
    fsn_to_embed = [e["_clean_fsn_for_embedding"] for e in engine_instance.nhs_data]

    primary_embeddings = np.array(nlp_proc.batch_get_embeddings(primary_names_to_embed), dtype='float32')
    fsn_embeddings = np.array(nlp_proc.batch_get_embeddings(fsn_to_embed), dtype='float32')

    ensemble_embeddings = np.concatenate([primary_embeddings, fsn_embeddings], axis=1)
    faiss.normalize_L2(ensemble_embeddings)

    dimension = ensemble_embeddings.shape[1]
    vector_index = faiss.IndexFlatIP(dimension)
    vector_index.add(ensemble_embeddings)
    index_to_snomed_id = [e.get('snomed_concept_id') for e in engine_instance.nhs_data]
    
    logger.info(f"Built FAISS index with {vector_index.ntotal} vectors.")

    cache_content = {
        'index_data': faiss.serialize_index(vector_index),
        'id_mapping': index_to_snomed_id
    }

    if r2_manager.is_available():
        data_hash = engine_instance._get_data_hash()
        # The V2 engine now has a dedicated cache name for the index.
        # We need to reflect this in the upload logic.
        object_key = f"nhs-embeddings/{model_key}/faiss_index_{data_hash}.cache"
        logger.info(f"Uploading new FAISS index cache to R2 with key: {object_key}")
        # The upload_cache function needs to be slightly adapted to take the raw bytes and key.
        # For simplicity, let's assume `upload_cache` can handle this, or we adapt it.
        # Let's assume a simplified direct upload here.
        
        r2_manager.client.put_object(
            Bucket=r2_manager.bucket_name,
            Key=object_key,
            Body=pickle.dumps(cache_content)
        )
        logger.info(f"Successfully uploaded cache to R2: {object_key}")
        return True
    return False

def main_build():
    from nhs_lookup_engine import NHSLookupEngine
    from parser import RadiologySemanticParser
    from parsing_utils import AbbreviationExpander, AnatomyExtractor, LateralityDetector, ContrastMapper
    from preprocessing import initialize_preprocessor

    logger.info("--- Starting Pre-computation of NHS Embeddings Cache for R2 ---")
    
    r2_manager = R2CacheManager()
    if not r2_manager.is_available():
        logger.error("R2 cache manager not available. Check R2_* environment variables.")
        sys.exit(1)
        
    available_models = NLPProcessor.get_available_models()
    for model_key in available_models.keys():
        nlp_processor = NLPProcessor(model_key=model_key)
        # --- Initialize Dependencies (same as your original script) ---
        base_dir = os.path.dirname(os.path.abspath(__file__))
        nhs_json_path = os.path.join(base_dir, 'core', 'NHS.json')
        with open(nhs_json_path, 'r') as f: nhs_authority = {item.get('primary_source_name'): item for item in json.load(f)}
        abbreviation_expander = AbbreviationExpander()
        initialize_preprocessor(abbreviation_expander)
        anatomy_extractor = AnatomyExtractor(nhs_authority)
        laterality_detector = LateralityDetector()
        contrast_mapper = ContrastMapper()
        semantic_parser = RadiologySemanticParser(nlp_processor, anatomy_extractor, laterality_detector, contrast_mapper)
        engine = NHSLookupEngine(nhs_json_path, nlp_processor, semantic_parser)

        compute_and_cache_index_for_model(model_key, engine, r2_manager)

if __name__ == '__main__':
    main_build()