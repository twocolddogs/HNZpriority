import time, json, logging, threading, os, sys, multiprocessing, signal, atexit
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import List, Dict, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from parser import RadiologySemanticParser
from nlp_processor import NLPProcessor # Simplified import
from nhs_lookup_engine import NHSLookupEngine
from database_models import DatabaseManager, CacheManager
from feedback_training import FeedbackTrainingManager
from parsing_utils import AbbreviationExpander, AnatomyExtractor, LateralityDetector, USAContrastMapper
from cache_version import get_current_cache_version, format_cache_key

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Simplified globals
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

def _initialize_model_processors() -> Dict[str, NLPProcessor]:
    """Initialize available NLP processors for different models"""
    MODEL_MAPPING = {
        'default': 'sentence-transformers/all-MiniLM-L6-v2',
        'pubmed': 'NeuML/pubmedbert-base-embeddings'
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

# Graceful shutdown handling
_active_workers = set()
_shutdown_requested = False
_worker_lock = threading.Lock()

def _initialize_app():
    global semantic_parser, db_manager, cache_manager, feedback_manager, \
           nlp_processor, model_processors, nhs_lookup_engine, abbreviation_expander
    logger.info("--- Performing first-time application initialization... ---")
    start_time = time.time()
    try:
        db_manager = DatabaseManager(); cache_manager = CacheManager(); feedback_manager = FeedbackTrainingManager()
        logger.info("Database, Cache, and Feedback managers initialized.")

        # Initialize model mapping and processors
        model_processors = _initialize_model_processors()
        nlp_processor = model_processors.get('default')  # Default processor for compatibility
        if not nlp_processor or not nlp_processor.is_available():
            logger.error("API-based NLP processor is not available (HUGGING_FACE_TOKEN missing?). Semantic features will be degraded.")

        base_dir = os.path.dirname(os.path.abspath(__file__))
        nhs_json_path = os.path.join(base_dir, 'core', 'NHS.json')
        usa_json_path = os.path.join(base_dir, 'core', 'USA.json')
        nhs_authority = {}
        if os.path.exists(nhs_json_path):
            with open(nhs_json_path, 'r', encoding='utf-8') as f: nhs_data = json.load(f)
            for item in nhs_data:
                if clean_name := item.get('Clean Name'): nhs_authority[clean_name] = item
        else: logger.critical(f"CRITICAL: NHS JSON file not found at {nhs_json_path}"); sys.exit(1)
        
        usa_patterns = {} # Simplified loading for this example

        ### REFACTOR: INITIALIZATION ORDER IS NOW CRITICAL ###
        
        # 1. First, create all the component utilities for the parser.
        abbreviation_expander = AbbreviationExpander(usa_patterns)
        anatomy_extractor = AnatomyExtractor(nhs_authority, usa_patterns)
        laterality_detector = LateralityDetector()
        contrast_mapper = USAContrastMapper()
        
        # 2. Then, create the Semantic Parser which depends on them.
        semantic_parser = RadiologySemanticParser(
            nlp_processor=nlp_processor, 
            anatomy_extractor=anatomy_extractor,
            laterality_detector=laterality_detector, 
            contrast_mapper=contrast_mapper
        )
        logger.info("RadiologySemanticParser initialized.")
        
        # 3. Finally, create the Lookup Engine and INJECT the parser into it for unified logic.
        nhs_lookup_engine = NHSLookupEngine(
            nhs_json_path=nhs_json_path, 
            nlp_processor=nlp_processor,
            semantic_parser=semantic_parser  # <-- The crucial injection
        )
        
        nhs_lookup_engine.validate_consistency()
        logger.info("All components initialized successfully with unified parsing logic.")
        logger.info(f"Initialization complete in {time.time() - start_time:.2f} seconds.")

    except Exception as e:
        logger.critical(f"FATAL: Failed to initialize components: {e}", exc_info=True); sys.exit(1)

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
    """Preprocess exam name to clean up common formatting issues."""
    if not exam_name: return exam_name
    cleaned = exam_name
    
    # Strip "NO REPORT" suffix that appears in some data sources
    if cleaned.upper().endswith(" - NO REPORT"):
        cleaned = cleaned[:-len(" - NO REPORT")].strip()
    elif cleaned.upper().endswith("- NO REPORT"):
        cleaned = cleaned[:-len("- NO REPORT")].strip()
    elif cleaned.upper().endswith("NO REPORT"):
        cleaned = cleaned[:-len("NO REPORT")].strip()
    
    # Remove administrative qualifiers that don't affect semantic meaning
    import re
    cleaned = re.sub(r'\s*\(non-acute\)\s*', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*\(acute\)\s*', ' ', cleaned, flags=re.IGNORECASE)
    
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
    """Normalize ordinal numbers in obstetric exam names for better parsing."""
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
    """Detect gender/pregnancy context from exam name and anatomy."""
    import re
    exam_lower = exam_name.lower()
    
    # Debug logging for gender detection
    if 'female' in exam_lower or 'male' in exam_lower:
        logger.info(f"DEBUG: Gender detection for '{exam_name}' -> '{exam_lower}'")
    
    pregnancy_patterns = [r'\b(obstetric|pregnancy|prenatal)\b', r'\b(fetal|fetus)\b', r'\b(trimester)\b']
    if any(re.search(p, exam_lower) for p in pregnancy_patterns): 
        logger.info(f"DEBUG: Detected pregnancy context for '{exam_name}'")
        return 'pregnancy'
    
    female_anatomy = ['female pelvis', 'uterus', 'ovary', 'endometrial']
    female_patterns = [r'\b(female)\b', r'\b(woman|women)\b', r'\b(gynecological|gynaecological)\b']
    
    # Check female anatomy terms
    for term in female_anatomy:
        if term.lower() in exam_lower:
            logger.info(f"DEBUG: Detected female anatomy '{term}' in '{exam_name}'")
            return 'female'
    
    # Check female patterns
    for pattern in female_patterns:
        if re.search(pattern, exam_lower):
            logger.info(f"DEBUG: Detected female pattern '{pattern}' in '{exam_name}'")
            return 'female'
    
    male_anatomy = ['prostate', 'testicular', 'scrotal']
    male_patterns = [r'\b(male)\b', r'\b(men)\b']
    
    # Check male anatomy terms
    for term in male_anatomy:
        if term.lower() in exam_lower:
            logger.info(f"DEBUG: Detected male anatomy '{term}' in '{exam_name}'")
            return 'male'
    
    # Check male patterns
    for pattern in male_patterns:
        if re.search(pattern, exam_lower):
            logger.info(f"DEBUG: Detected male pattern '{pattern}' in '{exam_name}'")
            return 'male'
    
    return None

def _detect_age_context(exam_name: str) -> Optional[str]:
    """Detect age context from exam name (e.g., paediatric, adult)."""
    import re
    exam_lower = exam_name.lower()
    pediatric_patterns = [
        r'\b(paediatric|pediatric|paed|peds)\b',
        r'\b(child|children|infant|infants|baby|babies)\b',
        r'\b(newborn|neonate|neonatal)\b',
        r'\b(toddler|adolescent|juvenile)\b'
    ]
    if any(re.search(p, exam_lower) for p in pediatric_patterns): return 'paediatric'
    if any(re.search(p, exam_lower) for p in [r'\b(adult)\b']): return 'adult'
    return None

def _detect_clinical_context(exam_name: str, anatomy: List[str]) -> List[str]:
    """Detect clinical context from exam name."""
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

def process_exam_with_nhs_lookup(exam_name: str, modality_code: str = None, nlp_proc: NLPProcessor = None) -> Dict:
    """NHS-first processing pipeline that uses NHS.json as the single source of truth."""
    _ensure_app_is_initialized()
    if not nhs_lookup_engine or not semantic_parser:
        logger.error("Core components (NHS Engine or Parser) not available")
        return {'error': 'Core components not initialized'}
    try:
        # 1. Preprocess the raw input string
        cleaned_exam_name = _preprocess_exam_name(exam_name)
        
        # 2. Parse the cleaned input string to get its components
        # Use provided NLP processor or fall back to global default
        active_nlp = nlp_proc or nlp_processor
        if nlp_proc and nlp_proc != nlp_processor:
            # Create temporary parser with custom NLP processor
            temp_parser = RadiologySemanticParser(
                nlp_processor=nlp_proc,
                anatomy_extractor=semantic_parser.anatomy_extractor,
                laterality_detector=semantic_parser.laterality_detector,
                contrast_mapper=semantic_parser.contrast_mapper
            )
            parsed_result = temp_parser.parse_exam_name(cleaned_exam_name, modality_code or 'Other')
        else:
            parsed_result = semantic_parser.parse_exam_name(cleaned_exam_name, modality_code or 'Other')
        
        # 3. Use the cleaned name and its parsed components to find the best match in the NHS dataset
        nhs_result = nhs_lookup_engine.standardize_exam(cleaned_exam_name, parsed_result)
        
        # 4. Format the final output
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
            'age_context': _detect_age_context(cleaned_exam_name)
        }
    except Exception as e:
        logger.error(f"Error processing exam '{exam_name}': {e}", exc_info=True)
        return {'error': str(e)}

def _adapt_nhs_to_legacy_format(nhs_result: Dict, original_exam_name: str, cleaned_exam_name: str) -> Dict:
    """Adapts the output of the modern NHS lookup to the legacy /parse endpoint format."""
    if 'error' in nhs_result: return {'error': nhs_result['error']}
    
    # The new nhs_result already contains the structured components from the best match
    anatomy = [a for a in nhs_result.get('anatomy', []) if a]
    laterality = (nhs_result.get('laterality') or [None])[0]
    contrast = (nhs_result.get('contrast') or [None])[0]
    modality = (nhs_result.get('modality') or ['Unknown'])[0]
    technique = nhs_result.get('technique', [])

    snomed_data = {
        'snomed_concept_id': nhs_result.get('snomed_id'),
        'snomed_fsn': nhs_result.get('snomed_fsn'),
        # These fields may not be available in the new model, add placeholder
        'snomed_laterality_concept_id': None,
        'snomed_laterality_fsn': None
    }
    
    return {
        'cleanName': nhs_result.get('clean_name'),
        'anatomy': anatomy,
        'laterality': laterality,
        'contrast': contrast,
        'technique': technique,
        'gender_context': _detect_gender_context(cleaned_exam_name, anatomy),
        'age_context': _detect_age_context(cleaned_exam_name),
        'clinical_context': _detect_clinical_context(cleaned_exam_name, anatomy),
        'confidence': nhs_result.get('confidence', 0.0),
        'snomed': snomed_data,
        'equivalence': {'clinical_equivalents': [], 'procedural_equivalents': []},
        'is_paediatric': _detect_age_context(cleaned_exam_name) == 'paediatric',
        'modality': modality,
        'parsing_method': 'unified_nhs_lookup_v4', # Updated version
        'original_exam_name': original_exam_name,
        'cleaned_exam_name': cleaned_exam_name
    }

# --- API Endpoints (No changes needed from here down) ---
@app.route('/health', methods=['GET'])
def health_check():
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
def parse_exam():
    """Legacy parsing endpoint, now unified to use the modern NHS-first lookup pipeline."""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    # Register worker for tracking
    worker_id = f"parse_{int(time.time() * 1000000)}"
    if not _register_worker(worker_id):
        return jsonify({"error": "Server shutting down"}), 503
    
    try:
        data = request.json
        if not data or 'exam_name' not in data: return jsonify({"error": "Missing exam_name"}), 400
        exam_name = data['exam_name']
        modality = data.get('modality_code')
        cache_version = get_current_cache_version()
        cache_key = format_cache_key("unified", cache_version, exam_name, modality or 'None')
        if cached_result := cache_manager.get(cache_key): return jsonify(cached_result)
        
        # The core processing logic is now centralized
        nhs_result = process_exam_with_nhs_lookup(exam_name, modality)
        cleaned_exam_name = _preprocess_exam_name(exam_name) # Needed for adapter
        adapted_result = _adapt_nhs_to_legacy_format(nhs_result, exam_name, cleaned_exam_name)
        
        cache_manager.set(cache_key, adapted_result)
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse', processing_time, len(exam_name), 'error' not in adapted_result)
        return jsonify(adapted_result)
    except Exception as e:
        logger.error(f"Parse endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    finally:
        _unregister_worker(worker_id)

@app.route('/parse_enhanced', methods=['POST'])
def parse_enhanced():
    """Enhanced parsing endpoint using the new hybrid NLP parser."""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    # Register worker for tracking
    worker_id = f"parse_enhanced_{int(time.time() * 1000000)}"
    if not _register_worker(worker_id):
        return jsonify({"error": "Server shutting down"}), 503
    
    try:
        data = request.json
        if not data or 'exam_name' not in data: return jsonify({"error": "Missing exam_name"}), 400
        exam_name, modality, model = data['exam_name'], data.get('modality_code'), data.get('model', 'default')
        
        # Get the appropriate NLP processor for the selected model
        selected_nlp_processor = _get_nlp_processor(model)
        logger.info(f"Using model '{model}' for exam: {exam_name}")

        cache_version = get_current_cache_version()
        cache_key = format_cache_key("enhanced", cache_version, f"{exam_name}_{model}", modality or 'None')
        if cached_result := cache_manager.get(cache_key): return jsonify(cached_result)

        result = process_exam_with_nhs_lookup(exam_name, modality, selected_nlp_processor)
        cleaned_exam_name = _preprocess_exam_name(exam_name)
        
        anatomy = [a for a in result.get('anatomy', []) if a]
        laterality = [l for l in result.get('laterality', []) if l]
        contrast = [c for c in result.get('contrast', []) if c]
        modality_list = [m for m in result.get('modality', []) if m]

        response = {
            'clean_name': result.get('clean_name', ''),
            'snomed': {'id': result.get('snomed_id', ''), 'fsn': result.get('snomed_fsn', ''), 'found': result.get('snomed_found', False)},
            'components': {
                'anatomy': anatomy, 
                'laterality': laterality, 
                'contrast': contrast, 
                'technique': result.get('technique', []), 
                'modality': modality_list, 
                'confidence': result.get('confidence', 0.0),
                'gender_context': _detect_gender_context(cleaned_exam_name, anatomy),
                'age_context': _detect_age_context(cleaned_exam_name),
                'clinical_context': _detect_clinical_context(cleaned_exam_name, anatomy),
                'clinical_equivalents': []
            },
            'metadata': {'processing_time_ms': int((time.time() - start_time) * 1000), 'confidence': result.get('confidence', 0.0), 'source': result.get('source')}
        }
        
        cache_manager.set(cache_key, response)

        record_performance('parse_enhanced', response['metadata']['processing_time_ms'], len(exam_name), True)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Enhanced parse endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500
    finally:
        _unregister_worker(worker_id)

@app.route('/parse_batch', methods=['POST'])
def parse_batch():
    """Optimized batch processing using the new hybrid parser."""
    _ensure_app_is_initialized()
    start_time = time.time()
    try:
        data = request.json
        if not data or 'exams' not in data: return jsonify({"error": "Missing exams array"}), 400
        exams = data['exams']
        model = data.get('model', 'default')
        
        # Get the appropriate NLP processor for the selected model
        selected_nlp_processor = _get_nlp_processor(model)
        logger.info(f"Using model '{model}' for batch processing of {len(exams)} exams")
            
        results, errors, cache_hits, uncached_exams, cached_results = [], [], 0, [], []
        cache_version = get_current_cache_version()
        for exam_data in exams:
            cache_key = format_cache_key("batch", cache_version, f"{exam_data['exam_name']}_{model}", exam_data.get('modality_code', 'Unknown'))
            if cached := cache_manager.get(cache_key):
                cached_results.append({"input": exam_data, "output": cached})
                cache_hits += 1
            else:
                uncached_exams.append(exam_data)
        if uncached_exams:
            def process_exam_batch(exam_data):
                try:
                    result = process_exam_with_nhs_lookup(exam_data.get('exam_name', ''), exam_data.get('modality_code'), selected_nlp_processor)
                    # Adapt the output for batch response format
                    anatomy = [a for a in result.get('anatomy', []) if a]
                    laterality = [l for l in result.get('laterality', []) if l]
                    contrast = [c for c in result.get('contrast', []) if c]
                    modality_list = [m for m in result.get('modality', []) if m]
                    
                    return {
                        'clean_name': result.get('clean_name', ''), 
                        'snomed': {'id': result.get('snomed_id', ''), 'fsn': result.get('snomed_fsn', ''), 'found': result.get('snomed_found', False)}, 
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
                        if 'error' in result: errors.append({"error": result['error'], "original_exam": exam_data})
                        else:
                            results.append({"input": exam_data, "output": result})
                            cache_key = format_cache_key("batch", cache_version, exam_data['exam_name'], exam_data.get('modality_code', 'Unknown'))
                            cache_manager.set(cache_key, result)
                finally:
                    _unregister_worker(batch_worker_id)
        
        all_results = cached_results + results
        processing_stats = {'total_processed': len(exams), 'successful': len(all_results), 'errors': len(errors), 'cache_hits': cache_hits, 'processing_time_ms': int((time.time() - start_time) * 1000), 'cache_hit_ratio': cache_hits / len(exams) if exams else 0.0}
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
        if not data or 'exam_name' not in data: return jsonify({"error": "Missing exam_name"}), 400
        exam_name, modality_code = data['exam_name'], data.get('modality_code')
        parsed_result = process_exam_with_nhs_lookup(exam_name, modality_code)
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
        result = process_exam_with_nhs_lookup(exam_name, modality)
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


if __name__ == '__main__':
    logger.info("Running in local development mode, initializing app immediately.")
    _setup_signal_handlers()
    _ensure_app_is_initialized()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))