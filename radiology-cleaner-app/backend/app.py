# =============================================================================
# RADIOLOGY EXAM STANDARDIZATION API
# =============================================================================
# This Flask application provides a unified processing pipeline for standardizing
# radiology exam names against NHS reference data using NLP and semantic matching.
#
# PROCESSING PIPELINE OVERVIEW:
# 1. Input Preprocessing: Clean and normalize exam names
# 2. Semantic Parsing: Extract anatomical components using NLP
# 3. NHS Lookup: Match against NHS reference data with SNOMED codes
# 4. Context Detection: Identify gender, age, and clinical contexts
# 5. Output Formatting: Return standardized results with confidence scores
# =============================================================================

import time, json, logging, threading, os, sys, multiprocessing, signal, atexit
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import List, Dict, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# Initialize Flask application
app = Flask(__name__)
CORS(app)

# =============================================================================
# GLOBAL COMPONENT INSTANCES
# =============================================================================
# These components form the core processing pipeline
semantic_parser: Optional[RadiologySemanticParser] = None
db_manager: Optional[DatabaseManager] = None
cache_manager: Optional[CacheManager] = None
feedback_manager: Optional[FeedbackTrainingManager] = None
nlp_processor: Optional[NLPProcessor] = None
model_processors: Dict[str, NLPProcessor] = {}
nhs_lookup_engine: Optional[NHSLookupEngine] = None
abbreviation_expander: Optional[AbbreviationExpander] = None
_init_lock = threading.Lock()
_app_initialized = False

# =============================================================================
# COMPONENT INITIALIZATION SYSTEM
# =============================================================================
# Manages the initialization of all processing components in the correct order

def _initialize_model_processors() -> Dict[str, NLPProcessor]:
    """Initialize available NLP processors for different models"""
    MODEL_MAPPING = {
        'default': 'NeuML/pubmedbert-base-embeddings',  # PubMed model is now default for better medical terminology
        'pubmed': 'NeuML/pubmedbert-base-embeddings',
        'general': 'sentence-transformers/all-MiniLM-L6-v2'  # General-purpose model available as alternative
    }
    
    processors = {}
    for model_key, model_name in MODEL_MAPPING.items():
        try:
            processor = NLPProcessor(model_name=model_name)
            if processor.is_available():
                processors[model_key] = processor
                logger.info(f"Initialized model processor for '{model_key}' -> '{model_name}'")
            else:
                logger.warning(f"Model processor for '{model_key}' -> '{model_name}' is not available")
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

# =============================================================================
# GRACEFUL SHUTDOWN HANDLING
# =============================================================================
_active_workers = set()
_shutdown_requested = False
_worker_lock = threading.Lock()

def _initialize_app():
    """
    Initialize all application components in the correct dependency order.
    
    INITIALIZATION PIPELINE:
    1. Core managers (Database, Cache, Feedback)
    2. NLP processors for semantic analysis
    3. Reference data loading (NHS.json)
    4. Utility components (Abbreviation, Anatomy, Laterality, Contrast, Preprocessor)
    5. Semantic parser (combines NLP + utilities)
    6. NHS lookup engine (uses parser for unified logic)
    """
    global semantic_parser, db_manager, cache_manager, feedback_manager, \
           nlp_processor, model_processors, nhs_lookup_engine, abbreviation_expander
    logger.info("--- Performing first-time application initialization... ---")
    start_time = time.time()
    try:
        # STEP 1: Initialize core managers
        db_manager = DatabaseManager()
        cache_manager = CacheManager()
        feedback_manager = FeedbackTrainingManager()
        logger.info("Database, Cache, and Feedback managers initialized.")

        # STEP 2: Initialize NLP processors for semantic analysis
        model_processors = _initialize_model_processors()
        nlp_processor = model_processors.get('default')  # Default processor for compatibility
        if not nlp_processor or not nlp_processor.is_available():
            logger.error("API-based NLP processor is not available (HUGGING_FACE_TOKEN missing?). Semantic features will be degraded.")

        # STEP 3: Load reference data files
        base_dir = os.path.dirname(os.path.abspath(__file__))
        nhs_json_path = os.path.join(base_dir, 'core', 'NHS.json')
        
        # Load NHS reference data (required)
        nhs_authority = {}
        if os.path.exists(nhs_json_path):
            with open(nhs_json_path, 'r', encoding='utf-8') as f: 
                nhs_data = json.load(f)
            for item in nhs_data:
                if clean_name := item.get('Clean Name'): 
                    nhs_authority[clean_name] = item
            logger.info(f"Loaded {len(nhs_authority)} NHS reference entries")
        else: 
            logger.critical(f"CRITICAL: NHS JSON file not found at {nhs_json_path}")
            sys.exit(1)

        # STEP 4: Initialize utility components for parsing and preprocessing
        abbreviation_expander = AbbreviationExpander()
        anatomy_extractor = AnatomyExtractor(nhs_authority)
        laterality_detector = LateralityDetector()
        contrast_mapper = ContrastMapper()
        initialize_preprocessor(abbreviation_expander)
        logger.info("Utility components initialized (Abbreviation, Anatomy, Laterality, Contrast, Preprocessor)")
        
        # STEP 5: Initialize semantic parser with all utilities
        semantic_parser = RadiologySemanticParser(
            nlp_processor=nlp_processor, 
            anatomy_extractor=anatomy_extractor,
            laterality_detector=laterality_detector, 
            contrast_mapper=contrast_mapper
        )
        logger.info("RadiologySemanticParser initialized.")
        
        # STEP 6: Initialize NHS lookup engine with unified parsing logic
        nhs_lookup_engine = NHSLookupEngine(
            nhs_json_path=nhs_json_path, 
            nlp_processor=nlp_processor,
            semantic_parser=semantic_parser  # Inject parser for unified logic
        )
        
        nhs_lookup_engine.validate_consistency()
        logger.info("NHS lookup engine initialized with unified parsing logic.")
        logger.info(f"Initialization complete in {time.time() - start_time:.2f} seconds.")

    except Exception as e:
        logger.critical(f"FATAL: Failed to initialize components: {e}", exc_info=True)
        sys.exit(1)

def _ensure_app_is_initialized():
    """Thread-safe gatekeeper to ensure initialization runs only once."""
    global _app_initialized
    if _app_initialized:
        return
    with _init_lock:
        if not _app_initialized:
            _initialize_app()
            _app_initialized = True

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_optimal_worker_count(task_type: str = 'mixed', max_items: int = 100) -> int:
    """Calculate optimal worker count for threading operations"""
    cpu_count = multiprocessing.cpu_count()
    if task_type == 'cpu_bound':
        return min(cpu_count, max_items)
    return min(cpu_count * 2, max_items, 32)

def record_performance(endpoint: str, processing_time_ms: int, input_size: int,
                      success: bool, error_message: Optional[str] = None):
    """Record performance metrics for monitoring and optimization"""
    _ensure_app_is_initialized()
    if not db_manager: return
    try:
        db_manager.record_performance_metric({
            'endpoint': endpoint,
            'processing_time_ms': processing_time_ms,
            'input_size': input_size,
            'success': success,
            'error_message': error_message
        })
    except Exception as e:
        logger.error(f"Failed to record performance metric: {e}")

# =============================================================================
# NOTE: PREPROCESSING MOVED TO preprocessing.py MODULE
# =============================================================================
# Input preprocessing (cleaning and normalization) is now handled by the 
# preprocessing module for better code organization and reusability.


# =============================================================================
# CORE PROCESSING PIPELINE
# =============================================================================
# Main processing function that orchestrates the entire pipeline

def process_exam_with_nhs_lookup(exam_name: str, modality_code: str = None, nlp_proc: NLPProcessor = None) -> Dict:
    """
    NHS-first processing pipeline that uses NHS.json as the single source of truth.
    
    PROCESSING PIPELINE:
    1. Preprocess: Clean and normalize the input exam name
    2. Parse: Extract semantic components using NLP and parsing utilities
    3. Lookup: Match against NHS reference data with confidence scoring
    4. Format: Return standardized results with metadata
    """
    _ensure_app_is_initialized()
    if not nhs_lookup_engine or not semantic_parser:
        logger.error("Core components (NHS Engine or Parser) not available")
        return {'error': 'Core components not initialized'}
    try:
        # STEP 1: Preprocess the raw input string
        cleaned_exam_name = preprocess_exam_name(exam_name)
        
        # STEP 2: Parse the cleaned input string to get its components for matching
        # Use provided NLP processor or fall back to global default
        if nlp_proc and nlp_proc != nlp_processor:
            # Create temporary parser with custom NLP processor
            temp_parser = RadiologySemanticParser(
                nlp_processor=nlp_proc,
                anatomy_extractor=semantic_parser.anatomy_extractor,
                laterality_detector=semantic_parser.laterality_detector,
                contrast_mapper=semantic_parser.contrast_mapper
            )
            parsed_input_components = temp_parser.parse_exam_name(cleaned_exam_name, modality_code or 'Other')
        else:
            parsed_input_components = semantic_parser.parse_exam_name(cleaned_exam_name, modality_code or 'Other')
        
        # STEP 3: Use the cleaned name and its parsed components to find the best match
        # Pass the custom NLP processor to NHS lookup engine if provided
        nhs_result = nhs_lookup_engine.standardize_exam(cleaned_exam_name, parsed_input_components, nlp_proc)
        
        # STEP 4: Format the final output, using components from the STANDARDIZED result
        return {
            'input_exam': exam_name,
            'cleaned_exam': cleaned_exam_name,
            'clean_name': nhs_result.get('clean_name'),
            'anatomy': nhs_result.get('anatomy', []),
            'laterality': nhs_result.get('laterality', []),
            'modality': nhs_result.get('modality', []),
            'contrast': nhs_result.get('contrast', []),
            'technique': nhs_result.get('technique', []),
            'snomed_id': nhs_result.get('snomed_id'),
            'snomed_fsn': nhs_result.get('snomed_fsn'),
            'confidence': nhs_result.get('confidence'),
            'source': nhs_result.get('source'),
            'snomed_found': bool(nhs_result.get('snomed_id')),
            'age_context': detect_age_context(cleaned_exam_name)
        }
    except Exception as e:
        logger.error(f"Error processing exam '{exam_name}': {e}", exc_info=True)
        return {'error': str(e)}

# =============================================================================
# LEGACY FORMAT ADAPTER (REMOVED)
# =============================================================================
# Legacy format adapter has been removed as part of API simplification.
# All endpoints now use the unified /parse_enhanced format.

# =============================================================================
# API ENDPOINTS
# =============================================================================
# REST API endpoints that expose the processing pipeline functionality

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring service availability"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat(), 'app_initialized': _app_initialized})

@app.route('/cache-version', methods=['GET'])
def cache_version_info():
    """Get detailed cache version information for debugging and monitoring."""
    try:
        from cache_version import get_cache_version_info
        cache_info = get_cache_version_info()
        
        # Add current cache stats
        if cache_manager:
            cache_stats = {
                'in_memory_size': cache_manager.size(),
                'in_memory_usage_percent': cache_manager.usage_percentage(),
                'max_size': cache_manager._max_size
            }
            cache_info['cache_stats'] = cache_stats
        
        return jsonify(cache_info)
    except Exception as e:
        logger.error(f"Cache version info error: {e}", exc_info=True)
        return jsonify({"error": "Failed to get cache version info"}), 500

@app.route('/parse', methods=['POST'])
def parse_exam_legacy():
    """
    DEPRECATED: Use /parse_enhanced instead.
    
    Legacy parsing endpoint for backward compatibility.
    Redirects to unified /parse_enhanced endpoint.
    """
    return jsonify({
        "error": "Deprecated endpoint", 
        "message": "Use /parse_enhanced instead. See API documentation for details.",
        "deprecated": True
    }), 410

@app.route('/parse_enhanced', methods=['POST'])
def parse_enhanced():
    """
    Unified parsing endpoint that handles both single exams and batches intelligently.
    
    INPUT FORMATS:
    - Single exam: {"exam_name": "CT Chest", "modality_code": "CT", "model": "pubmed"}
    - Batch exams: {"exams": [{"exam_name": "CT Chest", "modality_code": "CT"}, ...], "model": "pubmed"}
    
    ENDPOINT PIPELINE:
    1. Detect input format (single vs batch)
    2. Validate input and select NLP model
    3. Check cache for existing results
    4. Process using optimal strategy (single or batch processing)
    5. Format unified response with detailed components
    6. Cache results and record performance metrics
    """
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Missing request data"}), 400
        
        # DETECT INPUT FORMAT: Single exam or batch
        if 'exam_name' in data:
            # Single exam format
            return _handle_single_exam(data, start_time)
        elif 'exams' in data:
            # Batch format
            return _handle_batch_exams(data, start_time)
        else:
            return jsonify({"error": "Invalid input format. Expected 'exam_name' or 'exams' field"}), 400
            
    except Exception as e:
        logger.error(f"Parse endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

def _handle_single_exam(data: dict, start_time: float):
    """Handle single exam processing with caching and performance tracking."""
    worker_id = f"single_{int(time.time() * 1000000)}"
    if not _register_worker(worker_id):
        return jsonify({"error": "Server shutting down"}), 503
    
    try:
        exam_name = data['exam_name']
        modality = data.get('modality_code')
        model = data.get('model', 'default')
        
        # Get the appropriate NLP processor for the selected model
        selected_nlp_processor = _get_nlp_processor(model)
        logger.info(f"Using model '{model}' for single exam: {exam_name}")

        # Check cache first
        cache_version = get_current_cache_version()
        cache_key = format_cache_key("enhanced", cache_version, f"{exam_name}_{model}", modality or 'None')
        if cached_result := cache_manager.get(cache_key):
            return jsonify(cached_result)

        # Process the exam
        result = process_exam_with_nhs_lookup(exam_name, modality, selected_nlp_processor)
        cleaned_exam_name = preprocess_exam_name(exam_name)
        
        # Format response
        anatomy = [a for a in result.get('anatomy', []) if a]
        laterality = [l for l in result.get('laterality', []) if l]
        contrast = [c for c in result.get('contrast', []) if c]
        modality_list = [m for m in result.get('modality', []) if m]

        response = {
            'clean_name': result.get('clean_name', ''),
            'snomed': {
                'id': result.get('snomed_id', ''), 
                'fsn': result.get('snomed_fsn', ''), 
                'found': result.get('snomed_found', False),
                'laterality_concept_id': result.get('snomed_laterality_concept_id', ''),
                'laterality_fsn': result.get('snomed_laterality_fsn', '')
            },
            'procedure_type': {
                'is_diagnostic': result.get('is_diagnostic', False),
                'is_interventional': result.get('is_interventional', False),
                'detected_interventional_terms': result.get('detected_interventional_terms', [])
            },
            'components': {
                'anatomy': anatomy, 
                'laterality': laterality, 
                'contrast': contrast, 
                'technique': result.get('technique', []), 
                'modality': modality_list, 
                'confidence': result.get('confidence', 0.0),
                'gender_context': detect_gender_context(cleaned_exam_name, anatomy),
                'age_context': detect_age_context(cleaned_exam_name),
                'clinical_context': detect_clinical_context(cleaned_exam_name, anatomy),
                'clinical_equivalents': []
            },
            'metadata': {'processing_time_ms': int((time.time() - start_time) * 1000), 'confidence': result.get('confidence', 0.0), 'source': result.get('source')}
        }
        
        # Cache and record performance
        cache_manager.set(cache_key, response)
        record_performance('parse_enhanced_single', response['metadata']['processing_time_ms'], len(exam_name), True)
        return jsonify(response)
        
    finally:
        _unregister_worker(worker_id)

def _handle_batch_exams(data: dict, start_time: float):
    """Handle batch exam processing with threading and cache optimization."""
    exams = data['exams']
    model = data.get('model', 'default')
    
    # Get the appropriate NLP processor for the selected model
    selected_nlp_processor = _get_nlp_processor(model)
    logger.info(f"Using model '{model}' for batch processing of {len(exams)} exams")
    
    # Process cache hits and misses
    results, errors, cache_hits, uncached_exams, cached_results = [], [], 0, [], []
    cache_version = get_current_cache_version()
    
    for exam_data in exams:
        cache_key = format_cache_key("batch", cache_version, f"{exam_data['exam_name']}_{model}", exam_data.get('modality_code', 'Unknown'))
        if cached := cache_manager.get(cache_key):
            cached_results.append({"input": exam_data, "output": cached})
            cache_hits += 1
        else:
            uncached_exams.append(exam_data)
    
    # Process uncached exams with threading
    if uncached_exams:
        def process_exam_batch(exam_data):
            try:
                result = process_exam_with_nhs_lookup(exam_data.get('exam_name', ''), exam_data.get('modality_code'), selected_nlp_processor)
                # Format for batch response
                anatomy = [a for a in result.get('anatomy', []) if a]
                laterality = [l for l in result.get('laterality', []) if l]
                contrast = [c for c in result.get('contrast', []) if c]
                modality_list = [m for m in result.get('modality', []) if m]
                
                return {
                    'clean_name': result.get('clean_name', ''), 
                    'snomed': {
                        'id': result.get('snomed_id', ''), 
                        'fsn': result.get('snomed_fsn', ''), 
                        'found': result.get('snomed_found', False),
                        'laterality_concept_id': result.get('snomed_laterality_concept_id', ''),
                        'laterality_fsn': result.get('snomed_laterality_fsn', '')
                    },
                    'procedure_type': {
                        'is_diagnostic': result.get('is_diagnostic', False),
                        'is_interventional': result.get('is_interventional', False),
                        'detected_interventional_terms': result.get('detected_interventional_terms', [])
                    },
                    'components': {
                        'anatomy': anatomy, 
                        'laterality': laterality, 
                        'contrast': contrast, 
                        'technique': result.get('technique', []), 
                        'confidence': result.get('confidence', 0.0), 
                        'modality': modality_list,
                        'gender_context': result.get('gender_context'),
                        'age_context': result.get('age_context'),
                        'clinical_context': result.get('clinical_context', [])
                    }, 
                    'original_exam': exam_data
                }
            except Exception as e:
                return {"error": str(e), "original_exam": exam_data}
        
        # Use threading for batch processing
        max_workers = get_optimal_worker_count(max_items=len(uncached_exams))
        logger.info(f"Processing {len(uncached_exams)} uncached exams with {max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            batch_worker_id = f"batch_{int(time.time() * 1000)}"
            if not _register_worker(batch_worker_id):
                logger.warning("Shutdown requested, aborting batch processing")
                return jsonify({"error": "Server shutting down"}), 503
            
            try:
                future_to_exam = {executor.submit(process_exam_batch, exam): exam for exam in uncached_exams}
                for future in as_completed(future_to_exam):
                    if _shutdown_requested:
                        logger.info("Shutdown requested during batch processing, stopping...")
                        break
                        
                    exam_data, result = future_to_exam[future], future.result()
                    if 'error' in result:
                        errors.append({"error": result['error'], "original_exam": exam_data})
                    else:
                        results.append({"input": exam_data, "output": result})
                        cache_key = format_cache_key("batch", cache_version, f"{exam_data['exam_name']}_{model}", exam_data.get('modality_code', 'Unknown'))
                        cache_manager.set(cache_key, result)
            finally:
                _unregister_worker(batch_worker_id)
    
    # Combine results and generate response
    all_results = cached_results + results
    processing_stats = {
        'total_processed': len(exams), 
        'successful': len(all_results), 
        'errors': len(errors), 
        'cache_hits': cache_hits, 
        'processing_time_ms': int((time.time() - start_time) * 1000), 
        'cache_hit_ratio': cache_hits / len(exams) if exams else 0.0
    }
    
    response = {'results': all_results, 'errors': errors, 'processing_stats': processing_stats}
    record_performance('parse_enhanced_batch', processing_stats['processing_time_ms'], len(exams), len(errors) == 0)
    return jsonify(response)

# =============================================================================
# LEGACY ENDPOINTS (DEPRECATED)
# =============================================================================
# These endpoints are deprecated. Use /parse_enhanced for all parsing needs.

@app.route('/parse', methods=['POST'])
def parse_exam():
    """
    DEPRECATED: Use /parse_enhanced instead.
    
    Legacy parsing endpoint for backward compatibility.
    Redirects to unified /parse_enhanced endpoint.
    """
    return jsonify({
        "error": "Deprecated endpoint", 
        "message": "Use /parse_enhanced instead. See API documentation for details.",
        "deprecated": True
    }), 410

@app.route('/parse_batch', methods=['POST'])
def parse_batch():
    """
    DEPRECATED: Use /parse_enhanced instead.
    
    Legacy batch processing endpoint for backward compatibility.
    Redirects to unified /parse_enhanced endpoint.
    """
    return jsonify({
        "error": "Deprecated endpoint", 
        "message": "Use /parse_enhanced with 'exams' array instead. See API documentation for details.",
        "deprecated": True
    }), 410

@app.route('/validate', methods=['POST'])
def validate_exam_data():
    """Validates exam data using the unified NHS-first lookup pipeline."""
    _ensure_app_is_initialized()
    start_time = time.time()
    try:
        data = request.json
        if not data or 'exam_name' not in data: return jsonify({"error": "Missing exam_name"}), 400
        exam_name, modality_code = data['exam_name'], data.get('modality_code')
        parsed_result = process_exam_with_nhs_lookup(exam_name, modality_code, None)
        quality_score = parsed_result.get('confidence', 0.0)
        warnings = []
        if not parsed_result.get('snomed_found'): warnings.append("No matching SNOMED code found.")
        if not parsed_result.get('anatomy'): warnings.append("Could not identify anatomy.")
        if quality_score < 0.5: warnings.append("Low confidence parse; result may be unreliable.")
        suggestions = []
        if parsed_result.get('clean_name') and parsed_result['clean_name'] != exam_name:
            suggestions.append(f"Consider using the standardized name: '{parsed_result['clean_name']}'")
        response = {'valid': quality_score >= 0.7, 'quality_score': quality_score, 'warnings': warnings, 'suggestions': suggestions, 'normalized_name': parsed_result.get('clean_name', exam_name), 'transformations_applied': ['unified_processing_v4'], 'metadata': {'processing_time_ms': int((time.time() - start_time) * 1000)}}
        record_performance('validate', response['metadata']['processing_time_ms'], len(exam_name), True)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Validation endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/feedback', methods=['POST'])
def feedback_endpoint():
    _ensure_app_is_initialized()
    start_time = time.time()
    try:
        data = request.json
        feedback_type = data.get('type', 'correction')
        feedback_id = db_manager.submit_feedback(data) if feedback_type != 'general' else db_manager.submit_general_feedback(data)
        response = {'feedback_id': feedback_id, 'type': feedback_type, 'status': 'submitted', 'message': f'{feedback_type.title()} feedback submitted successfully', 'processing_time_ms': int((time.time() - start_time) * 1000)}
        record_performance('feedback', response['processing_time_ms'], 1, True)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Feedback endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/parse_with_learning', methods=['POST'])
def parse_with_learning():
    """Parses an exam, with a placeholder for future learning enhancements."""
    _ensure_app_is_initialized()
    start_time = time.time()
    try:
        data = request.json
        if not data or 'exam_name' not in data: return jsonify({"error": "Missing exam_name"}), 400
        exam_name, modality = data['exam_name'], data.get('modality_code')
        result = process_exam_with_nhs_lookup(exam_name, modality, None)
        result['metadata'] = {'processing_time_ms': int((time.time() - start_time) * 1000), 'source_endpoint': '/parse_with_learning'}
        return jsonify(result)
    except Exception as e:
        logger.error(f"Parse with learning error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/admin/retrain', methods=['POST'])
def retrain_patterns():
    _ensure_app_is_initialized()
    try:
        auth_header = request.headers.get('Authorization')
        admin_token = os.environ.get('ADMIN_TOKEN')
        if not admin_token or auth_header != f"Bearer {admin_token}": return jsonify({"error": "Unauthorized"}), 401
        feedback_manager.retrain_patterns()
        return jsonify({'status': 'completed', 'message': 'Pattern retraining initiated successfully.'})
    except Exception as e:
        logger.error(f"Retraining error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

# =============================================================================
# WORKER MANAGEMENT AND GRACEFUL SHUTDOWN
# =============================================================================
# Handles concurrent request processing and graceful application shutdown

def _register_worker(worker_id: str):
    """Register a worker for tracking during graceful shutdown."""
    with _worker_lock:
        if not _shutdown_requested:
            _active_workers.add(worker_id)
            logger.debug(f"Registered worker {worker_id}. Active workers: {len(_active_workers)}")
            return True
        return False

def _unregister_worker(worker_id: str):
    """Unregister a worker when processing completes."""
    with _worker_lock:
        _active_workers.discard(worker_id)
        logger.debug(f"Unregistered worker {worker_id}. Active workers: {len(_active_workers)}")

def _cleanup_resources():
    """Cleanup application resources during shutdown."""
    global db_manager, cache_manager, feedback_manager, nlp_processor
    
    logger.info("Cleaning up application resources...")
    
    max_wait_time = 30  # seconds
    wait_interval = 1
    waited = 0
    
    while _active_workers and waited < max_wait_time:
        logger.info(f"Waiting for {len(_active_workers)} active workers to complete... ({waited}s/{max_wait_time}s)")
        time.sleep(wait_interval)
        waited += wait_interval
    
    if _active_workers:
        logger.warning(f"Forcefully terminating {len(_active_workers)} remaining workers after {max_wait_time}s timeout")
    
    if db_manager and hasattr(db_manager, 'close'):
        try:
            db_manager.close()
            logger.info("Database manager cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up database manager: {e}")
    
    if cache_manager and hasattr(cache_manager, 'close'):
        try:
            cache_manager.close()
            logger.info("Cache manager cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up cache manager: {e}")
    
    logger.info("Resource cleanup completed")

def _signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    
    signal_names = {signal.SIGTERM: 'SIGTERM', signal.SIGINT: 'SIGINT'}
    signal_name = signal_names.get(signum, f'Signal {signum}')
    
    logger.info(f"Received {signal_name}, initiating graceful shutdown...")
    
    with _worker_lock:
        _shutdown_requested = True
    
    _cleanup_resources()
    
    logger.info("Graceful shutdown completed")
    sys.exit(0)

def _setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    atexit.register(_cleanup_resources)
    logger.info("Signal handlers registered for graceful shutdown")

# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    logger.info("Running in local development mode, initializing app immediately.")
    _setup_signal_handlers()
    _ensure_app_is_initialized()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))