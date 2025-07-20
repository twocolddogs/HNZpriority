# --- START OF FILE app.py ---

# =============================================================================
# RADIOLOGY EXAM STANDARDIZATION API
# =============================================================================
# This Flask application provides a unified processing pipeline for standardizing
# radiology exam names against NHS reference data using NLP and semantic matching.

import time, json, logging, threading, os, sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import List, Dict, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

# Core processing components
from parser import RadiologySemanticParser
from nlp_processor import NLPProcessor
from nhs_lookup_engine import NHSLookupEngine
from database_models import DatabaseManager, CacheManager
from feedback_training import FeedbackTrainingManager
from parsing_utils import AbbreviationExpander, AnatomyExtractor, LateralityDetector, ContrastMapper
from context_detection import detect_gender_context, detect_age_context, detect_clinical_context
from preprocessing import initialize_preprocessor, preprocess_exam_name
from cache_version import get_current_cache_version, format_cache_key

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global component instances
semantic_parser: Optional[RadiologySemanticParser] = None
nhs_lookup_engine: Optional[NHSLookupEngine] = None
model_processors: Dict[str, NLPProcessor] = {}
_init_lock = threading.Lock()
_app_initialized = False
# DB/Cache managers would be initialized here in a full app
db_manager = None
cache_manager = None

def _initialize_model_processors() -> Dict[str, NLPProcessor]:
    """Initialize available NLP processors for different models"""
    # Get model keys dynamically from nlp_processor.py
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

def _get_nlp_processor(model: str = 'default') -> Optional[NLPProcessor]:
    """Get the appropriate NLP processor for the specified model"""
    global model_processors
    processor = model_processors.get(model)
    if not processor:
        logger.warning(f"Model '{model}' not available, falling back to default")
        processor = model_processors.get('default')
    return processor

def _initialize_app():
    """Initializes all application components in the correct dependency order."""
    global semantic_parser, nlp_processor, model_processors, nhs_lookup_engine, cache_manager
    logger.info("--- Performing first-time application initialization... ---")
    start_time = time.time()
    
    # Enhanced cache with version-based invalidation
    class SimpleCache:
        def __init__(self):
            self.cache = {}
            self.cache_version = get_current_cache_version()
            logger.info(f"Initialized cache with version: {self.cache_version}")
        
        def _check_version_and_clear_if_needed(self):
            """Check if cache version has changed and clear if needed"""
            current_version = get_current_cache_version()
            if current_version != self.cache_version:
                logger.info(f"Cache version changed from {self.cache_version} to {current_version}, clearing cache")
                self.cache.clear()
                self.cache_version = current_version
        
        def get(self, key):
            self._check_version_and_clear_if_needed()
            # Use format_cache_key for consistent key formatting
            formatted_key = format_cache_key("simple_cache", self.cache_version, key)
            return self.cache.get(formatted_key)
        
        def set(self, key, value):
            self._check_version_and_clear_if_needed()
            # Use format_cache_key for consistent key formatting
            formatted_key = format_cache_key("simple_cache", self.cache_version, key)
            self.cache[formatted_key] = value
            return formatted_key
    cache_manager = SimpleCache()

    model_processors = _initialize_model_processors()
    nlp_processor = model_processors.get('default')
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    nhs_json_path = os.path.join(base_dir, 'core', 'NHS.json')
    
    nhs_authority = {}
    if os.path.exists(nhs_json_path):
        with open(nhs_json_path, 'r', encoding='utf-8') as f: 
            nhs_data = json.load(f)
        for item in nhs_data:
            # MODIFICATION: Use the new, clean key name here
            if primary_source_name := item.get('primary_source_name'): 
                nhs_authority[primary_source_name] = item
        logger.info(f"Loaded {len(nhs_authority)} NHS reference entries")
    else: 
        logger.critical(f"CRITICAL: NHS JSON file not found at {nhs_json_path}")
        sys.exit(1)


    abbreviation_expander = AbbreviationExpander()
    
    # Load config for enhanced preprocessing with super-strong contrast detection
    import yaml
    try:
        config_path = os.path.join(base_dir, 'config.yaml')
        with open(config_path, 'r') as f:
            full_config = yaml.safe_load(f)
            preprocessing_config = full_config.get('preprocessing', {})
    except Exception as e:
        logger.warning(f"Could not load config.yaml: {e}")
        preprocessing_config = {}
    
    # MODIFICATION: Pass config to preprocessor for enhanced contrast detection
    initialize_preprocessor(abbreviation_expander, config=preprocessing_config)
    
    anatomy_extractor = AnatomyExtractor(nhs_authority)
    laterality_detector = LateralityDetector()
    contrast_mapper = ContrastMapper()

    semantic_parser = RadiologySemanticParser(
        nlp_processor=nlp_processor,
        anatomy_extractor=anatomy_extractor,
        laterality_detector=laterality_detector,
        contrast_mapper=contrast_mapper
    )

    nhs_lookup_engine = NHSLookupEngine(
        nhs_json_path=nhs_json_path,
        nlp_processor=nlp_processor,
        semantic_parser=semantic_parser
    )
    
    nhs_lookup_engine.validate_consistency()
    logger.info(f"Initialization complete in {time.time() - start_time:.2f} seconds.")

def _ensure_app_is_initialized():
    """Thread-safe gatekeeper to ensure initialization runs only once."""
    global _app_initialized
    if _app_initialized: return
    with _init_lock:
        if not _app_initialized:
            _initialize_app()
            _app_initialized = True

def process_exam_request(exam_name: str, modality_code: Optional[str], nlp_processor: NLPProcessor) -> Dict:
    """Central processing logic for a single exam."""
    _ensure_app_is_initialized()
    if not nhs_lookup_engine or not semantic_parser:
        return {'error': 'Core components not initialized'}
    
    cleaned_exam_name = preprocess_exam_name(exam_name)
    parsed_input_components = semantic_parser.parse_exam_name(cleaned_exam_name, modality_code or 'Other')
    
    # The lookup engine performs the match and returns a dictionary with the correct final structure.
    nhs_result = nhs_lookup_engine.standardize_exam(cleaned_exam_name, parsed_input_components, custom_nlp_processor=nlp_processor)
    
    # --- CRITICAL FIX IS HERE ---
    # The nhs_result now contains a nested 'components' dictionary. We just use it directly.
    components_from_engine = nhs_result.get('components', {})

    final_result = {
        'data_source': 'N/A',
        'modality_code': components_from_engine.get('modality'),
        'exam_code': 'N/A',
        'exam_name': exam_name,
        'clean_name': nhs_result.get('clean_name', cleaned_exam_name),
        'snomed': {
            'found': bool(nhs_result.get('snomed_id')),
            'fsn': nhs_result.get('snomed_fsn', ''),
            'id': nhs_result.get('snomed_id', ''),
            'laterality_concept_id': nhs_result.get('snomed_laterality_concept_id', ''),
            'laterality_fsn': nhs_result.get('snomed_laterality_fsn', '')
        },
        'components': {
            # Directly use the components from the authoritative engine result
            'anatomy': components_from_engine.get('anatomy', []),
            'laterality': components_from_engine.get('laterality', []),
            'contrast': components_from_engine.get('contrast', []),
            'technique': components_from_engine.get('technique', []),
            
            # Contexts are calculated once on the cleaned input for consistency
            'gender_context': detect_gender_context(cleaned_exam_name, components_from_engine.get('anatomy', [])),
            'age_context': detect_age_context(cleaned_exam_name),
            'clinical_context': detect_clinical_context(cleaned_exam_name, components_from_engine.get('anatomy', [])),
            
            'confidence': components_from_engine.get('confidence', 0.0)
        }
    }
    return final_result

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring service availability"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(), 
        'app_initialized': _app_initialized
    })

@app.route('/models', methods=['GET'])
def list_available_models():
    """List available NLP models and their status (lightweight, no initialization required)"""
    try:
        # Get model info directly from NLPProcessor without initializing the full app
        available_models = NLPProcessor.get_available_models()
        model_info = {}
        
        for model_key, model_config in available_models.items():
            # Check if embeddings are loaded for this model
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
        
        return jsonify({
            'models': model_info,
            'default_model': 'default',
            'usage': 'Add "model": "model_key" to your request to use a specific model',
            'app_initialized': _app_initialized
        })
    except Exception as e:
        logger.error(f"Models endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Failed to list models"}), 500

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
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name in request data"}), 400
        
        exam_name = data['exam_name']
        modality_code = data.get('modality_code')
        model = data.get('model', 'default')
        
        # Get the appropriate NLP processor for the selected model
        selected_nlp_processor = _get_nlp_processor(model)
        if not selected_nlp_processor:
            return jsonify({"error": f"Model '{model}' not available"}), 400
        
        logger.info(f"Using model '{model}' for exam: {exam_name}")
        
        # USE THE NEW SIGNATURE
        result = process_exam_request(exam_name, modality_code, selected_nlp_processor)
        
        # Add processing metadata
        result['metadata'] = {
            'processing_time_ms': int((time.time() - start_time) * 1000),
            'model_used': model
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Parse enhanced endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
        

@app.route('/parse_batch', methods=['POST'])
def parse_batch():
    """
    Processes a batch of exam names concurrently for high performance.
    Accepts a JSON payload with a list of exams and an optional model key.
    """
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exams' not in data:
            return jsonify({"error": "Missing 'exams' list in request data"}), 400
        
        exams_to_process = data['exams']
        model_key = data.get('model', 'default')
        
        logger.info(f"Starting batch processing for {len(exams_to_process)} exams using model: '{model_key}'")

        selected_nlp_processor = _get_nlp_processor(model_key)
        if not selected_nlp_processor:
            return jsonify({"error": f"Model '{model_key}' not available"}), 400

        results = []
        errors = []
        
        # Conservative thread pool sizing for batch processing to prevent resource exhaustion.
        # Use a more conservative approach to avoid overwhelming the system during initialization.
        cpu_cnt = os.cpu_count() or 1
        max_workers = min(8, max(2, cpu_cnt))
        logger.info(f"ThreadPoolExecutor starting with max_workers={max_workers}")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Map each future to its original exam for better error tracking
            future_to_exam = {
                executor.submit(process_exam_request, exam.get("exam_name"), exam.get("modality_code"), selected_nlp_processor): exam 
                for exam in exams_to_process
            }
            
            completed = 0
            total = len(exams_to_process)
            per_future_timeout = 60  # seconds

            for future in as_completed(future_to_exam):
                original_exam = future_to_exam[future]
                try:
                    # Get the result from the future
                    processed_result = future.result(timeout=per_future_timeout)
                    results.append({
                        "input": original_exam,
                        "output": processed_result
                    })
                except Exception as e:
                    logger.error(f"Error processing exam '{original_exam.get('exam_name')}': {e}", exc_info=True)
                    errors.append({
                        "original_exam": original_exam,
                        "error": str(e)
                    })
                finally:
                    completed += 1
                    if completed % 100 == 0 or completed == total:
                        logger.info(f"Batch progress: {completed}/{total} exams processed")

        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Batch processing finished in {processing_time_ms}ms. Success: {len(results)}, Errors: {len(errors)}")

        return jsonify({
            "results": results,
            "errors": errors,
            "processing_stats": {
                "total_processed": len(exams_to_process),
                "successful": len(results),
                "errors": len(errors),
                "processing_time_ms": processing_time_ms,
                "model_used": model_key
            }
        })
        
    except Exception as e:
        logger.error(f"Batch endpoint failed with a critical error: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred during batch processing"}), 500

@app.route('/process_sanity_test', methods=['POST'])
def process_sanity_test_endpoint():
    """
    Processes the entire sanity_test.json file using a user-specified model,
    or the default model if none is provided.
    """
    _ensure_app_is_initialized()
    
    try:
        # Check if the user sent a JSON body with a model preference
        data = request.json or {}
        model_key = data.get('model', 'default') # Default to 'default' if no model is specified
        
        logger.info(f"Processing sanity_test.json using model: '{model_key}'")

        # Get the NLP processor corresponding to the user's choice
        selected_nlp_processor = _get_nlp_processor(model_key)
        if not selected_nlp_processor:
            return jsonify({"error": f"Model '{model_key}' not available"}), 400

        # Load sanity_test.json from the core directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sanity_test_path = os.path.join(base_dir, 'core', 'sanity_test.json')
        
        with open(sanity_test_path, 'r', encoding='utf-8') as f:
            sanity_data = json.load(f)

        results = []
        for exam in sanity_data:
            exam_name = exam.get("EXAM_NAME")
            modality_code = exam.get("MODALITY_CODE")
            
            if exam_name:
                # Use the SELECTED processor for the test
                processed_result = process_exam_request(exam_name, modality_code, selected_nlp_processor)
                
                # Add original data source info back
                processed_result['data_source'] = exam.get("DATA_SOURCE")
                processed_result['exam_code'] = exam.get("EXAM_CODE")
                results.append(processed_result)
        
        return jsonify(results)

    except FileNotFoundError:
        return jsonify({"error": "sanity_test.json not found"}), 404
    except Exception as e:
        logger.error(f"Error processing sanity test: {e}", exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    logger.info("Running in local development mode, initializing app immediately.")
    _ensure_app_is_initialized()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))