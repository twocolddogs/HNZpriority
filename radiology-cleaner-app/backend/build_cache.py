import os
import logging

# =============================================================================
# EMBEDDING CACHE BUILDER
# =============================================================================
# This script is intended to be run as a build step during deployment.
# It pre-computes the NLP embeddings for the NHS dataset and saves them to a
# cache file, so the live application can start instantly without hitting
# server timeouts.
# =============================================================================

# Configure logging to see progress during the build
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# We need to import the components that do the work
from nlp_processor import NLPProcessor
from nhs_lookup_engine import NHSLookupEngine
from parser import RadiologySemanticParser # NHSLookupEngine needs this for its init
# Import all other dependencies required by the classes above
from parsing_utils import AbbreviationExpander, AnatomyExtractor, LateralityDetector, ContrastMapper
from preprocessing import initialize_preprocessor
from r2_cache_manager import R2CacheManager
import sys
import json

def build_embeddings_cache():
    """
    Initializes the necessary components to compute and save NHS embeddings for both
    production and experimental models.
    
    NOTE: On Render.com, build commands run on separate compute that cannot access
    persistent disks. The cache files created here will be in /tmp and won't persist
    to runtime. The application will detect missing cache at runtime and rebuild
    embeddings using the persistent disk storage.
    """
    logger.info("--- Starting Pre-computation of NHS Embeddings Cache ---")
    logger.info("Building cache to upload to Cloudflare R2 for persistent storage across deployments")
    
    # Initialize R2 cache manager
    r2_manager = R2CacheManager()
    if not r2_manager.is_available():
        logger.error("R2 cache manager not available. Check R2_* environment variables.")
        sys.exit(1)
    
    # Get available models from NLPProcessor
    available_models = NLPProcessor.get_available_models()
    logger.info(f"Building caches for models: {list(available_models.keys())}")
    
    success_count = 0
    total_models = len(available_models)
    
    for model_alias, model_info in available_models.items():
        logger.info(f"\n=== Building cache for {model_alias} model: {model_info['hf_name']} ===")
        
        # --- 1. Initialize NLP Processor for this model ---
        try:
            nlp_processor = NLPProcessor(model_key=model_alias)
            if not nlp_processor.is_available():
                logger.error("HUGGING_FACE_TOKEN is not set. Cannot build embeddings cache.")
                sys.exit(1)
            logger.info(f"Using NLP model: {nlp_processor.hf_model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize NLP Processor for {model_alias}: {e}", exc_info=True)
            continue

        # --- 2. Initialize Dependencies for NHSLookupEngine ---
        # This part mimics the setup in _initialize_app() but is focused only on what's
        # needed for the NHSLookupEngine to do its embedding work.
        base_dir = os.path.dirname(os.path.abspath(__file__))
        nhs_json_path = os.path.join(base_dir, 'core', 'NHS.json')

        nhs_authority = {}
        if os.path.exists(nhs_json_path):
            with open(nhs_json_path, 'r', encoding='utf-8') as f:
                nhs_data = json.load(f)
            for item in nhs_data:
                if primary_source_name := item.get('primary_source_name'):
                    nhs_authority[primary_source_name] = item
        else:
            logger.critical(f"CRITICAL: NHS JSON file not found at {nhs_json_path}")
            sys.exit(1)

        abbreviation_expander = AbbreviationExpander()
        initialize_preprocessor(abbreviation_expander)
        anatomy_extractor = AnatomyExtractor(nhs_authority)
        laterality_detector = LateralityDetector()
        contrast_mapper = ContrastMapper()

        semantic_parser = RadiologySemanticParser(
            nlp_processor=nlp_processor, # a processor is needed for the init
            anatomy_extractor=anatomy_extractor,
            laterality_detector=laterality_detector,
            contrast_mapper=contrast_mapper
        )

        # --- 3. Initialize NHSLookupEngine (will auto-load from R2 or compute) ---
        logger.info(f"Initializing NHSLookupEngine for {model_alias} model...")
        try:
            engine = NHSLookupEngine(
                nhs_json_path=nhs_json_path,
                nlp_processor=nlp_processor,
                semantic_parser=semantic_parser
            )
            
            # The engine initialization already handled R2 loading/computing
            # Check if cache now exists in R2 to confirm success
            current_data_hash = engine._get_data_hash()
            
            if r2_manager.cache_exists(model_alias, current_data_hash):
                logger.info(f"SUCCESS: {model_alias} embeddings cache available in R2 with hash {current_data_hash}")
                success_count += 1
            else:
                # If not in R2, force a recomputation to ensure cache is created
                logger.info(f"Forcing cache recomputation for {model_alias} to ensure R2 upload...")
                engine._load_or_compute_embeddings(allow_recompute=True)
                
                # Verify cache was uploaded to R2
                if r2_manager.cache_exists(model_alias, current_data_hash):
                    logger.info(f"SUCCESS: {model_alias} embeddings cache computed and uploaded to R2")
                    success_count += 1
                else:
                    logger.error(f"FAILURE: {model_alias} embeddings cache was not uploaded to R2")

        except Exception as e:
            logger.error(f"An error occurred during {model_alias} cache generation: {e}", exc_info=True)
    
    # Final summary
    logger.info(f"\n=== Cache Build Summary ===")
    logger.info(f"Successfully built {success_count}/{total_models} embedding caches")
    
    if success_count == 0:
        logger.error("CRITICAL: No embedding caches were successfully created.")
        sys.exit(1)
    elif success_count < total_models:
        logger.warning(f"WARNING: Only {success_count}/{total_models} caches were created successfully.")
    else:
        logger.info("SUCCESS: All embedding caches created successfully.")

if __name__ == '__main__':
    build_embeddings_cache()