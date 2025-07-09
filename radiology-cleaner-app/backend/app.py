import spacy
import joblib
import time
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import List, Dict, Optional
from datetime import datetime
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import our enhanced components
from parser import RadiologySemanticParser
from standardization_engine import StandardizationEngine
from database_models import DatabaseManager, CacheManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- App Initialization ---
app = Flask(__name__)
CORS(app) # Allows our frontend to call the API

# Initialize enhanced components
db_manager = DatabaseManager()
cache_manager = CacheManager()
standardization_engine = StandardizationEngine()
semantic_parser = RadiologySemanticParser()

# --- Load Models on Startup ---
print("Loading ScispaCy model...")
try:
    nlp = spacy.load("en_core_sci_sm")
    print("ScispaCy model loaded.")
except OSError:
    print("ScispaCy model not found. Please run: pip install https://...")
    nlp = None

print("Loading ML models...")
try:
    classifier = joblib.load('radiology_classifier.pkl')
    vectorizer = joblib.load('radiology_vectorizer.pkl')
    mlb = joblib.load('radiology_mlb.pkl')
    print("ML models loaded.")
except FileNotFoundError:
    print("ML model files not found. Run train.py to create placeholders.")
    classifier = vectorizer = mlb = None

def record_performance(endpoint: str, processing_time_ms: int, input_size: int, 
                      success: bool, error_message: Optional[str] = None):
    """Record performance metrics."""
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
    """Extract entities using ScispaCy."""
    scispacy_entities = {'ANATOMY': [], 'DIRECTION': []}
    
    if nlp:
        try:
            doc = nlp(exam_name)
            for ent in doc.ents:
                if ent.label_ in ['ANATOMY', 'BODY_PART_OR_ORGAN']:
                    scispacy_entities['ANATOMY'].append(ent.text.capitalize())
                elif ent.label_ == 'DIRECTION':
                    scispacy_entities['DIRECTION'].append(ent.text.capitalize())
        except Exception as e:
            logger.error(f"ScispaCy processing failed: {e}")
    
    return scispacy_entities

# --- Original API Endpoint (Enhanced) ---
@app.route('/parse', methods=['POST'])
def parse_exam():
    """Original parsing endpoint with enhancements."""
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data or 'modality_code' not in data:
            return jsonify({"error": "Missing exam_name or modality_code"}), 400

        exam_name = data['exam_name']
        modality = data['modality_code']

        # Check cache first
        cache_key = f"{exam_name}|{modality}"
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return jsonify(cached_result)

        # 1. Use ScispaCy for Named Entity Recognition
        scispacy_entities = extract_scispacy_entities(exam_name)

        # 2. Use our robust rule-based parser, enhanced with ScispaCy's output
        result = semantic_parser.parse_exam_name(exam_name, modality, scispacy_entities)
        
        # 3. ML Model as a fallback (conceptual)
        # If rules find no anatomy, you could use the ML model here.
        # For now, we'll just return the rule-based result.

        # Format the response with enhanced metadata
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
        
        # Cache result
        cache_manager.set(cache_key, response)
        
        # Record performance
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse', processing_time, len(exam_name), True)

        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Parse endpoint error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500

# --- Enhanced API Endpoints ---

@app.route('/parse_enhanced', methods=['POST'])
def parse_enhanced():
    """Enhanced parsing endpoint with full standardization."""
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data or 'modality_code' not in data:
            return jsonify({"error": "Missing exam_name or modality_code"}), 400
        
        exam_name = data['exam_name']
        modality = data['modality_code']
        
        # Check database cache first
        cached_result = db_manager.get_cached_result(data)
        if cached_result:
            return jsonify(cached_result)
        
        # Extract entities
        scispacy_entities = extract_scispacy_entities(exam_name)
        
        # Parse with semantic parser
        parsed_result = semantic_parser.parse_exam_name(exam_name, modality, scispacy_entities)
        
        # Apply standardization
        standardized = standardization_engine.normalize_exam_name(exam_name)
        
        # Calculate quality metrics
        quality_metrics = standardization_engine.calculate_quality_metrics(exam_name, parsed_result)
        
        # Build enhanced response
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
        
        # Cache result
        db_manager.cache_result(data, response)
        
        # Record performance
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
    """Batch processing endpoint for high-volume data."""
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exams' not in data:
            return jsonify({"error": "Missing exams array"}), 400
        
        exams = data['exams']
        if len(exams) > 1000:
            return jsonify({"error": "Maximum 1000 exams per batch"}), 400
        
        results = []
        errors = []
        cache_hits = 0
        
        def process_exam(exam_data):
            try:
                exam_name = exam_data['exam_name']
                modality = exam_data['modality_code']
                
                # Check cache
                cache_key = f"{exam_name}|{modality}"
                cached_result = cache_manager.get(cache_key)
                if cached_result:
                    return cached_result, True
                
                # Extract entities
                scispacy_entities = extract_scispacy_entities(exam_name)
                
                # Parse
                parsed_result = semantic_parser.parse_exam_name(exam_name, modality, scispacy_entities)
                
                # Standardize
                standardized = standardization_engine.normalize_exam_name(exam_name)
                
                result = {
                    'input': exam_data,
                    'clean_name': parsed_result['cleanName'],
                    'canonical_form': standardized['canonical_form'],
                    'components': {
                        'anatomy': parsed_result['anatomy'],
                        'laterality': parsed_result['laterality'],
                        'contrast': parsed_result['contrast'],
                        'technique': parsed_result['technique'],
                        'gender_context': parsed_result['gender_context'],
                        'clinical_context': parsed_result['clinical_context']
                    },
                    'confidence': parsed_result['confidence']
                }
                
                # Cache result
                cache_manager.set(cache_key, result)
                
                return result, False
                
            except Exception as e:
                return {"error": str(e), "exam": exam_data}, False
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(process_exam, exam): exam for exam in exams}
            
            for future in as_completed(futures):
                result, was_cached = future.result()
                if was_cached:
                    cache_hits += 1
                
                if 'error' in result:
                    errors.append(result)
                else:
                    results.append(result)
        
        # Find equivalence groups
        equivalence_groups = standardization_engine.find_equivalence_groups(
            [{'name': r['clean_name'], 'source': r['input'].get('source', 'unknown')} 
             for r in results]
        )
        
        # Generate processing statistics
        processing_stats = {
            'total_processed': len(exams),
            'successful': len(results),
            'errors': len(errors),
            'cache_hits': cache_hits,
            'processing_time_ms': int((time.time() - start_time) * 1000),
            'equivalence_groups_found': len(equivalence_groups)
        }
        
        response = {
            'results': results,
            'errors': errors,
            'processing_stats': processing_stats,
            'equivalence_groups': equivalence_groups
        }
        
        # Record performance
        record_performance('parse_batch', processing_stats['processing_time_ms'], 
                          len(exams), len(errors) == 0)
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Batch parse endpoint error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('parse_batch', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/equivalence_groups', methods=['POST'])
def find_equivalence_groups():
    """Find equivalence groups for exam names."""
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exams' not in data:
            return jsonify({"error": "Missing exams array"}), 400
        
        exams = data['exams']
        similarity_threshold = data.get('similarity_threshold', 0.85)
        
        # Find equivalence groups
        groups = standardization_engine.find_equivalence_groups(exams, similarity_threshold)
        
        # Save groups to database
        for group in groups:
            db_manager.save_equivalence_group({
                'group_id': group['group_id'],
                'canonical_name': group['canonical_name'],
                'members': group['members'],
                'confidence_score': group['average_confidence']
            })
        
        response = {
            'groups': groups,
            'processing_stats': {
                'total_exams': len(exams),
                'groups_found': len(groups),
                'similarity_threshold': similarity_threshold,
                'processing_time_ms': int((time.time() - start_time) * 1000)
            }
        }
        
        # Record performance
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('equivalence_groups', processing_time, len(exams), True)
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Equivalence groups endpoint error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('equivalence_groups', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/validate', methods=['POST'])
def validate_exam_data():
    """Validate exam data quality."""
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name"}), 400
        
        exam_name = data['exam_name']
        
        # Normalize the exam name
        normalized = standardization_engine.normalize_exam_name(exam_name)
        
        # Extract entities for validation
        scispacy_entities = extract_scispacy_entities(exam_name)
        
        # Parse for component validation
        parsed_result = semantic_parser.parse_exam_name(
            exam_name, 
            data.get('modality_code', 'Unknown'), 
            scispacy_entities
        )
        
        # Calculate quality metrics
        quality_metrics = standardization_engine.calculate_quality_metrics(exam_name, parsed_result)
        
        # Determine validation result
        is_valid = quality_metrics['overall_quality'] >= 0.7
        
        response = {
            'valid': is_valid,
            'quality_score': quality_metrics['overall_quality'],
            'warnings': quality_metrics['flags'],
            'suggestions': quality_metrics['suggestions'],
            'normalized_name': normalized['normalized'],
            'transformations_applied': normalized['transformations_applied'],
            'metadata': {
                'processing_time_ms': int((time.time() - start_time) * 1000)
            }
        }
        
        # Record performance
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('validate', processing_time, len(exam_name), True)
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Validation endpoint error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('validate', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback for learning."""
    start_time = time.time()
    
    try:
        data = request.json
        required_fields = ['original_exam_name', 'original_mapping', 'corrected_mapping', 'confidence_level']
        
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Validate confidence level
        if data['confidence_level'] not in ['low', 'medium', 'high']:
            return jsonify({"error": "Invalid confidence level"}), 400
        
        # Submit feedback
        feedback_id = db_manager.submit_feedback(data)
        
        response = {
            'feedback_id': feedback_id,
            'status': 'submitted',
            'message': 'Feedback submitted successfully',
            'processing_time_ms': int((time.time() - start_time) * 1000)
        }
        
        # Record performance
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('feedback', processing_time, 1, True)
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Feedback endpoint error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('feedback', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/compare_systems', methods=['POST'])
def compare_systems():
    """Compare radiology systems for equivalence."""
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'system_data' not in data:
            return jsonify({"error": "Missing system_data"}), 400
        
        system_data = data['system_data']
        systems = list(system_data.keys())
        
        # Check for cached comparison
        cached_result = db_manager.get_system_comparison(systems)
        if cached_result:
            return jsonify(cached_result)
        
        # Perform comparison
        comparison_results = {}
        
        for i, system_a in enumerate(systems):
            for system_b in systems[i+1:]:
                exams_a = system_data[system_a]
                exams_b = system_data[system_b]
                
                # Find matching exams
                matches = []
                unique_to_a = []
                unique_to_b = []
                
                for exam_a in exams_a:
                    best_match = None
                    best_score = 0
                    
                    for exam_b in exams_b:
                        score = standardization_engine.calculate_similarity_score(
                            exam_a['name'], exam_b['name']
                        )
                        if score > best_score:
                            best_score = score
                            best_match = exam_b
                    
                    if best_score >= 0.8:
                        matches.append({
                            'exam_a': exam_a,
                            'exam_b': best_match,
                            'similarity': best_score
                        })
                    else:
                        unique_to_a.append(exam_a)
                
                # Find exams unique to system B
                matched_b_names = {match['exam_b']['name'] for match in matches}
                unique_to_b = [exam for exam in exams_b if exam['name'] not in matched_b_names]
                
                comparison_key = f"{system_a}_vs_{system_b}"
                comparison_results[comparison_key] = {
                    'matching_exams': len(matches),
                    'unique_to_a': len(unique_to_a),
                    'unique_to_b': len(unique_to_b),
                    'total_a': len(exams_a),
                    'total_b': len(exams_b),
                    'match_percentage': (len(matches) / max(len(exams_a), len(exams_b))) * 100,
                    'confidence_avg': sum(match['similarity'] for match in matches) / len(matches) if matches else 0,
                    'matches': matches[:10],  # Top 10 matches
                    'unique_samples_a': unique_to_a[:5],  # Sample unique exams
                    'unique_samples_b': unique_to_b[:5]
                }
        
        # Find consolidation opportunities
        all_exams = []
        for system, exams in system_data.items():
            for exam in exams:
                exam['system'] = system
                all_exams.append(exam)
        
        equivalence_groups = standardization_engine.find_equivalence_groups(all_exams)
        
        response = {
            'system_comparison': comparison_results,
            'consolidation_opportunities': equivalence_groups,
            'processing_stats': {
                'systems_compared': len(systems),
                'total_exams': len(all_exams),
                'processing_time_ms': int((time.time() - start_time) * 1000)
            }
        }
        
        # Cache the comparison
        db_manager.save_system_comparison({
            'systems': systems,
            'results': response
        })
        
        # Record performance
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('compare_systems', processing_time, len(all_exams), True)
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"System comparison endpoint error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('compare_systems', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/config', methods=['GET', 'POST'])
def manage_configuration():
    """Manage configuration settings."""
    start_time = time.time()
    
    try:
        if request.method == 'GET':
            # Get configuration
            category = request.args.get('category')
            config = db_manager.get_all_configuration(category)
            
            response = {
                'configuration': config,
                'processing_time_ms': int((time.time() - start_time) * 1000)
            }
            
            return jsonify(response)
            
        elif request.method == 'POST':
            # Update configuration
            data = request.json
            if not data or 'settings' not in data:
                return jsonify({"error": "Missing settings"}), 400
            
            settings = data['settings']
            category = data.get('category', 'general')
            
            # Update each setting
            for key, value in settings.items():
                db_manager.set_configuration(key, str(value), category)
            
            response = {
                'status': 'updated',
                'settings_updated': len(settings),
                'processing_time_ms': int((time.time() - start_time) * 1000)
            }
            
            return jsonify(response)
            
    except Exception as e:
        logger.error(f"Configuration endpoint error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('config', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/analytics', methods=['GET'])
def get_analytics():
    """Get system analytics and performance metrics."""
    start_time = time.time()
    
    try:
        hours = int(request.args.get('hours', 24))
        
        # Get performance metrics
        performance_metrics = db_manager.get_performance_metrics(hours=hours)
        
        # Calculate analytics
        total_requests = len(performance_metrics)
        successful_requests = sum(1 for m in performance_metrics if m['success'])
        
        if total_requests > 0:
            success_rate = (successful_requests / total_requests) * 100
            avg_processing_time = sum(m['processing_time_ms'] for m in performance_metrics) / total_requests
        else:
            success_rate = 0
            avg_processing_time = 0
        
        # Get cache statistics
        cache_stats = db_manager.get_cache_statistics()
        memory_cache_stats = cache_manager.stats()
        
        # Get equivalence groups count
        equivalence_groups = db_manager.get_equivalence_groups()
        
        response = {
            'performance_metrics': {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'success_rate': success_rate,
                'avg_processing_time_ms': avg_processing_time,
                'time_period_hours': hours
            },
            'cache_statistics': {
                'database_cache': cache_stats,
                'memory_cache': memory_cache_stats
            },
            'equivalence_groups': {
                'total_groups': len(equivalence_groups),
                'groups': equivalence_groups[:10]  # Top 10
            },
            'processing_time_ms': int((time.time() - start_time) * 1000)
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Analytics endpoint error: {e}")
        processing_time = int((time.time() - start_time) * 1000)
        record_performance('analytics', processing_time, 0, False, str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        db_stats = db_manager.get_cache_statistics()
        
        # Check memory cache
        cache_stats = cache_manager.stats()
        
        # Check models
        models_loaded = {
            'scispacy': nlp is not None,
            'classifier': classifier is not None,
            'vectorizer': vectorizer is not None,
            'mlb': mlb is not None
        }
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'cache': f"{cache_stats['usage_percent']:.1f}% full",
            'models': models_loaded,
            'version': '2.1.0'
        }
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Background tasks
def cleanup_old_data():
    """Clean up old cached data."""
    try:
        db_manager.cleanup_old_cache(days=30)
        logger.info("Old cache data cleaned up")
    except Exception as e:
        logger.error(f"Cache cleanup error: {e}")

# Start background cleanup task
cleanup_thread = threading.Thread(target=cleanup_old_data, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
