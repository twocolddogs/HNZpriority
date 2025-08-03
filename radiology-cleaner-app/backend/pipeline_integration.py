#!/usr/bin/env python3
"""
Integration module for connecting the secondary pipeline with existing Flask application.
Provides hooks and utilities for seamless integration.
"""

import asyncio
import json
import logging
import statistics
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
        self.secondary_pipeline = None
    
    def is_enabled(self) -> bool:
        """Check if secondary pipeline is enabled by checking for the API key."""
        return os.getenv('OPENROUTER_API_KEY') is not None
    
    async def trigger_secondary_processing(self, batch_results: List[Dict]) -> Optional[Dict]:
        """Trigger secondary processing for a batch of results"""
        
        if not self.is_enabled():
            logger.info("Secondary pipeline disabled (OPENROUTER_API_KEY not set)")
            return None
        
        # Initialize pipeline if needed. It loads its own config.
        if not self.secondary_pipeline:
            self.secondary_pipeline = SecondaryPipeline()
        
        try:
            # Identify low-confidence results based on the threshold from its own config
            confidence_threshold = self.secondary_pipeline.config.get('secondary_pipeline', {}).get('confidence_threshold', 0.8)
            low_confidence_results = [
                result for result in batch_results
                if result.get('output', {}).get('components', {}).get('confidence', 1.0) < confidence_threshold
            ]
            
            if not low_confidence_results:
                logger.info("No low-confidence results found, skipping secondary processing")
                return {'processed': 0, 'improved': 0, 'skipped_reason': 'no_low_confidence_results'}
            
            logger.info(f"Starting secondary processing for {len(low_confidence_results)} results")
            
            ensemble_results = await self.secondary_pipeline.process_low_confidence_results(low_confidence_results)
            
            # Generate and return the report
            report = self.secondary_pipeline.generate_improvement_report(ensemble_results)
            report['results'] = [res.to_dict() for res in ensemble_results]
            
            logger.info(f"Secondary processing completed: {report.get('improved_results', 0)}/{report.get('total_processed', 0)} improved")
            
            return report
            
        except Exception as e:
            logger.error(f"Secondary pipeline error: {e}", exc_info=True)
            return {'error': str(e), 'processed': 0, 'improved': 0}

class BatchResultProcessor:
    """Processor for handling batch results with secondary pipeline integration"""
    
    def __init__(self, integration: PipelineIntegration):
        self.integration = integration
        
    async def process_batch_with_secondary(self, batch_results: List[Dict]) -> Dict:
        """Process batch results and automatically trigger secondary pipeline if needed"""
        
        primary_stats = self._calculate_batch_stats(batch_results)
        secondary_report = None
        
        if self.integration.is_enabled() and primary_stats['low_confidence_count'] > 0:
            secondary_report = await self.integration.trigger_secondary_processing(batch_results)
        
        return {
            'primary_results': primary_stats,
            'secondary_results': secondary_report,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_batch_stats(self, results: List[Dict]) -> Dict:
        """Calculate statistics for batch results"""
        if not results:
            return {'low_confidence_count': 0, 'average_confidence': 0.0}
        
        # This is tricky because the threshold is in the secondary pipeline's config.
        # We can't access it easily here without loading it twice. 
        # For now, we will just count all results below 1.0 as potentially low confidence.
        # The actual filtering happens inside trigger_secondary_processing.
        confidences = [r.get('output', {}).get('components', {}).get('confidence', 1.0) for r in results]
        
        return {
            'total_processed': len(results),
            'low_confidence_count': sum(1 for c in confidences if c < 0.99), # Approximate count
            'average_confidence': statistics.mean(confidences) if confidences else 0.0
        }
