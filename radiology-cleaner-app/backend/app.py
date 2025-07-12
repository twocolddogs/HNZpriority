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
from nhs_lookup_engine import NHSLookupEngine
from database_models import DatabaseManager, CacheManager
from feedback_training import FeedbackTrainingManager, FeedbackEnhancedPreprocessor
from comprehensive_preprocessor import ComprehensivePreprocessor, AbbreviationExpander, AnatomyExtractor, LateralityDetector, USAContrastMapper
from nhs_lookup_engine import NHSLookupEngine

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
nhs_lookup_engine: Optional[NHSLookupEngine] = None
abbreviation_expander: Optional[AbbreviationExpander] = None

# 2. Create a lock to ensure initialization only happens once.
_init_lock = threading.Lock()
_app_initialized = False

def _initialize_app():
    """
    This function contains the main application initialization logic.
    It will only be called once, controlled by _ensure_app_is_initialized.
    """
    global semantic_parser, db_manager, cache_manager, feedback_manager, \
           feedback_enhanced_preprocessor, nlp_processor, comprehensive_preprocessor, nhs_lookup_engine

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
        # You'll need to place your word embedding file (e.g., 'BioWordVec_PubMed_MIMICIII_d200.vec')
        # in a suitable location, e.g., 'backend/resources/'
        base_dir = os.path.dirname(os.path.abspath(__file__))
        word_embedding_file = os.path.join(base_dir, 'resources', 'BioWordVec_PubMed_MIMICIII_d200.vec') # Example path
        nlp_processor = NLPProcessor(word_embedding_path=word_embedding_file)
        if not nlp_processor.nlp:
            logger.error("NLP Processor failed to initialize. Parsing will be limited to rules.")
        if not nlp_processor.word_vectors:
            logger.warning("Word embeddings not loaded. Semantic similarity will be disabled.")

        # Initialize the core parser
        semantic_parser = RadiologySemanticParser(nlp_processor=nlp_processor)
        
        # --- CORRECTED FILE PATHS ---
        # Build absolute paths from the directory where this script (app.py) is located.
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # This preprocessor is from your original code, initialize it with correct paths
        nhs_json_path = os.path.join(base_dir, 'core', 'NHS.json')
        usa_json_path = os.path.join(base_dir, 'core', 'USA.json')
        
        usa_patterns = {}
        if os.path.exists(usa_json_path):
            try:
                with open(usa_json_path, 'r', encoding='utf-8') as f:
                    usa_data = json.load(f)
                # Extract patterns from USA data for AbbreviationExpander
                for item in usa_data:
                    short_name = item.get('SHORT_NAME', '')
                    long_name = item.get('LONG_NAME', '')
                    if short_name and long_name:
                        short_words = short_name.split()
                        long_words = long_name.split()
                        for short_word in short_words:
                            if len(short_word) <= 4:  # Likely abbreviation
                                for long_word in long_words:
                                    if long_word.lower().startswith(short_word.lower()):
                                        usa_patterns[short_word.lower()] = long_word.lower()
            except Exception as e:
                logger.warning(f"Failed to load or parse USA.json: {e}")
        else:
            logger.warning(f"USA JSON file not found at {usa_json_path}")

        global abbreviation_expander, anatomy_extractor
        
        # Initialize ComprehensivePreprocessor first to get usa_patterns
        comprehensive_preprocessor = None
        if os.path.exists(nhs_json_path):
            comprehensive_preprocessor = ComprehensivePreprocessor(nhs_json_path, usa_json_path if os.path.exists(usa_json_path) else None)
            logger.info("Comprehensive preprocessor initialized.")
        else:
            logger.error(f"CRITICAL: NHS JSON file not found at {nhs_json_path}")

        # Initialize AbbreviationExpander with patterns from comprehensive_preprocessor
        if comprehensive_preprocessor and hasattr(comprehensive_preprocessor, 'usa_patterns'):
            abbreviation_expander = AbbreviationExpander(comprehensive_preprocessor.usa_patterns)
            logger.info("Abbreviation expander initialized.")
        else:
            abbreviation_expander = AbbreviationExpander({}) # Fallback to empty patterns
            logger.warning("Abbreviation expander initialized with empty patterns due to missing ComprehensivePreprocessor or usa_patterns.")

        # Initialize AnatomyExtractor using the loaded NHS data and usa_patterns
        if comprehensive_preprocessor and hasattr(comprehensive_preprocessor, 'nhs_authority') and hasattr(comprehensive_preprocessor, 'usa_patterns'):
            anatomy_extractor = AnatomyExtractor(comprehensive_preprocessor.nhs_authority, comprehensive_preprocessor.usa_patterns)
            logger.info("Anatomy extractor initialized.")
        else:
            anatomy_extractor = AnatomyExtractor({}) # Fallback to empty authority
            logger.warning("Anatomy extractor initialized with empty authority due to missing ComprehensivePreprocessor or nhs_authority/usa_patterns.")

        # Initialize LateralityDetector and USAContrastMapper
        laterality_detector = LateralityDetector()
        contrast_mapper = USAContrastMapper()
        logger.info("Laterality and Contrast detectors initialized.")

        # Initialize the core parser with the anatomy extractor
        semantic_parser = RadiologySemanticParser(nlp_processor=nlp_processor, anatomy_extractor=anatomy_extractor, laterality_detector=laterality_detector, contrast_mapper=contrast_mapper)

        # Load SNOMED data into database (moved after comprehensive_preprocessor init)
        json_path = os.path.join(base_dir, 'code_set.json')
        if os.path.exists(json_path):
            db_manager.load_snomed_from_json(json_path)
            logger.info("SNOMED data loaded from JSON into database.")
        else:
            logger.warning(f"SNOMED JSON file not found at {json_path}")

        # Initialize NHS Lookup Engine - the single source of truth
        if os.path.exists(nhs_json_path):
            nhs_lookup_engine = NHSLookupEngine(nhs_json_path, nlp_processor)
            # Validate NHS data consistency
            consistency_report = nhs_lookup_engine.validate_consistency()
            logger.info(f"NHS Lookup Engine initialized: {consistency_report}")
        else:
            logger.error(f"CRITICAL: NHS JSON file not found at {nhs_json_path}")
            nhs_lookup_engine = None

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

def _preprocess_exam_name(exam_name: str) -> str:
    """
    Preprocess exam name to clean up common formatting issues.
    """
    if not exam_name:
        return exam_name
    
    cleaned = exam_name

    if abbreviation_expander:
        cleaned = abbreviation_expander.expand(cleaned)

    if '^' in cleaned:
        cleaned = cleaned.split('^', 1)[1].strip()
    
    if '/' in cleaned:
        cleaned = cleaned.replace('/', ' ')
    
    cleaned = _normalize_ordinals(cleaned)
    
    cleaned = ' '.join(cleaned.split())
    
    return cleaned

def _normalize_ordinals(text: str) -> str:
    """
    Normalize ordinal numbers in obstetric exam names for better parsing.
    """
    import re
    
    ordinal_replacements = {
        r'\b1ST\b': 'First', r'\b2ND\b': 'Second', r'\b3RD\b': 'Third',
        r'\b1st\b': 'First', r'\b2nd\b': 'Second', r'\b3rd\b': 'Third',
        r'\bfirst\b': 'First', r'\bsecond\b': 'Second', r'\bthird\b': 'Third',
        r'\btrimester\b': 'Trimester', r'\bTRIMESTER\b': 'Trimester',
        r'\bobstetric\b': 'Obstetric', r'\bOBSTETRIC\b': 'Obstetric',
    }
    
    result = text
    for pattern, replacement in ordinal_replacements.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result

def _detect_gender_context(exam_name: str, anatomy: List[str]) -> Optional[str]:
    """
    Detect gender/pregnancy context from exam name and anatomy.
    """
    import re
    exam_lower = exam_name.lower()
    
    pregnancy_patterns = [
        r'\b(obstetric|pregnancy|prenatal)\b', r'\b(fetal|fetus)\b', r'\b(trimester)\b'
    ]
    if any(re.search(p, exam_lower) for p in pregnancy_patterns):
        return 'pregnancy'
    
    female_anatomy = ['female pelvis', 'uterus', 'ovary', 'endometrial']
    if any(term.lower() in exam_lower for term in female_anatomy):
        return 'female'
    
    male_anatomy = ['prostate', 'testicular', 'scrotal']
    if any(term.lower() in exam_lower for term in male_anatomy):
        return 'male'
        
    return None

def _detect_age_context(exam_name: str) -> Optional[str]:
    """
    Detect age context from exam name (e.g., paediatric, adult).
    """
    import re
    exam_lower = exam_name.lower()

    if any(re.search(p, exam_lower) for p in [r'\b(paediatric|pediatric|paed|peds)\b', r'\b(child|infant|newborn)\b']):
        return 'paediatric'
    
    if any(re.search(p, exam_lower) for p in [r'\b(adult)\b']):
        return 'adult'
        
    return None

def _detect_clinical_context(exam_name: str, anatomy: List[str]) -> List[str]:
    """
    Detect clinical context from exam name.
    """
    import re
    exam_lower = exam_name.lower()
    contexts = []
    
    context_patterns = {
        'screening': [r'\b(screening|surveillance)\b'],
        'emergency': [r'\b(emergency|urgent|stat|trauma)\b'],
        'follow-up': [r'\b(follow.?up|post.?op)\b'],
        'intervention': [r'\b(biopsy|drainage|injection)\b']
    }
    
    for context, patterns in context_patterns.items():
        if any(re.search(p, exam_lower) for p in patterns):
            contexts.append(context)
            
    return contexts

def _validate_nhs_match(input_exam_name: str, nhs_clean_name: str, parsed_anatomy: List[str]) -> bool:
    """
    Validate that an NHS official clean name makes sense for the input exam name.
    """
    import re
    input_lower = input_exam_name.lower()
    nhs_lower = nhs_clean_name.lower()
    
    anatomy_terms = [
        'head', 'neck', 'chest', 'abdomen', 'pelvis', 'spine', 'shoulder', 'knee', 'hip'
    ]
    
    input_anatomy = {term for term in anatomy_terms if re.search(r'\b' + term + r'\b', input_lower)}
    nhs_anatomy = {term for term in anatomy_terms if re.search(r'\b' + term + r'\b', nhs_lower)}

    if extra_anatomy := nhs_anatomy - input_anatomy:
        logger.warning(f"NHS match validation failed: Extra anatomy '{extra_anatomy}' in NHS name.")
        return False
        
    return True

def process_exam_with_nhs_lookup(exam_name: str, modality_code: str = None) -> Dict:
    """
    NHS-first processing pipeline that uses NHS.json as the single source of truth.
    """
    _ensure_app_is_initialized()
    
    if not nhs_lookup_engine:
        logger.error("NHS Lookup Engine not available")
        return {'error': 'NHS Lookup Engine not initialized'}
    
    try:
        cleaned_exam_name = _preprocess_exam_name(exam_name)
        
        if semantic_parser:
            parsed_result = semantic_parser.parse_exam_name(cleaned_exam_name, modality_code or 'Other')
        else:
            parsed_result = {}
        
        extracted_components = {
            'modality': [], 'anatomy': [], 'laterality': [], 'contrast': [], 'procedure_type': []
        }

        if modality_code:
            extracted_components['modality'].append(modality_code.lower())
        elif parsed_result.get('modality'):
            extracted_components['modality'].append(parsed_result['modality'].lower())

        if parsed_result.get('anatomy'):
            extracted_components['anatomy'].extend([a.lower() for a in parsed_result['anatomy']])
        if parsed_result.get('laterality'):
            extracted_components['laterality'].append(parsed_result['laterality'].lower())
        if parsed_result.get('contrast'):
            extracted_components['contrast'].append(parsed_result['contrast'].lower())

        for key in extracted_components:
            extracted_components[key] = list(set(extracted_components[key]))
        
        nhs_result = nhs_lookup_engine.standardize_exam(exam_name, extracted_components)
        
        result = {
            'input_exam': exam_name,
            'cleaned_exam': cleaned_exam_name,
            'clean_name': nhs_result['clean_name'],
            'anatomy': extracted_components['anatomy'],
            'laterality': extracted_components['laterality'],
            'modality': extracted_components['modality'],
            'contrast': extracted_components['contrast'],
            'snomed_id': nhs_result['snomed_id'],
            'snomed_fsn': nhs_result['snomed_fsn'],
            'confidence': nhs_result['confidence'],
            'source': nhs_result['source'],
            'snomed_found': bool(nhs_result['snomed_id']),
            'age_context': _detect_age_context(cleaned_exam_name)
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing exam '{exam_name}': {e}", exc_info=True)
        return {'error': str(e)}

# --- HELPER FUNCTIONS FOR ENDPOINTS ---
def _adapt_nhs_to_legacy_format(nhs_result: Dict, original_exam_name: str, cleaned_exam_name: str) -> Dict:
    """Adapts the output of the modern NHS lookup to the legacy /parse endpoint format."""
    if 'error' in nhs_result:
        return {'error': nhs_result['error']}

    snomed_data = {
        'snomed_concept_id': nhs_result.get('snomed_id'),
        'snomed_fsn': nhs_result.get('snomed_fsn'),
        'snomed_laterality_concept_id': nhs_result.get('laterality_snomed'),
        'snomed_laterality_fsn': nhs_result.get('laterality_fsn')
    }

    return {
        'cleanName': nhs_result.get('clean_name'),
        'anatomy': nhs_result.get('anatomy', []),
        'laterality': (nhs_result.get('laterality') or [None])[0],
        'contrast': (nhs_result.get('contrast') or [None])[0],
        'technique': nhs_result.get('technique', []),
        'gender_context': _detect_gender_context(cleaned_exam_name, nhs_result.get('anatomy', [])),
        'age_context': _detect_age_context(cleaned_exam_name),
        'clinical_context': _detect_clinical_context(cleaned_exam_name, nhs_result.get('anatomy', [])),
        'confidence': nhs_result.get('confidence', 0.0),
        'snomed': snomed_data,
        'equivalence': {'clinical_equivalents': [], 'procedural_equivalents': []},
        'is_paediatric': _detect_age_context(cleaned_exam_name) == 'paediatric',
        'modality': (nhs_result.get('modality') or ['Unknown'])[0],
        'parsing_method': 'unified_nhs_lookup',
        'original_exam_name': original_exam_name,
        'cleaned_exam_name': cleaned_exam_name
    }

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
    """Legacy parsing endpoint, now unified to use the modern NHS-first lookup pipeline."""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name"}), 400

        exam_name = data['exam_name']
        modality = data.get('modality_code')
        
        cache_key = f"unified_{exam_name}|{modality or 'None'}"
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return jsonify(cached_result)

        cleaned_exam_name = _preprocess_exam_name(exam_name)
        nhs_result = process_exam_with_nhs_lookup(cleaned_exam_name, modality)
        adapted_result = _adapt_nhs_to_legacy_format(nhs_result, exam_name, cleaned_exam_name)

        cache_manager.set(cache_key, adapted_result)
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse', processing_time, len(exam_name), 'error' not in adapted_result)
        return jsonify(adapted_result)
        
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
        modality = data.get('modality_code')
        
        cache_key = f"enhanced_v2_{exam_name}|{modality or 'None'}"
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return jsonify(cached_result)

        result = process_exam_with_nhs_lookup(exam_name, modality)
        
        response = {
            'clean_name': result.get('clean_name', ''),
            'snomed': {
                'id': result.get('snomed_id', ''),
                'fsn': result.get('snomed_fsn', ''),
                'found': result.get('snomed_found', False)
            },
            'components': {
                'anatomy': result.get('anatomy', []),
                'laterality': result.get('laterality', []),
                'contrast': result.get('contrast', []),
                'technique': result.get('technique', []),
                'modality': result.get('modality', []),
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
                    result = process_exam_with_nhs_lookup(exam_name, modality_code)
                    
                    formatted_result = {
                        'clean_name': result.get('clean_name', ''),
                        'snomed': {
                            'id': result.get('snomed_id', ''),
                            'fsn': result.get('snomed_fsn', ''),
                            'found': result.get('snomed_found', False)
                        },
                        'components': {
                            'anatomy': result.get('anatomy', []),
                            'laterality': result.get('laterality', []),
                            'contrast': result.get('contrast', []),
                            'technique': result.get('technique', []),
                            'gender_context': result.get('gender_context', ''),
                            'age_context': result.get('age_context', ''),
                            'clinical_context': result.get('clinical_context', []),
                            'confidence': result.get('confidence', 0.0),
                            'modality': result.get('modality', [])
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
    """Validates exam data using the unified NHS-first lookup pipeline."""
    _ensure_app_is_initialized()
    start_time = time.time()
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name"}), 400
        
        exam_name = data['exam_name']
        modality_code = data.get('modality_code')

        parsed_result = process_exam_with_nhs_lookup(exam_name, modality_code)
        
        quality_score = parsed_result.get('confidence', 0.0)
        is_valid = quality_score >= 0.7

        warnings = []
        if not parsed_result.get('snomed_found'):
            warnings.append("No matching SNOMED code found.")
        if not parsed_result.get('anatomy'):
            warnings.append("Could not identify anatomy.")
        if quality_score < 0.5:
            warnings.append("Low confidence parse; result may be unreliable.")

        suggestions = []
        if parsed_result.get('clean_name') and parsed_result['clean_name'] != exam_name:
            suggestions.append(f"Consider using the standardized name: '{parsed_result['clean_name']}'")

        response = {
            'valid': is_valid, 
            'quality_score': quality_score,
            'warnings': warnings, 
            'suggestions': suggestions,
            'normalized_name': parsed_result.get('clean_name', exam_name),
            'transformations_applied': ['unified_processing'],
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
        feedback_id = db_manager.submit_feedback(data) if feedback_type != 'general' else db_manager.submit_general_feedback(data)

        response = {
            'feedback_id': feedback_id, 'type': feedback_type, 'status': 'submitted',
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
    """
    Parses an exam, with a placeholder for future learning enhancements.
    FIXED: This endpoint now calls the unified `process_exam_with_nhs_lookup` pipeline.
    """
    _ensure_app_is_initialized()
    start_time = time.time()
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name"}), 400

        exam_name = data['exam_name']
        modality = data.get('modality_code')

        result = process_exam_with_nhs_lookup(exam_name, modality)
        
        result['metadata'] = {
            'processing_time_ms': int((time.time() - start_time) * 1000),
            'source_endpoint': '/parse_with_learning'
        }
        
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