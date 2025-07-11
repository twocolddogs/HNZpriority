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
        feedback_manager = FeedbackTrainingManager()
        logger.info("Database, Cache, and Feedback managers initialized.")

        # Initialize NLP Processor
        nlp_processor = NLPProcessor()
        if not nlp_processor.nlp:
            logger.error("NLP Processor failed to initialize. Parsing will be limited to rules.")

        # Initialize the core parser
        semantic_parser = RadiologySemanticParser()
        
        # --- CORRECTED FILE PATHS ---
        # Build absolute paths from the directory where this script (app.py) is located.
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # This preprocessor is from your original code, initialize it with correct paths
        nhs_json_path = os.path.join(base_dir, 'core', 'NHS.json')
        usa_json_path = os.path.join(base_dir, 'core', 'USA.json')
        
        if os.path.exists(nhs_json_path):
            # Load SNOMED data from JSON into database first
            json_path = os.path.join(base_dir, 'code_set.json')
            if os.path.exists(json_path):
                db_manager.load_snomed_from_json(json_path)
                logger.info("SNOMED data loaded from JSON into database.")
            else:
                logger.warning(f"SNOMED JSON file not found at {json_path}")
            
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
    
    if not semantic_parser or not comprehensive_preprocessor:
        logger.error("Parser components not available")
        return {'error': 'Parser not initialized'}
    
    try:
        # HYBRID APPROACH: Best of both worlds
        logger.info(f"Processing exam: '{exam_name}' with modality: '{modality_code}'")
        
        # Step 1: Use semantic parser for superior component extraction (NLP + longest-match-first)
        parsed_result = semantic_parser.parse_exam_name(exam_name, modality_code or 'Other')
        logger.debug(f"Semantic parser result: {parsed_result}")
        
        # Step 2: Use comprehensive preprocessor for authority-file mapping to get official standards
        comprehensive_result = comprehensive_preprocessor.preprocess_exam_name(exam_name, modality_code)
        logger.debug(f"Comprehensive preprocessor result: best_match={comprehensive_result.get('best_match') is not None}, confidence={comprehensive_result.get('confidence', 0)}")
        
        # Step 3: Combine the best from both systems
        best_match = comprehensive_result.get('best_match')
        
        # FIXED: Prioritize semantic parser results, use comprehensive preprocessor for official standardization
        anatomy = parsed_result.get('anatomy', [])
        laterality = parsed_result.get('laterality')
        contrast = parsed_result.get('contrast')
        technique = parsed_result.get('technique', [])
        
        # Clean name priority: 1) NHS official name if high confidence, 2) semantic parser construction, 3) enhanced original
        if best_match and comprehensive_result.get('confidence', 0) > 0.7:
            # High confidence NHS match - use official clean name
            clean_name = best_match['clean_name']
            logger.debug(f"Using NHS official clean name: '{clean_name}' (confidence: {comprehensive_result.get('confidence', 0):.2f})")
        elif anatomy and parsed_result.get('modality'):
            # Construct clean name from semantic parser results
            modality = parsed_result.get('modality', '')
            anatomy_str = ' '.join(anatomy)
            laterality_str = f" {laterality}" if laterality else ""
            contrast_str = f" {contrast}" if contrast else ""
            clean_name = f"{modality} {anatomy_str}{laterality_str}{contrast_str}".strip()
            logger.debug(f"Constructed clean name from semantic parser: '{clean_name}' (anatomy: {anatomy}, modality: {modality})")
        else:
            # Fallback to enhanced original
            clean_name = exam_name
            logger.warning(f"No anatomy or modality found, using original name: '{clean_name}'")
        
        # Step 4: Get SNOMED data - FIXED: prioritize semantic parser results
        snomed_data = {}
        
        # Primary: Use constructed clean name and anatomy for database lookup
        if db_manager:
            snomed_match = None
            
            # Try 1: Constructed clean name using clean_name field (e.g., "XR Chest" -> "CT Chest")
            if clean_name and clean_name != exam_name:
                snomed_match = db_manager.get_snomed_code(clean_name)
                if snomed_match:
                    logger.debug(f"Found SNOMED match for constructed clean name: '{clean_name}'")
            
            # Try 2: Fuzzy matching for clean names if exact match failed
            if not snomed_match and clean_name:
                fuzzy_matches = db_manager.fuzzy_match_clean_names(clean_name, threshold=0.8)
                if fuzzy_matches:
                    snomed_match = fuzzy_matches[0]  # Take the best match
                    logger.debug(f"Found SNOMED fuzzy match for clean name: '{clean_name}' -> '{snomed_match['clean_name']}'")
            
            # Try 3: Individual anatomy terms in clean_name field
            if not snomed_match and anatomy:
                for anatomy_term in anatomy:
                    snomed_match = db_manager.get_snomed_code(anatomy_term)
                    if snomed_match:
                        logger.debug(f"Found SNOMED match for anatomy term: '{anatomy_term}'")
                        break
            
            # Try 4: Original exam name in FSN field (for full procedure names)
            if not snomed_match:
                snomed_match = db_manager.get_snomed_reference_by_exam_name(exam_name)
                if snomed_match:
                    logger.debug(f"Found SNOMED match for original exam name: '{exam_name}'")
            
            if snomed_match:
                snomed_data = {
                    'snomed_concept_id': snomed_match.get('snomed_concept_id'),
                    'snomed_fsn': snomed_match.get('snomed_fsn'),
                    'snomed_laterality_concept_id': snomed_match.get('snomed_laterality_concept_id'),
                    'snomed_laterality_fsn': snomed_match.get('snomed_laterality_fsn')
                }
            else:
                logger.debug(f"No SNOMED match found for exam: '{exam_name}', clean_name: '{clean_name}', anatomy: {anatomy}")
        
        # Secondary: Use comprehensive preprocessor's SNOMED data for validation/fallback
        if not snomed_data and best_match and best_match.get('snomed_data'):
            snomed_raw = best_match['snomed_data']
            snomed_data = {
                'snomed_concept_id': snomed_raw.get('snomed_concept_id'),
                'snomed_fsn': snomed_raw.get('snomed_fsn'),
                'snomed_laterality_concept_id': snomed_raw.get('snomed_laterality_id'),
                'snomed_laterality_fsn': snomed_raw.get('snomed_laterality_fsn')
            }
        
        # Step 5: FIXED: Calculate balanced hybrid confidence score
        confidence = 0.0
        
        # Primary: Component extraction confidence (80% - this is the core functionality)
        if anatomy: confidence += 0.4  # Most important - did we identify anatomy?
        if parsed_result.get('modality') and parsed_result['modality'] != 'Other': confidence += 0.2
        if laterality: confidence += 0.1
        if contrast: confidence += 0.05
        if technique: confidence += 0.05
        
        # Secondary: Authority mapping bonus (20% - nice to have but not essential)
        if best_match:
            authority_confidence = comprehensive_result.get('confidence', 0.0)
            confidence += authority_confidence * 0.2
        
        # Bonus: SNOMED data found (10% - indicates successful integration)
        if snomed_data: confidence += 0.1
        
        logger.info(f"Processing complete for '{exam_name}': clean_name='{clean_name}', anatomy={anatomy}, confidence={confidence:.2f}, snomed_found={bool(snomed_data)}")
        
        response = {
            'cleanName': clean_name,
            'anatomy': anatomy,
            'laterality': laterality,
            'contrast': contrast,
            'technique': technique,
            'gender_context': comprehensive_result.get('components', {}).get('gender_context'),
            'clinical_context': [],
            'confidence': min(confidence, 1.0),  # Cap at 1.0
            'snomed': snomed_data,
            'equivalence': {
                'clinical_equivalents': [],
                'procedural_equivalents': []
            },
            'is_paediatric': comprehensive_result.get('components', {}).get('is_paediatric', False),
            'modality': parsed_result.get('modality', modality_code),
            'best_match': best_match,  # Include for debugging
            'parsing_method': 'hybrid'  # Indicate this used the hybrid approach
        }
        return response
    except Exception as e:
        logger.error(f"Hybrid parsing failed for '{exam_name}': {e}", exc_info=True)
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

        # Use the comprehensive hybrid parser that includes SNOMED data
        result = process_exam_with_preprocessor(exam_name, modality)
        
        response = {
            'clean_name': result.get('cleanName', ''),
            'snomed': result.get('snomed', {}),
            'components': {
                'anatomy': result.get('anatomy', []),
                'laterality': result.get('laterality'),
                'contrast': result.get('contrast'),
                'technique': result.get('technique', []),
                'modality': result.get('modality'),
                'confidence': result.get('confidence', 0.0)
            },
            'clinical_equivalents': result.get('equivalence', {}).get('clinical_equivalents', []),
            'metadata': {
                'processing_time_ms': int((time.time() - start_time) * 1000),
                'confidence': result.get('confidence', 0.0),
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
                    exam_name = exam_data.get('exam_name', '')
                    modality_code = exam_data.get('modality_code')
                    result = process_exam_with_preprocessor(exam_name, modality_code)
                    
                    # Format response to match frontend expectations
                    formatted_result = {
                        'clean_name': result.get('cleanName', ''),
                        'snomed': result.get('snomed', {}),
                        'components': {
                            'anatomy': result.get('anatomy', []),
                            'laterality': result.get('laterality'),
                            'contrast': result.get('contrast'),
                            'technique': result.get('technique', []),
                            'gender_context': result.get('gender_context'),
                            'clinical_context': result.get('clinical_context', []),
                            'confidence': result.get('confidence', 0.0),
                            'modality': result.get('modality')
                        },
                        'clinical_equivalents': result.get('equivalence', {}).get('clinical_equivalents', []),
                        'original_exam': exam_data
                    }
                    
                    return formatted_result
                except Exception as e:
                    return {"error": str(e), "original_exam": exam_data}

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
        modality_code = data.get('modality_code')
        parsed_result = process_exam_with_preprocessor(exam_name, modality_code)
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
