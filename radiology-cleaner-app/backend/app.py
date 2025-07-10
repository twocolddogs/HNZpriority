import time
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import List, Dict, Optional
from datetime import datetime
import logging
import threading
import os
import sys
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Import Custom Modules ---
# These are assumed to be in the same directory or accessible via PYTHONPATH
from parser import RadiologySemanticParser
from nlp_processor import NLPProcessor
from database_models import DatabaseManager, CacheManager
from feedback_training import FeedbackTrainingManager, FeedbackEnhancedPreprocessor
from comprehensive_preprocessor import ComprehensivePreprocessor

# --- Configure logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- App Initialization ---
app = Flask(__name__)
CORS(app)

# --- START: LAZY LOADING IMPLEMENTATION ---
# 1. Initialize all components as None. They will be loaded on the first request.
semantic_parser: Optional[RadiologySemanticParser] = None
db_manager: Optional[DatabaseManager] = None
cache_manager: Optional[CacheManager] = None
feedback_manager: Optional[FeedbackTrainingManager] = None
feedback_enhanced_preprocessor: Optional[FeedbackEnhancedPreprocessor] = None
nlp_processor: Optional[NLPProcessor] = None
comprehensive_preprocessor: Optional[ComprehensivePreprocessor] = None

# Placeholder for StandardizationEngine to make the /validate endpoint runnable
class StandardizationEnginePlaceholder:
    def normalize_exam_name(self, name):
        return {'normalized': name.lower(), 'transformations_applied': ['lowercase']}
    def calculate_quality_metrics(self, name, parsed):
        return {'overall_quality': parsed.get('confidence', 0.5), 'flags': [], 'suggestions': []}

standardization_engine = StandardizationEnginePlaceholder()

# 2. Create a lock to ensure initialization only happens once.
_init_lock = threading.Lock()
_app_initialized = False

def _initialize_app():
    """
    This function contains the main application initialization logic.
    It will only be called once, controlled by _ensure_app_is_initialized.
    """
    global semantic_parser, db_manager, cache_manager, feedback_manager, \
           feedback_enhanced_preprocessor, nlp_processor, comprehensive_preprocessor

    logger.info("--- Performing first-time application initialization... ---")
    start_time = time.time()

    try:
        # Initialize database and cache managers first
        # Assuming your DatabaseManager and FeedbackTrainingManager don't have heavy init
        db_manager = DatabaseManager()
        cache_manager = CacheManager()
        feedback_manager = FeedbackTrainingManager(db_manager=db_manager)
        logger.info("Database, Cache, and Feedback managers initialized.")

        # Initialize NLP Processor
        nlp_processor = NLPProcessor()
        if not nlp_processor.nlp:
            logger.error("NLP Processor failed to initialize. Parsing will be limited to rules.")

        # Initialize the core parser
        semantic_parser = RadiologySemanticParser(db_manager=db_manager)
        
        # --- CORRECTED FILE PATHS ---
        # Build absolute paths from the directory where this script (app.py) is located.
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # This preprocessor is from your original code, initialize it with correct paths
        nhs_json_path = os.path.join(base_dir, 'core', 'NHS.json')
        usa_json_path = os.path.join(base_dir, 'core', 'USA.json')
        
        if os.path.exists(nhs_json_path):
            comprehensive_preprocessor = ComprehensivePreprocessor(nhs_json_path, usa_json_path if os.path.exists(usa_json_path) else None)
            logger.info("Comprehensive preprocessor initialized.")
        else:
            logger.error(f"CRITICAL: NHS JSON file not found at {nhs_json_path}")
            comprehensive_preprocessor = None # Ensure it's None if data is missing

        # This preprocessor uses the comprehensive one and adds learning
        if comprehensive_preprocessor:
             feedback_enhanced_preprocessor = FeedbackEnhancedPreprocessor(
                comprehensive_preprocessor, feedback_manager
            )
             logger.info("Feedback-enhanced preprocessor initialized.")
        else:
            feedback_enhanced_preprocessor = None
            logger.warning("Feedback-enhanced preprocessor could not be initialized because ComprehensivePreprocessor failed.")


    except Exception as e:
        logger.error(f"FATAL: Failed to initialize components: {e}", exc_info=True)
        sys.exit(1)

    logger.info(f"--- Full initialization completed in {time.time() - start_time:.2f} seconds. ---")

def _ensure_app_is_initialized():
    """A thread-safe gatekeeper to ensure initialization runs only once."""
    global _app_initialized
    if _app_initialized:
        return
    with _init_lock:
        if not _app_initialized:
            _initialize_app()
            _app_initialized = True
# --- END: LAZY LOADING ---

def get_optimal_worker_count(task_type: str = 'mixed', max_items: int = 100) -> int:
    cpu_count = multiprocessing.cpu_count()
    if task_type == 'cpu_bound':
        return min(cpu_count, max_items)
    return min(cpu_count * 2, max_items, 32)

def record_performance(endpoint: str, processing_time_ms: int, input_size: int, 
                      success: bool, error_message: Optional[str] = None):
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

# This is the processing function from your original file, adapted for lazy-loading
def process_exam_with_preprocessor(exam_name: str, modality_code: str = None) -> Dict:
    _ensure_app_is_initialized()
    
    if not comprehensive_preprocessor:
        logger.error("Comprehensive preprocessor not available")
        return {'error': 'Preprocessor not initialized'}
    
    try:
        result = comprehensive_preprocessor.preprocess_exam_name(exam_name, modality_code)
        components = result.get('components', {})
        best_match = result.get('best_match')
        
        response = {
            'cleanName': best_match['clean_name'] if best_match else components.get('expanded', exam_name),
            'anatomy': components.get('anatomy', []),
            'laterality': components.get('laterality'),
            'contrast': components.get('contrast'),
            'technique': [], 'gender_context': components.get('gender_context'),
            'clinical_context': [], 'confidence': result.get('confidence', 0.0),
            'snomed': best_match.get('snomed_data', {}) if best_match else {},
            'clinical_equivalents': [], 'is_paediatric': components.get('is_paediatric', False),
            'modality': components.get('modality', modality_code)
        }
        return response
    except Exception as e:
        logger.error(f"Comprehensive preprocessing failed for '{exam_name}': {e}", exc_info=True)
        return {'error': str(e)}

# --- API Endpoints ---
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'app_initialized': _app_initialized
    })

@app.route('/parse', methods=['POST'])
def parse_exam():
    """Legacy parsing endpoint using comprehensive preprocessor."""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name"}), 400

        exam_name = data['exam_name']
        modality = data.get('modality_code', 'Unknown')

        cache_key = f"legacy_{exam_name}|{modality}"
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return jsonify(cached_result)

        result = process_exam_with_preprocessor(exam_name, modality)
        
        cache_manager.set(cache_key, result)
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse', processing_time, len(exam_name), 'error' not in result)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Parse endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/parse_enhanced', methods=['POST'])
def parse_enhanced():
    """Enhanced parsing endpoint using the new hybrid NLP parser."""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name"}), 400
        
        exam_name = data['exam_name']
        modality = data.get('modality_code', 'Unknown')
        
        cache_key = f"enhanced_v2_{exam_name}|{modality}"
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return jsonify(cached_result)

        # Use the new hybrid parser
        scispacy_entities = nlp_processor.extract_entities(exam_name)
        parsed_result = semantic_parser.parse_exam_name(exam_name, modality, scispacy_entities)
        
        response = {
            'input': data,
            'standardized': {
                'clean_name': parsed_result['cleanName'],
                'components': {
                    'anatomy': parsed_result['anatomy'],
                    'laterality': parsed_result['laterality'],
                    'contrast': parsed_result['contrast'],
                    'technique': parsed_result['technique'],
                    'modality': parsed_result['modality'],
                },
                'quality_score': parsed_result['confidence']
            },
            'metadata': {
                'processing_time_ms': int((time.time() - start_time) * 1000),
                'confidence': parsed_result['confidence'],
                'source': 'hybrid_parser_v2'
            }
        }
        
        cache_manager.set(cache_key, response)
        record_performance('parse_enhanced', response['metadata']['processing_time_ms'], len(exam_name), True)
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Enhanced parse endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/parse_batch', methods=['POST'])
def parse_batch():
    """Optimized batch processing using the new hybrid parser."""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exams' not in data:
            return jsonify({"error": "Missing exams array"}), 400
        
        exams = data['exams']
        results, errors, cache_hits, uncached_exams, cached_results = [], [], 0, [], []

        for exam_data in exams:
            cache_key = f"hybrid_{exam_data['exam_name']}|{exam_data.get('modality_code', 'Unknown')}"
            cached = cache_manager.get(cache_key)
            if cached:
                cached_results.append({"input": exam_data, "output": cached})
                cache_hits += 1
            else:
                uncached_exams.append(exam_data)
        
        if uncached_exams:
            def process_exam_batch(exam_data):
                try:
                    return process_single_exam_hybrid(exam_data)
                except Exception as e:
                    return {"error": str(e)}

            max_workers = get_optimal_worker_count(max_items=len(uncached_exams))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_exam = {executor.submit(process_exam_batch, exam): exam for exam in uncached_exams}
                for future in as_completed(future_to_exam):
                    exam_data = future_to_exam[future]
                    result = future.result()
                    if 'error' in result:
                        errors.append({"error": result['error'], "original_exam": exam_data})
                    else:
                        results.append({"input": exam_data, "output": result})
                        cache_key = f"hybrid_{exam_data['exam_name']}|{exam_data.get('modality_code', 'Unknown')}"
                        cache_manager.set(cache_key, result)

        all_results = cached_results + results
        
        processing_stats = {
            'total_processed': len(exams), 'successful': len(all_results),
            'errors': len(errors), 'cache_hits': cache_hits,
            'processing_time_ms': int((time.time() - start_time) * 1000),
            'cache_hit_ratio': cache_hits / len(exams) if exams else 0.0
        }
        
        response = {'results': all_results, 'errors': errors, 'processing_stats': processing_stats}
        record_performance('parse_batch', processing_stats['processing_time_ms'], len(exams), len(errors) == 0)
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Batch parse endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/validate', methods=['POST'])
def validate_exam_data():
    _ensure_app_is_initialized()
    start_time = time.time()
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name"}), 400
        
        exam_name = data['exam_name']
        normalized = standardization_engine.normalize_exam_name(exam_name)
        parsed_result = process_single_exam_hybrid(data)
        quality_metrics = standardization_engine.calculate_quality_metrics(exam_name, parsed_result)
        
        is_valid = quality_metrics['overall_quality'] >= 0.7
        response = {
            'valid': is_valid, 'quality_score': quality_metrics['overall_quality'],
            'warnings': quality_metrics.get('flags', []), 'suggestions': quality_metrics.get('suggestions', []),
            'normalized_name': normalized['normalized'], 'transformations_applied': normalized['transformations_applied'],
            'metadata': {'processing_time_ms': int((time.time() - start_time) * 1000)}
        }
        record_performance('validate', response['metadata']['processing_time_ms'], len(exam_name), True)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Validation endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

# --- FEEDBACK & TRAINING ENDPOINTS ---

@app.route('/feedback', methods=['POST'])
def feedback_endpoint():
    _ensure_app_is_initialized()
    start_time = time.time()
    try:
        data = request.json
        feedback_type = data.get('type', 'correction')
        if feedback_type == 'general':
            feedback_id = db_manager.submit_general_feedback(data)
        else:
            feedback_id = db_manager.submit_feedback(data)

        response = {
            'feedback_id': feedback_id,
            'type': feedback_type,
            'status': 'submitted',
            'message': f'{feedback_type.title()} feedback submitted successfully',
            'processing_time_ms': int((time.time() - start_time) * 1000)
        }
        record_performance('feedback', response['processing_time_ms'], 1, True)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Feedback endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/feedback/submit', methods=['POST'])
def submit_feedback_training_route():
    _ensure_app_is_initialized()
    start_time = time.time()
    try:
        data = request.json
        if not data or 'original_exam_name' not in data:
            return jsonify({"error": "Missing required fields"}), 400
        
        feedback_id = feedback_manager.submit_user_feedback(data)
        response = {
            'feedback_id': feedback_id, 'status': 'received',
            'message': 'Feedback for training submitted successfully',
            'processing_time_ms': int((time.time() - start_time) * 1000)
        }
        record_performance('feedback_submit', response['processing_time_ms'], 1, True)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Feedback submission error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/feedback/stats', methods=['GET'])
def get_feedback_stats():
    _ensure_app_is_initialized()
    try:
        days = request.args.get('days', 30, type=int)
        stats = feedback_manager.get_feedback_stats(days)
        return jsonify({'stats': stats, 'period_days': days})
    except Exception as e:
        logger.error(f"Feedback stats error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/parse_with_learning', methods=['POST'])
def parse_with_learning():
    _ensure_app_is_initialized()
    start_time = time.time()
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name"}), 400
        
        result = process_single_exam(data, use_learning=True)
        result['metadata']['processing_time_ms'] = int((time.time() - start_time) * 1000)
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
        if not admin_token or auth_header != f"Bearer {admin_token}":
            return jsonify({"error": "Unauthorized"}), 401
        
        feedback_manager.retrain_patterns()
        return jsonify({'status': 'completed', 'message': 'Pattern retraining initiated successfully.'})
    except Exception as e:
        logger.error(f"Retraining error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    logger.info("Running in local development mode, initializing app immediately.")
    _ensure_app_is_initialized()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
