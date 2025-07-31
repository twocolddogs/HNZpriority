#!/usr/bin/env python3
"""
Integration module for connecting the secondary pipeline with existing Flask application.
Provides hooks and utilities for seamless integration.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
from pathlib import Path

from secondary_pipeline import SecondaryPipeline

logger = logging.getLogger(__name__)

class PipelineIntegration:
    """Integration layer for secondary pipeline with main application"""
    
    def __init__(self, app_config: Dict = None):
        self.app_config = app_config or {}
        self.pipeline_config = self._build_pipeline_config()
        self.secondary_pipeline = None
        
    def _build_pipeline_config(self) -> Dict:
        """Build secondary pipeline configuration from app config"""
        return {
            'confidence_threshold': self.app_config.get('SECONDARY_PIPELINE_THRESHOLD', 0.8),
            'openrouter_api_key': self.app_config.get('OPENROUTER_API_KEY') or os.getenv('OPENROUTER_API_KEY'),
            'max_concurrent_requests': self.app_config.get('SECONDARY_PIPELINE_CONCURRENCY', 3),
            'output_path': self.app_config.get('SECONDARY_PIPELINE_OUTPUT', '/tmp/secondary_results.json'),
            'enabled': self.app_config.get('ENABLE_SECONDARY_PIPELINE', True)
        }
    
    def is_enabled(self) -> bool:
        """Check if secondary pipeline is enabled"""
        return (
            self.pipeline_config.get('enabled', True) and 
            self.pipeline_config.get('openrouter_api_key') is not None
        )
    
    async def trigger_secondary_processing(self, batch_results: List[Dict]) -> Optional[Dict]:
        """Trigger secondary processing for a batch of results"""
        
        if not self.is_enabled():
            logger.info("Secondary pipeline disabled or not configured")
            return None
        
        # Initialize pipeline if needed
        if not self.secondary_pipeline:
            self.secondary_pipeline = SecondaryPipeline(self.pipeline_config)
        
        try:
            # Identify low-confidence results
            low_confidence_results = [
                result for result in batch_results
                if result.get('output', {}).get('components', {}).get('confidence', 1.0) < self.pipeline_config['confidence_threshold']
            ]
            
            if not low_confidence_results:
                logger.info("No low-confidence results found, skipping secondary processing")
                return {
                    'processed': 0,
                    'improved': 0,
                    'skipped_reason': 'no_low_confidence_results'
                }
            
            logger.info(f"Starting secondary processing for {len(low_confidence_results)} results")
            
            # Process through ensemble
            ensemble_results = await self.secondary_pipeline.process_low_confidence_results(
                low_confidence_results
            )
            
            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"/tmp/secondary_results_{timestamp}.json"
            self.secondary_pipeline.save_results(ensemble_results, output_file)
            
            # Generate report
            report = self.secondary_pipeline.generate_improvement_report(ensemble_results)
            report['output_file'] = output_file
            report['timestamp'] = timestamp
            report['results'] = [res.to_dict() for res in ensemble_results] # Add full results to report
            
            logger.info(f"Secondary processing completed: {report['improved_results']}/{report['total_processed']} improved")
            
            return report
            
        except Exception as e:
            logger.error(f"Secondary pipeline error: {e}")
            return {
                'error': str(e),
                'processed': 0,
                'improved': 0
            }

# Flask routes are now defined directly in app.py to avoid duplication

class BatchResultProcessor:
    """Processor for handling batch results with secondary pipeline integration"""
    
    def __init__(self, integration: PipelineIntegration):
        self.integration = integration
        
    async def process_batch_with_secondary(self, batch_results: List[Dict]) -> Dict:
        """Process batch results and automatically trigger secondary pipeline if needed"""
        
        # Original batch processing results
        original_stats = self._calculate_batch_stats(batch_results)
        
        # Check if secondary processing is warranted
        secondary_report = None
        if self._should_trigger_secondary(original_stats):
            secondary_report = await self.integration.trigger_secondary_processing(batch_results)
        
        return {
            'primary_results': {
                'total_processed': len(batch_results),
                'low_confidence_count': original_stats['low_confidence_count'],
                'average_confidence': original_stats['average_confidence']
            },
            'secondary_results': secondary_report,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_batch_stats(self, results: List[Dict]) -> Dict:
        """Calculate statistics for batch results"""
        if not results:
            return {'low_confidence_count': 0, 'average_confidence': 0.0}
        
        confidences = [r.get('output', {}).get('components', {}).get('confidence', 1.0) for r in results]
        threshold = self.integration.pipeline_config['confidence_threshold']
        
        return {
            'low_confidence_count': sum(1 for c in confidences if c < threshold),
            'average_confidence': sum(confidences) / len(confidences)
        }
    
    def _should_trigger_secondary(self, stats: Dict) -> bool:
        """Determine if secondary processing should be triggered"""
        
        if not self.integration.is_enabled():
            return False
        
        # Trigger if we have low-confidence results
        return stats['low_confidence_count'] > 0

def create_config_template() -> Dict:
    """Create configuration template for secondary pipeline"""
    return {
        # Secondary Pipeline Configuration
        'ENABLE_SECONDARY_PIPELINE': True,
        'SECONDARY_PIPELINE_THRESHOLD': 0.8,
        'SECONDARY_PIPELINE_CONCURRENCY': 3,
        'SECONDARY_PIPELINE_OUTPUT': '/tmp/secondary_results.json',
        'OPENROUTER_API_KEY': 'your-openrouter-api-key-here',
        
        # Model Configuration
        'SECONDARY_PIPELINE_MODELS': [
            'anthropic/claude-3.5-sonnet',
            'openai/gpt-4-turbo', 
            'google/gemini-pro'
        ],
        
        # Performance Settings
        'SECONDARY_PIPELINE_TIMEOUT': 300,  # 5 minutes
        'SECONDARY_PIPELINE_RETRY_COUNT': 2,
        
        # Logging
        'SECONDARY_PIPELINE_LOG_LEVEL': 'INFO'
    }

if __name__ == "__main__":
    # Example usage
    print("Secondary Pipeline Integration Module")
    print("Configuration template:")
    print(json.dumps(create_config_template(), indent=2))