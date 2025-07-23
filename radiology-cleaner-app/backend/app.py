# --- START OF FILE app.py ---

# =============================================================================
# RADIOLOGY EXAM STANDARDIZATION API
# =============================================================================
# This Flask application provides a unified processing pipeline for standardizing
# radiology exam names against NHS reference data using NLP and semantic matching.

import time, json, logging, threading, os, sys, re, math
from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS
from typing import List, Dict, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from pathlib import Path

# Core processing components
from parser import RadiologySemanticParser
from nlp_processor import NLPProcessor
from nhs_lookup_engine import NHSLookupEngine
from database_models import DatabaseManager, CacheManager
from feedback_training import FeedbackTrainingManager
from parsing_utils import AbbreviationExpander, AnatomyExtractor, LateralityDetector, ContrastMapper
### FIX: Import detect_all_contexts for correct data flow. Context is determined from the input request.
from context_detection import detect_all_contexts
from preprocessing import initialize_preprocessor, preprocess_exam_name, get_preprocessor
from cache_version import get_current_cache_version, format_cache_key
from r2_cache_manager import R2CacheManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
_init_lock = threading.Lock()
_app_initialized = False
# DB/Cache managers would be initialized here in a full app
db_manager = None
cache_manager = None
r2_manager = R2CacheManager()

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
    
    # V3 Architecture: Initialize dual processors for retriever-reranker pipeline
    retriever_processor = model_processors.get('default')  # BioLORD for retrieval
    reranker_processor = model_processors.get('experimental')  # MedCPT for reranking
    
    # Ensure both required processors are available
    if not retriever_processor:
        logger.critical("Required retriever processor ('default' - BioLORD) could not be initialized.")
        sys.exit(1)
    if not reranker_processor:
        logger.critical("Required reranker processor ('experimental' - MedCPT) could not be initialized.")
        sys.exit(1)
    
    logger.info("🚀 [V3-INIT] Initializing V3 dual-processor architecture")
    logger.info(f"📥 [V3-INIT] Retriever: {retriever_processor.hf_model_name} ({retriever_processor.pipeline})")
    logger.info(f"🔄 [V3-INIT] Reranker: {reranker_processor.hf_model_name} ({reranker_processor.pipeline})")
    
    # Test processor availability
    if retriever_processor.is_available():
        logger.info("✅ [V3-INIT] Retriever processor ready")
    else:
        logger.warning("⚠️ [V3-INIT] Retriever processor not available (missing HF token)")
        
    if reranker_processor.is_available():
        logger.info("✅ [V3-INIT] Reranker processor ready") 
    else:
        logger.warning("⚠️ [V3-INIT] Reranker processor not available (missing HF token)")
    
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
    
    import yaml
    try:
        config_path = os.path.join(base_dir, 'config.yaml')
        with open(config_path, 'r') as f:
            full_config = yaml.safe_load(f)
            preprocessing_config = full_config.get('preprocessing', {})
    except Exception as e:
        logger.warning(f"Could not load config.yaml: {e}")
        preprocessing_config = {}
    
    initialize_preprocessor(abbreviation_expander, config=preprocessing_config)
    
    anatomy_vocab_from_config = preprocessing_config.get('anatomy_vocabulary', {})
    if not anatomy_vocab_from_config:
        logger.warning("Anatomy vocabulary not found in config.yaml. AnatomyExtractor will be empty.")

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
        reranker_processor=reranker_processor,
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

    _preprocessor = get_preprocessor()
    
    if _preprocessor and _preprocessor.should_exclude_exam(exam_name):
        return {
            'error': 'EXCLUDED_NON_CLINICAL',
            'message': f'Excluded non-clinical entry: {exam_name}',
            'exam_name': exam_name,
            'excluded': True
        }
    
    cleaned_exam_name = preprocess_exam_name(exam_name)
    parsed_input_components = semantic_parser.parse_exam_name(cleaned_exam_name, modality_code or 'Other')
    
    # V3 Architecture: Always use the main dual-processor lookup engine
    # The v3 architecture uses both retriever and reranker models regardless of API model parameter
    lookup_engine_to_use = nhs_lookup_engine
    
    if nlp_processor.model_key != nhs_lookup_engine.retriever_processor.model_key:
        logger.warning(f"🔄 [V3-API] Model parameter '{nlp_processor.model_key}' ignored - using V3 dual-processor pipeline")
        logger.info(f"🔄 [V3-API] Pipeline: {nhs_lookup_engine.retriever_processor.model_key} → {nhs_lookup_engine.reranker_processor.model_key}")
    
    # V3 Architecture: Use dual-processor pipeline (custom_nlp_processor parameter deprecated)
    nhs_result = lookup_engine_to_use.standardize_exam(cleaned_exam_name, parsed_input_components)
    
    ### FIX: The context (gender, age, etc.) is a property of the INPUT request, not the matched NHS entry.
    ### We must calculate context here from the cleaned input string to ensure it's always correct.
    components_from_engine = nhs_result.get('components', {})
    context_from_input = detect_all_contexts(cleaned_exam_name, parsed_input_components.get('anatomy', []))

    matched_modalities = components_from_engine.get('modality', [])
    primary_modality_code = matched_modalities[0] if matched_modalities else (modality_code or 'Other')

    final_result = {
        'data_source': 'N/A',
        'modality_code': components_from_engine.get('modality'),
        'exam_code': 'N/A',
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
        
        return jsonify({
            'models': model_info,
            'default_model': 'default',
            'usage': 'Add "model": "model_key" to your request to use a specific model',
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
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name in request data"}), 400
        
        exam_name = data['exam_name']
        modality_code = data.get('modality_code')
        model = data.get('model', 'default')
        
        selected_nlp_processor = _get_nlp_processor(model)
        if not selected_nlp_processor:
            return jsonify({"error": f"Model '{model}' not available"}), 400
        
        logger.info(f"Using model '{model}' for exam: {exam_name}")
        
        result = process_exam_request(exam_name, modality_code, selected_nlp_processor)
        
        result['metadata'] = {
            'processing_time_ms': int((time.time() - start_time) * 1000),
            'model_used': model
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Parse enhanced endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/parse_batch', methods=['POST', 'OPTIONS'])
def parse_batch():
    """
    Processes a batch of exam names concurrently with streaming output to disk.
    """
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return '', 200
    
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exams' not in data:
            return jsonify({"error": "Missing 'exams' list in request data"}), 400
        
        exams_to_process = data['exams']
        model_key = data.get('model', 'default')
        
        import uuid
        output_dir = os.environ.get('RENDER_DISK_PATH', 'batch_outputs')
        os.makedirs(output_dir, exist_ok=True)
        results_filename = f"batch_results_{uuid.uuid4().hex}.jsonl"
        results_filepath = os.path.join(output_dir, results_filename)
        
        logger.info(f"Starting batch processing for {len(exams_to_process)} exams using model: '{model_key}'")
        logger.info(f"Results will be streamed to: {results_filepath}")

        selected_nlp_processor = _get_nlp_processor(model_key)
        if not selected_nlp_processor:
            return jsonify({"error": f"Model '{model_key}' not available"}), 400

        success_count = 0
        error_count = 0
        
        # Process in chunks of 25 to manage memory and provide progress updates
        chunk_size = 25
        total_exams = len(exams_to_process)
        chunks = [exams_to_process[i:i + chunk_size] for i in range(0, total_exams, chunk_size)]
        
        cpu_cnt = os.cpu_count() or 1
        max_workers = min(4, max(2, cpu_cnt))
        logger.info(f"Processing {total_exams} exams in {len(chunks)} chunks of {chunk_size}")
        logger.info(f"ThreadPoolExecutor using max_workers={max_workers}")

        with open(results_filepath, 'w', encoding='utf-8') as f_out:
            for chunk_idx, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {chunk_idx + 1}/{len(chunks)} ({len(chunk)} exams)")
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_exam = {
                        executor.submit(process_exam_request, exam.get("exam_name"), exam.get("modality_code"), selected_nlp_processor): exam 
                        for exam in chunk
                    }
                    
                    chunk_completed = 0
                    per_future_timeout = 60

                    for future in as_completed(future_to_exam):
                        original_exam = future_to_exam[future]
                        try:
                            processed_result = future.result(timeout=per_future_timeout)
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
                    
                    logger.info(f"Completed chunk {chunk_idx + 1}/{len(chunks)}: {chunk_completed} exams processed")
                    logger.info(f"Overall progress: {success_count + error_count}/{total_exams} exams processed")

        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Batch processing finished in {processing_time_ms}ms. Success: {success_count}, Errors: {error_count}")

        # Upload consolidated results to R2 for permanent storage and frontend access
        r2_upload_success = False
        r2_url = None
        if r2_manager.is_available():
            try:
                # Read and consolidate all results into a single JSON array
                consolidated_results = []
                with open(results_filepath, 'r', encoding='utf-8') as f_in:
                    for line in f_in:
                        if line.strip():
                            consolidated_results.append(json.loads(line.strip()))
                
                # Get current config for versioning
                from config_manager import get_config
                config_manager = get_config()
                config_source = "R2" if config_manager._r2_config_cache else "local"
                config_timestamp = datetime.fromtimestamp(config_manager._r2_config_cache_time).isoformat() if config_manager._r2_config_cache else "unknown"
                
                # Create consolidated JSON with metadata
                consolidated_data = {
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "total_processed": len(exams_to_process),
                        "successful": success_count,
                        "errors": error_count,
                        "processing_time_ms": processing_time_ms,
                        "model_used": model_key,
                        "results_count": len(consolidated_results),
                        "config_source": config_source,
                        "config_timestamp": config_timestamp
                    },
                    "results": consolidated_results
                }
                
                # Upload to R2 with JSON format for easy frontend consumption
                r2_key = f"batch-results/{results_filename.replace('.jsonl', '.json')}"
                consolidated_json = json.dumps(consolidated_data, indent=None, separators=(',', ':')).encode('utf-8')
                
                if r2_manager.upload_object(r2_key, consolidated_json, content_type="application/json"):
                    # Generate public URL
                    r2_url = f"https://pub-cc78b976831e4f649dd695ffa52d1171.r2.dev/{r2_key}"
                    r2_upload_success = True
                    logger.info(f"Successfully uploaded consolidated results to R2: {r2_key}")
                    
                    # Save versioned config copy for this run
                    try:
                        config_key = f"batch-configs/{results_filename.replace('.jsonl', '')}_config.yaml"
                        if config_manager._r2_config_cache:
                            # Save the R2 config version that was used
                            import yaml
                            config_yaml = yaml.dump(config_manager.config, default_flow_style=False).encode('utf-8')
                            if r2_manager.upload_object(config_key, config_yaml, content_type="text/yaml"):
                                logger.info(f"Saved versioned config to R2: {config_key}")
                            else:
                                logger.warning(f"Failed to save config version: {config_key}")
                        else:
                            # Save local config file
                            config_path = Path(__file__).parent / 'config.yaml'
                            if config_path.exists():
                                with open(config_path, 'rb') as f:
                                    config_data = f.read()
                                if r2_manager.upload_object(config_key, config_data, content_type="text/yaml"):
                                    logger.info(f"Saved versioned local config to R2: {config_key}")
                                else:
                                    logger.warning(f"Failed to save local config version: {config_key}")
                    except Exception as config_save_error:
                        logger.warning(f"Failed to save config version: {config_save_error}")
                        
                else:
                    logger.warning(f"Failed to upload results to R2: {r2_key}")
                    
            except Exception as e:
                logger.error(f"Error uploading to R2: {e}", exc_info=True)
        else:
            logger.warning("R2 not available - results only stored locally")

        # V3 Fix: Use lighter approach to avoid I/O storm restarts
        # For small batches, provide results but avoid heavy disk I/O
        MAX_INMEMORY_RESULTS = 10  # Reduced from 50 to minimize I/O
        
        if len(exams_to_process) <= MAX_INMEMORY_RESULTS:
            # Minimal I/O approach: read once, no deletion
            try:
                results = []
                with open(results_filepath, 'r', encoding='utf-8') as f_in:
                    for line in f_in:
                        if line.strip():
                            results.append(json.loads(line.strip()))
                logger.info(f"Loaded {len(results)} results into memory (no file deletion to avoid I/O issues)")
                
                return jsonify({
                    "message": "Batch processing complete.",
                    "results": results,
                    "results_file": results_filepath,
                    "results_filename": results_filename,
                    "r2_url": r2_url,
                    "r2_uploaded": r2_upload_success,
                    "processing_stats": {
                        "total_processed": len(exams_to_process),
                        "successful": success_count,
                        "errors": error_count,
                        "processing_time_ms": processing_time_ms,
                        "model_used": model_key
                    }
                })
            except Exception as read_error:
                logger.error(f"Failed to read results file: {read_error}")
                # Fallback to file reference
                pass
        
        # For larger batches or if reading failed, return file reference
        logger.info(f"Returning file reference to avoid I/O issues: {results_filename}")
        return jsonify({
            "message": "Batch processing complete. Results streamed to disk.",
            "results_file": results_filepath,
            "results_filename": results_filename,
            "r2_url": r2_url,
            "r2_uploaded": r2_upload_success,
            "processing_stats": {
                "total_processed": len(exams_to_process),
                "successful": success_count,
                "errors": error_count,
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
    Processes the entire sanity_test.json file using a user-specified model.
    """
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json or {}
        model_key = data.get('model', 'default')
        
        logger.info(f"Processing sanity_test.json using model: '{model_key}'")
        selected_nlp_processor = _get_nlp_processor(model_key)
        if not selected_nlp_processor:
            return jsonify({"error": f"Model '{model_key}' not available"}), 400

        base_dir = os.path.dirname(os.path.abspath(__file__))
        sanity_test_path = os.path.join(base_dir, 'core', 'sanity_test.json')
        
        with open(sanity_test_path, 'r', encoding='utf-8') as f:
            sanity_data = json.load(f)

        total_exams = len(sanity_data)
        logger.info(f"Starting sanity test processing for {total_exams} exams")
        results = []
        processed_count = 0
        
        for i, exam in enumerate(sanity_data):
            exam_name = exam.get("EXAM_NAME")
            modality_code = exam.get("MODALITY_CODE")
            
            if exam_name:
                processed_result = process_exam_request(exam_name, modality_code, selected_nlp_processor)
                processed_result['data_source'] = exam.get("DATA_SOURCE")
                processed_result['exam_code'] = exam.get("EXAM_CODE")
                results.append(processed_result)
                processed_count += 1
                
                if (i + 1) % 25 == 0 or (i + 1) == total_exams:
                    progress_pct = ((i + 1) / total_exams) * 100
                    elapsed_time = time.time() - start_time
                    logger.info(f"Sanity test progress: {i + 1}/{total_exams} ({progress_pct:.1f}%) - Elapsed: {elapsed_time:.1f}s")
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Sanity test processing complete in {processing_time_ms}ms. Processed: {processed_count}/{total_exams} exams")
        
        return jsonify(results)

    except FileNotFoundError:
        return jsonify({"error": "sanity_test.json not found"}), 404
    except Exception as e:
        logger.error(f"Error processing sanity test: {e}", exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500

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

if __name__ == '__main__':
    logger.info("Running in local development mode, initializing app immediately.")
    _ensure_app_is_initialized()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
