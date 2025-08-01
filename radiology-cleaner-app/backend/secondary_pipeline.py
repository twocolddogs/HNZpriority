#!/usr/bin/env python3
"""
Secondary Pipeline for Low-Confidence Result Reassessment
Uses multiple OpenRouter models to achieve consensus on uncertain classifications.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
import openai
from datetime import datetime
import os
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelType(Enum):
    """Available OpenRouter models for ensemble processing"""
    CLAUDE_SONNET = "anthropic/claude-3.5-sonnet"
    GPT4_TURBO = "openai/gpt-4-turbo"
    GEMINI_PRO = "google/gemini-2.5-pro"

@dataclass
class ModelResponse:
    """Response from a single model"""
    model: str
    modality: str
    confidence: float
    reasoning: str
    raw_response: str
    processing_time: float

@dataclass
class EnsembleResult:
    """Final ensemble result with consensus"""
    original_result: Dict[str, Any]
    consensus_modality: str
    consensus_confidence: float
    model_responses: List[ModelResponse]
    agreement_score: float
    final_reasoning: str
    improved: bool
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass to dictionary"""
        return asdict(self)

class OpenRouterEnsemble:
    """Ensemble system using multiple OpenRouter models"""
    
    def __init__(self, api_key: str = None, config: Dict = None):
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OpenRouter API key required")
        
        # Load configuration
        self.config = config or self._load_default_config()
        
        # Configure OpenAI client for OpenRouter
        self.client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        self.models = self.config.get('secondary_pipeline', {}).get('models', [
            ModelType.CLAUDE_SONNET.value,
            ModelType.GPT4_TURBO.value, 
            ModelType.GEMINI_PRO.value
        ])
    
    async def query_model(self, model: str, exam_name: str, context: Dict) -> ModelResponse:
        """Query a single model for exam classification"""
        start_time = asyncio.get_event_loop().time()
        
        # Enhanced prompt with context from original processing
        prompt = self._build_enhanced_prompt(exam_name, context)
        
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.get('secondary_pipeline', {}).get('temperature', 0.1),
                max_tokens=self.config.get('secondary_pipeline', {}).get('max_tokens', 500)
            )
            
            processing_time = asyncio.get_event_loop().time() - start_time
            content = response.choices[0].message.content
            
            # Parse structured response
            parsed = self._parse_model_response(content)
            
            return ModelResponse(
                model=model,
                modality=parsed['modality'],
                confidence=parsed['confidence'],
                reasoning=parsed['reasoning'],
                raw_response=content,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error querying {model}: {e}")
            return ModelResponse(
                model=model,
                modality="UNKNOWN",
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                raw_response="",
                processing_time=asyncio.get_event_loop().time() - start_time
            )
    
    def _load_default_config(self) -> Dict:
        """Load configuration from YAML file"""
        config_path = os.path.join(os.path.dirname(__file__), 'training_testing', 'config.yaml')
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found at {config_path}, using defaults")
            return {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def _get_default_prompt_template(self) -> str:
        """Default prompt template as fallback"""
        return """You are a radiology informatics expert tasked with accurately classifying medical imaging exams.

EXAM TO CLASSIFY: "{exam_name}"

CONTEXT FROM INITIAL PROCESSING:
- Original Classification: {original_modality}
- Original Confidence: {original_confidence:.2f}
- This exam was flagged for review due to low confidence (<80%)

SIMILAR EXAMS FOR REFERENCE:
{similar_exams}

AVAILABLE MODALITIES:
- XR (X-Ray/Radiography)
- CT (Computed Tomography) 
- MR (Magnetic Resonance Imaging)
- US (Ultrasound)
- FL (Fluoroscopy)
- IR (Interventional Radiology)
- Mamm (Mammography)
- NM (Nuclear Medicine)
- PET (Positron Emission Tomography)
- Other (Procedures not fitting standard modalities)

INSTRUCTIONS:
1. Analyze the exam name carefully, considering medical terminology and context
2. Consider the original classification and whether it seems reasonable
3. Use the similar exams as reference points for pattern recognition
4. Provide your classification with confidence score (0.0-1.0)
5. Explain your reasoning clearly

REQUIRED OUTPUT FORMAT (JSON):
{{
    "modality": "YOUR_CLASSIFICATION",
    "confidence": 0.XX,
    "reasoning": "Detailed explanation of your classification logic"
}}"""
    
    def _build_enhanced_prompt(self, exam_name: str, context: Dict) -> str:
        """Build enhanced prompt with context from original processing"""
        
        original_modality = context.get('original_modality', 'UNKNOWN')
        original_confidence = context.get('original_confidence', 0.0)
        similar_exams = context.get('similar_exams', [])
        
        
        # Get prompt template from config
        prompt_template = self.config.get('secondary_pipeline', {}).get('prompt_template', self._get_default_prompt_template())
        
        # Format the prompt with context variables
        prompt = prompt_template.format(
            exam_name=exam_name,
            original_modality=original_modality,
            original_confidence=original_confidence,
            similar_exams=self._format_similar_exams(similar_exams)
        )
        
        return prompt
    
    def _format_similar_exams(self, similar_exams: List[Dict]) -> str:
        """Format similar exams for context"""
        if not similar_exams:
            return "No similar exams provided"
        
        formatted = []
        for exam in similar_exams[:5]:  # Limit to top 5
            formatted.append(f"- \"{exam.get('name', '')}\" → {exam.get('modality', 'UNKNOWN')}")
        
        return "\n".join(formatted)
    
    def _parse_model_response(self, content: str) -> Dict:
        """Parse structured response from model"""
        try:
            # Try to extract JSON from response
            start = content.find('{')
            end = content.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = content[start:end]
                parsed = json.loads(json_str)
                
                return {
                    'modality': parsed.get('modality', 'UNKNOWN').upper(),
                    'confidence': float(parsed.get('confidence', 0.0)),
                    'reasoning': parsed.get('reasoning', 'No reasoning provided')
                }
        except:
            logger.warning("Failed to parse structured response, attempting fallback")
        
        # Fallback parsing
        return {
            'modality': 'UNKNOWN',
            'confidence': 0.0,
            'reasoning': 'Failed to parse response'
        }
    
    async def process_ensemble(self, exam_name: str, context: Dict) -> EnsembleResult:
        """Process exam through all models and generate ensemble result"""
        
        # Query all models concurrently
        tasks = [
            self.query_model(model, exam_name, context)
            for model in self.models
        ]
        
        model_responses = await asyncio.gather(*tasks)
        
        # Calculate consensus
        consensus_result = self._calculate_consensus(model_responses)
        
        # Check if result improved over original
        original_confidence = context.get('original_confidence', 0.0)
        improved = consensus_result['confidence'] > original_confidence
        
        return EnsembleResult(
            original_result=context,
            consensus_modality=consensus_result['modality'],
            consensus_confidence=consensus_result['confidence'],
            model_responses=model_responses,
            agreement_score=consensus_result['agreement_score'],
            final_reasoning=consensus_result['reasoning'],
            improved=improved,
            timestamp=datetime.now().isoformat()
        )
    
    def _calculate_consensus(self, responses: List[ModelResponse]) -> Dict:
        """Calculate consensus from multiple model responses"""
        
        # Filter out error responses
        valid_responses = [r for r in responses if r.modality != "UNKNOWN"]
        
        if not valid_responses:
            return {
                'modality': 'UNKNOWN',
                'confidence': 0.0,
                'agreement_score': 0.0,
                'reasoning': 'All models failed to provide valid responses'
            }
        
        # Count modality votes
        modality_votes = {}
        confidence_by_modality = {}
        
        for response in valid_responses:
            modality = response.modality
            
            if modality not in modality_votes:
                modality_votes[modality] = []
                confidence_by_modality[modality] = []
            
            modality_votes[modality].append(response)
            confidence_by_modality[modality].append(response.confidence)
        
        # Find consensus modality (most votes, then highest average confidence)
        consensus_modality = max(
            modality_votes.keys(),
            key=lambda m: (len(modality_votes[m]), statistics.mean(confidence_by_modality[m]))
        )
        
        # Calculate consensus confidence (weighted average)
        consensus_responses = modality_votes[consensus_modality]
        total_confidence = sum(r.confidence for r in consensus_responses)
        consensus_confidence = total_confidence / len(consensus_responses)
        
        # Calculate agreement score
        agreement_score = len(consensus_responses) / len(valid_responses)
        
        # Generate simplified reasoning for logs
        model_names = [r.model.split('/')[-1] for r in consensus_responses]
        final_reasoning = f"Consensus ({len(consensus_responses)}/{len(valid_responses)} models agree): {', '.join(model_names)}"
        
        return {
            'modality': consensus_modality,
            'confidence': consensus_confidence,
            'agreement_score': agreement_score,
            'reasoning': final_reasoning
        }

class SecondaryPipeline:
    """Main secondary pipeline coordinator"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._load_config()
        self.ensemble = OpenRouterEnsemble(self.config.get('openrouter_api_key'), self.config)
        
    def _load_config(self) -> Dict:
        """Load configuration from YAML file with defaults"""
        config_path = os.path.join(os.path.dirname(__file__), 'training_testing', 'config.yaml')
        try:
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f)
        except (FileNotFoundError, Exception) as e:
            logger.warning(f"Could not load config from {config_path}: {e}")
            yaml_config = {}
        
        # Merge with defaults
        defaults = {
            'confidence_threshold': 0.8,
            'openrouter_api_key': os.getenv('OPENROUTER_API_KEY'),
            'max_concurrent_requests': 5,
            'output_path': os.path.join(os.environ.get('RENDER_DISK_PATH', '/tmp'), 'secondary_pipeline_results.json')
        }
        
        # Override defaults with values from secondary_pipeline section if present
        secondary_config = yaml_config.get('secondary_pipeline', {})
        if 'confidence_threshold' in secondary_config:
            defaults['confidence_threshold'] = secondary_config['confidence_threshold']
        if 'max_concurrent_requests' in secondary_config:
            defaults['max_concurrent_requests'] = secondary_config['max_concurrent_requests']
        
        # Return merged config with yaml data included
        return {**defaults, **yaml_config}
    
    async def process_low_confidence_results(self, results: List[Dict]) -> List[EnsembleResult]:
        """Process list of low-confidence results through ensemble"""

        # The 'results' list is already filtered for low confidence by the integration layer.
        # No need to filter again.
        low_confidence = results

        logger.info(f"Processing {len(low_confidence)} low-confidence results")
        if not low_confidence:
            return []

        # Process in batches to respect rate limits
        ensemble_results = []
        batch_size = self.config['max_concurrent_requests']

        for i in range(0, len(low_confidence), batch_size):
            batch = low_confidence[i:i + batch_size]

            tasks = []
            for result in batch:
                # Extract data from the nested structure provided by the primary pipeline
                components = result.get('output', {}).get('components', {})
                exam_name = components.get('exam_name', 'Unknown Exam')
                context = {
                    'original_modality': components.get('modality', 'UNKNOWN'),
                    'original_confidence': components.get('confidence', 0.0),
                    'similar_exams': components.get('similar_exams', []),
                    'original_result': result
                }
                tasks.append(self.ensemble.process_ensemble(exam_name, context))

            batch_results = await asyncio.gather(*tasks)
            ensemble_results.extend(batch_results)

            if len(low_confidence) > 0:
                logger.info(f"Completed batch {i//batch_size + 1}/{(len(low_confidence) - 1) // batch_size + 1}")

        return ensemble_results
    
    def save_results(self, results: List[EnsembleResult], output_path: str = None):
        """Save ensemble results to file"""
        output_path = output_path or self.config['output_path']
        
        serializable_results = [asdict(result) for result in results]
        
        with open(output_path, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_processed': len(results),
                'results': serializable_results
            }, f, indent=2)
        
        logger.info(f"Results saved to {output_path}")
    
    def generate_improvement_report(self, results: List[EnsembleResult]) -> Dict:
        """Generate report on improvements achieved"""
        
        improved_count = sum(1 for r in results if r.improved)
        total_count = len(results)
        
        original_avg_confidence = statistics.mean([
            r.original_result.get('original_confidence', 0.0) for r in results
        ])
        
        new_avg_confidence = statistics.mean([r.consensus_confidence for r in results])
        
        high_agreement = sum(1 for r in results if r.agreement_score >= 0.67)  # 2/3 agreement
        
        return {
            'total_processed': total_count,
            'improved_results': improved_count,
            'improvement_rate': improved_count / total_count if total_count > 0 else 0,
            'original_avg_confidence': original_avg_confidence,
            'new_avg_confidence': new_avg_confidence,
            'confidence_improvement': new_avg_confidence - original_avg_confidence,
            'high_agreement_results': high_agreement,
            'high_agreement_rate': high_agreement / total_count if total_count > 0 else 0
        }

# Example usage and integration
async def run_secondary_pipeline(primary_results_file: str):
    """Example function showing how to run the secondary pipeline"""
    
    # Load primary results
    with open(primary_results_file, 'r') as f:
        primary_results = json.load(f)
    
    # Initialize pipeline
    pipeline = SecondaryPipeline()
    
    # Process low-confidence results
    ensemble_results = await pipeline.process_low_confidence_results(primary_results)
    
    # Save results
    pipeline.save_results(ensemble_results)
    
    # Generate report
    report = pipeline.generate_improvement_report(ensemble_results)
    
    logger.info("Secondary Pipeline Report:")
    logger.info(f"Processed: {report['total_processed']} exams")
    logger.info(f"Improved: {report['improved_results']} ({report['improvement_rate']:.1%})")
    logger.info(f"Confidence boost: {report['confidence_improvement']:.3f}")
    logger.info(f"High agreement: {report['high_agreement_results']} ({report['high_agreement_rate']:.1%})")
    
    return ensemble_results, report

if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 secondary_pipeline.py <primary_results_file>")
        sys.exit(1)
    
    asyncio.run(run_secondary_pipeline(sys.argv[1]))