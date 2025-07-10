import spacy
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- App Initialization ---
app = Flask(__name__)
CORS(app)  # Allows our frontend to call the API

# --- START: LAZY LOADING IMPLEMENTATION ---

# 1. Initialize all heavy components as None. They will be loaded on the first request.
nlp = None
db_manager = None
cache_manager = None
model_manager = None
standardization_engine = None
semantic_parser = None

# 2. Create a lock to ensure initialization only happens once, even with multiple threads.
_init_lock = threading.Lock()
_app_initialized = False

def _initialize_app():
    """
    This function contains all the slow, heavy loading.
    It will only be called once, controlled by the _ensure_app_is_initialized function.
    """
    global nlp, db_manager, cache_manager, model_manager, standardization_engine, semantic_parser

    logger.info("--- Performing one-time application initialization... ---")
    start_time = time.time()

    try:
        # Import our enhanced components
        from parser import RadiologySemanticParser
        from standardization_engine import StandardizationEngine
        from database_models import DatabaseManager, CacheManager
        from model_manager import ModelManager

        # Initialize enhanced components
        db_manager = DatabaseManager()
        cache_manager = CacheManager()
        model_manager = ModelManager()
        standardization_engine = StandardizationEngine(db_manager=db_manager)
        semantic_parser = RadiologySemanticParser(
            db_manager=db_manager,
            standardization_engine=standardization_engine,
            model_manager=model_manager
        )
        logger.info("Core components initialized.")

    except Exception as e:
        logger.error(f"FATAL: Failed to initialize core components: {e}")
        # In case of failure, create dummy components to prevent crashes
        class DummyComponent:
            def __getattr__(self, name):
                return lambda *args, **kwargs: None

        db_manager = db_manager or DummyComponent()
        cache_manager = cache_manager or DummyComponent()
        model_manager = model_manager or DummyComponent()
        standardization_engine = standardization_engine or DummyComponent()
        semantic_parser = semantic_parser or DummyComponent()

    # --- Load Models on Startup ---
    logger.info("Loading ScispaCy model...")
    try:
        # This model was installed by the build.sh script
        nlp = spacy.load("en_core_sci_sm")
        logger.info("ScispaCy model loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading ScispaCy model: {e}")
        logger.warning("App will continue without ScispaCy NLP features")
        nlp = None

    # Load ML models via ModelManager
    logger.info("Loading ML models...")
    try:
        if model_manager and hasattr(model_manager, 'load_ml_models'):
            ml_models_loaded = model_manager.load_ml_models()
            if ml_models_loaded:
                logger.info("All ML models loaded successfully.")
            else:
                logger.warning("Some ML models failed to load. Check model files.")
    except Exception as e:
        logger.error(f"Failed to load ML models: {e}")

    # --- Load Data Files ---
    logger.info("Loading SNOMED and Abbreviations data...")
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'base_code_set.csv')
        if os.path.exists(csv_path) and db_manager and hasattr(db_manager, 'load_snomed_from_csv'):
            db_manager.load_snomed_from_csv(csv_path)
            logger.info("SNOMED data loaded.")
        else:
            logger.warning(f"SNOMED data file not found at {csv_path}")

        abbreviations_csv_path = os.path.join(os.path.dirname(__file__), 'abbreviations.csv')
        if os.path.exists(abbreviations_csv_path) and db_manager and hasattr(db_manager, 'load_abbreviations_from_csv'):
            db_manager.load_abbreviations_from_csv(abbreviations_csv_path)
            logger.info("Abbreviations data loaded.")
        else:
            logger.warning(f"Abbreviations file not found at {abbreviations_csv_path}")
    except Exception as e:
        logger.error(f"Failed to load reference data files: {e}")

    logger.info(f"--- One-time initialization completed in {time.time() - start_time:.2f} seconds. ---")

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

def extract_scispacy_entities(exam_name: str) -> Dict:
    """Extract entities using ScispaCy with proper error handling."""
    _ensure_app_is_initialized()
    scispacy_entities = {'ANATOMY': [], 'DIRECTION': []}
    
    if nlp is None:
        logger.debug("ScispaCy model not available, returning empty entities")
        return scispacy_entities
    
    try:
        doc = nlp(exam_name)
        for ent in doc.ents:
            if ent.label_ in ['ANATOMY', 'BODY_PART_OR_ORGAN']:
                scispacy_entities['ANATOMY'].append(ent.text.capitalize())
            elif ent.label_ == 'DIRECTION':
                scispacy_entities['DIRECTION'].append(ent.text.capitalize())
    except Exception as e:
        logger.error(f"ScispaCy processing failed for '{exam_name}': {e}")
    
    return scispacy_entities

def extract_scispacy_entities_batch(exam_names: List[str]) -> List[Dict]:
    """Extract entities for multiple exam names in batch with robust error handling."""
    _ensure_app_is_initialized()
    if not nlp:
        logger.debug("ScispaCy model not available, returning empty entities for batch")
        return [{'ANATOMY': [], 'DIRECTION': []} for _ in exam_names]
    
    if not exam_names:
        return []
    
    results = []
    
    try:
        batch_size = 100
        for i in range(0, len(exam_names), batch_size):
            batch = exam_names[i:i+batch_size]
            try:
                docs = nlp.pipe(batch)
                for doc in docs:
                    entities = {'ANATOMY': [], 'DIRECTION': []}
                    for ent in doc.ents:
                        if ent.label_ in ['ANATOMY', 'BODY_PART_OR_ORGAN']:
                            entities['ANATOMY'].append(ent.text.capitalize())
                        elif ent.label_ == 'DIRECTION':
                            entities['DIRECTION'].append(ent.text.capitalize())
                    results.append(entities)
            except Exception as e:
                logger.error(f"Batch processing failed for batch {i//batch_size + 1}: {e}")
                for name in batch:
                    results.append(extract_scispacy_entities(name))
    except Exception as e:
        logger.error(f"Batch ScispaCy processing completely failed: {e}")
        results = [extract_scispacy_entities(name) for name in exam_names]
    
    return results

# --- API Endpoints ---
# All endpoints now call _ensure_app_is_initialized() first.

@app.route('/parse', methods=['POST'])
def parse_exam():
    """Original parsing endpoint with enhancements."""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data or 'modality_code' not in data:
            return jsonify({"error": "Missing exam_name or modality_code"}), 400

        exam_name = data['exam_name']
        modality = data['modality_code']

        cache_key = f"{exam_name}|{modality}"
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return jsonify(cached_result)

        scispacy_entities = extract_scispacy_entities(exam_name)
        result = semantic_parser.parse_exam_name(exam_name, modality, scispacy_entities)
        
        response = {
            'cleanName': result['cleanName'],
            'anatomy': result['anatomy'],
            'laterality': result['laterality'],
            'contrast': result['contrast'],
            'technique': result['technique'],
            'gender_context': result['gender_context'],
            'clinical_context': result['clinical_context'],
            'confidence': result['confidence'],
            'clinical_equivalents': result['clinical_equivalents']
        }
        
        cache_manager.set(cache_key, response)
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse', processing_time, len(exam_name), True)
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Parse endpoint error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/parse_enhanced', methods=['POST'])
def parse_enhanced():
    """Enhanced parsing endpoint with full standardization."""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data or 'modality_code' not in data:
            return jsonify({"error": "Missing exam_name or modality_code"}), 400
        
        exam_name = data['exam_name']
        modality = data['modality_code']
        
        cached_result = db_manager.get_cached_result(data)
        if cached_result:
            return jsonify(cached_result)
        
        scispacy_entities = extract_scispacy_entities(exam_name)
        parsed_result = semantic_parser.parse_exam_name(exam_name, modality, scispacy_entities)
        standardized = standardization_engine.normalize_exam_name(exam_name)
        quality_metrics = standardization_engine.calculate_quality_metrics(exam_name, parsed_result)
        
        response = {
            'input': data,
            'standardized': {
                'clean_name': parsed_result['cleanName'],
                'canonical_form': standardized['canonical_form'],
                'normalized_name': standardized['normalized'],
                'components': {
                    'anatomy': parsed_result['anatomy'],
                    'laterality': parsed_result['laterality'],
                    'contrast': parsed_result['contrast'],
                    'technique': parsed_result['technique'],
                    'gender_context': parsed_result['gender_context'],
                    'clinical_context': parsed_result['clinical_context']
                },
                'quality_score': quality_metrics['overall_quality']
            },
            'snomed': parsed_result.get('snomed', {}),
            'quality_metrics': quality_metrics,
            'equivalence': {
                'clinical_equivalents': parsed_result['clinical_equivalents']
            },
            'metadata': {
                'processing_time_ms': int((time.time() - start_time) * 1000),
                'model_version': '2.1.0',
                'confidence': parsed_result['confidence']
            }
        }
        
        db_manager.cache_result(data, response)
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
            exam_names = [exam['exam_name'] for exam in uncached_exams]
            batch_entities = extract_scispacy_entities_batch(exam_names)
            
            def process_exam_batch(exam_data, scispacy_entities):
                try:
                    exam_name = exam_data['exam_name']
                    modality = exam_data['modality_code']
                    parsed_result = semantic_parser.parse_exam_name(exam_name, modality, scispacy_entities)
                    standardized = standardization_engine.normalize_exam_name(exam_name)
                    
                    result = {
                        'input': exam_data,
                        'clean_name': parsed_result['cleanName'],
                        'canonical_form': standardized['canonical_form'],
                        'snomed': parsed_result.get('snomed', {}),
                        'components': {
                            'anatomy': parsed_result['anatomy'],
                            'laterality': parsed_result['laterality'],
                            'contrast': parsed_result['contrast'],
                            'technique': parsed_result['technique'],
                            'gender_context': parsed_result['gender_context'],
                            'clinical_context': parsed_result['clinical_context']
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
                futures = {executor.submit(process_exam_batch, exam, entities): exam for exam, entities in zip(uncached_exams, batch_entities)}
                for future in as_completed(futures):
                    result = future.result()
                    if 'error' in result:
                        errors.append(result)
                    else:
                        results.append(result)
        
        all_results = cached_results + results
        
        cache_items = {f"{res['input']['exam_name']}|{res['input']['modality_code']}": res for res in results if 'input' in res}
        if cache_items:
            cache_manager.bulk_set(cache_items)
        
        equivalence_groups = standardization_engine.find_equivalence_groups([{'name': r['clean_name'], 'source': r['input'].get('source', 'unknown')} for r in all_results])
        
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


if __name__ == '__main__':
    # For local development, initialize immediately for easier debugging.
    # On a production server (like Render), this block is not executed.
    logger.info("Running in local development mode, initializing app immediately.")
    _ensure_app_is_initialized()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))