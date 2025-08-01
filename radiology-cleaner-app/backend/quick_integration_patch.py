#!/usr/bin/env python3
"""
Quick Integration Patch for Secondary Pipeline
Add these code snippets to your existing app.py file
"""

# =============================================================================
# STEP 1: ADD THESE IMPORTS TO THE TOP OF YOUR app.py
# =============================================================================

# Add these lines after your existing imports in app.py:
from secondary_pipeline import SecondaryPipeline
from pipeline_integration import PipelineIntegration, BatchResultProcessor
import asyncio

# =============================================================================
# STEP 2: ADD SECONDARY PIPELINE INITIALIZATION 
# =============================================================================

# Add this code after your Flask app creation (around line 35-45):
"""
# Secondary Pipeline Configuration
app.config.setdefault('OPENROUTER_API_KEY', os.getenv('OPENROUTER_API_KEY'))
app.config.setdefault('ENABLE_SECONDARY_PIPELINE', True)
app.config.setdefault('SECONDARY_PIPELINE_THRESHOLD', 0.8)
app.config.setdefault('SECONDARY_PIPELINE_CONCURRENCY', 3)

# Initialize secondary pipeline (add after line ~75 where other globals are defined)
secondary_integration = None
secondary_batch_processor = None

def _initialize_secondary_pipeline():
    global secondary_integration, secondary_batch_processor
    if secondary_integration is None:
        secondary_integration = PipelineIntegration(app.config)
        secondary_batch_processor = BatchResultProcessor(secondary_integration)
        logger.info(f"Secondary pipeline initialized - Enabled: {secondary_integration.is_enabled()}")
"""

# =============================================================================
# STEP 3: ADD NEW ROUTES TO YOUR app.py
# =============================================================================

# Add these route functions anywhere in your app.py (around line 1400+):

@app.route('/api/secondary-pipeline/status', methods=['GET'])
def secondary_pipeline_status():
    """Get secondary pipeline status"""
    _initialize_secondary_pipeline()
    return jsonify({
        'enabled': secondary_integration.is_enabled() if secondary_integration else False,
        'config': {
            'threshold': app.config.get('SECONDARY_PIPELINE_THRESHOLD', 0.8),
            'concurrency': app.config.get('SECONDARY_PIPELINE_CONCURRENCY', 3),
            'has_api_key': bool(app.config.get('OPENROUTER_API_KEY'))
        },
        'models': ['claude-3.5-sonnet', 'gpt-4-turbo', 'gemini-pro']
    })

@app.route('/parse_batch_v2', methods=['POST', 'OPTIONS'])
def parse_batch_v2():
    """Enhanced batch processing with optional secondary pipeline"""
    
    if request.method == 'OPTIONS':
        return '', 200
    
    _ensure_app_is_initialized()
    _initialize_secondary_pipeline()
    start_time = time.time()
    
    try:
        data = request.json
        if not data or 'exams' not in data:
            return jsonify({"error": "Missing 'exams' list in request data"}), 400
        
        exams_to_process = data['exams']
        model_key = data.get('model', 'retriever')
        reranker_key = data.get('reranker', reranker_manager.get_default_reranker_key() if reranker_manager else 'medcpt')
        enable_secondary = data.get('enable_secondary_pipeline', True)
        
        # Use your existing batch processing logic
        selected_nlp_processor = _get_nlp_processor(model_key)
        if not selected_nlp_processor:
            return jsonify({"error": f"Model '{model_key}' not available"}), 400
        
        logger.info(f"Starting batch processing for {len(exams_to_process)} exams (secondary: {enable_secondary and secondary_integration.is_enabled()})")
        
        # Process normally using your existing logic
        success_count = 0
        error_count = 0
        primary_results = []
        
        # Use your existing ThreadPoolExecutor batch processing logic here
        cpu_cnt = os.cpu_count() or 1
        max_workers = min(2, max(1, cpu_cnt))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_exam = {
                executor.submit(process_exam_request, exam.get("exam_name"), exam.get("modality_code"), selected_nlp_processor, False, reranker_key, exam.get("data_source"), exam.get("exam_code")): exam 
                for exam in exams_to_process
            }
            
            for future in as_completed(future_to_exam):
                original_exam = future_to_exam[future]
                try:
                    processed_result = future.result(timeout=60)
                    
                    # Prepare for secondary processing
                    primary_results.append({
                        'exam_name': original_exam.get("exam_name"),
                        'modality': processed_result.get('components', {}).get('modality', ['Other'])[0] if processed_result.get('components', {}).get('modality') else 'Other',
                        'confidence': processed_result.get('components', {}).get('confidence', 0.0),
                        'similar_exams': processed_result.get('all_candidates', [])[:5],
                        'full_result': processed_result,
                        'original_exam': original_exam
                    })
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error processing exam '{original_exam.get('exam_name')}': {e}")
                    primary_results.append({
                        'exam_name': original_exam.get("exam_name"),
                        'modality': 'Other',
                        'confidence': 0.0,
                        'error': str(e),
                        'original_exam': original_exam
                    })
                    error_count += 1
        
        # Run secondary processing if enabled
        secondary_report = None
        if enable_secondary and secondary_integration and secondary_integration.is_enabled():
            try:
                logger.info("Running secondary pipeline processing...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    secondary_report = loop.run_until_complete(
                        secondary_integration.trigger_secondary_processing(primary_results)
                    )
                    if secondary_report:
                        logger.info(f"Secondary processing completed: {secondary_report.get('improved_results', 0)} results improved")
                finally:
                    loop.close()
                    
            except Exception as e:
                logger.error(f"Secondary processing error: {e}")
                secondary_report = {'error': str(e), 'processed': 0, 'improved': 0}
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Return standard format with secondary processing info
        response = {
            "message": "Batch processing complete" + (" with secondary enhancement" if secondary_report else ""),
            "processing_stats": {
                "total_processed": len(exams_to_process),
                "successful": success_count,
                "errors": error_count,
                "processing_time_ms": processing_time_ms,
                "model_used": model_key,
                "secondary_pipeline_enabled": enable_secondary and secondary_integration and secondary_integration.is_enabled()
            },
            "results": [r.get('full_result', r) for r in primary_results if 'full_result' in r],
            "secondary_processing": secondary_report
        }
        
        # Add improvement summary
        if secondary_report and secondary_report.get('improved_results', 0) > 0:
            low_confidence_count = len([r for r in primary_results if r.get('confidence', 1.0) < 0.8])
            response['improvement_summary'] = {
                'low_confidence_count': low_confidence_count,
                'improved_count': secondary_report.get('improved_results', 0),
                'confidence_improvement': secondary_report.get('confidence_improvement', 0.0)
            }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Enhanced batch endpoint error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/secondary-pipeline/test', methods=['POST'])
def test_secondary_pipeline():
    """Test secondary pipeline with a sample exam"""
    _initialize_secondary_pipeline()
    
    if not secondary_integration or not secondary_integration.is_enabled():
        return jsonify({'error': 'Secondary pipeline not enabled - check OPENROUTER_API_KEY'}), 400
    
    try:
        # Test with a known low-confidence case
        test_cases = [
            {
                'exam_name': 'ERCP',
                'modality': 'FL',
                'confidence': 0.65,
                'similar_exams': [
                    {'name': 'Upper GI', 'modality': 'FL'},
                    {'name': 'Barium Swallow', 'modality': 'FL'}
                ]
            }
        ]
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            report = loop.run_until_complete(
                secondary_integration.trigger_secondary_processing(test_cases)
            )
            return jsonify({
                'message': 'Secondary pipeline test completed',
                'test_exam': 'ERCP',
                'results': report
            })
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Secondary pipeline test error: {e}")
        return jsonify({'error': str(e)}), 500

# =============================================================================
# STEP 4: INSTRUCTIONS FOR INTEGRATION
# =============================================================================

"""
INTEGRATION INSTRUCTIONS:

1. Copy the imports from STEP 1 to the top of your app.py file

2. Copy the configuration code from STEP 2 and add it after your Flask app creation

3. Copy all the route functions from STEP 3 and add them to your app.py file

4. Set your environment variable:
   export OPENROUTER_API_KEY="your-openrouter-api-key-here"

5. Test the integration:
   # Check status
   curl http://localhost:10000/api/secondary-pipeline/status
   
   # Test the pipeline
   curl -X POST http://localhost:10000/api/secondary-pipeline/test
   
   # Use enhanced batch processing
   curl -X POST http://localhost:10000/parse_batch_v2 \
     -H "Content-Type: application/json" \
     -d '{"exams": [{"exam_name": "ERCP"}, {"exam_name": "US Biopsy Thyroid"}], "enable_secondary_pipeline": true}'

6. The system will automatically:
   - Detect results with confidence < 80%
   - Query Claude, GPT-4, and Gemini for better classification
   - Return improved results with detailed metrics

That's it! Your existing endpoints continue to work normally, and you get the new enhanced endpoint with secondary processing.
"""