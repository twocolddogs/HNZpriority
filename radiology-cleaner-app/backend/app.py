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
from parser import RadiologySemanticParser
from nlp_processor import NLPProcessor
from database_models import DatabaseManager, CacheManager
from feedback_training import FeedbackTrainingManager, FeedbackEnhancedPreprocessor
# This import is from your original file, so we keep it.
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

        # Initialize the core parser and other systems
        semantic_parser = RadiologySemanticParser(db_manager=db_manager)
        
        # This preprocessor is from your original code, initialize it as well
        nhs_json_path = os.path.join(os.path.dirname(__file__), 'NHS.json')
        usa_json_path = os.path.join(os.path.dirname(__file__), 'USA.json')
        if os.path.exists(nhs_json_path):
            comprehensive_preprocessor = ComprehensivePreprocessor(nhs_json_path, usa_json_path if os.path.exists(usa_json_path) else None)
        
        # This preprocessor uses the comprehensive one and adds learning
        if comprehensive_preprocessor:
             feedback_enhanced_preprocessor = FeedbackEnhancedPreprocessor(
                comprehensive_preprocessor, feedback_manager
            )
        
        logger.info("Parsers and preprocessors initialized.")

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

# --- CORE PROCESSING FUNCTION (using the new parser) ---
def process_single_exam_hybrid(exam_data: Dict) -> Dict:
    exam_name = exam_data['exam_name']
    modality = exam_data.get('modality_code', 'Unknown')
    
    # NLP is now the first step
    scispacy_entities = nlp_processor.extract_entities(exam_name)
    
    # The hybrid parser uses both rules and NLP entities
    return semantic_parser.parse_exam_name(exam_name, modality, scispacy_entities)

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
    """Parses a single exam name using the hybrid NLP/rule-based approach."""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name"}), 400

        cache_key = f"hybrid_{data['exam_name']}|{data.get('modality_code', 'Unknown')}"
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return jsonify(cached_result)

        result = process_single_exam_hybrid(data)
        
        cache_manager.set(cache_key, result)
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse', processing_time, len(data['exam_name']), True)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Parse endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/parse_enhanced', methods=['POST'])
def parse_enhanced():
    """Enhanced parsing endpoint using the new hybrid parser."""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name"}), 400
        
        # This now uses the new hybrid parser
        parsed_result = process_single_exam_hybrid(data)
        
        # Format the response to match the detailed structure you had
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
        
        cache_key = f"enhanced_{data['exam_name']}|{data.get('modality_code', 'Unknown')}"
        cache_manager.set(cache_key, response)
        record_performance('parse_enhanced', response['metadata']['processing_time_ms'], len(data['exam_name']), True)
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Enhanced parse endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/parse_batch', methods=['POST'])
def parse_batch():
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exams' not in data:
            return jsonify({"error": "Missing exams array"}), 400
        
        exams = data['exams']
        results, errors = [], []

        max_workers = get_optimal_worker_count(max_items=len(exams))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_exam = {executor.submit(process_single_exam_hybrid, exam): exam for exam in exams}
            
            for future in as_completed(future_to_exam):
                exam_data = future_to_exam[future]
                try:
                    result = future.result()
                    results.append({"input": exam_data, "output": result})
                except Exception as exc:
                    errors.append({"error": str(exc), "original_exam": exam_data})

        processing_time = int((time.time() - start_time) * 1000)
        response = {
            'results': results, 
            'errors': errors, 
            'processing_stats': {
                'total_exams': len(exams),
                'successful': len(results),
                'failed': len(errors),
                'processing_time_ms': processing_time
            }
        }
        
        record_performance('parse_batch', processing_time, len(exams), len(errors) == 0)
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
        
        # This endpoint uses the placeholder `standardization_engine` for compatibility
        normalized = standardization_engine.normalize_exam_name(exam_name)
        parsed_result = process_single_exam_hybrid(data) # Use the new hybrid parser
        quality_metrics = standardization_engine.calculate_quality_metrics(exam_name, parsed_result)
        
        is_valid = quality_metrics['overall_quality'] >= 0.7
        response = {
            'valid': is_valid,
            'quality_score': quality_metrics['overall_quality'],
            'warnings': quality_metrics.get('flags', []),
            'suggestions': quality_metrics.get('suggestions', []),
            'normalized_name': normalized['normalized'],
            'transformations_applied': normalized['transformations_applied'],
            'metadata': {'processing_time_ms': int((time.time() - start_time) * 1000)}
        }
        record_performance('validate', response['metadata']['processing_time_ms'], len(exam_name), True)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Validation endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/feedback', methods=['POST'])
def feedback_endpoint(): # Renamed to avoid conflict with the other feedback endpoint
    _ensure_app_is_initialized()
    start_time = time.time()
    try:
        data = request.json
        feedback_type = data.get('type', 'correction')
        required_fields = {
            'correction': ['original_exam_name', 'original_mapping', 'corrected_mapping', 'confidence_level'],
            'general': ['suggestion_text', 'confidence_level']
        }
        if feedback_type not in required_fields or not all(field in data for field in required_fields[feedback_type]):
            return jsonify({"error": f"Missing required fields for {feedback_type} feedback"}), 400
        if data['confidence_level'] not in ['low', 'medium', 'high']:
            return jsonify({"error": "Invalid confidence level"}), 400

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

# --- FEEDBACK TRAINING ENDPOINTS ---
@app.route('/feedback/submit', methods=['POST'])
def submit_feedback_training_route(): # Renamed to avoid conflict
    _ensure_app_is_initialized()
    start_time = time.time()
    try:
        data = request.json
        required_fields = ['original_exam_name', 'predicted_clean_name', 'feedback_type']
        if not data or not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        feedback_id = feedback_manager.submit_user_feedback(data)
        
        response = {
            'feedback_id': feedback_id,
            'status': 'received',
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
