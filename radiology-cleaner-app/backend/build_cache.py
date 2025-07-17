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
import sys
import json

def build_embeddings_cache():
    """
    Initializes the necessary components to compute and save NHS embeddings.
    """
    logger.info("--- Starting Pre-computation of NHS Embeddings Cache ---")
    
    # --- 1. Initialize NLP Processor ---
    # It will use the default model defined in NLPProcessor, which matches the app's default.
    # Ensure HUGGING_FACE_TOKEN is set in your build environment.
    try:
        nlp_processor = NLPProcessor()
        if not nlp_processor.is_available():
            logger.error("HUGGING_FACE_TOKEN is not set. Cannot build embeddings cache.")
            sys.exit(1)
        logger.info(f"Using NLP model: {nlp_processor.model_name}")
    except Exception as e:
        logger.error(f"Failed to initialize NLP Processor: {e}", exc_info=True)
        sys.exit(1)

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

    # --- 3. Initialize NHSLookupEngine and Trigger Cache Build ---
    # The __init__ method of NHSLookupEngine automatically calls _load_or_compute_embeddings.
    # Since no cache exists, it will compute them and save the file.
    logger.info("Initializing NHSLookupEngine to trigger embedding computation...")
    try:
        engine = NHSLookupEngine(
            nhs_json_path=nhs_json_path,
            nlp_processor=nlp_processor,
            semantic_parser=semantic_parser
        )
        # The cache is built during the engine's initialization.
        # We just need to confirm it was created.
        cache_path = engine._get_cache_path()
        if os.path.exists(cache_path):
             logger.info(f"SUCCESS: Embeddings cache successfully created at: {cache_path}")
        else:
             logger.error("FAILURE: Embeddings cache file was not created.")
             sys.exit(1)

    except Exception as e:
        logger.error(f"An error occurred during cache generation: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    build_embeddings_cache()