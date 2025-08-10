# --- START OF FILE app.py ---

# =============================================================================
# RADIOLOGY EXAM STANDARDIZATION API
# =============================================================================
# This Flask application provides a unified processing pipeline for standardizing
# radiology exam names against NHS reference data using NLP and semantic matching.

import time, json, logging, threading, os, sys, re, math, hashlib
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from pathlib import Path
from secondary_pipeline import SecondaryPipeline, get_secondary_pipeline
from pipeline_integration import PipelineIntegration, BatchResultProcessor
import asyncio 

# Core processing components
from parser import RadiologySemanticParser
from nlp_processor import NLPProcessor
from nhs_lookup_engine import NHSLookupEngine
from reranker_manager import RerankerManager
from database_models import DatabaseManager, CacheManager
from feedback_training import FeedbackTrainingManager
from parsing_utils import AbbreviationExpander, AnatomyExtractor, LateralityDetector, ContrastMapper
### FIX: Import detect_all_contexts for correct data flow. Context is determined from the input request.
from context_detection import detect_all_contexts
from preprocessing import initialize_preprocessor, preprocess_exam_name, get_preprocessor
from cache_version import get_current_cache_version, format_cache_key
from r2_cache_manager import R2CacheManager
from validation_cache_manager import ValidationCacheManager
from common.hash_keys import compute_request_hash_with_preimage

# Secondary Pipeline Integration
try:
    from secondary_pipeline import SecondaryPipeline, get_secondary_pipeline
    from pipeline_integration import PipelineIntegration, BatchResultProcessor
    import asyncio
    SECONDARY_PIPELINE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Secondary pipeline not available: {e}")
    SECONDARY_PIPELINE_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Reduce third-party library debug noise
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('botocore.hooks').setLevel(logging.CRITICAL)
logging.getLogger('botocore.loaders').setLevel(logging.CRITICAL)
logging.getLogger('botocore.client').setLevel(logging.CRITICAL)
logging.getLogger('botocore.endpoint').setLevel(logging.CRITICAL)
logging.getLogger('botocore.regions').setLevel(logging.CRITICAL)
logging.getLogger('botocore.utils').setLevel(logging.CRITICAL)
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('charset_normalizer').setLevel(logging.WARNING)
logging.getLogger('faiss').setLevel(logging.WARNING)
# Complete silence for AWS/HTTP libraries
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('requests.packages.urllib3').setLevel(logging.WARNING)

app = Flask(__name__)
CORS(app, 
     origins=[
         'https://develop.radiology-cleaner-app.pages.dev',
         'https://develop.hnzradtools.nz',
         'https://hnzradtools.nz',
         'https://*.pages.dev'
     ], 
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=False)

# =============================================================================
# ### START OF ADDED CODE FOR ASYNC MANAGEMENT ###
# =============================================================================

def run_async_task(coro):
    """
    Safely runs an async coroutine in a synchronous context by creating,
    managing, and gracefully shutting down a new event loop.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(coro)
        
        # --- START OF NEW, GRACEFUL SHUTDOWN LOGIC ---
        
        # Allow time for background cleanup tasks (like from httpx) to complete
        # by running all pending tasks before closing the loop.
        pending = asyncio.all_tasks(loop=loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending))
        
        # Additional graceful shutdown step for async generators
        loop.run_until_complete(loop.shutdown_asyncgens())
        
        # --- END OF NEW, GRACEFUL SHUTDOWN LOGIC ---
        
        return result
    finally:
        # Close the loop only after ensuring all tasks are done.
        loop.close()
        asyncio.set_event_loop(None)

# =============================================================================
# ### END OF ADDED CODE ###
# =============================================================================

@app.before_request
def handle_preflight():
    """Handle preflight OPTIONS requests"""
    if request.method == "OPTIONS":
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

@app.after_request
def after_request(response):
    """Ensure CORS headers are always present"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# Global component instances
semantic_parser: Optional[RadiologySemanticParser] = None
nhs_lookup_engine: Optional[NHSLookupEngine] = None
model_processors: Dict[str, NLPProcessor] = {}
reranker_manager: Optional[RerankerManager] = None
_batch_preloaded_config = None  # Shared config for secondary pipeline to avoid repeated R2 fetches

def compute_request_hash_with_preimage(data_source: str, exam_code: str, exam_name: str, modality_code: Optional[str]) -> Tuple[str, str]:
    """
    Generate SHA-256 hash for request matching validation system with consistent preimage.
    
    Args:
        data_source: Data source identifier
        exam_code: Exam code from input
        exam_name: Original exam name  
        modality_code: Modality code (can be None)
        
    Returns:
        Tuple of (hash_string, preimage_string) for validation cache lookup
    """
    # Use same key fields as expected by ValidationCacheManager
    key_fields = [
        str(data_source or '').strip().lower(),
        str(exam_code or '').strip().lower(),
        str(exam_name or '').strip().lower(), 
        str(modality_code or '').strip().lower()
    ]
    
    # Create hash from concatenated fields with consistent separator
    preimage = '|'.join(key_fields)
    hash_value = hashlib.sha256(preimage.encode('utf-8')).hexdigest()
    return hash_value, preimage
_init_lock = threading.Lock()
_app_initialized = False
# DB/Cache managers would be initialized here in a full app
db_manager = None
cache_manager = None
r2_manager = R2CacheManager()
validation_cache_manager = None

# Secondary Pipeline Configuration
app.config.setdefault('OPENROUTER_API_KEY', os.getenv('OPENROUTER_API_KEY'))
app.config.setdefault('ENABLE_SECONDARY_PIPELINE', True)
app.config.setdefault('SECONDARY_PIPELINE_THRESHOLD', 0.8)
app.config.setdefault('SECONDARY_PIPELINE_CONCURRENCY', 3)

# Secondary pipeline globals
secondary_integration = None
secondary_batch_processor = None

def _initialize_secondary_pipeline():
    """Initialize secondary pipeline components"""
    global secondary_integration, secondary_batch_processor
    if SECONDARY_PIPELINE_AVAILABLE and secondary_integration is None:
        try:
            secondary_integration = PipelineIntegration(app.config)
            secondary_batch_processor = BatchResultProcessor(secondary_integration)
            logger.info(f"Secondary pipeline initialized - Enabled: {secondary_integration.is_enabled()}")
        except Exception as e:
            logger.error(f"Failed to initialize secondary pipeline: {e}")
            secondary_integration = None
            secondary_batch_processor = None

def _initialize_model_processors() -> Dict[str, NLPProcessor]:
    """Initialize available NLP processors for different models"""
    available_models = NLPProcessor.get_available_models()
    processors = {}
    for model_key in available_models.keys():
        try:
            processor = NLPProcessor(model_key=model_key)
            if processor.is_available():
                processors[model_key] = processor
                logger.info(f"Initialized model processor for '{model_key}': {processor.hf_model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize model processor for '{model_key}': {e}")
    return processors

def _get_nlp_processor(model: str = 'retriever') -> Optional[NLPProcessor]:
    """Get the appropriate NLP processor for the specified model"""
    global model_processors
    processor = model_processors.get(model)
    if not processor:
        logger.warning(f"Model '{model}' not available, falling back to retriever")
        processor = model_processors.get('retriever')
    return processor

def _initialize_app():
    """Initializes all application components in the correct dependency order."""
    global semantic_parser, nlp_processor, model_processors, nhs_lookup_engine, cache_manager, reranker_manager, validation_cache_manager
    logger.info("--- Performing first-time application initialization... ---")
    start_time = time.time()
    
    try:
        from config_manager import get_config
        config = get_config()
    except RuntimeError as e:
        logger.critical(f"Failed to initialize config manager: {e}")
        sys.exit(1)
    
    class SimpleCache:
        def __init__(self):
            self.cache = {}
            self.cache_version = get_current_cache_version()
            logger.info(f"Initialized cache with version: {self.cache_version}")
        
        def _check_version_and_clear_if_needed(self):
            current_version = get_current_cache_version()
            if current_version != self.cache_version:
                logger.info(f"Cache version changed from {self.cache_version} to {current_version}, clearing cache")
                self.cache.clear()
                self.cache_version = current_version
        
        def get(self, key):
            self._check_version_and_clear_if_needed()
            formatted_key = format_cache_key("simple_cache", self.cache_version, key)
            return self.cache.get(formatted_key)
        
        def set(self, key, value):
            self._check_version_and_clear_if_needed()
            formatted_key = format_cache_key("simple_cache", self.cache_version, key)
            self.cache[formatted_key] = value
            return formatted_key
    cache_manager = SimpleCache()

    model_processors = _initialize_model_processors()
    
    # V4 Architecture: Initialize retriever and reranker manager for flexible reranking
    retriever_processor = model_processors.get('retriever')  # BioLORD for retrieval
    
    # Ensure retriever processor is available
    if not retriever_processor:
        logger.critical("Required retriever processor ('retriever' - BioLORD) could not be initialized.")
        sys.exit(1)
    
    # Initialize the reranker manager with multiple backend support
    reranker_manager = RerankerManager()
    
    logger.info("🚀 [V4-INIT] Initializing V4 architecture with flexible reranking")
    logger.info(f"📥 [V4-INIT] Retriever: {retriever_processor.hf_model_name} ({retriever_processor.pipeline})")
    logger.info(f"🔄 [V4-INIT] Available rerankers: {list(reranker_manager.get_available_rerankers().keys())}")
    logger.info(f"🎯 [V4-INIT] Default reranker: {reranker_manager.get_default_reranker_key()}")
    
    # Test retriever availability
    if retriever_processor.is_available():
        logger.info("✅ [V4-INIT] Retriever processor ready")
    else:
        logger.warning("⚠️ [V4-INIT] Retriever processor not available (missing HF token)")
    
    # Backward compatibility - some parts of the code still expect nlp_processor
    nlp_processor = retriever_processor
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    nhs_json_path = os.path.join(base_dir, 'core', 'NHS.json')
    
    nhs_authority = {}
    if os.path.exists(nhs_json_path):
        with open(nhs_json_path, 'r', encoding='utf-8') as f: 
            nhs_data = json.load(f)
        for item in nhs_data:
            if primary_source_name := item.get('primary_source_name'): 
                nhs_authority[primary_source_name] = item
        logger.info(f"Loaded {len(nhs_authority)} NHS reference entries")
    else: 
        logger.critical(f"CRITICAL: NHS JSON file not found at {nhs_json_path}")
        sys.exit(1)

    abbreviation_expander = AbbreviationExpander()
    
    # Use ConfigManager to get preprocessing configuration from R2
    from config_manager import get_config
    config_manager = get_config()
    preprocessing_config = config_manager.get_section('preprocessing')
    
    initialize_preprocessor(abbreviation_expander, config=preprocessing_config)
    
    anatomy_vocab_from_config = preprocessing_config.get('anatomy_vocabulary', {})
    if not anatomy_vocab_from_config:
        logger.warning("Anatomy vocabulary not found in R2 config. AnatomyExtractor will be empty.")

    anatomy_extractor = AnatomyExtractor(anatomy_vocabulary=anatomy_vocab_from_config)
    laterality_detector = LateralityDetector()
    contrast_mapper = ContrastMapper()

    semantic_parser = RadiologySemanticParser(
        nlp_processor=nlp_processor,
        anatomy_extractor=anatomy_extractor,
        laterality_detector=laterality_detector,
        contrast_mapper=contrast_mapper
    )


    # V3 Architecture: Initialize NHSLookupEngine with dual processors
    nhs_lookup_engine = NHSLookupEngine(
        nhs_json_path=nhs_json_path,
        retriever_processor=retriever_processor,
        reranker_manager=reranker_manager,
        semantic_parser=semantic_parser
    )
    
    nhs_lookup_engine.validate_consistency()
    
    # Initialize validation cache manager for preflight checking
    validation_cache_manager = ValidationCacheManager(r2_manager)
    logger.info(f"Validation cache manager initialized: {validation_cache_manager.is_available()}")
    
    logger.info(f"Initialization complete in {time.time() - start_time:.2f} seconds.")

def _ensure_app_is_initialized():
    """Thread-safe gatekeeper to ensure initialization runs only once."""
    global _app_initialized
    if _app_initialized: return
    with _init_lock:
        if not _app_initialized:
            _initialize_app()
            _app_initialized = True

def _refresh_validation_caches():
    """
    Refresh validation caches from R2 to ensure latest human-in-the-loop feedback is used.
    Called at the start of every processing run to pick up new validation entries.
    """
    global nhs_lookup_engine
    if nhs_lookup_engine:
        try:
            refresh_result = nhs_lookup_engine.reload_validation_caches()
            if refresh_result.get('status') == 'success':
                logger.info(f"[CACHE-REFRESH] Updated validation caches: approved={refresh_result.get('approved_count', 0)} (Δ{refresh_result.get('approved_delta', 0):+d}), rejected={refresh_result.get('rejected_count', 0)} (Δ{refresh_result.get('rejected_delta', 0):+d})")
            else:
                logger.warning(f"[CACHE-REFRESH] Validation cache refresh returned non-success status: {refresh_result}")
        except Exception as e:
            logger.error(f"[CACHE-REFRESH] Failed to refresh validation caches: {e}")
    else:
        logger.warning("[CACHE-REFRESH] NHS lookup engine not available for cache refresh")

def process_exam_request(exam_name: str, modality_code: Optional[str], nlp_processor: NLPProcessor, debug: bool = False, reranker_key: Optional[str] = None, data_source: Optional[str] = None, exam_code: Optional[str] = None, run_secondary_inline: bool = True) -> Dict:
    """Central processing logic for a single exam."""
    if debug:
        logger.info(f"[DEBUG-FLOW] process_exam_request received debug=True for exam: {exam_name}")
    
    _ensure_app_is_initialized()
    if not nhs_lookup_engine or not semantic_parser:
        return {'error': 'Core components not initialized'}

    _preprocessor = get_preprocessor()
    
    if _preprocessor and _preprocessor.should_exclude_exam(exam_name):
        return {
            'error': 'EXCLUDED_NON_CLINICAL',
            'message': f'Excluded non-clinical entry: {exam_name}',
            'exam_name': exam_name,
            'excluded': True
        }
    
    cleaned_exam_name, is_input_simple = _preprocessor.preprocess_with_complexity(exam_name)
    parsed_input_components = semantic_parser.parse_exam_name(cleaned_exam_name, modality_code or 'Other')
    
    lookup_engine_to_use = nhs_lookup_engine
    
    if nlp_processor.model_key != nhs_lookup_engine.retriever_processor.model_key:
        logger.warning(f"🔄 [V4-API] Model parameter '{nlp_processor.model_key}' ignored - using V4 dual-processor pipeline")
        logger.info(f"🔄 [V4-API] Pipeline: {nhs_lookup_engine.retriever_processor.model_key} → {reranker_key or 'default'}")
    
    if debug:
        logger.info(f"[DEBUG-FLOW] About to call standardize_exam with debug=True, is_input_simple={is_input_simple}")
    
    # Wrap the entire processing logic in a try...except block to prevent crashes from returning malformed data
    try:
        nhs_result = lookup_engine_to_use.standardize_exam(cleaned_exam_name, parsed_input_components, is_input_simple=is_input_simple, debug=debug, reranker_key=reranker_key, data_source=data_source, exam_code=exam_code)

        # =============================================================================
        # ### START OF REFACTORED SECONDARY PIPELINE LOGIC ###
        # =============================================================================

        # Determine if the secondary pipeline should run for this single result
        confidence = nhs_result.get('components', {}).get('confidence', 1.0)
        should_apply_secondary = (
            nhs_result.get('ambiguous', False) or
            confidence < 0.8 or  # Use a clear threshold
            nhs_result.get('semantic_similarity_safeguard', {}).get('applied', False)
        )
        if run_secondary_inline and should_apply_secondary and SECONDARY_PIPELINE_AVAILABLE:
            # Ensure the error for non-clinical exams is handled first
            if nhs_result.get('error') == 'EXCLUDED_NON_CLINICAL':
                logger.info(f"Engine excluded '{exam_name}' as non-clinical. Formatting final response.")
                return {
                    'error': 'EXCLUDED_NON_CLINICAL',
                    'message': nhs_result.get('message', f'Excluded non-clinical entry: {exam_name}'),
                    'exam_name': exam_name,
                    'excluded': True
                }

            # Apply secondary pipeline if the conditions are met and the module is available
            logger.info(f"[SECONDARY-PIPELINE] Applying secondary pipeline for single exam: {exam_name} (Confidence: {confidence:.2f})")
            _initialize_secondary_pipeline() # Make sure it's ready
            
            # Construct the single-item batch using the full result structure
            single_item_batch = {
                "input": {
                    "exam_name": exam_name,
                    "modality_code": modality_code,
                    "data_source": data_source,
                    "exam_code": exam_code
                },
                "output": nhs_result,
                "status": "success"
            }
            
            try:
                # Use shared instance with preloaded config to avoid repeated R2 fetches
                global _batch_preloaded_config
                pipeline = get_secondary_pipeline(preloaded_config=_batch_preloaded_config)
                # Use the new helper function to run the async code
                ensemble_results = run_async_task(pipeline.process_low_confidence_results([single_item_batch]))
                
                if ensemble_results and ensemble_results[0].improved:
                    secondary_result = ensemble_results[0]
                    logger.info(f"[SECONDARY-PIPELINE] Secondary pipeline improved result for: {exam_name}")
                    
                    # Overwrite the primary result fields with the improved consensus data
                    nhs_result['clean_name'] = secondary_result.consensus_best_match_procedure_name
                    nhs_result['snomed_id'] = secondary_result.consensus_best_match_snomed_id
                    nhs_result['snomed_fsn'] = secondary_result.consensus_snomed_fsn
                    nhs_result['components']['confidence'] = secondary_result.consensus_confidence
                    
                    nhs_result['secondary_pipeline_applied'] = True
                    nhs_result['secondary_pipeline_details'] = {
                        'improved': True,
                        'original_confidence': confidence,
                        'consensus_confidence': secondary_result.consensus_confidence,
                        'agreement_score': secondary_result.agreement_score
                    }
                else:
                    logger.info(f"[SECONDARY-PIPELINE] No improvement from secondary pipeline for: {exam_name}")
                    nhs_result['secondary_pipeline_applied'] = True
                    nhs_result['secondary_pipeline_details'] = {'improved': False, 'reason': 'No consensus improvement found'}

            except Exception as e:
                logger.error(f"Error during single-exam secondary pipeline processing: {e}", exc_info=True)
                nhs_result['secondary_pipeline_applied'] = False
                nhs_result['secondary_pipeline_error'] = str(e)

        else:
            nhs_result['secondary_pipeline_applied'] = False

        # =============================================================================
        # ### END OF REFACTORED LOGIC ###
        # =============================================================================

        components_from_engine = nhs_result.get('components', {})
        context_from_input = detect_all_contexts(cleaned_exam_name, parsed_input_components.get('anatomy', []))
        matched_modalities = components_from_engine.get('modality', [])

        final_result = {
            'data_source': data_source or 'N/A',
            'modality_code': [modality_code] if modality_code else [],
            'exam_code': exam_code or 'N/A',
            'exam_name': exam_name,
            'clean_name': _medical_title_case(nhs_result.get('clean_name', cleaned_exam_name)),
            'ambiguous': nhs_result.get('ambiguous', False),
            'snomed': {
                'found': bool(nhs_result.get('snomed_id')),
                'fsn': nhs_result.get('snomed_fsn', ''),
                'id': nhs_result.get('snomed_id', ''),
                'laterality_concept_id': nhs_result.get('snomed_laterality_concept_id', ''),
                'laterality_fsn': nhs_result.get('snomed_laterality_fsn', '')
            },
            'components': {
                'anatomy': components_from_engine.get('anatomy', []),
                'laterality': components_from_engine.get('laterality', []),
                'contrast': components_from_engine.get('contrast', []),
                'technique': components_from_engine.get('technique', []),
                'modality': matched_modalities,
                'confidence': components_from_engine.get('confidence', 0.0),
                'gender_context': context_from_input['gender_context'],
                'age_context': context_from_input['age_context'],
                'clinical_context': context_from_input['clinical_context'],
            },
            # Add secondary pipeline status fields directly to the main result object
            'secondary_pipeline_applied': nhs_result.get('secondary_pipeline_applied', False),
            'secondary_pipeline_details': nhs_result.get('secondary_pipeline_details')
        }
        
        if 'all_candidates' in nhs_result:
            final_result['all_candidates'] = nhs_result['all_candidates']
        
        if debug and 'debug' in nhs_result:
            final_result['debug'] = nhs_result['debug']
        
        return final_result

    except Exception as e:
        # This is a critical safeguard. If anything goes wrong, return a proper error structure.
        logger.error(f"FATAL ERROR in process_exam_request for '{exam_name}': {e}", exc_info=True)
        return {
            "error": f"Internal processing error: {type(e).__name__}",
            "message": str(e),
            "exam_name": exam_name,
            "clean_name": f"ERROR: {type(e).__name__}",
            "excluded": True
        }
    
    
    ### FIX: The context (gender, age, etc.) is a property of the INPUT request, not the matched NHS entry.
    ### We must calculate context here from the cleaned input string to ensure it's always correct.
    components_from_engine = nhs_result.get('components', {})
    context_from_input = detect_all_contexts(cleaned_exam_name, parsed_input_components.get('anatomy', []))

    matched_modalities = components_from_engine.get('modality', [])
    primary_modality_code = matched_modalities[0] if matched_modalities else (modality_code or 'Other')

    final_result = {
        'data_source': data_source or 'N/A',
        'modality_code': [modality_code] if modality_code else [],
        'exam_code': exam_code or 'N/A',
        'exam_name': exam_name,
        'clean_name': _medical_title_case(nhs_result.get('clean_name', cleaned_exam_name)),
        'ambiguous': nhs_result.get('ambiguous', False),
        'snomed': {
            'found': bool(nhs_result.get('snomed_id')),
            'fsn': nhs_result.get('snomed_fsn', ''),
            'id': nhs_result.get('snomed_id', ''),
            'laterality_concept_id': nhs_result.get('snomed_laterality_concept_id', ''),
            'laterality_fsn': nhs_result.get('snomed_laterality_fsn', '')
        },
        'components': {
            # Components from the matched NHS entry (the result of the lookup)
            'anatomy': components_from_engine.get('anatomy', []),
            'laterality': components_from_engine.get('laterality', []),
            'contrast': components_from_engine.get('contrast', []),
            'technique': components_from_engine.get('technique', []),
            'modality': matched_modalities, # NEW: Keep the full list here for transparency
            'confidence': components_from_engine.get('confidence', 0.0),
            
            # Context from the original input request, calculated once and stored
            'gender_context': context_from_input['gender_context'],
            'age_context': context_from_input['age_context'],
            'clinical_context': context_from_input['clinical_context'],
        }
    }
    
    # Always include all candidates for hover functionality
    if 'all_candidates' in nhs_result:
        final_result['all_candidates'] = nhs_result['all_candidates']
    
    # Preserve debug information if it exists in nhs_result
    if debug and 'debug' in nhs_result:
        final_result['debug'] = nhs_result['debug']
    if debug and 'debug_simple' in nhs_result:
        final_result['debug_simple'] = nhs_result['debug_simple']
    if debug and 'debug_test' in nhs_result:
        final_result['debug_test'] = nhs_result['debug_test']
    
    return final_result

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring service availability"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(), 
        'app_initialized': _app_initialized
    })

@app.route('/warmup', methods=['POST', 'GET'])
def warmup_api():
    """Warm up the API by initializing all components without processing data"""
    try:
        logger.info("🔥 API warmup requested - initializing components...")
        start_time = time.time()
        
        # Trigger initialization
        _ensure_app_is_initialized()
        
        # Test that key components are ready
        warmup_status = {
            'initialized': _app_initialized,
            'model_processors': len(model_processors) if model_processors else 0,
            'nhs_lookup_engine': nhs_lookup_engine is not None,
            'semantic_parser': semantic_parser is not None,
            'reranker_manager': reranker_manager is not None
        }
        
        if reranker_manager:
            warmup_status['available_rerankers'] = len(reranker_manager.get_available_rerankers())
        
        elapsed_time = time.time() - start_time
        logger.info(f"✅ API warmup completed in {elapsed_time:.2f}s")
        
        return jsonify({
            'status': 'success',
            'message': 'API warmed up successfully',
            'warmup_time': elapsed_time,
            'components': warmup_status
        })
        
    except Exception as e:
        logger.error(f"❌ API warmup failed: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Warmup failed: {str(e)}'
        }), 500

@app.route('/models', methods=['GET'])
def list_available_models():
    """List available NLP models and their status (lightweight, no initialization required)"""
    _ensure_app_is_initialized() # Ensure components are initialized
    try:
        available_models = NLPProcessor.get_available_models()
        model_info = {}
        
        for model_key, model_config in available_models.items():
            embeddings_loaded = False
            if nhs_lookup_engine and hasattr(nhs_lookup_engine, '_embeddings_loaded'):
                embeddings_loaded = (nhs_lookup_engine._embeddings_loaded and 
                                   nhs_lookup_engine.nlp_processor.model_key == model_key)
            
            model_info[model_key] = {
                'name': model_config['hf_name'],
                'status': model_config['status'],
                'description': model_config['description'],
                'embeddings_loaded': embeddings_loaded
            }
        
        # Get reranker information
        reranker_info = {}
        default_reranker = 'medcpt'
        
        if reranker_manager:
            reranker_info = reranker_manager.get_available_rerankers()
            default_reranker = reranker_manager.get_default_reranker_key()
        
        return jsonify({
            'models': model_info,
            'default_model': 'retriever',
            'rerankers': reranker_info,
            'default_reranker': default_reranker,
            'usage': 'Add "model": "model_key" and "reranker": "reranker_key" to your request',
            'app_initialized': _app_initialized
        })
    except Exception as e:
        logger.error(f"Models endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Failed to list models"}), 500

@app.route('/config/reload', methods=['POST'])
def reload_config():
    """Reload configuration from R2, enabling real-time config updates."""
    try:
        from config_manager import get_config
        config_manager = get_config()
        
        # Force reload from R2
        success = config_manager.force_r2_reload()
        
        if success:
            return jsonify({
                'message': 'Configuration reloaded successfully from R2',
                'timestamp': datetime.now().isoformat(),
                'source': 'R2'
            })
        else:
            # Try regular reload (will use cache or fallback)
            config_manager.reload()
            return jsonify({
                'message': 'Configuration reloaded from fallback sources',
                'timestamp': datetime.now().isoformat(),
                'source': 'local/cache',
                'warning': 'R2 config fetch failed'
            })
            
    except Exception as e:
        logger.error(f"Config reload endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Failed to reload configuration"}), 500

@app.route('/admin/reload-validation-cache', methods=['POST'])
def reload_validation_cache():
    """
    Admin endpoint to reload validation caches from R2 cloud storage.
    
    This allows administrators to refresh validation caches after updating
    the validation files in R2 without restarting the backend service.
    
    Returns:
        JSON response with detailed statistics and status
    """
    try:
        if not nhs_lookup_engine:
            return jsonify({
                'status': 'error',
                'error': 'NHS lookup engine not available',
                'timestamp': time.time()
            }), 500
        
        # Call the reload method on the NHS lookup engine
        result = nhs_lookup_engine.reload_validation_caches()
        
        # Return appropriate HTTP status code based on result
        if result.get('status') == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Failed to reload validation cache via admin endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': time.time()
        }), 500

@app.route('/config/status', methods=['GET'])
def config_status():
    """Get configuration source and cache status."""
    try:
        from config_manager import get_config
        config_manager = get_config()
        
        # Check if R2 config is cached
        r2_cached = config_manager._r2_config_cache is not None
        cache_age = 0
        if r2_cached:
            cache_age = time.time() - config_manager._r2_config_cache_time
            
        return jsonify({
            'r2_url': config_manager._r2_config_url,
            'r2_cached': r2_cached,
            'cache_age_seconds': int(cache_age),
            'cache_ttl_seconds': config_manager._r2_config_ttl,
            'cache_valid': cache_age < config_manager._r2_config_ttl if r2_cached else False,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Config status endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Failed to get config status"}), 500

@app.route('/config_rebuild_status', methods=['GET'])
def get_config_rebuild_status():
    """Get the current status of config upload and cache rebuild."""
    try:
        from config_status_manager import status_manager
        status = status_manager.get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Config rebuild status endpoint error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Failed to get rebuild status",
            "progress": 0,
            "timestamp": datetime.utcnow().isoformat(),
            "details": {"error": str(e)}
        }), 500

@app.route('/upload_config', methods=['POST'])
def upload_config():
    """Upload a new config.yaml file, save it temporarily, and trigger the upload/rebuild script."""
    try:
        if 'config' not in request.files:
            return jsonify({"error": "No config file provided"}), 400
        
        config_file = request.files['config']
        if config_file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not config_file.filename.lower().endswith(('.yaml', '.yml')):
            return jsonify({"error": "File must be a YAML file (.yaml or .yml)"}), 400
        
        # Save to a temporary file
        import tempfile
        import uuid
        import subprocess
        temp_dir = tempfile.gettempdir()
        temp_filename = f"config_{uuid.uuid4().hex}.yaml"
        temp_filepath = os.path.join(temp_dir, temp_filename)
        
        config_file.save(temp_filepath)
        logger.info(f"Uploaded config file saved temporarily to: {temp_filepath}")

        # Trigger the upload and rebuild script in a background thread
        def run_upload_script():
            try:
                logger.info(f"Starting config upload and cache rebuild for {temp_filepath}...")
                script_path = os.path.join(os.path.dirname(__file__), 'upload_config_to_r2.py')
                
                result = subprocess.run(
                    [sys.executable, script_path, temp_filepath],
                    capture_output=True, text=True, timeout=1800, check=True
                )
                
                logger.info("Config upload and cache rebuild script finished successfully.")
                logger.info(f"Script output:\n{result.stdout}")

            except subprocess.CalledProcessError as e:
                logger.error(f"Config upload script failed with return code {e.returncode}. stderr:\n{e.stderr}")
            except subprocess.TimeoutExpired:
                logger.error("Config upload script timed out after 30 minutes.")
            except Exception as e:
                logger.error(f"An error occurred running the upload script: {e}")
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                    logger.info(f"Cleaned up temporary config file: {temp_filepath}")

        # Start the script in a background thread
        script_thread = threading.Thread(target=run_upload_script, daemon=True)
        script_thread.start()

        return jsonify({
            "message": "Config upload process initiated. The cache will be rebuilt in the background.",
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Config upload endpoint error: {e}", exc_info=True)
        return jsonify({"error": f"Failed to upload config: {str(e)}"}), 500

@app.route('/config/current', methods=['GET'])
def get_current_config():
    """Fetch the current config.yaml file from R2."""
    try:
        import requests
        
        # Use the same R2 URL as config manager
        r2_config_url = "https://pub-cc78b976831e4f649dd695ffa52d1171.r2.dev/config/config.yaml"
        
        logger.info(f"Fetching current config from R2: {r2_config_url}")
        response = requests.get(r2_config_url, timeout=10)
        response.raise_for_status()
        
        # Return the raw YAML content
        return jsonify({
            "config_yaml": response.text,
            "timestamp": datetime.now().isoformat(),
            "message": "Config fetched successfully from R2"
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch config from R2: {e}")
        return jsonify({"error": f"Failed to fetch config from R2: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Config fetch endpoint error: {e}", exc_info=True)
        return jsonify({"error": f"Failed to fetch config: {str(e)}"}), 500

@app.route('/config/update', methods=['POST'])
def update_config():
    """Update the config.yaml file by saving new content to R2."""
    try:
        # Get the YAML content from request body
        data = request.get_json()
        if not data or 'config_yaml' not in data:
            return jsonify({"error": "Missing 'config_yaml' in request body"}), 400
        
        config_yaml_content = data['config_yaml']
        
        # Validate YAML syntax and check for problematic characters
        try:
            import yaml
            
            # Check for problematic Unicode characters
            problematic_chars = []
            for i, char in enumerate(config_yaml_content):
                char_code = ord(char)
                # Check for common problematic Unicode characters
                if char_code in [0x0086, 0x0087, 0x0088, 0x0089, 0x008A, 0x008B, 0x008C, 0x008D, 0x008E, 0x008F]:
                    problematic_chars.append((i, char, hex(char_code)))
                # Check for smart quotes and other common issues
                elif char_code in [0x201C, 0x201D, 0x2018, 0x2019, 0x2013, 0x2014]:
                    problematic_chars.append((i, char, f"smart quote/dash {hex(char_code)}"))
            
            if problematic_chars:
                error_msg = f"Found {len(problematic_chars)} problematic characters: "
                for pos, char, desc in problematic_chars[:3]:  # Show first 3
                    error_msg += f"position {pos} ('{char}' - {desc}), "
                error_msg = error_msg.rstrip(", ")
                logger.error(f"Character validation failed: {error_msg}")
                return jsonify({"error": f"Invalid characters found: {error_msg}"}), 400
            
            # Validate YAML structure
            yaml.safe_load(config_yaml_content)
            logger.info("YAML validation passed")
            
        except yaml.YAMLError as e:
            logger.error(f"YAML validation failed: {e}")
            return jsonify({"error": f"Invalid YAML syntax: {str(e)}"}), 400
        
        # Save to a temporary file and trigger the upload script (reuse existing logic)
        import tempfile
        import uuid
        import subprocess
        import threading
        
        temp_dir = tempfile.gettempdir()
        temp_filename = f"config_editor_{uuid.uuid4().hex}.yaml"
        temp_filepath = os.path.join(temp_dir, temp_filename)
        
        # Write the YAML content to temp file
        with open(temp_filepath, 'w', encoding='utf-8') as f:
            f.write(config_yaml_content)
        
        logger.info(f"Config editor content saved temporarily to: {temp_filepath}")

        # Trigger the upload and rebuild script in a background thread (same as upload_config)
        def run_upload_script():
            try:
                logger.info(f"Starting config update and cache rebuild for {temp_filepath}...")
                script_path = os.path.join(os.path.dirname(__file__), 'upload_config_to_r2.py')
                
                # Run the upload script with the temporary file
                result = subprocess.run([
                    'python3', script_path, temp_filepath
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    logger.info("✅ Config update and cache rebuild completed successfully")
                    logger.info(f"Script output: {result.stdout}")
                else:
                    logger.error(f"❌ Config update script failed with return code {result.returncode}")
                    logger.error(f"STDOUT: {result.stdout}")
                    logger.error(f"STDERR: {result.stderr}")

            except subprocess.TimeoutExpired:
                logger.error("⏰ Config update script timed out after 5 minutes")
            except Exception as e:
                logger.error(f"💥 Config update script error: {e}")
            finally:
                # Clean up temporary file
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                    logger.info(f"Cleaned up temporary config file: {temp_filepath}")

        # Start the script in a background thread
        script_thread = threading.Thread(target=run_upload_script, daemon=True)
        script_thread.start()

        return jsonify({
            "message": "Config update process initiated. The cache will be rebuilt in the background.",
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Config update endpoint error: {e}", exc_info=True)
        return jsonify({"error": f"Failed to update config: {str(e)}"}), 500

def _medical_title_case(text: str) -> str:
    """
    Convert text to proper medical title case with special rules.
    """
    modalities = {
        'ct', 'mri', 'mr', 'us', 'xr', 'pet', 'nm', 'dexa', 'dxa', 
        'mg', 'ir', 'picc', 'hrct', 'mrcp', 'cta', 'mra'
    }
    lowercase_words = {
        'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'without',
        'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'between', 'among', 'a', 'an', 'the'
    }
    laterality_expansions = {
        'rt': 'Right', 'lt': 'Left', 'both': 'Both', 'bilateral': 'Both'
    }
    
    words = text.split()
    result_words = []
    
    for i, word in enumerate(words):
        clean_word = re.sub(r'[^\w]', '', word.lower())
        
        if clean_word in modalities:
            result_words.append(word.upper())
        elif clean_word in laterality_expansions:
            result_words.append(laterality_expansions[clean_word])
        elif clean_word in lowercase_words and i > 0:
            result_words.append(word.lower())
        else:
            result_words.append(word.capitalize())
    
    return ' '.join(result_words)

def _get_model_description(model_key: str) -> str:
    """Get description for each model type"""
    descriptions = {
        'default': 'BioLORD - Advanced biomedical language model with superior medical concept understanding (preferred default)',
        'experimental': 'MedCPT - NCBI Medical Clinical Practice Text encoder (experimental)'
    }
    return descriptions.get(model_key, 'No description available')

@app.route('/parse_enhanced', methods=['POST'])
def parse_enhanced():
    """Enhanced parsing endpoint for single exam processing"""
    _ensure_app_is_initialized()
    _refresh_validation_caches()  # Refresh validation caches for latest human feedback
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name in request data"}), 400
        
        exam_name = data['exam_name']
        modality_code = data.get('modality_code')
        data_source = data.get('data_source')
        exam_code = data.get('exam_code')
        model = data.get('model', 'retriever')
        reranker_key = data.get('reranker', reranker_manager.get_default_reranker_key() if reranker_manager else 'medcpt')
        debug = data.get('debug', False)  # Add debug parameter
        
        selected_nlp_processor = _get_nlp_processor(model)
        if not selected_nlp_processor:
            return jsonify({"error": f"Model '{model}' not available"}), 400
        
        logger.info(f"Using model '{model}' for exam: {exam_name}")
        
        # Perform preflight checking using validation caches
        request_hash, preimage = compute_request_hash_with_preimage(data_source, exam_code, exam_name, modality_code)
        
        if debug:
            logger.info(f"[DEBUG-PREFLIGHT] Request hash: {request_hash}")
            logger.info(f"[DEBUG-PREFLIGHT] Preimage: {preimage}")
        
        # Check if this request has been cached
        cached_approved = None
        cached_rejected = None
        if validation_cache_manager and validation_cache_manager.is_available():
            cached_approved = validation_cache_manager.check_approved(request_hash)
            cached_rejected = validation_cache_manager.check_rejected(request_hash)
        
        # Handle rejected cache (strict skip)
        if cached_rejected:
            logger.info(f"[PREFLIGHT-SKIP] Request rejected from cache: {request_hash}")
            result = {
                'error': 'PREFLIGHT_REJECTED',
                'message': cached_rejected['reason'],
                'exam_name': exam_name,
                'cached_skip': True,
                'cache_type': 'rejected',
                'request_hash': request_hash
            }
            result['metadata'] = {
                'processing_time_ms': int((time.time() - start_time) * 1000),
                'model_used': model,
                'reranker_used': reranker_key,
                'preflight_skipped': True
            }
            return jsonify(result)
        
        # Handle approved cache (return cached result with confidence unchanged)
        if cached_approved:
            logger.info(f"[PREFLIGHT-SKIP] Request approved from cache: {request_hash}")
            result = cached_approved['result'].copy()
            result['cached_skip'] = True
            result['cache_type'] = 'approved'
            result['request_hash'] = request_hash
            result['metadata'] = {
                'processing_time_ms': int((time.time() - start_time) * 1000),
                'model_used': model,
                'reranker_used': reranker_key,
                'preflight_skipped': True
            }
            return jsonify(result)
        
        result = process_exam_request(exam_name, modality_code, selected_nlp_processor, debug=debug, reranker_key=reranker_key, data_source=data_source, exam_code=exam_code)
        
        # Add transparent flags to indicate this was NOT a cached result
        result['cached_skip'] = False
        result['cache_type'] = None
        result['request_hash'] = request_hash
        
        result['metadata'] = {
            'processing_time_ms': int((time.time() - start_time) * 1000),
            'model_used': model,
            'reranker_used': reranker_key,
            'preflight_skipped': False
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Parse enhanced endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

def _perform_preflight_check(exam_dict, model_key, reranker_key, debug=False):
    """
    Perform preflight checking for a single exam using validation caches.
    
    Args:
        exam_dict: Dictionary containing exam data (exam_name, modality_code, data_source, exam_code)
        model_key: Model key for metadata
        reranker_key: Reranker key for metadata  
        debug: Whether to enable debug logging
        
    Returns:
        Tuple of (cache_result, is_cache_hit, request_hash)
        - cache_result: Complete result dict if cache hit, None if no cache hit
        - is_cache_hit: Boolean indicating if cache was hit
        - request_hash: The computed request hash for this exam
    """
    # Extract exam data with flexible field names
    exam_name = exam_dict.get("EXAM_NAME") or exam_dict.get("exam_name")
    modality_code = exam_dict.get("MODALITY_CODE") or exam_dict.get("modality_code")
    data_source = exam_dict.get("DATA_SOURCE") or exam_dict.get("data_source")
    exam_code = exam_dict.get("EXAM_CODE") or exam_dict.get("exam_code")
    
    if not exam_name:
        return None, False, None
        
    # Compute request hash for preflight checking
    request_hash, preimage = compute_request_hash_with_preimage(data_source, exam_code, exam_name, modality_code)
    
    if debug:
        logger.info(f"[DEBUG-PREFLIGHT-BATCH] Request hash: {request_hash} for exam: {exam_name}")
        logger.info(f"[DEBUG-PREFLIGHT-BATCH] Preimage: {preimage}")
    
    # Check validation caches
    cached_approved = None
    cached_rejected = None
    if validation_cache_manager and validation_cache_manager.is_available():
        cached_approved = validation_cache_manager.check_approved(request_hash)
        cached_rejected = validation_cache_manager.check_rejected(request_hash)
    
    # Handle rejected cache (strict skip)
    if cached_rejected:
        logger.info(f"[PREFLIGHT-SKIP-BATCH] Request rejected from cache: {request_hash}")
        result = {
            'error': 'PREFLIGHT_REJECTED',
            'message': cached_rejected['reason'],
            'exam_name': exam_name,
            'cached_skip': True,
            'cache_type': 'rejected',
            'request_hash': request_hash,
            'metadata': {
                'processing_time_ms': 0,  # Immediate rejection
                'model_used': model_key,
                'reranker_used': reranker_key,
                'preflight_skipped': True
            }
        }
        return result, True, request_hash
    
    # Handle approved cache (return cached result)
    if cached_approved:
        logger.info(f"[PREFLIGHT-SKIP-BATCH] Request approved from cache: {request_hash}")
        result = cached_approved['result'].copy()
        result['cached_skip'] = True
        result['cache_type'] = 'approved'
        result['request_hash'] = request_hash
        result['metadata'] = {
            'processing_time_ms': 0,  # Immediate cache hit
            'model_used': model_key,
            'reranker_used': reranker_key,
            'preflight_skipped': True
        }
        return result, True, request_hash
    
    # No cache hit - return hash for transparent flagging
    return None, False, request_hash


def _process_batch(data, start_time):
    """Helper function to process a batch of exams."""
    if not data or 'exams' not in data:
        return jsonify({"error": "Missing 'exams' list in request data"}), 400
    
    exams_to_process = data['exams']
    model_key = data.get('model', 'retriever')
    reranker_key = data.get('reranker', reranker_manager.get_default_reranker_key() if reranker_manager else 'medcpt')
    enable_secondary = data.get('enable_secondary_pipeline', False)
    
    import uuid
    # Use persistent disk if available, otherwise fall back to local directory
    output_dir = os.environ.get('RENDER_DISK_PATH', 'batch_outputs')
    os.makedirs(output_dir, exist_ok=True)
    batch_id = uuid.uuid4().hex
    results_filename = f"batch_results_{batch_id}.jsonl"
    results_filepath = os.path.join(output_dir, results_filename)
    progress_filename = f"batch_progress_{batch_id}.json"
    progress_filepath = os.path.join(output_dir, progress_filename)
    
    logger.info(f"Starting batch processing for {len(exams_to_process)} exams using model: '{model_key}', reranker: '{reranker_key}' (preflight checking enabled)")
    logger.info(f"Results will be streamed to: {results_filepath}")
    logger.info(f"Progress will be tracked at: {progress_filepath}")
    logger.info(f"RENDER_DISK_PATH environment variable: {os.environ.get('RENDER_DISK_PATH', 'NOT_SET')}")
    logger.info(f"Using output directory: {output_dir}")
    
    def update_progress(processed, total, success, errors):
        """Update progress file with current status"""
        progress_data = {
            "processed": processed,
            "total": total,
            "success": success,
            "errors": errors,
            "percentage": round((processed / total) * 100, 1) if total > 0 else 0,
            "timestamp": datetime.now().isoformat()
        }
        try:
            with open(progress_filepath, 'w') as pf:
                json.dump(progress_data, pf)
        except Exception as e:
            logger.error(f"Failed to update progress file: {e}")

    selected_nlp_processor = _get_nlp_processor(model_key)
    if not selected_nlp_processor:
        return jsonify({"error": f"Model '{model_key}' not available"}), 400

    success_count = 0
    error_count = 0
    cache_hits_count = 0
    cache_rejects_count = 0
    
    # Pre-load config once for the entire batch to avoid repeated R2 fetches during secondary pipeline processing
    global _batch_preloaded_config
    _batch_preloaded_config = None
    if enable_secondary and SECONDARY_PIPELINE_AVAILABLE:
        try:
            from config_manager import get_config
            config_manager = get_config()
            if config_manager.force_r2_reload():
                _batch_preloaded_config = config_manager.get_full_config()
                logger.info("Pre-loaded configuration from R2 for batch processing (will be reused for secondary pipeline)")
            else:
                logger.warning("Failed to pre-load config from R2, secondary pipeline will load individually")
        except Exception as e:
            logger.warning(f"Could not pre-load config from R2 ({e}), secondary pipeline will load individually")
    
    chunk_size = 10
    total_exams = len(exams_to_process)
    chunks = [exams_to_process[i:i + chunk_size] for i in range(0, total_exams, chunk_size)]
    
    update_progress(0, total_exams, 0, 0)
    
    cpu_cnt = os.cpu_count() or 1
    max_workers = min(2, max(1, cpu_cnt))
    logger.info(f"Processing {total_exams} exams in {len(chunks)} chunks of {chunk_size}")
    logger.info(f"ThreadPoolExecutor using max_workers={max_workers}")

    with open(results_filepath, 'w', encoding='utf-8') as f_out:
        for chunk_idx, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {chunk_idx + 1}/{len(chunks)} ({len(chunk)} exams)")
            
            # Perform preflight checking for all exams in this chunk
            cached_results = []
            exams_for_processing = []
            exam_hash_map = {}  # Map original exam to its hash for transparent flagging
            
            for exam in chunk:
                cache_result, is_cache_hit, request_hash = _perform_preflight_check(exam, model_key, reranker_key)
                
                if is_cache_hit:
                    # Handle cache hit immediately
                    result_entry = {
                        "input": exam,
                        "output": cache_result,
                        "status": "success"
                    }
                    cached_results.append(result_entry)
                    success_count += 1
                    cache_hits_count += 1
                    
                    # Track rejection vs approval caches
                    if cache_result.get('error') == 'PREFLIGHT_REJECTED':
                        cache_rejects_count += 1
                else:
                    # No cache hit - add to processing queue
                    exams_for_processing.append(exam)
                    if request_hash:
                        exam_hash_map[id(exam)] = request_hash
            
            # Write all cached results first
            for cached_entry in cached_results:
                f_out.write(json.dumps(cached_entry) + '\n')
                f_out.flush()
            
            logger.info(f"Chunk {chunk_idx + 1}: {len(cached_results)} cache hits, {len(exams_for_processing)} to process")
            
            # Only process exams that weren't cached
            if exams_for_processing:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_exam = {
                        executor.submit(
                            process_exam_request, 
                            exam.get("EXAM_NAME") or exam.get("exam_name"), 
                            exam.get("MODALITY_CODE") or exam.get("modality_code"), 
                            selected_nlp_processor, 
                            False, 
                            reranker_key, 
                            exam.get("DATA_SOURCE") or exam.get("data_source"), 
                            exam.get("EXAM_CODE") or exam.get("exam_code"),
                            run_secondary_inline=False
                        ): exam 
                        for exam in exams_for_processing
                    }
                    
                    chunk_completed = 0
                    per_future_timeout = 60

                    for future in as_completed(future_to_exam):
                        original_exam = future_to_exam[future]
                        try:
                            processed_result = future.result(timeout=per_future_timeout)
                            
                            # Add transparent flags for non-cached results
                            processed_result['cached_skip'] = False
                            processed_result['cache_type'] = None
                            request_hash = exam_hash_map.get(id(original_exam))
                            if request_hash:
                                processed_result['request_hash'] = request_hash
                            if 'metadata' not in processed_result:
                                processed_result['metadata'] = {}
                            processed_result['metadata']['preflight_skipped'] = False
                            
                            result_entry = {
                                "input": original_exam,
                                "output": processed_result,
                                "status": "success"
                            }
                            f_out.write(json.dumps(result_entry) + '\n')
                            f_out.flush()
                            success_count += 1
                        except Exception as e:
                            logger.error(f"Error processing exam '{original_exam.get('exam_name')}': {e}", exc_info=True)
                            error_entry = {
                                "input": original_exam,
                                "error": str(e),
                                "status": "error"
                            }
                            f_out.write(json.dumps(error_entry) + '\n')
                            f_out.flush()
                            error_count += 1
                        finally:
                            chunk_completed += 1
                            update_progress(success_count + error_count, total_exams, success_count, error_count)
            
            # Update progress for the entire chunk (including cached results)
            update_progress(success_count + error_count, total_exams, success_count, error_count)
            
            logger.info(f"Completed chunk {chunk_idx + 1}/{len(chunks)}: {len(cached_results)} cached, {len(exams_for_processing)} processed")
            logger.info(f"Overall progress: {success_count + error_count}/{total_exams} exams processed")

    processing_time_ms = int((time.time() - start_time) * 1000)
    logger.info(f"Batch processing finished in {processing_time_ms}ms. Success: {success_count}, Errors: {error_count}")
    logger.info(f"Cache performance: {cache_hits_count} total hits ({cache_rejects_count} rejects, {cache_hits_count - cache_rejects_count} approvals)")
    
    cache_hit_rate = (cache_hits_count / total_exams * 100) if total_exams > 0 else 0
    logger.info(f"Cache hit rate: {cache_hit_rate:.1f}% ({cache_hits_count}/{total_exams})")
    
    try:
        if os.path.exists(progress_filepath):
            os.remove(progress_filepath)
            logger.info(f"Cleaned up progress file: {progress_filename}")
    except Exception as e:
        logger.warning(f"Failed to clean up progress file: {e}")

    r2_upload_success = False
    r2_url = None
    consolidated_filepath = None

    if r2_manager.is_available():
        try:
            from config_manager import get_config
            config_manager = get_config()
            config_source = "R2" if config_manager._r2_config_cache else "local"
            config_timestamp = datetime.fromtimestamp(config_manager._r2_config_cache_time).isoformat() if config_manager._r2_config_cache else "unknown"

            metadata = {
                "timestamp": datetime.now().isoformat(),
                "total_processed": total_exams,
                "successful": success_count,
                "errors": error_count,
                "processing_time_ms": processing_time_ms,
                "model_used": model_key,
                "reranker_used": reranker_key,
                "config_source": config_source,
                "config_timestamp": config_timestamp
            }

            # Create a new file for the consolidated JSON to stream into
            consolidated_filename = f"consolidated_{results_filename.replace('.jsonl', '.json')}"
            consolidated_filepath = os.path.join(output_dir, consolidated_filename)

            logger.info(f"Streaming results to consolidated file: {consolidated_filepath}")
            with open(consolidated_filepath, 'w', encoding='utf-8') as f_out:
                f_out.write('{"metadata": ')
                json.dump(metadata, f_out)
                f_out.write(', "results": [')

                # Stream-read the JSONL and write to the new JSON file
                with open(results_filepath, 'r', encoding='utf-8') as f_in:
                    first = True
                    for line in f_in:
                        if line.strip():
                            if not first:
                                f_out.write(',')
                            f_out.write(line.strip())
                            first = False
                
                f_out.write(']}')
            
            logger.info("Consolidated file created successfully.")

            # Consolidated file ready for R2 upload
            logger.info("Consolidated file created and ready for R2 upload")

        except Exception as e:
            logger.error(f"Error during R2 upload process: {e}", exc_info=True)
    else:
        logger.warning("R2 not available - results only stored locally")

    secondary_report = None
    merged_filepath = None
    
    if enable_secondary and SECONDARY_PIPELINE_AVAILABLE:
        _initialize_secondary_pipeline()
        if secondary_integration and secondary_integration.is_enabled():
            logger.info("Starting secondary pipeline processing for the entire batch...")
            
            # 1. Load all results from the primary processing stage
            all_results = []
            if os.path.exists(results_filepath):
                with open(results_filepath, 'r', encoding='utf-8') as f_in:
                    for line in f_in:
                        if line.strip():
                            all_results.append(json.loads(line.strip()))
            
            if all_results:
                try:
                    # 2. Trigger secondary processing ONCE with all results
                    # The integration layer will filter for low-confidence items internally
                    secondary_report = run_async_task(
                        secondary_integration.trigger_secondary_processing(all_results)
                    )
                    
                    # 3. If there were improvements, merge them into a new file
                    if secondary_report and secondary_report.get('results'):
                        logger.info("Merging secondary pipeline improvements into final results...")
                        
                        # Load the original consolidated data to modify it
                        with open(consolidated_filepath, 'r', encoding='utf-8') as f:
                            original_data = json.load(f)
                        
                        # Create a map for efficient lookups
                        results_map = {res['input']['exam_name']: res for res in original_data['results'] if 'exam_name' in res.get('input', {})}
                        
                        for secondary_res_dict in secondary_report['results']:
                            # The original result is nested inside the ensemble result
                            original_full_record = secondary_res_dict.get('original_result', {})
                            exam_name = original_full_record.get('input', {}).get('exam_name')
                            
                            if exam_name and exam_name in results_map:
                                result_to_update = results_map[exam_name]
                                output_to_update = result_to_update['output']

                                # Overwrite with improved data
                                output_to_update['clean_name'] = secondary_res_dict['consensus_best_match_procedure_name']
                                output_to_update['snomed']['id'] = secondary_res_dict['consensus_best_match_snomed_id']
                                output_to_update['snomed']['fsn'] = secondary_res_dict.get('consensus_snomed_fsn')
                                output_to_update['components']['confidence'] = secondary_res_dict['consensus_confidence']
                                
                                # Add metadata for transparency
                                output_to_update['secondary_pipeline_applied'] = True
                                output_to_update['secondary_pipeline_details'] = {
                                    'improved': secondary_res_dict.get('improved', False),
                                    'original_confidence': secondary_res_dict.get('original_result', {}).get('output', {}).get('components', {}).get('confidence'),
                                    'consensus_confidence': secondary_res_dict.get('consensus_confidence'),
                                    'agreement_score': secondary_res_dict.get('agreement_score'),
                                }
                        
                        # Reconstruct the results list and save to a new merged file
                        original_data['results'] = list(results_map.values())
                        merged_filepath = consolidated_filepath.replace('.json', '_merged.json')
                        with open(merged_filepath, 'w', encoding='utf-8') as f:
                            json.dump(original_data, f, indent=2)
                        
                        logger.info(f"Successfully merged results into: {merged_filepath}")
                        
                except Exception as e:
                    logger.error(f"Secondary pipeline batch processing failed: {e}", exc_info=True)
                    secondary_report = {"error": str(e)}

    # Upload the consolidated file to R2
    final_upload_path = merged_filepath if merged_filepath else consolidated_filepath
    if r2_manager and final_upload_path and os.path.exists(final_upload_path):
        try:
            final_filename = os.path.basename(consolidated_filepath)
            r2_key = f"batch-results/{final_filename}"
            if r2_manager.upload_file(final_upload_path, r2_key, content_type="application/json"):
                r2_url = f"https://pub-cc78b976831e4f649dd695ffa52d1171.r2.dev/{r2_key}"
                r2_upload_success = True
                logger.info(f"Successfully uploaded final results to R2: {r2_key}")
            else:
                logger.warning(f"Failed to upload final results to R2: {r2_key}")
        except Exception as e:
            logger.error(f"Error during final R2 upload: {e}", exc_info=True)

    # Cleanup temporary files (keep merged files for R2 upload)
    try:
        if os.path.exists(results_filepath):
            os.remove(results_filepath)
            logger.info(f"Cleaned up temporary results file: {results_filepath}")
        # Keep consolidated file for R2 upload success verification
    except Exception as e:
        logger.warning(f"Failed to clean up temporary files: {e}")

    # Always return the R2 URL if available, otherwise return a message.
    # Avoid returning in-memory results or file references to deleted files.
    logger.info(f"Batch processing complete. Returning response with R2 URL: {r2_url}")
    
    response_data = {
        "message": "Batch processing complete. Results are available at the provided R2 URL." + (" Secondary pipeline applied inline to low-confidence results." if enable_secondary else ""),
        "batch_id": batch_id,
        "r2_url": r2_url,
        "r2_uploaded": r2_upload_success,
        "processing_stats": {
            "total_processed": total_exams,
            "successful": success_count,
            "errors": error_count,
            "processing_time_ms": processing_time_ms,
            "model_used": model_key,
            "reranker_used": reranker_key,
            "secondary_pipeline_enabled": enable_secondary and SECONDARY_PIPELINE_AVAILABLE and secondary_integration and secondary_integration.is_enabled(),
            "cache_hits": cache_hits_count,
            "cache_rejects": cache_rejects_count,
            "cache_approvals": cache_hits_count - cache_rejects_count,
            "cache_hit_rate": (cache_hits_count / total_exams * 100) if total_exams > 0 else 0,
            "preflight_enabled": True
        },
        "secondary_pipeline_summary": "Secondary pipeline processing handled inline per exam" if enable_secondary else None
    }
    
    return jsonify(response_data)

@app.route('/parse_batch', methods=['POST', 'OPTIONS'])
def parse_batch():
    """
    Processes a batch of exam names concurrently with streaming output to disk.
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    _ensure_app_is_initialized()
    _refresh_validation_caches()  # Refresh validation caches for latest human feedback
    start_time = time.time()
    
    try:
        return _process_batch(request.json, start_time)
    except Exception as e:
        logger.error(f"Batch endpoint failed with a critical error: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred during batch processing"}), 500

@app.route('/batch_progress/<batch_id>', methods=['GET'])
def get_batch_progress(batch_id):
    """
    Get progress for a specific batch processing job.
    Returns progress information from the progress file.
    """
    try:
        # Use the same dedicated directory as batch processing for temporary files
        output_dir = 'batch_outputs'
        progress_filename = f"batch_progress_{batch_id}.json"
        progress_filepath = os.path.join(output_dir, progress_filename)
        
        logger.info(f"Polling for batch_id: {batch_id}")
        logger.info(f"Looking for progress file at: {progress_filepath}")
        logger.info(f"RENDER_DISK_PATH environment variable: {os.environ.get('RENDER_DISK_PATH', 'NOT_SET')}")
        logger.info(f"Using output directory: {output_dir}")
        
        if not os.path.exists(progress_filepath):
            logger.info(f"Progress file not found at: {progress_filepath}")
            return jsonify({"error": "Progress not found or batch completed"}), 404
        
        with open(progress_filepath, 'r') as pf:
            progress_data = json.load(pf)
        
        return jsonify(progress_data)
        
    except Exception as e:
        logger.error(f"Error fetching batch progress: {e}")
        return jsonify({"error": "Failed to fetch progress"}), 500


@app.route('/load_batch_chunk/<filename>', methods=['GET'])
def load_batch_chunk(filename):
    """
    Load a chunk of batch processing results for pagination.
    """
    try:
        if not filename.startswith('batch_results_') or not filename.endswith('.jsonl'):
            return jsonify({"error": "Invalid filename format"}), 400
        
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 100))
        sort_by = request.args.get('sort_by', 'default')
        sort_order = request.args.get('sort_order', 'asc')
        
        limit = min(limit, 500)
        
        output_dir = os.environ.get('RENDER_DISK_PATH', 'batch_outputs')
        file_path = os.path.join(output_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
        
        results = []
        with open(file_path, 'r', encoding='utf-8') as f_in:
            for line in f_in:
                if line.strip():
                    results.append(json.loads(line.strip()))
        
        if sort_by == 'confidence':
            results.sort(key=lambda x: x.get('output', {}).get('components', {}).get('confidence', 0), 
                        reverse=(sort_order == 'desc'))
        elif sort_by == 'name':
            results.sort(key=lambda x: x.get('output', {}).get('clean_name', ''), 
                        reverse=(sort_order == 'desc'))
        
        total_items = len(results)
        paginated_results = results[offset:offset + limit]
        
        return jsonify({
            "results": paginated_results,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total_items": total_items,
                "total_pages": math.ceil(total_items / limit) if limit > 0 else 0,
                "current_page": math.floor(offset / limit) + 1 if limit > 0 else 1
            }
        })
        
    except Exception as e:
        logger.error(f"Error loading batch chunk: {e}", exc_info=True)
        return jsonify({"error": "Failed to load batch chunk"}), 500

@app.route('/get_batch_results/<filename>', methods=['GET'])
def get_batch_results(filename):
    """
    Get batch processing results as JSON array for frontend consumption.
    """
    try:
        if not filename.startswith('batch_results_') or not filename.endswith('.jsonl'):
            return jsonify({"error": "Invalid filename format"}), 400
        
        output_dir = os.environ.get('RENDER_DISK_PATH', 'batch_outputs')
        file_path = os.path.join(output_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
        
        # Read and parse JSONL file
        results = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line.strip()))
        
        logger.info(f"Serving {len(results)} results from local file: {filename}")
        return jsonify({"results": results})
        
    except Exception as e:
        logger.error(f"Error serving batch results: {e}", exc_info=True)
        return jsonify({"error": "Failed to load results"}), 500

@app.route('/download_batch_results/<filename>', methods=['GET'])
def download_batch_results(filename):
    """
    Download batch processing results file by filename.
    """
    try:
        if not filename.startswith('batch_results_') or not filename.endswith('.jsonl'):
            return jsonify({"error": "Invalid filename format"}), 400
        
        output_dir = os.environ.get('RENDER_DISK_PATH', 'batch_outputs')
        file_path = os.path.join(output_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/x-jsonlines'
        )
        
    except Exception as e:
        logger.error(f"Error downloading batch results: {e}", exc_info=True)
        return jsonify({"error": "Failed to download file"}), 500

@app.route('/list_batch_results', methods=['GET'])
def list_batch_results():
    """
    List all available batch results files, sorted by modification time (newest first).
    Returns metadata including filename, creation time, and file size.
    """
    try:
        output_dir = os.environ.get('RENDER_DISK_PATH', 'batch_outputs')
        
        if not os.path.exists(output_dir):
            return jsonify({"files": []})
        
        batch_files = []
        for filename in os.listdir(output_dir):
            if filename.startswith('batch_results_') and filename.endswith('.jsonl'):
                file_path = os.path.join(output_dir, filename)
                if os.path.isfile(file_path):
                    try:
                        stat = os.stat(file_path)
                        batch_files.append({
                            "filename": filename,
                            "modified_time": stat.st_mtime,
                            "created_time": stat.st_ctime,
                            "size_bytes": stat.st_size,
                            "modified_iso": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "created_iso": datetime.fromtimestamp(stat.st_ctime).isoformat()
                        })
                    except OSError as e:
                        logger.warning(f"Could not get stats for file {filename}: {e}")
                        continue
        
        # Sort by modification time, newest first
        batch_files.sort(key=lambda x: x['modified_time'], reverse=True)
        
        return jsonify({
            "files": batch_files,
            "total_count": len(batch_files),
            "most_recent": batch_files[0]["filename"] if batch_files else None
        })
        
    except Exception as e:
        logger.error(f"Error listing batch results: {e}", exc_info=True)
        return jsonify({"error": "Failed to list batch results"}), 500

@app.route('/random_sample', methods=['POST'])
def random_sample():
    """
    Random sample endpoint that downloads hnz_hdp_json from R2, takes a random sample of codes,
    and passes them to the batch processing endpoint.
    """
    _ensure_app_is_initialized()
    _refresh_validation_caches()  # Refresh validation caches for latest human feedback
    start_time = time.time()
    
    try:
        data = request.json or {}
        model_key = data.get('model', 'retriever')
        reranker_key = data.get('reranker', reranker_manager.get_default_reranker_key() if reranker_manager else 'medcpt')
        enable_secondary = data.get('enable_secondary_pipeline', False)
        sample_size = data.get('sample_size', 100)  # Default to 100 if not provided
        
        # Validate sample_size
        try:
            sample_size = int(sample_size)
            if sample_size < 1 or sample_size > 1000:
                return jsonify({"error": "Sample size must be between 1 and 1000"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Sample size must be a valid integer"}), 400
        
        logger.info(f"Starting random sample with model: '{model_key}', reranker: '{reranker_key}', secondary pipeline: {enable_secondary}, sample_size: {sample_size}")
        
        selected_nlp_processor = _get_nlp_processor(model_key)
        if not selected_nlp_processor:
            return jsonify({"error": f"Model '{model_key}' not available"}), 400
        
        if not r2_manager.is_available():
            return jsonify({"error": "R2 storage not available"}), 500
        
        import tempfile
        import random
        import uuid
        
        input_r2_key = "hnz_hdp.json"
        temp_dir = tempfile.gettempdir()
        temp_input_file = os.path.join(temp_dir, f"input_{uuid.uuid4().hex}.json")
        
        logger.info(f"Downloading {input_r2_key} from R2...")
        
        try:
            import requests
            r2_url = f"https://pub-cc78b976831e4f649dd695ffa52d1171.r2.dev/{input_r2_key}"
            response = requests.get(r2_url, timeout=30)
            response.raise_for_status()
            
            with open(temp_input_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info(f"Successfully downloaded input file from R2")
        except Exception as e:
            logger.error(f"Failed to download input file from R2: {e}")
            return jsonify({"error": f"Failed to download input file: {str(e)}"}), 500
        
        try:
            with open(temp_input_file, 'r', encoding='utf-8') as f:
                input_data = json.load(f)
        except Exception as e:
            return jsonify({"error": f"Invalid JSON in input file: {str(e)}"}), 400
        finally:
            if os.path.exists(temp_input_file):
                os.remove(temp_input_file)

        if not isinstance(input_data, list):
            return jsonify({"error": "Input file must contain a JSON array"}), 400
        
        # Use sample_size from request parameter (already extracted above)
        if len(input_data) < sample_size:
            logger.warning(f"Input file contains only {len(input_data)} items, using all")
            sample_size = len(input_data)
        
        random_sample = random.sample(input_data, sample_size)
        logger.info(f"Selected random sample of {len(random_sample)} items from {len(input_data)} total")
        
        # Reformat sample for batch processing
        exams_for_batch = []
        for item in random_sample:
            exam_name = None
            if isinstance(item, dict):
                exam_name = (item.get('exam_name') or 
                               item.get('EXAM_NAME') or 
                               item.get('name') or 
                               item.get('description') or 
                               item.get('title'))
            elif isinstance(item, str):
                exam_name = item
            
            if exam_name:
                exam_entry = {'exam_name': exam_name}
                if isinstance(item, dict):
                    # Handle both uppercase and lowercase field names
                    modality_code = item.get('MODALITY_CODE') or item.get('modality_code')
                    if modality_code:
                        exam_entry['modality_code'] = modality_code
                    
                    data_source = item.get('DATA_SOURCE') or item.get('data_source')
                    if data_source:
                        exam_entry['data_source'] = data_source
                    
                    exam_code = item.get('EXAM_CODE') or item.get('exam_code')
                    if exam_code:
                        exam_entry['exam_code'] = exam_code
                exams_for_batch.append(exam_entry)

        logger.info(f"Passing {len(exams_for_batch)} exams to batch processor with preflight checking enabled.")
        batch_payload = {
            "exams": exams_for_batch,
            "model": model_key,
            "reranker": reranker_key,
            "enable_secondary_pipeline": enable_secondary
        }

        return _process_batch(batch_payload, start_time)

    except Exception as e:
        logger.error(f"Random sample endpoint error: {e}", exc_info=True)
        return jsonify({"error": f"Random sample failed: {str(e)}"}), 500

# =============================================================================
# SECONDARY PIPELINE ROUTES
# =============================================================================

@app.route('/api/secondary-pipeline/status', methods=['GET'])
def secondary_pipeline_status():
    """Get secondary pipeline status and configuration"""
    _initialize_secondary_pipeline()
    
    return jsonify({
        'available': SECONDARY_PIPELINE_AVAILABLE,
        'enabled': secondary_integration.is_enabled() if secondary_integration else False,
        'config': {
            'threshold': app.config.get('SECONDARY_PIPELINE_THRESHOLD', 0.8),
            'concurrency': app.config.get('SECONDARY_PIPELINE_CONCURRENCY', 3),
            'has_api_key': bool(app.config.get('OPENROUTER_API_KEY'))
        },
        'models': ['claude-3.5-sonnet', 'gpt-4-turbo', 'gemini-pro'] if SECONDARY_PIPELINE_AVAILABLE else [],
        'app_initialized': _app_initialized
    })


@app.route('/api/secondary-pipeline/test', methods=['POST'])
def test_secondary_pipeline():
    """Test secondary pipeline with a sample exam"""
    _initialize_secondary_pipeline()
    
    if not secondary_integration or not secondary_integration.is_enabled():
        return jsonify({'error': 'Secondary pipeline not enabled - check OPENROUTER_API_KEY'}), 400
    
    try:
        # Test with a known low-confidence case
        test_cases = [
            {
                'exam_name': 'ERCP',
                'modality': 'FL',
                'confidence': 0.65,
                'similar_exams': [
                    {'name': 'Upper GI', 'modality': 'FL'},
                    {'name': 'Barium Swallow', 'modality': 'FL'}
                ]
            }
        ]
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            report = loop.run_until_complete(
                secondary_integration.trigger_secondary_processing(test_cases)
            )
            return jsonify({
                'message': 'Secondary pipeline test completed',
                'test_exam': 'ERCP',
                'results': report
            })
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Secondary pipeline test error: {e}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# VALIDATION API ENDPOINTS
# =============================================================================
# Human-in-the-Loop validation system endpoints for reviewing and correcting
# mapping decisions from the radiology cleaner pipeline

@app.route('/validation/initialize', methods=['POST'])
def initialize_validation():
    """
    Initialize validation state from export mappings.
    Takes array of mapping objects and creates validation state.
    """
    try:
        data = request.get_json()
        if not data or 'mappings' not in data:
            return jsonify({'error': 'Missing mappings data'}), 400
            
        mappings = data['mappings']
        if not isinstance(mappings, list):
            return jsonify({'error': 'Mappings must be an array'}), 400
            
        logger.info(f"Initializing validation for {len(mappings)} mappings")
        
        # Transform mappings into validation state (similar to frontend logic)
        validation_state = {}
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        for mapping in mappings:
            # Generate mapping ID
            key_string = f"{mapping.get('data_source', '')}-{mapping.get('exam_code', '')}-{mapping.get('exam_name', '')}-{mapping.get('clean_name', '')}"
            mapping_id = key_string.replace(' ', '_').replace('/', '_')[:32]
            
            # Apply attention flags
            flags = []
            confidence = mapping.get('components', {}).get('confidence', 0)
            
            if confidence < 0.85:
                flags.append('low_confidence')
            if mapping.get('ambiguous', False):
                flags.append('ambiguous')
                
            candidates = mapping.get('all_candidates', [])
            if len(candidates) == 1:
                flags.append('singleton_mapping')
            elif len(candidates) > 1:
                top_conf = candidates[0].get('confidence', 0)
                second_conf = candidates[1].get('confidence', 0)
                if top_conf - second_conf > 0.15:
                    flags.append('high_confidence_gap')
                    
            if mapping.get('secondary_pipeline_applied', False):
                flags.append('secondary_pipeline')
            
            validation_state[mapping_id] = {
                'unique_mapping_id': mapping_id,
                'original_mapping': mapping,
                'validation_status': 'pending_review',
                'validator_decision': None,
                'validation_notes': None,
                'needs_attention_flags': flags,
                'timestamp_created': timestamp,
                'timestamp_reviewed': None
            }
        
        logger.info(f"Created validation state for {len(validation_state)} mappings")
        
        return jsonify({
            'success': True,
            'mapping_count': len(validation_state),
            'validation_state': validation_state,
            'summary': {
                'total_mappings': len(validation_state),
                'flagged_mappings': len([v for v in validation_state.values() if v['needs_attention_flags']]),
                'timestamp': timestamp
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to initialize validation: {e}")
        return jsonify({'error': f'Validation initialization failed: {str(e)}'}), 500


@app.route('/validation/decision', methods=['POST'])
def submit_validation_decision():
    """
    Submit a validation decision for a specific mapping.
    Updates the validation state with reviewer decision and notes.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing request data'}), 400
            
        mapping_id = data.get('mapping_id')
        decision = data.get('decision')  # 'approve', 'reject', 'modify'
        notes = data.get('notes', '')
        corrected_mapping = data.get('corrected_mapping')  # For 'modify' decisions
        
        if not mapping_id or not decision:
            return jsonify({'error': 'Missing mapping_id or decision'}), 400
            
        if decision not in ['approve', 'reject', 'modify']:
            return jsonify({'error': 'Invalid decision type'}), 400
            
        logger.info(f"Processing validation decision: {decision} for mapping {mapping_id}")
        
        # In a real implementation, this would update a database or validation store
        # For now, return success with the decision data
        validation_decision = {
            'mapping_id': mapping_id,
            'decision': decision,
            'notes': notes,
            'timestamp_reviewed': datetime.utcnow().isoformat() + 'Z',
            'validation_status': 'reviewed' if decision == 'approve' else 'needs_correction'
        }
        
        if decision == 'modify' and corrected_mapping:
            validation_decision['corrected_mapping'] = corrected_mapping
            
        return jsonify({
            'success': True,
            'validation_decision': validation_decision,
            'message': f'Decision "{decision}" recorded for mapping {mapping_id}'
        })
        
    except Exception as e:
        logger.error(f"Failed to submit validation decision: {e}")
        return jsonify({'error': f'Decision submission failed: {str(e)}'}), 500


@app.route('/validation/batch_decisions', methods=['POST'])
def submit_batch_validation_decisions():
    """
    Submit multiple validation decisions in a single request.
    Accepts array of decision objects and saves them to R2 validation caches.

    Changes:
    - Cache files now have a top-level {"entries": {...}, "meta": {...}} structure.
    - Entries are keyed by request_hash (computed from data_source, exam_code, exam_name, modality_code).
    - Approved entries store 'result' (the full mapping), 'validation_notes', 'approved_at', 'decision_metadata'.
    - Rejected entries store 'reason', 'rejected_at', 'decision_metadata' (and optional 'rejected_snomed_ids').
    - Legacy flat caches from R2 are migrated into the new structure on write.
    """
    try:
        data = request.get_json()
        if not data or 'decisions' not in data:
            return jsonify({'error': 'Missing decisions data'}), 400

        decisions = data['decisions']
        if not isinstance(decisions, list):
            return jsonify({'error': 'Decisions must be an array'}), 400

        logger.info(f"Processing batch validation decisions: {len(decisions)} decisions")

        from r2_cache_manager import R2CacheManager
        r2_manager = R2CacheManager()

        if not r2_manager.is_available():
            logger.error("R2CacheManager not available - validation decisions cannot be saved")
            return jsonify({'error': 'R2 storage not available - decisions cannot be persisted'}), 500

        processed_decisions = []
        approved_items = []
        rejected_items = []
        errors = []

        # Helpers
        def _first_modality(val):
            if isinstance(val, list) and val:
                return val[0]
            return val

        def _compute_request_hash(decision_obj):
            # Prefer explicit fields from decision; fall back to original_mapping when needed
            ds = decision_obj.get('data_source') or decision_obj.get('original_mapping', {}).get('data_source') or ''
            ex_code = decision_obj.get('exam_code') or decision_obj.get('original_mapping', {}).get('exam_code') or ''
            ex_name = decision_obj.get('exam_name') or decision_obj.get('original_mapping', {}).get('exam_name') or ''
            modality = (
                decision_obj.get('modality_code')
                or _first_modality(decision_obj.get('original_mapping', {}).get('modality_code'))
                or _first_modality(decision_obj.get('original_mapping', {}).get('modality'))
                or None
            )
            req_hash, _preimage = compute_request_hash_with_preimage(ds, ex_code, ex_name, modality)
            return req_hash, ds, ex_code, ex_name

        def _load_existing_cache(url, default_schema):
            import requests
            entries = {}
            meta = {'version': 1, 'schema': default_schema, 'last_updated': datetime.utcnow().isoformat() + 'Z'}
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200 and resp.text.strip():
                    data = resp.json()
                    if isinstance(data, dict) and 'entries' in data and isinstance(data['entries'], dict):
                        entries = data['entries']
                        if isinstance(data.get('meta'), dict):
                            meta.update(data['meta'])
                    elif isinstance(data, dict):
                        # Legacy flat dict: treat keys as entries
                        entries = data
                    logger.info(f"Loaded existing cache from R2: {len(entries)} entries")
                else:
                    logger.info("No existing cache found at R2; starting fresh.")
            except Exception as e:
                logger.warning(f"Could not load existing cache from R2 ({url}): {e}")
            return {'entries': entries, 'meta': meta}

        for decision_data in decisions:
            try:
                mapping_id = decision_data.get('mapping_id')
                decision = decision_data.get('decision')
                notes = decision_data.get('notes', '')

                if not mapping_id or not decision:
                    errors.append('Invalid decision data: missing mapping_id or decision')
                    continue

                processed = {
                    'mapping_id': mapping_id,
                    'decision': decision,
                    'notes': notes,
                    'timestamp_reviewed': datetime.utcnow().isoformat() + 'Z',
                    'original_mapping': decision_data.get('original_mapping', {}),
                    'data_source': decision_data.get('data_source', ''),
                    'exam_code': decision_data.get('exam_code', ''),
                    'exam_name': decision_data.get('exam_name', ''),
                    'modality_code': decision_data.get('modality_code')
                }
                processed_decisions.append(processed)

                if decision == 'approve':
                    approved_items.append(processed)
                elif decision == 'reject':
                    rejected_items.append(processed)

            except Exception as e:
                errors.append(f'Error processing decision: {str(e)}')

        r2_success = True
        cache_reload_success = True

        logger.info(f"Starting R2 save process: {len(approved_items)} approved, {len(rejected_items)} rejected")

        try:
            import json

            # Approved cache
            if approved_items:
                approved_url = "https://pub-cc78b976831e4f649dd695ffa52d1171.r2.dev/validation/approved_mappings_cache.json"
                approved_cache = _load_existing_cache(
                    approved_url,
                    default_schema="approved_mappings_cache.v1"
                )

                # If legacy flat shape, migrate to entries
                if 'entries' not in approved_cache or not isinstance(approved_cache['entries'], dict):
                    approved_cache['entries'] = {}
                # Move any top-level hashed keys into entries
                for k in list(approved_cache.keys()):
                    if k not in ('entries', 'meta') and isinstance(approved_cache[k], dict):
                        approved_cache['entries'][k] = approved_cache.pop(k)

                for item in approved_items:
                    try:
                        req_hash, ds, ex_code, ex_name = _compute_request_hash(item)
                        entry = {
                            'result': item.get('original_mapping', {}),
                            'validation_notes': item.get('notes', ''),
                            'approved_at': item.get('timestamp_reviewed'),
                            'decision_metadata': {
                                'data_source': ds,
                                'exam_code': ex_code,
                                'exam_name': ex_name
                            }
                        }
                        approved_cache['entries'][req_hash] = entry
                    except Exception as e:
                        errors.append(f"Failed to build approved entry for {item.get('mapping_id')}: {e}")

                approved_cache['meta']['last_updated'] = datetime.utcnow().isoformat() + 'Z'

                approved_json = json.dumps(approved_cache, indent=2)
                success = r2_manager.upload_object(
                    object_key='validation/approved_mappings_cache.json',
                    data=approved_json.encode('utf-8'),
                    content_type='application/json',
                    cors_headers=True
                )
                if success:
                    logger.info(f"Saved approved cache to R2 (total entries: {len(approved_cache['entries'])})")
                else:
                    r2_success = False
                    logger.error("Failed to save approved mappings cache to R2")

            # Rejected cache
            if rejected_items:
                rejected_url = "https://pub-cc78b976831e4f649dd695ffa52d1171.r2.dev/validation/rejected_mappings.json"
                rejected_cache = _load_existing_cache(
                    rejected_url,
                    default_schema="rejected_mappings_cache.v1"
                )

                if 'entries' not in rejected_cache or not isinstance(rejected_cache['entries'], dict):
                    rejected_cache['entries'] = {}
                for k in list(rejected_cache.keys()):
                    if k not in ('entries', 'meta') and isinstance(rejected_cache[k], dict):
                        rejected_cache['entries'][k] = rejected_cache.pop(k)

                for item in rejected_items:
                    try:
                        req_hash, ds, ex_code, ex_name = _compute_request_hash(item)
                        snomed_ids = []
                        snomed_obj = item.get('original_mapping', {}).get('snomed', {})
                        for key in ('id', 'concept_id', 'snomed_id'):
                            if snomed_obj.get(key):
                                snomed_ids.append(snomed_obj[key])
                                break

                        entry = {
                            'reason': item.get('notes', ''),
                            'rejected_at': item.get('timestamp_reviewed'),
                            'decision_metadata': {
                                'data_source': ds,
                                'exam_code': ex_code,
                                'exam_name': ex_name
                            }
                        }
                        if snomed_ids:
                            entry['rejected_snomed_ids'] = snomed_ids

                        rejected_cache['entries'][req_hash] = entry
                    except Exception as e:
                        errors.append(f"Failed to build rejected entry for {item.get('mapping_id')}: {e}")

                rejected_cache['meta']['last_updated'] = datetime.utcnow().isoformat() + 'Z'

                rejected_json = json.dumps(rejected_cache, indent=2)
                success = r2_manager.upload_object(
                    object_key='validation/rejected_mappings.json',
                    data=rejected_json.encode('utf-8'),
                    content_type='application/json',
                    cors_headers=True
                )
                if success:
                    logger.info(f"Saved rejected cache to R2 (total entries: {len(rejected_cache['entries'])})")
                else:
                    r2_success = False
                    logger.error("Failed to save rejected mappings cache to R2")

        except Exception as e:
            r2_success = False
            logger.error(f"Exception saving validation caches to R2: {e}", exc_info=True)

        # Reload in-engine caches if we saved successfully
        try:
            if nhs_lookup_engine and r2_success:
                reload_result = nhs_lookup_engine.reload_validation_caches()
                if reload_result.get('status') != 'success':
                    cache_reload_success = False
                    logger.error(f"Failed to reload validation caches: {reload_result}")
                else:
                    logger.info("Successfully reloaded validation caches in NHS lookup engine")
        except Exception as e:
            cache_reload_success = False
            logger.error(f"Exception reloading validation caches: {e}")

        response_data = {
            'success': r2_success,
            'processed_count': len(processed_decisions),
            'approved_count': len(approved_items),
            'rejected_count': len(rejected_items),
            'error_count': len(errors),
            'r2_storage_success': r2_success,
            'cache_reload_success': cache_reload_success,
            'cache_updated': cache_reload_success,
            'decisions': processed_decisions,
            'errors': errors if errors else None
        }

        if not r2_success:
            response_data['error'] = 'Validation decisions could not be saved to R2 storage - decisions not persisted'
            return jsonify(response_data), 500

        if not cache_reload_success:
            response_data['warning'] = 'Cache reload failed - restart may be needed for changes to take effect'

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Failed to process batch validation decisions: {e}", exc_info=True)
        return jsonify({'error': f'Batch decision processing failed: {str(e)}'}), 500


@app.route('/validation/export', methods=['POST'])
def export_validation_results():
    """
    Export validation results in various formats.
    Returns validation decisions and approved/rejected mappings.
    """
    try:
        data = request.get_json()
        validation_state = data.get('validation_state', {}) if data else {}
        export_format = data.get('format', 'json') if data else 'json'
        
        logger.info(f"Exporting validation results in {export_format} format")
        
        # Process validation state to create export data
        export_data = {
            'export_timestamp': datetime.utcnow().isoformat() + 'Z',
            'total_mappings': len(validation_state),
            'approved_mappings': [],
            'rejected_mappings': [],
            'modified_mappings': [],
            'pending_mappings': []
        }
        
        for mapping_id, state in validation_state.items():
            decision = state.get('validator_decision')
            if decision == 'approve':
                export_data['approved_mappings'].append(state)
            elif decision == 'reject':
                export_data['rejected_mappings'].append(state)
            elif decision == 'modify':
                export_data['modified_mappings'].append(state)
            else:
                export_data['pending_mappings'].append(state)
        
        # Add summary statistics
        export_data['summary'] = {
            'approved_count': len(export_data['approved_mappings']),
            'rejected_count': len(export_data['rejected_mappings']),
            'modified_count': len(export_data['modified_mappings']),
            'pending_count': len(export_data['pending_mappings']),
            'completion_rate': (len(export_data['approved_mappings']) + 
                              len(export_data['rejected_mappings']) + 
                              len(export_data['modified_mappings'])) / len(validation_state) * 100 if validation_state else 0
        }
        
        return jsonify({
            'success': True,
            'export_data': export_data,
            'format': export_format
        })
        
    except Exception as e:
        logger.error(f"Failed to export validation results: {e}")
        return jsonify({'error': f'Export failed: {str(e)}'}), 500


if __name__ == '__main__':
    logger.info("Running in local development mode, initializing app immediately.")
    _ensure_app_is_initialized()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))