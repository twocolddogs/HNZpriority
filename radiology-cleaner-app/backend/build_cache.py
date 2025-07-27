# --- START OF FILE build_cache.py (Corrected) ---

import yaml
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
from preprocessing import initialize_preprocessor, get_preprocessor
from cache_version import get_current_cache_version

from config_manager import get_config

def build_and_upload_cache_for_model(model_key: str, nlp_processor, r2_manager, config):
    """
    Computes the FAISS index for a given model and uploads it to R2 with a timestamped filename.
    Skips building if a cache with the current version already exists in R2.
    """
    logger.info(f"\n=== Building and uploading cache for {model_key} model ===")
    
    # Check if cache with current version already exists in R2
    cache_version = get_current_cache_version()
    logger.info(f"Current cache version: {cache_version}")
    
    # DEBUGGING: Check if R2 manager is available
    if not r2_manager.is_available():
        logger.warning("R2 cache manager not available - R2 environment variables may be missing")
        logger.warning("This will force a cache rebuild even if cache already exists")
        logger.info("R2 environment check:")
        logger.info(f"  R2_ACCESS_KEY_ID: {'✓' if os.getenv('R2_ACCESS_KEY_ID') else '✗'}")
        logger.info(f"  R2_SECRET_ACCESS_KEY: {'✓' if os.getenv('R2_SECRET_ACCESS_KEY') else '✗'}")
        logger.info(f"  R2_BUCKET_NAME: {'✓' if os.getenv('R2_BUCKET_NAME') else '✗'}")
        logger.info(f"  R2_ENDPOINT_URL: {'✓' if os.getenv('R2_ENDPOINT_URL') else '✗'}")
    
    prefix = f"caches/{model_key}/"
    r2_objects = r2_manager.list_objects(prefix)
    
    logger.info(f"Found {len(r2_objects)} existing cache objects in R2 with prefix: {prefix}")
    
    # Check if any existing cache matches current version
    for obj in r2_objects or []:
        obj_key = obj['Key']
        logger.info(f"Checking existing cache: {obj_key}")
        if f"_{cache_version}_" in obj_key:
            logger.info(f"Cache with version {cache_version} already exists: {obj_key}")
            logger.info("Skipping rebuild - NHS.json and dependencies haven't changed")
            return True
    
    logger.info(f"No cache found for version {cache_version}. Building new cache...")
    logger.info("Reason: Either no R2 connection or no matching cache version found")
    
    # 1. Initialize dependencies to create an engine instance
    base_dir = os.path.dirname(os.path.abspath(__file__))
    nhs_json_path = os.path.join(base_dir, 'core', 'NHS.json')
    with open(nhs_json_path, 'r', encoding='utf-8') as f:
        nhs_authority_data = json.load(f)
    
    preprocessing_config = config.get_section('preprocessing')

    # 2. Initialize the preprocessor and its dependencies
    abbreviation_expander = AbbreviationExpander()
    initialize_preprocessor(abbreviation_expander, config=preprocessing_config)
    
    # 3. Initialize the parsing utils using the config, NOT nhs_authority
    anatomy_vocab_from_config = preprocessing_config.get('anatomy_vocabulary', {})
    if not anatomy_vocab_from_config:
        logger.error("Anatomy vocabulary not found in config.yaml. Cannot build cache.")
        return False
        
    anatomy_extractor = AnatomyExtractor(anatomy_vocabulary=anatomy_vocab_from_config)
    laterality_detector = LateralityDetector()
    contrast_mapper = ContrastMapper()

    # 4. Initialize the Semantic Parser with the corrected components
    semantic_parser = RadiologySemanticParser(
        nlp_processor=nlp_processor,
        anatomy_extractor=anatomy_extractor,
        laterality_detector=laterality_detector,
        contrast_mapper=contrast_mapper
    )

    # 5. Initialize the NHSLookupEngine for cache building (V4 architecture)
    # For cache building, we only need the retriever processor since we're building the FAISS index
    # We pass None for reranker_manager to avoid initializing rerankers during cache building
    engine = NHSLookupEngine(
        nhs_json_path=nhs_json_path,
        retriever_processor=nlp_processor,  # This is the processor we're building cache for
        reranker_manager=None,  # None during cache building to avoid reranker initialization
        semantic_parser=semantic_parser
    )
    
    # 2. Compute the ensemble embeddings and FAISS index
    logger.info("Computing ensemble embeddings...")

    primary_names = [e["_clean_primary_name_for_embedding"] for e in engine.nhs_data]
    fsn_names = [e["_clean_fsn_for_embedding"] for e in engine.nhs_data]
    
    # Get embeddings and handle None values
    logger.info(f"Getting embeddings for {len(primary_names)} primary names...")
    primary_embeddings_raw = nlp_processor.batch_get_embeddings(primary_names)
    logger.info(f"Getting embeddings for {len(fsn_names)} FSN names...")
    fsn_embeddings_raw = nlp_processor.batch_get_embeddings(fsn_names)
    
    # Filter out None values and track valid indices
    valid_indices = []
    valid_primary_embeddings = []
    valid_fsn_embeddings = []
    valid_nhs_data = []
    
    for i, (primary_emb, fsn_emb) in enumerate(zip(primary_embeddings_raw, fsn_embeddings_raw)):
        if primary_emb is not None and fsn_emb is not None:
            valid_indices.append(i)
            valid_primary_embeddings.append(primary_emb)
            valid_fsn_embeddings.append(fsn_emb)
            valid_nhs_data.append(engine.nhs_data[i])
        else:
            logger.warning(f"Skipping entry {i} due to missing embeddings: primary={primary_emb is not None}, fsn={fsn_emb is not None}")
    
    if len(valid_primary_embeddings) == 0:
        logger.error("No valid embeddings generated. Cannot build cache.")
        return False
    
    logger.info(f"Successfully generated embeddings for {len(valid_primary_embeddings)}/{len(primary_names)} entries")
    
    # Convert to numpy arrays
    primary_embeddings = np.array(valid_primary_embeddings, dtype='float32')
    fsn_embeddings = np.array(valid_fsn_embeddings, dtype='float32')
    ensemble_embeddings = np.concatenate([primary_embeddings, fsn_embeddings], axis=1)
    faiss.normalize_L2(ensemble_embeddings)
    
    logger.info("Building FAISS index...")
    dimension = ensemble_embeddings.shape[1]
    vector_index = faiss.IndexFlatIP(dimension)
    vector_index.add(ensemble_embeddings)
    
    # Use only valid entries for the SNOMED ID mapping
    index_to_snomed_id = [e.get('snomed_concept_id') for e in valid_nhs_data]

    cache_content = {
        'index_data': faiss.serialize_index(vector_index),
        'id_mapping': index_to_snomed_id
    }
    
    # 3. Create a versioned filename and upload to R2
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    filename = f"{model_key}_{cache_version}_{timestamp}_faiss_index.cache"
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
    
    try:
        config = get_config()
    except RuntimeError as e:
        logger.critical(f"Failed to initialize config manager: {e}")
        sys.exit(1)

    r2_manager = R2CacheManager()
    if not r2_manager.is_available():
        logger.error("R2 manager not available. Aborting build.")
        sys.exit(1)
        
    available_models = NLPProcessor.get_available_models()
    
    # Only build caches for embedding models (feature-extraction), not cross-encoders (sentence-similarity)
    embedding_models = {k: v for k, v in available_models.items() if v.get('pipeline') == 'feature-extraction'}
    logger.info(f"Building caches for embedding models: {list(embedding_models.keys())}")
    logger.info(f"Skipping cross-encoder models: {[k for k, v in available_models.items() if v.get('pipeline') != 'feature-extraction']}")
    
    success_count = 0
    for model_key in embedding_models.keys():
        nlp_processor = NLPProcessor(model_key=model_key)
        if build_and_upload_cache_for_model(model_key, nlp_processor, r2_manager, config):
            success_count += 1
    
    logger.info(f"\n=== Build Summary: {success_count}/{len(embedding_models)} caches built and uploaded. ===")
    if success_count < len(embedding_models):
        logger.error("Build failed: Not all embedding model caches were created.")
        sys.exit(1)

if __name__ == '__main__':
    main_build()
