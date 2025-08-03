#!/usr/bin/env python3
"""
Secondary Pipeline for Low-Confidence Result Reassessment
Uses multiple OpenRouter models to achieve consensus on uncertain classifications.
"""

import asyncio
import json
import logging
import re
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
    """Response from a single model, aligned with the new selection prompt"""
    model: str
    best_match_candidate_number: Optional[int]
    best_match_procedure_name: Optional[str]
    final_modality: str
    confidence: float
    reasoning: str
    raw_response: str
    processing_time: float


@dataclass
class EnsembleResult:
    """Final ensemble result with consensus, aligned with the new selection prompt"""
    original_result: Dict[str, Any]
    consensus_best_match_candidate_number: Optional[int]
    consensus_best_match_procedure_name: Optional[str]
    consensus_final_modality: str
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
        
        self.config = config or self._load_default_config()
        
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
        """Query a single model for exam classification using the new selection prompt."""
        start_time = asyncio.get_event_loop().time()
        
        prompt = self._build_enhanced_prompt(exam_name, context)
        
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.get('secondary_pipeline', {}).get('temperature', 0.1),
                max_tokens=self.config.get('secondary_pipeline', {}).get('max_tokens', 800) # Increased for longer reasoning
            )
            
            processing_time = asyncio.get_event_loop().time() - start_time
            content = response.choices[0].message.content
            
            parsed = self._parse_model_response(content)
            
            return ModelResponse(
                model=model,
                best_match_candidate_number=parsed['best_match_candidate_number'],
                best_match_procedure_name=parsed['best_match_procedure_name'],
                final_modality=parsed['final_modality'],
                confidence=parsed['confidence'],
                reasoning=parsed['reasoning'],
                raw_response=content,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error querying {model}: {e}")
            return ModelResponse(
                model=model,
                best_match_candidate_number=None,
                best_match_procedure_name=None,
                final_modality="UNKNOWN",
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                raw_response="",
                processing_time=asyncio.get_event_loop().time() - start_time
            )
    
    def _load_default_config(self) -> Dict:
        """Load configuration from R2 production URL (same as primary pipeline)"""
        try:
            from config_manager import get_config
            config_manager = get_config()
            
            # Get the full config (all sections)
            full_config = {}
            
            # Load all sections that secondary pipeline needs
            scoring_config = config_manager.get_section('scoring')
            if scoring_config:
                full_config['scoring'] = scoring_config
                
            secondary_config = config_manager.get_section('secondary_pipeline') 
            if secondary_config:
                full_config['secondary_pipeline'] = secondary_config
                
            modality_config = config_manager.get_section('modality_similarity')
            if modality_config:
                full_config['modality_similarity'] = modality_config
                
            preprocessing_config = config_manager.get_section('preprocessing')
            if preprocessing_config:
                full_config['preprocessing'] = preprocessing_config
            
            logger.info("Loaded configuration from R2 production config (same as primary pipeline)")
            return full_config
            
        except Exception as e:
            logger.error(f"Could not load R2 production config: {e}")
            logger.info("Falling back to local config file")
            
            # Fallback to local file
            config_path = os.path.join(os.path.dirname(__file__), 'training_testing', 'config', 'config.yaml')
            try:
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
            except FileNotFoundError:
                logger.warning(f"Config file not found at {config_path}, using defaults")
                return {}
            except Exception as e:
                logger.error(f"Error loading local config: {e}")
                return {}
    
    def _get_default_prompt_template(self) -> str:
        """Default prompt template as fallback"""
        # This should not be used if config is loaded correctly, but is a safe fallback.
        return """You are a senior radiology informatics specialist performing a final quality assurance review.\nPlease select the best match for the input exam from the candidates provided.\nREQUIRED OUTPUT FORMAT (JSON):\n{{\n    "best_match_candidate_number": <Integer>,\n    "best_match_procedure_name": "The full name of the chosen procedure",\n    "final_modality": "The modality of the chosen procedure (e.g., CT, MRI, XR)",\n    "confidence": <Float from 0.0 to 1.0>,\n    "reasoning": "Detailed explanation of your choice."\n}}"""
    
    def _build_enhanced_prompt(self, exam_name: str, context: Dict) -> str:
        """Build enhanced prompt with context from original processing"""
        
        similar_exams = context.get('similar_exams', [])
        
        prompt_template = self.config.get('secondary_pipeline', {}).get('prompt_template', self._get_default_prompt_template())
        
        # Debug logging
        logger.info(f"Building prompt for exam: {exam_name}")
        logger.info(f"Similar exams count: {len(similar_exams)}")
        logger.info(f"Template found: {prompt_template is not None}")
        
        # Limit to top 10 candidates
        limited_exams = similar_exams[:10]
        
        try:
            prompt = prompt_template.format(
                exam_name=exam_name,
                similar_exams=json.dumps(limited_exams, indent=2)
            )
            logger.info(f"Prompt built successfully, length: {len(prompt)}")
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            logger.error(f"Template: {prompt_template[:200]}...")
            raise
        
        return prompt
    
    
    def _parse_model_response(self, content: str) -> Dict:
        """Parse structured response from the new selection-focused model prompt."""
        try:
            # Try to extract JSON from response, including markdown code blocks
            match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                start = content.find('{')
                end = content.rfind('}') + 1
                if start == -1 or end <= start:
                    raise ValueError("No JSON object found in response")
                json_str = content[start:end]

            parsed = json.loads(json_str)
            
            return {
                'best_match_snomed_id': parsed.get('best_match_snomed_id'),
                'best_match_procedure_name': parsed.get('best_match_procedure_name'),
                'confidence': float(parsed.get('confidence', 0.0)),
                'reasoning': parsed.get('reasoning', 'No reasoning provided')
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse structured response: {e}. Content: {content}")
            return {
                'best_match_snomed_id': None,
                'best_match_procedure_name': None,
                'confidence': 0.0,
                'reasoning': f'Failed to parse response: {str(e)}'
            }
    
    async def process_ensemble(self, exam_name: str, context: Dict) -> EnsembleResult:
        """Process exam through all models and generate ensemble result"""
        
        tasks = [self.query_model(model, exam_name, context) for model in self.models]
        model_responses = await asyncio.gather(*tasks)
        
        consensus_result = self._calculate_consensus(model_responses, context.get('similar_exams', []))
        
        original_confidence = context.get('original_confidence', 0.0)
        improved = consensus_result['confidence'] > original_confidence
        
        return EnsembleResult(
            original_result=context.get('original_result', {}),
            consensus_best_match_snomed_id=consensus_result['best_match_snomed_id'],
            consensus_best_match_procedure_name=consensus_result['best_match_procedure_name'],
            consensus_confidence=consensus_result['confidence'],
            model_responses=model_responses,
            agreement_score=consensus_result['agreement_score'],
            final_reasoning=consensus_result['reasoning'],
            improved=improved,
            timestamp=datetime.now().isoformat()
        )
    
    def _calculate_consensus(self, responses: List[ModelResponse], candidates: List[Dict]) -> Dict:
        """Calculate consensus based on the selected best match SNOMED ID."""
        
        valid_responses = [r for r in responses if r.best_match_snomed_id is not None]
        
        if not valid_responses:
            return {
                'best_match_snomed_id': None,
                'best_match_procedure_name': None,
                'confidence': 0.0,
                'agreement_score': 0.0,
                'reasoning': 'All models failed to provide a valid selection.'
            }
            
        # Vote for the best SNOMED ID
        votes = {}
        for r in valid_responses:
            snomed_id = str(r.best_match_snomed_id) # Ensure SNOMED ID is a string for consistent voting
            if snomed_id not in votes:
                votes[snomed_id] = []
            votes[snomed_id].append(r)
            
        # Find the winning SNOMED ID (most votes, then highest average confidence)
        winning_snomed_id = max(
            votes.keys(),
            key=lambda snomed: (len(votes[snomed]), statistics.mean(r.confidence for r in votes[snomed]))
        )
        
        consensus_responses = votes[winning_snomed_id]
        
        # Calculate consensus confidence
        consensus_confidence = statistics.mean(r.confidence for r in consensus_responses)
        agreement_score = len(consensus_responses) / len(valid_responses)
        
        # Get procedure name from the original candidate list using the winning SNOMED ID
        winning_candidate = next((c for c in candidates if str(c.get('snomed_id')) == winning_snomed_id), None)
        consensus_procedure_name = winning_candidate.get('primary_name') if winning_candidate else "Unknown Procedure"

        # Combine reasoning from all agreeing models
        agreeing_models = [r.model.split('/')[-1] for r in consensus_responses]
        combined_reasoning = f"Consensus choice is SNOMED ID {winning_snomed_id} with {agreement_score:.0%} agreement from models: {', '.join(agreeing_models)}.\n\n"
        for r in consensus_responses:
            combined_reasoning += f"--- Reasoning from {r.model.split('/')[-1]} (Confidence: {r.confidence:.2f}) ---\n{r.reasoning}\n\n"
            
        return {
            'best_match_snomed_id': winning_snomed_id,
            'best_match_procedure_name': consensus_procedure_name,
            'confidence': consensus_confidence,
            'agreement_score': agreement_score,
            'reasoning': combined_reasoning.strip()
        }

class SecondaryPipeline:
    """Main secondary pipeline coordinator"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._load_config()
        self.ensemble = OpenRouterEnsemble(self.config.get('openrouter_api_key'), self.config)
        
    def _load_config(self) -> Dict:
        """Load configuration from R2 production URL (same as primary pipeline)"""
        try:
            from config_manager import get_config
            config_manager = get_config()
            
            # Get the full config (all sections)
            full_config = {}
            
            # Load all sections that secondary pipeline needs
            scoring_config = config_manager.get_section('scoring')
            if scoring_config:
                full_config['scoring'] = scoring_config
                
            secondary_config = config_manager.get_section('secondary_pipeline') 
            if secondary_config:
                full_config['secondary_pipeline'] = secondary_config
                # Also merge secondary_pipeline settings directly into root config for compatibility
                full_config.update(secondary_config)
                
            modality_config = config_manager.get_section('modality_similarity')
            if modality_config:
                full_config['modality_similarity'] = modality_config
                
            preprocessing_config = config_manager.get_section('preprocessing')
            if preprocessing_config:
                full_config['preprocessing'] = preprocessing_config
            
            # Add defaults for any missing values
            defaults = {
                'confidence_threshold': 0.8,
                'openrouter_api_key': os.getenv('OPENROUTER_API_KEY'),
                'max_concurrent_requests': 5,
                'output_path': os.path.join(os.environ.get('RENDER_DISK_PATH', '/tmp'), 'secondary_pipeline_results.json')
            }
            
            # Merge defaults with loaded config
            for key, value in defaults.items():
                if key not in full_config:
                    full_config[key] = value
            
            logger.info("SecondaryPipeline loaded configuration from R2 production config")
            return full_config
            
        except Exception as e:
            logger.error(f"SecondaryPipeline could not load R2 production config: {e}")
            logger.info("Falling back to local config file")
            
            # Fallback to local file
            config_path = os.path.join(os.path.dirname(__file__), 'training_testing', 'config', 'config.yaml')
            try:
                with open(config_path, 'r') as f:
                    yaml_config = yaml.safe_load(f)
            except (FileNotFoundError, Exception) as e:
                logger.warning(f"Could not load config from {config_path}: {e}")
                yaml_config = {}
            
            defaults = {
                'confidence_threshold': 0.8,
                'openrouter_api_key': os.getenv('OPENROUTER_API_KEY'),
                'max_concurrent_requests': 5,
                'output_path': os.path.join(os.environ.get('RENDER_DISK_PATH', '/tmp'), 'secondary_pipeline_results.json')
            }
            
            secondary_config = yaml_config.get('secondary_pipeline', {})
            return {**defaults, **secondary_config, 'prompt_template': secondary_config.get('prompt_template')}

    async def process_low_confidence_results(self, results: List[Dict]) -> List[EnsembleResult]:
        """Process list of low-confidence results through ensemble"""

        low_confidence = results
        logger.info(f"Processing {len(low_confidence)} low-confidence results")
        if not low_confidence:
            return []

        ensemble_results = []
        batch_size = self.config.get('max_concurrent_requests', 5)

        for i in range(0, len(low_confidence), batch_size):
            batch = low_confidence[i:i + batch_size]

            tasks = []
            for result in batch:
                output_data = result.get('output', {})
                components = output_data.get('components', {})
                
                # Correctly get exam_name from the top-level of the output object
                exam_name = output_data.get('exam_name', 'Unknown Exam')
                
                context = {
                    'original_confidence': components.get('confidence', 0.0),
                    # Correctly get 'all_candidates' and map it to 'similar_exams'
                    'similar_exams': output_data.get('all_candidates', []),
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
        output_path = output_path or self.config.get('output_path')
        
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
        
        if not results:
            return {'total_processed': 0}

        improved_count = sum(1 for r in results if r.improved)
        total_count = len(results)
        
        original_avg_confidence = statistics.mean([
            r.original_result.get('output', {}).get('components', {}).get('confidence', 0.0) for r in results
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
    
    try:
        with open(primary_results_file, 'r') as f:
            primary_results_data = json.load(f)
            # Assuming the results are in a top-level key, e.g., 'results'
            primary_results = primary_results_data.get('results', primary_results_data)
            if not isinstance(primary_results, list):
                raise ValueError("Primary results file should contain a list of results.")
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error loading or parsing primary results file: {e}")
        return

    pipeline = SecondaryPipeline()
    
    # Filter for low-confidence results based on the pipeline's config
    confidence_threshold = pipeline.config.get('confidence_threshold', 0.8)
    low_confidence_results = [
        r for r in primary_results 
        if r.get('output', {}).get('components', {}).get('confidence', 1.0) < confidence_threshold
    ]

    if not low_confidence_results:
        logger.info("No low-confidence results to process.")
        return [], {}

    ensemble_results = await pipeline.process_low_confidence_results(low_confidence_results)
    
    if ensemble_results:
        pipeline.save_results(ensemble_results)
        report = pipeline.generate_improvement_report(ensemble_results)
        
        logger.info("--- Secondary Pipeline Report ---")
        logger.info(f"Total Exams Processed: {report['total_processed']}")
        logger.info(f"Improved Results: {report['improved_results']} ({report['improvement_rate']:.1%})")
        logger.info(f"Avg. Confidence Change: {report['original_avg_confidence']:.3f} -> {report['new_avg_confidence']:.3f} (Boost: {report['confidence_improvement']:.3f})")
        logger.info(f"High Agreement (>66%): {report['high_agreement_results']} ({report['high_agreement_rate']:.1%})")
        logger.info("---------------------------------")
        
        return ensemble_results, report
    else:
        logger.info("No results were generated by the secondary pipeline.")
        return [], {}

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 secondary_pipeline.py <primary_results_file.json>")
        sys.exit(1)
    
    asyncio.run(run_secondary_pipeline(sys.argv[1]))
