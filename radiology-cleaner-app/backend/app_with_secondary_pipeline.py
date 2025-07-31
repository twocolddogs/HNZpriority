#!/usr/bin/env python3
"""
Enhanced Flask app with secondary pipeline integration for low-confidence result reassessment.
This version adds OpenRouter ensemble processing to improve accuracy on uncertain classifications.
"""

# Import secondary pipeline components
from secondary_pipeline import SecondaryPipeline
from pipeline_integration import PipelineIntegration, BatchResultProcessor

# Add these imports to your existing imports section
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os

# =============================================================================
# SECONDARY PIPELINE CONFIGURATION
# =============================================================================

def initialize_secondary_pipeline(app):
    """Initialize secondary pipeline with Flask app configuration"""
    
    # Secondary pipeline configuration
    app.config.setdefault('ENABLE_SECONDARY_PIPELINE', True)
    app.config.setdefault('SECONDARY_PIPELINE_THRESHOLD', 0.8)
    app.config.setdefault('SECONDARY_PIPELINE_CONCURRENCY', 3)
    app.config.setdefault('OPENROUTER_API_KEY', os.getenv('OPENROUTER_API_KEY'))
    
    # Create integration and batch processor
    integration = PipelineIntegration(app.config)
    batch_processor = BatchResultProcessor(integration)
    
    logger.info(f"Secondary pipeline enabled: {integration.is_enabled()}")
    if integration.is_enabled():
        logger.info(f"Confidence threshold: {integration.pipeline_config['confidence_threshold']}")
        logger.info(f"Max concurrent requests: {integration.pipeline_config['max_concurrent_requests']}")
    
    return integration, batch_processor

# =============================================================================
# ENHANCED PROCESSING FUNCTIONS
# =============================================================================

def process_exam_with_secondary_pipeline(exam_name: str, modality_code: Optional[str], 
                                       nlp_processor: NLPProcessor, debug: bool = False, 
                                       reranker_key: Optional[str] = None, 
                                       data_source: Optional[str] = None, 
                                       exam_code: Optional[str] = None,
                                       secondary_pipeline_integration=None) -> Dict:
    """
    Enhanced exam processing that includes secondary pipeline for low confidence results.
    """
    # Process normally first
    result = process_exam_request(exam_name, modality_code, nlp_processor, debug, 
                                reranker_key, data_source, exam_code)
    
    # Check if secondary processing is needed
    if (secondary_pipeline_integration and 
        secondary_pipeline_integration.is_enabled() and 
        result.get('components', {}).get('confidence', 1.0) < secondary_pipeline_integration.pipeline_config['confidence_threshold']):
        
        try:
            # Run secondary processing in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Prepare context for secondary processing
                context = {
                    'original_modality': result.get('components', {}).get('modality', ['Other'])[0] if result.get('components', {}).get('modality') else 'Other',
                    'original_confidence': result.get('components', {}).get('confidence', 0.0),
                    'similar_exams': result.get('all_candidates', [])[:5],  # Top 5 similar exams
                    'original_result': result
                }
                
                # Process through ensemble
                ensemble_result = loop.run_until_complete(
                    secondary_pipeline_integration.secondary_pipeline.process_ensemble(exam_name, context)
                )
                
                # Update result if secondary processing improved confidence
                if ensemble_result.improved:
                    # Update the main result with improved data
                    result['components']['modality'] = [ensemble_result.consensus_modality]
                    result['components']['confidence'] = ensemble_result.consensus_confidence
                    result['secondary_processing'] = {
                        'applied': True,
                        'original_confidence': context['original_confidence'],
                        'new_confidence': ensemble_result.consensus_confidence,
                        'improvement': ensemble_result.consensus_confidence - context['original_confidence'],
                        'agreement_score': ensemble_result.agreement_score,
                        'models_used': [r.model for r in ensemble_result.model_responses],
                        'consensus_reasoning': ensemble_result.final_reasoning
                    }
                    logger.info(f"Secondary pipeline improved confidence for '{exam_name}': {context['original_confidence']:.3f} → {ensemble_result.consensus_confidence:.3f}")
                else:
                    result['secondary_processing'] = {
                        'applied': True,
                        'improved': False,
                        'original_confidence': context['original_confidence'],
                        'new_confidence': ensemble_result.consensus_confidence,
                        'agreement_score': ensemble_result.agreement_score
                    }
                    
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Secondary pipeline error for '{exam_name}': {e}")
            result['secondary_processing'] = {
                'applied': False,
                'error': str(e)
            }
    
    return result

# =============================================================================
# MODIFIED FLASK APP
# =============================================================================

# Add this after your existing Flask app initialization
# Initialize secondary pipeline components
secondary_integration, secondary_batch_processor = initialize_secondary_pipeline(app)

# =============================================================================
# NEW SECONDARY PIPELINE ROUTES
# =============================================================================

@app.route('/api/secondary-pipeline/status', methods=['GET'])
def secondary_pipeline_status():
    """Get secondary pipeline status and configuration"""
    return jsonify({
        'enabled': secondary_integration.is_enabled(),
        'config': {
            'threshold': secondary_integration.pipeline_config.get('confidence_threshold'),
            'concurrency': secondary_integration.pipeline_config.get('max_concurrent_requests'),
            'has_api_key': bool(secondary_integration.pipeline_config.get('openrouter_api_key')),
            'models': ['anthropic/claude-3.5-sonnet', 'openai/gpt-4-turbo', 'google/gemini-pro']
        },
        'app_initialized': _app_initialized
    })

@app.route('/api/secondary-pipeline/trigger', methods=['POST'])
def trigger_secondary_pipeline():
    """Manually trigger secondary pipeline processing"""
    
    if not secondary_integration.is_enabled():
        return jsonify({'error': 'Secondary pipeline not enabled or API key missing'}), 400
    
    try:
        data = request.get_json()
        results = data.get('results', [])
        
        if not results:
            return jsonify({'error': 'No results provided'}), 400
        
        # Run secondary processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            report = loop.run_until_complete(
                secondary_integration.trigger_secondary_processing(results)
            )
            return jsonify(report or {'error': 'Processing failed'})
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Manual trigger error: {e}")
        return jsonify({'error': str(e)}), 500

# =============================================================================
# ENHANCED EXISTING ROUTES
# =============================================================================

@app.route('/parse_enhanced_v2', methods=['POST'])
def parse_enhanced_v2():
    """Enhanced parsing endpoint with automatic secondary pipeline processing"""
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exam_name' not in data:
            return jsonify({"error": "Missing exam_name in request data"}), 400
        
        exam_name = data['exam_name']
        modality_code = data.get('modality_code')
        data_source = data.get('data_source')
        exam_code = data.get('exam_code')
        model = data.get('model', 'retriever')
        reranker_key = data.get('reranker', reranker_manager.get_default_reranker_key() if reranker_manager else 'medcpt')
        debug = data.get('debug', False)
        enable_secondary = data.get('enable_secondary_pipeline', True)
        
        selected_nlp_processor = _get_nlp_processor(model)
        if not selected_nlp_processor:
            return jsonify({"error": f"Model '{model}' not available"}), 400
        
        logger.info(f"Using model '{model}' for exam: {exam_name}")
        
        # Use enhanced processing function
        result = process_exam_with_secondary_pipeline(
            exam_name, modality_code, selected_nlp_processor, debug, reranker_key, 
            data_source, exam_code, 
            secondary_pipeline_integration=secondary_integration if enable_secondary else None
        )
        
        result['metadata'] = {
            'processing_time_ms': int((time.time() - start_time) * 1000),
            'model_used': model,
            'reranker_used': reranker_key,
            'secondary_pipeline_enabled': enable_secondary and secondary_integration.is_enabled()
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Parse enhanced v2 endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/parse_batch_enhanced', methods=['POST', 'OPTIONS'])
def parse_batch_enhanced():
    """Enhanced batch processing with automatic secondary pipeline integration"""
    
    if request.method == 'OPTIONS':
        return '', 200
    
    _ensure_app_is_initialized()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exams' not in data:
            return jsonify({"error": "Missing 'exams' list in request data"}), 400
        
        exams_to_process = data['exams']
        model_key = data.get('model', 'retriever')
        reranker_key = data.get('reranker', reranker_manager.get_default_reranker_key() if reranker_manager else 'medcpt')
        enable_secondary = data.get('enable_secondary_pipeline', True)
        
        # Process batch normally first
        selected_nlp_processor = _get_nlp_processor(model_key)
        if not selected_nlp_processor:
            return jsonify({"error": f"Model '{model_key}' not available"}), 400
        
        logger.info(f"Starting enhanced batch processing for {len(exams_to_process)} exams")
        logger.info(f"Secondary pipeline enabled: {enable_secondary and secondary_integration.is_enabled()}")
        
        # Process primary results
        primary_results = []
        
        # Use ThreadPoolExecutor for primary processing
        cpu_cnt = os.cpu_count() or 1
        max_workers = min(3, max(1, cpu_cnt))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for exam in exams_to_process:
                future = executor.submit(
                    process_exam_request,
                    exam.get("exam_name"),
                    exam.get("modality_code"), 
                    selected_nlp_processor,
                    False,  # debug
                    reranker_key,
                    exam.get("data_source"),
                    exam.get("exam_code")
                )
                futures.append((future, exam))
            
            # Collect primary results
            for future, original_exam in futures:
                try:
                    result = future.result(timeout=60)
                    primary_results.append({
                        'exam_name': original_exam.get("exam_name"),
                        'modality': result.get('components', {}).get('modality', ['Other'])[0] if result.get('components', {}).get('modality') else 'Other',
                        'confidence': result.get('components', {}).get('confidence', 0.0),
                        'similar_exams': result.get('all_candidates', [])[:5],
                        'full_result': result
                    })
                except Exception as e:
                    logger.error(f"Error in primary processing: {e}")
                    primary_results.append({
                        'exam_name': original_exam.get("exam_name"),
                        'modality': 'Other',
                        'confidence': 0.0,
                        'error': str(e)
                    })
        
        # Run secondary processing if enabled
        secondary_report = None
        if enable_secondary and secondary_integration.is_enabled():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    secondary_report = loop.run_until_complete(
                        secondary_batch_processor.process_batch_with_secondary(primary_results)
                    )
                finally:
                    loop.close()
                    
            except Exception as e:
                logger.error(f"Secondary processing error: {e}")
                secondary_report = {'error': str(e)}
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Prepare final response
        response = {
            "message": "Enhanced batch processing complete",
            "processing_stats": {
                "total_processed": len(exams_to_process),
                "processing_time_ms": processing_time_ms,
                "model_used": model_key,
                "reranker_used": reranker_key,
                "secondary_pipeline_enabled": enable_secondary and secondary_integration.is_enabled()
            },
            "results": [r.get('full_result', r) for r in primary_results],
            "secondary_processing": secondary_report
        }
        
        # Add summary of improvements if secondary processing ran
        if secondary_report and secondary_report.get('secondary_results'):
            sec_results = secondary_report['secondary_results']
            response['improvement_summary'] = {
                'low_confidence_count': len([r for r in primary_results if r.get('confidence', 1.0) < 0.8]),
                'improved_count': sec_results.get('improved_results', 0),
                'average_confidence_boost': sec_results.get('confidence_improvement', 0)
            }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Enhanced batch endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

# =============================================================================
# CONFIGURATION AND MONITORING ROUTES  
# =============================================================================

@app.route('/api/secondary-pipeline/config', methods=['GET'])
def get_secondary_pipeline_config():
    """Get current secondary pipeline configuration"""
    return jsonify({
        'config': secondary_integration.pipeline_config,
        'status': {
            'enabled': secondary_integration.is_enabled(),
            'has_api_key': bool(secondary_integration.pipeline_config.get('openrouter_api_key')),
            'threshold': secondary_integration.pipeline_config.get('confidence_threshold', 0.8),
            'concurrency': secondary_integration.pipeline_config.get('max_concurrent_requests', 3)
        }
    })

@app.route('/api/secondary-pipeline/test', methods=['POST'])
def test_secondary_pipeline():
    """Test secondary pipeline with sample low-confidence result"""
    
    if not secondary_integration.is_enabled():
        return jsonify({'error': 'Secondary pipeline not enabled'}), 400
    
    try:
        # Create a test case
        test_exam = "ERCP"
        test_result = {
            'exam_name': test_exam,
            'modality': 'FL', 
            'confidence': 0.65,
            'similar_exams': [
                {'name': 'Upper GI', 'modality': 'FL'},
                {'name': 'Barium Swallow', 'modality': 'FL'}
            ]
        }
        
        # Process through secondary pipeline
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            report = loop.run_until_complete(
                secondary_integration.trigger_secondary_processing([test_result])
            )
            return jsonify({
                'message': 'Secondary pipeline test completed',
                'test_exam': test_exam, 
                'original_confidence': 0.65,
                'results': report
            })
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Secondary pipeline test error: {e}")
        return jsonify({'error': str(e)}), 500

# =============================================================================
# USAGE INSTRUCTIONS
# =============================================================================

"""
INTEGRATION INSTRUCTIONS:

1. Set Environment Variables:
   export OPENROUTER_API_KEY="your-openrouter-api-key"
   export ENABLE_SECONDARY_PIPELINE=true

2. Replace your existing routes with enhanced versions:
   - Use /parse_enhanced_v2 instead of /parse_enhanced 
   - Use /parse_batch_enhanced instead of /parse_batch

3. New endpoints available:
   - GET /api/secondary-pipeline/status - Check if secondary pipeline is enabled
   - POST /api/secondary-pipeline/trigger - Manually trigger secondary processing
   - POST /api/secondary-pipeline/test - Test the pipeline
   - GET /api/secondary-pipeline/config - View configuration

4. Enhanced processing features:
   - Automatic secondary processing for confidence < 80%
   - Ensemble of Claude, GPT-4, and Gemini models
   - Consensus-based confidence improvement
   - Detailed improvement reporting

5. Example usage:
   curl -X POST http://localhost:10000/parse_enhanced_v2 \
     -H "Content-Type: application/json" \
     -d '{"exam_name": "ERCP", "enable_secondary_pipeline": true}'

The secondary pipeline will automatically:
- Detect low confidence results (< 80%)
- Query multiple models in parallel
- Calculate consensus with improved confidence
- Return enhanced results with improvement metrics
"""

if __name__ == '__main__':
    logger.info("Running enhanced app with secondary pipeline support")
    logger.info(f"Secondary pipeline enabled: {secondary_integration.is_enabled()}")
    _ensure_app_is_initialized()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))