#!/usr/bin/env python3
"""
Secondary Pipeline for Low-Confidence Result Reassessment
Uses multiple OpenRouter models to achieve consensus on uncertain classifications.
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
import openai
from datetime import datetime
import os
import yaml

# Configure logging
logging.basicConfig(level=logging.DEBUG)
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
    best_match_snomed_id: Optional[str]
    best_match_procedure_name: Optional[str]
    confidence: float
    reasoning: str
    raw_response: str
    processing_time: float

@dataclass
class EnsembleResult:
    """Final ensemble result with consensus, aligned with the new selection prompt"""
    original_result: Dict[str, Any]
    consensus_best_match_snomed_id: Optional[str]
    consensus_best_match_procedure_name: Optional[str]
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
    
    def __init__(self, config: Dict):
        self.config = config.get('secondary_pipeline', {})
        self.api_key = os.getenv('OPENROUTER_API_KEY')

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set.")

        self.client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        self.models = self.config.get('models', [
            ModelType.CLAUDE_SONNET.value,
            ModelType.GPT4_TURBO.value, 
            ModelType.GEMINI_PRO.value
        ])
    
    async def query_model(self, model: str, exam_name: str, context: Dict) -> ModelResponse:
        """Query a single model for exam classification using the new selection prompt."""
        start_time = asyncio.get_event_loop().time()
        
        system_prompt, user_prompt = self._build_enhanced_prompt(exam_name, context)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=self.config.get('temperature', 0.0),
                max_tokens=self.config.get('max_tokens', 600)
            )
            
            processing_time = asyncio.get_event_loop().time() - start_time
            content = response.choices[0].message.content
            parsed = self._parse_model_response(content)
            
            return ModelResponse(
                model=model,
                best_match_snomed_id=parsed.get('best_match_snomed_id'),
                best_match_procedure_name=parsed.get('best_match_procedure_name'),
                confidence=parsed.get('confidence', 0.0),
                reasoning=parsed.get('reasoning', 'No reasoning provided'),
                raw_response=content,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error querying {model}: {e}", exc_info=True)
            return ModelResponse(
                model=model,
                best_match_snomed_id=None,
                best_match_procedure_name=None,
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                raw_response="",
                processing_time=asyncio.get_event_loop().time() - start_time
            )
    
    def _build_enhanced_prompt(self, exam_name: str, context: Dict) -> tuple[str, str]:
        """Build the system and user prompts from the configuration."""
        similar_exams = context.get('similar_exams', [])
        
        system_prompt = self.config.get('system_prompt', 'You are a JSON API.')
        user_prompt_template = self.config.get('prompt_template')

        if not user_prompt_template:
            logger.error("'prompt_template' not found in configuration. Cannot build prompt.")
            return system_prompt, "Error: User prompt template is missing from the configuration."
            
        try:
            user_prompt = user_prompt_template.format(
                exam_name=exam_name,
                similar_exams=json.dumps(similar_exams[:10], indent=2)
            )
            logger.debug(f"--- START OF USER PROMPT ---\n{user_prompt}\n--- END OF USER PROMPT ---")
            return system_prompt, user_prompt
        except KeyError as e:
            logger.error(f"A placeholder in the prompt template is missing from the format() call: {e}")
            return system_prompt, f"Error: Could not format prompt. Missing key: {e}"

    def _parse_model_response(self, content: str) -> Dict:
        """Robustly parse the JSON object from a model's potentially messy response."""
        try:
            # Find the start of a JSON object that specifically contains our key
            match = re.search(r'}_{{\s*"best_match_snomed_id":', content)
            if not match:
                raise ValueError("No valid JSON object start found in response.")

            # Start parsing from that point
            json_str = content[match.start():]
            
            # Use a proper JSON decoder to find the end of the object
            decoder = json.JSONDecoder()
            parsed, _ = decoder.raw_decode(json_str)

            confidence = float(parsed['confidence']) if parsed.get('confidence') is not None else 0.0

            return {
                'best_match_snomed_id': parsed.get('best_match_snomed_id'),
                'best_match_procedure_name': parsed.get('best_match_procedure_name'),
                'confidence': confidence,
                'reasoning': parsed.get('reasoning', 'No reasoning provided')
            }
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse structured response: {e}. Content: {content}")
            return {'best_match_snomed_id': None, 'best_match_procedure_name': None, 'confidence': 0.0, 'reasoning': f'Failed to parse response: {str(e)}'}
    
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
            return {'best_match_snomed_id': None, 'best_match_procedure_name': None, 'confidence': 0.0, 'agreement_score': 0.0, 'reasoning': 'All models failed to provide a valid selection.'}
            
        votes = {}
        for r in valid_responses:
            snomed_id = str(r.best_match_snomed_id)
            if snomed_id not in votes:
                votes[snomed_id] = []
            votes[snomed_id].append(r)
            
        winning_snomed_id = max(votes.keys(), key=lambda snomed: (len(votes[snomed]), statistics.mean(r.confidence for r in votes[snomed])))
        
        consensus_responses = votes[winning_snomed_id]
        consensus_confidence = statistics.mean(r.confidence for r in consensus_responses)
        agreement_score = len(consensus_responses) / len(valid_responses)
        
        winning_candidate = next((c for c in candidates if str(c.get('snomed_id')) == winning_snomed_id), None)
        consensus_procedure_name = winning_candidate.get('primary_name') if winning_candidate else "Unknown Procedure"

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
    
    def __init__(self):
        self.config = self._load_config()
        self.ensemble = OpenRouterEnsemble(config=self.config)
        
    def _load_config(self) -> Dict:
        """Load configuration, preferring R2 but falling back to local file."""
        try:
            from config_manager import get_config
            config_manager = get_config()
            if config_manager.force_r2_reload():
                logger.info("Successfully loaded latest configuration from R2 for Secondary Pipeline.")
                return config_manager.get_full_config()
            else:
                raise RuntimeError("Failed to fetch config from R2.")
        except Exception as e:
            logger.warning(f"Could not load config from R2 ({e}), falling back to local file.")
            config_path = os.path.join(os.path.dirname(__file__), 'training_testing', 'config', 'config.yaml')
            try:
                with open(config_path, 'r') as f:
                    conf = yaml.safe_load(f)
                    logger.info(f"Successfully loaded local config from {config_path}")
                    return conf
            except Exception as file_e:
                logger.error(f"CRITICAL: Failed to load local config file: {file_e}")
                return {}

    async def process_low_confidence_results(self, results: List[Dict]) -> List[EnsembleResult]:
        """Process list of low-confidence results through ensemble"""
        low_confidence = results
        logger.info(f"Processing {len(low_confidence)} low-confidence results")
        if not low_confidence:
            return []

        ensemble_results = []
        batch_size = self.config.get('secondary_pipeline', {}).get('max_concurrent_requests', 5)

        for i in range(0, len(low_confidence), batch_size):
            batch = low_confidence[i:i + batch_size]
            tasks = []
            for result in batch:
                output_data = result.get('output', {})
                context = {
                    'original_confidence': output_data.get('components', {}).get('confidence', 0.0),
                    'similar_exams': output_data.get('all_candidates', []),
                    'original_result': result
                }
                tasks.append(self.ensemble.process_ensemble(output_data.get('exam_name', 'Unknown'), context))

            batch_results = await asyncio.gather(*tasks)
            ensemble_results.extend(batch_results)
            logger.info(f"Completed batch {i//batch_size + 1}/{(len(low_confidence) - 1) // batch_size + 1}")

        return ensemble_results
    
    def save_results(self, results: List[EnsembleResult], output_path: str = None):
        """Save ensemble results to file"""
        path = output_path or self.config.get('secondary_pipeline', {}).get('output_path', '/tmp/secondary_pipeline_results.json')
        serializable_results = [res.to_dict() for res in results]
        
        with open(path, 'w') as f:
            json.dump({'timestamp': datetime.now().isoformat(), 'total_processed': len(results), 'results': serializable_results}, f, indent=2)
        
        logger.info(f"Results saved to {path}")
    
    def generate_improvement_report(self, results: List[EnsembleResult]) -> Dict:
        """Generate report on improvements achieved"""
        if not results:
            return {'total_processed': 0}

        improved_count = sum(1 for r in results if r.improved)
        total_count = len(results)
        
        original_confidences = [r.original_result.get('output', {}).get('components', {}).get('confidence', 0.0) for r in results]
        original_avg_confidence = statistics.mean(original_confidences) if original_confidences else 0.0
        
        new_confidences = [r.consensus_confidence for r in results]
        new_avg_confidence = statistics.mean(new_confidences) if new_confidences else 0.0
        
        high_agreement = sum(1 for r in results if r.agreement_score >= 0.67)
        
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
        return

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
