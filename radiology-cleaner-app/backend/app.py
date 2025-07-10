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
from feedback_training import FeedbackTrainingManager, FeedbackEnhancedPreprocessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- App Initialization ---
app = Flask(__name__)
CORS(app)  # Allows our frontend to call the API

# --- START: LAZY LOADING IMPLEMENTATION ---

# 1. Initialize lightweight components as None. They will be loaded on the first request.
comprehensive_preprocessor = None
feedback_enhanced_preprocessor = None
feedback_manager = None
cache_manager = None

# 2. Create a lock to ensure initialization only happens once, even with multiple threads.
_init_lock = threading.Lock()
_app_initialized = False

def _initialize_app():
    """
    This function contains the lightweight loading for NHS-first architecture.
    It will only be called once, controlled by the _ensure_app_is_initialized function.
    """
    global comprehensive_preprocessor, feedback_enhanced_preprocessor, feedback_manager, cache_manager

    logger.info("--- Performing lightweight application initialization... ---")
    start_time = time.time()

    try:
        # Import lightweight components
        from comprehensive_preprocessor import ComprehensivePreprocessor
        from database_models import CacheManager

        # Initialize cache manager
        cache_manager = CacheManager()
        logger.info("Cache manager initialized.")

        # Initialize feedback manager
        feedback_manager = FeedbackTrainingManager()
        logger.info("Feedback training manager initialized.")

        # Initialize comprehensive preprocessor with NHS and USA data
        nhs_json_path = os.path.join(os.path.dirname(__file__), '../core/NHS.json')
        usa_json_path = os.path.join(os.path.dirname(__file__), '../core/USA.json')
        
        if os.path.exists(nhs_json_path):
            if os.path.exists(usa_json_path):
                comprehensive_preprocessor = ComprehensivePreprocessor(nhs_json_path, usa_json_path)
                logger.info("Comprehensive preprocessor initialized with NHS and USA data.")
            else:
                comprehensive_preprocessor = ComprehensivePreprocessor(nhs_json_path)
                logger.info("Comprehensive preprocessor initialized with NHS data only.")
                
            # Initialize feedback-enhanced preprocessor
            feedback_enhanced_preprocessor = FeedbackEnhancedPreprocessor(
                comprehensive_preprocessor, feedback_manager
            )
            logger.info("Feedback-enhanced preprocessor initialized.")
        else:
            logger.error(f"NHS JSON file not found at {nhs_json_path}")
            # Create dummy preprocessor to prevent crashes
            class DummyPreprocessor:
                def preprocess_exam_name(self, exam_name, modality=None, organization=None):
                    return {
                        'components': {'original': exam_name, 'modality': modality, 'anatomy': []},
                        'nhs_candidates': [],
                        'confidence': 0.0,
                        'best_match': None
                    }
            comprehensive_preprocessor = DummyPreprocessor()
            feedback_enhanced_preprocessor = DummyPreprocessor()

    except Exception as e:
        logger.error(f"FATAL: Failed to initialize components: {e}")
        # Create dummy components to prevent crashes
        class DummyComponent:
            def __getattr__(self, name):
                return lambda *args, **kwargs: {}

        cache_manager = cache_manager or DummyComponent()
        comprehensive_preprocessor = comprehensive_preprocessor or DummyComponent()
        feedback_enhanced_preprocessor = feedback_enhanced_preprocessor or DummyComponent()
        feedback_manager = feedback_manager or DummyComponent()

    logger.info(f"--- Lightweight initialization completed in {time.time() - start_time:.2f} seconds. ---")

def _ensure_app_is_initialized():
    """
    A thread-safe gatekeeper function to be called at the beginning of each request.
    It ensures the heavy initialization is only ever run once.
    """
    global _app_initialized
    # Fast path: if already initialized, do nothing.
    if _app_initialized:
        return
    # Slow path: acquire lock and check again (double-checked locking).
    with _init_lock:
        if not _app_initialized:
            _initialize_app()
            _app_initialized = True

# --- END: LAZY LOADING IMPLEMENTATION ---


def get_optimal_worker_count(task_type: str = 'mixed', max_items: int = 100) -> int:
    """Calculate optimal worker count based on task type and workload."""
    cpu_count = multiprocessing.cpu_count()
    
    if task_type == 'cpu_bound':
        return min(cpu_count, max_items)
    elif task_type == 'io_bound':
        return min(cpu_count * 2, max_items, 20)
    else:
        return min(cpu_count + 2, max_items, 16)

def record_performance(endpoint: str, processing_time_ms: int, input_size: int, 
                      success: bool, error_message: Optional[str] = None):
    """Record performance metrics."""
    _ensure_app_is_initialized()
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

def process_exam_with_preprocessor(exam_name: str, modality_code: str = None) -> Dict:
    """Process exam name using comprehensive preprocessor."""
    _ensure_app_is_initialized()
    
    if not comprehensive_preprocessor:
        logger.error("Comprehensive preprocessor not available")
        return {
            'cleanName': exam_name,
            'anatomy': [],
            'laterality': None,
            'contrast': None,
            'technique': [],
            'gender_context': None,
            'clinical_context': [],
            'confidence': 0.0,
            'snomed': {},
            'clinical_equivalents': []
        }
    
    try:
        # Process with comprehensive preprocessor
        result = comprehensive_preprocessor.preprocess_exam_name(exam_name, modality_code)
        
        # Convert to legacy format for backward compatibility
        components = result.get('components', {})
        best_match = result.get('best_match')
        
        response = {
            'cleanName': best_match['clean_name'] if best_match else components.get('expanded', exam_name),
            'anatomy': components.get('anatomy', []),
            'laterality': components.get('laterality'),
            'contrast': components.get('contrast'),
            'technique': [],  # Will be enhanced later
            'gender_context': components.get('gender_context'),
            'clinical_context': [],  # Will be enhanced later
            'confidence': result.get('confidence', 0.0),
            'snomed': best_match['snomed_data'] if best_match else {},
            'clinical_equivalents': [],  # Will be enhanced later
            'is_paediatric': components.get('is_paediatric', False),
            'modality': components.get('modality', modality_code)
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Comprehensive preprocessing failed for '{exam_name}': {e}")
        return {
            'cleanName': exam_name,
            'anatomy': [],
            'laterality': None,
            'contrast': None,
            'technique': [],
            'gender_context': None,
            'clinical_context': [],
            'confidence': 0.0,
            'snomed': {},
            'clinical_equivalents': [],
            'error': str(e)
        }

# --- API Endpoints ---
# All endpoints now call _ensure_app_is_initialized() first.

@app.route('/parse', methods=['POST'])
def parse_exam():
    """Lightweight parsing endpoint using comprehensive preprocessor."""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name"}), 400

        exam_name = data['exam_name']
        modality = data.get('modality_code', 'Unknown')

        cache_key = f"{exam_name}|{modality}"
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return jsonify(cached_result)

        # Use comprehensive preprocessor instead of heavy models
        result = process_exam_with_preprocessor(exam_name, modality)
        
        cache_manager.set(cache_key, result)
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse', processing_time, len(exam_name), True)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Parse endpoint error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/parse_enhanced', methods=['POST'])
def parse_enhanced():
    """Enhanced parsing endpoint using comprehensive preprocessor with NHS authority."""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name"}), 400
        
        exam_name = data['exam_name']
        modality = data.get('modality_code', 'Unknown')
        
        cache_key = f"enhanced_{exam_name}|{modality}"
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return jsonify(cached_result)
        
        # Use comprehensive preprocessor for enhanced processing
        parsed_result = process_exam_with_preprocessor(exam_name, modality)
        
        # Build enhanced response format
        response = {
            'input': data,
            'standardized': {
                'clean_name': parsed_result['cleanName'],
                'canonical_form': parsed_result['cleanName'],  # NHS clean name is canonical
                'normalized_name': parsed_result['cleanName'],
                'components': {
                    'anatomy': parsed_result['anatomy'],
                    'laterality': parsed_result['laterality'],
                    'contrast': parsed_result['contrast'],
                    'technique': parsed_result['technique'],
                    'gender_context': parsed_result['gender_context'],
                    'clinical_context': parsed_result['clinical_context'],
                    'modality': parsed_result['modality'],
                    'is_paediatric': parsed_result.get('is_paediatric', False)
                },
                'quality_score': parsed_result['confidence']
            },
            'snomed': parsed_result.get('snomed', {}),
            'quality_metrics': {
                'overall_quality': parsed_result['confidence'],
                'nhs_authority_match': parsed_result.get('snomed', {}) != {},
                'flags': [],
                'suggestions': []
            },
            'equivalence': {
                'clinical_equivalents': parsed_result['clinical_equivalents']
            },
            'metadata': {
                'processing_time_ms': int((time.time() - start_time) * 1000),
                'model_version': 'NHS-First-v1.0',
                'confidence': parsed_result['confidence'],
                'source': 'comprehensive_preprocessor'
            }
        }
        
        cache_manager.set(cache_key, response)
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse_enhanced', processing_time, len(exam_name), True)
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Enhanced parse endpoint error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse_enhanced', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/parse_batch', methods=['POST'])
def parse_batch():
    """Optimized batch processing endpoint for high-volume data."""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exams' not in data:
            return jsonify({"error": "Missing exams array"}), 400
        
        exams = data['exams']
        chunk_size = data.get('chunk_size', 1000)
        
        if len(exams) > 10000:
            logger.warning(f"Large file detected: {len(exams)} exams. Processing in chunks of {chunk_size}.")
        
        results = []
        errors = []
        cache_hits = 0
        
        uncached_exams = []
        cached_results = []
        
        for exam_data in exams:
            cache_key = f"{exam_data['exam_name']}|{exam_data['modality_code']}"
            cached_result = cache_manager.get(cache_key)
            if cached_result:
                cached_results.append(cached_result)
                cache_hits += 1
            else:
                uncached_exams.append(exam_data)
        
        if uncached_exams:
            def process_exam_batch(exam_data):
                try:
                    exam_name = exam_data['exam_name']
                    modality = exam_data.get('modality_code', 'Unknown')
                    
                    # Use lightweight comprehensive preprocessor
                    parsed_result = process_exam_with_preprocessor(exam_name, modality)
                    
                    result = {
                        'input': exam_data,
                        'clean_name': parsed_result['cleanName'],
                        'canonical_form': parsed_result['cleanName'],  # NHS is canonical
                        'snomed': parsed_result.get('snomed', {}),
                        'components': {
                            'anatomy': parsed_result['anatomy'],
                            'laterality': parsed_result['laterality'],
                            'contrast': parsed_result['contrast'],
                            'technique': parsed_result['technique'],
                            'gender_context': parsed_result['gender_context'],
                            'clinical_context': parsed_result['clinical_context'],
                            'modality': parsed_result['modality'],
                            'is_paediatric': parsed_result.get('is_paediatric', False)
                        },
                        'confidence': parsed_result['confidence'],
                        'clinical_equivalents': parsed_result.get('clinical_equivalents', [])
                    }
                    cache_key = f"{exam_name}|{modality}"
                    cache_manager.set(cache_key, result)
                    return result
                    
                except Exception as e:
                    return {"error": str(e), "exam": exam_data}
            
            max_workers = get_optimal_worker_count('mixed', len(uncached_exams))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(process_exam_batch, exam): exam for exam in uncached_exams}
                for future in as_completed(futures):
                    result = future.result()
                    if 'error' in result:
                        errors.append(result)
                    else:
                        results.append(result)
        
        all_results = cached_results + results
        
        cache_items = {f"{res['input']['exam_name']}|{res['input'].get('modality_code', 'Unknown')}": res for res in results if 'input' in res}
        if cache_items:
            cache_manager.bulk_set(cache_items)
        
        # Simplified equivalence groups for now (can be enhanced later)
        equivalence_groups = []
        
        processing_stats = {
            'total_processed': len(exams),
            'successful': len(all_results),
            'errors': len(errors),
            'cache_hits': cache_hits,
            'processing_time_ms': int((time.time() - start_time) * 1000),
            'equivalence_groups_found': len(equivalence_groups),
            'cache_hit_ratio': cache_hits / len(exams) if exams else 0.0
        }
        
        response = {'results': all_results, 'errors': errors, 'processing_stats': processing_stats, 'equivalence_groups': equivalence_groups}
        record_performance('parse_batch', processing_stats['processing_time_ms'], len(exams), len(errors) == 0)
        
        if not errors:
            return jsonify(response), 200
        elif len(errors) / len(exams) < 0.5:
            return jsonify(response), 207
        else:
            return jsonify(response), 500
        
    except Exception as e:
        logger.error(f"Batch parse endpoint error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse_batch', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """
    Lightweight health check endpoint.
    Crucially, this DOES NOT call _ensure_app_is_initialized() so it can respond instantly.
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'app_initialized': _app_initialized  # Useful for debugging to see if loading has occurred
    })

# --- All other endpoints from your original file go here ---
# --- REMEMBER to add _ensure_app_is_initialized() to each one ---

@app.route('/parse_batch_chunked', methods=['POST'])
def parse_batch_chunked():
    _ensure_app_is_initialized()
    # (The rest of your original function code...)
    start_time = time.time()
    try:
        data = request.json
        if not data or 'exams' not in data:
            return jsonify({"error": "Missing exams array"}), 400
        exams = data['exams']
        chunk_size = data.get('chunk_size', 1000)
        all_results, all_errors, total_cache_hits = [], [], 0
        total_chunks = (len(exams) + chunk_size - 1) // chunk_size
        logger.info(f"Processing {len(exams)} exams in {total_chunks} chunks of {chunk_size}")
        for chunk_idx in range(0, len(exams), chunk_size):
            # (Your original chunk processing logic)
            # ...
            pass # Placeholder for your logic
        # (Your original response generation)
        return jsonify({"status": "placeholder for your logic"})
    except Exception as e:
        logger.error(f"Chunked batch parse endpoint error: {e}")
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
        scispacy_entities = extract_scispacy_entities(exam_name)
        parsed_result = semantic_parser.parse_exam_name(exam_name, data.get('modality_code', 'Unknown'), scispacy_entities)
        quality_metrics = standardization_engine.calculate_quality_metrics(exam_name, parsed_result)
        is_valid = quality_metrics['overall_quality'] >= 0.7
        response = {
            'valid': is_valid,
            'quality_score': quality_metrics['overall_quality'],
            'warnings': quality_metrics['flags'],
            'suggestions': quality_metrics['suggestions'],
            'normalized_name': normalized['normalized'],
            'transformations_applied': normalized['transformations_applied'],
            'metadata': {'processing_time_ms': int((time.time() - start_time) * 1000)}
        }
        record_performance('validate', response['metadata']['processing_time_ms'], len(exam_name), True)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Validation endpoint error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('validate', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/feedback', methods=['POST'])
def submit_feedback():
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
        else: # correction
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
        logger.error(f"Feedback endpoint error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('feedback', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500


# (Add all other endpoints here, following the same pattern)

# --- Background Task ---
def cleanup_old_data():
    """Clean up old cached data."""
    _ensure_app_is_initialized() # Also ensure init for background tasks
    try:
        db_manager.cleanup_old_cache(days=30)
        logger.info("Old cache data cleaned up")
    except Exception as e:
        logger.error(f"Cache cleanup error: {e}")

# Start background cleanup task
cleanup_thread = threading.Thread(target=cleanup_old_data, daemon=True)
cleanup_thread.start()


# --- FEEDBACK TRAINING ENDPOINTS ---

@app.route('/feedback/submit', methods=['POST'])
def submit_feedback():
    """Submit user feedback for active learning"""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        required_fields = ['original_exam_name', 'predicted_clean_name', 'feedback_type']
        
        if not data or not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        if data['feedback_type'] not in ['correct', 'incorrect', 'suggestion']:
            return jsonify({"error": "Invalid feedback_type"}), 400
        
        # Submit feedback
        feedback_id = feedback_manager.submit_user_feedback(data)
        
        response = {
            'feedback_id': feedback_id,
            'status': 'received',
            'message': 'Feedback submitted successfully',
            'processing_time_ms': int((time.time() - start_time) * 1000)
        }
        
        record_performance('feedback_submit', response['processing_time_ms'], 1, True)
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('feedback_submit', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/feedback/stats', methods=['GET'])
def get_feedback_stats():
    """Get feedback statistics for monitoring"""
    _ensure_app_is_initialized()
    
    try:
        days = request.args.get('days', 30, type=int)
        stats = feedback_manager.get_feedback_stats(days)
        
        return jsonify({
            'stats': stats,
            'period_days': days,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Feedback stats error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/parse_with_learning', methods=['POST'])
def parse_with_learning():
    """Enhanced parsing endpoint that uses learned patterns from feedback"""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name"}), 400

        exam_name = data['exam_name']
        modality = data.get('modality_code', 'Unknown')
        organization = data.get('organization', data.get('DATA_SOURCE'))

        cache_key = f"learning_{exam_name}|{modality}|{organization}"
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return jsonify(cached_result)

        # Use feedback-enhanced preprocessor
        result = feedback_enhanced_preprocessor.preprocess_exam_name(
            exam_name, modality, organization
        )
        
        # Convert to API format
        components = result.get('components', {})
        best_match = result.get('best_match')
        
        response = {
            'cleanName': best_match['clean_name'] if best_match else components.get('expanded', exam_name),
            'anatomy': components.get('anatomy', []),
            'laterality': components.get('laterality'),
            'contrast': components.get('contrast'),
            'technique': [],
            'gender_context': components.get('gender_context'),
            'clinical_context': [],
            'confidence': result.get('confidence', 0.0),
            'snomed': best_match.get('snomed_data', {}) if best_match else {},
            'modality': components.get('modality', modality),
            'is_paediatric': components.get('is_paediatric', False),
            'learning_metadata': result.get('learning_metadata', {}),
            'source': result.get('source', 'base_preprocessor')
        }
        
        cache_manager.set(cache_key, response)
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse_with_learning', processing_time, len(exam_name), True)
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Parse with learning endpoint error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse_with_learning', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/admin/retrain', methods=['POST'])
def retrain_patterns():
    """Administrative endpoint to retrain patterns from feedback"""
    _ensure_app_is_initialized()
    
    try:
        # Check if admin authentication is needed
        auth_header = request.headers.get('Authorization')
        # Add your authentication logic here
        
        feedback_manager.retrain_patterns()
        
        return jsonify({
            'status': 'completed',
            'message': 'Patterns retrained successfully',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Retraining error: {e}")
        return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    # For local development, initialize immediately for easier debugging.
    # On a production server (like Render), this block is not executed.
    logger.info("Running in local development mode, initializing app immediately.")
    _ensure_app_is_initialized()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))