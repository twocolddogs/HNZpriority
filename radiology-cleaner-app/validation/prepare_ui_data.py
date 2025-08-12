#!/usr/bin/env python3
"""
Validation UI Data Preparation Script

This script prepares validation state data for the frontend UI by:
1. Loading validation state from JSON files
2. Filtering and prioritizing mappings based on attention flags
3. Creating organized data structures for efficient UI rendering
4. Generating summary statistics and progress metrics

Part of the Human-in-the-Loop (HITL) validation pipeline for radiology cleaner.
"""

import json
import logging
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ValidationUIDataPreparer:
    """Prepares validation state data for optimal UI rendering and interaction."""
    
    def __init__(self, validation_dir: str = 'validation'):
        """
        Initialize the UI data preparer.
        
        Args:
            validation_dir: Directory containing validation state files
        """
        self.validation_dir = Path(validation_dir)
        self.validation_state = {}
        self.approved_mappings = {}
        self.rejected_mappings = {}
        
    def load_validation_files(self) -> bool:
        """
        Load all validation state files.
        
        Returns:
            bool: True if files loaded successfully
        """
        try:
            # Load validation state
            state_file = self.validation_dir / 'validation_state.json'
            if state_file.exists():
                with open(state_file, 'r') as f:
                    self.validation_state = json.load(f)
                logger.info(f"Loaded {len(self.validation_state)} mappings from validation state")
            else:
                logger.warning("validation_state.json not found")
                
            # Load approved mappings cache from R2
            self.approved_mappings = {}
            try:
                import requests
                approved_url = "https://pub-cc78b976831e4f649dd695ffa52d1171.r2.dev/validation/approved_mappings_cache.json"
                response = requests.get(approved_url, timeout=10)
                
                if response.status_code == 200:
                    approved_data = response.json()
                    
                    # Handle canonical schema with entries wrapper
                    if isinstance(approved_data, dict) and 'entries' in approved_data:
                        self.approved_mappings = approved_data['entries']
                    else:
                        # Legacy flat structure or other format
                        self.approved_mappings = approved_data
                        
                    logger.info(f"Loaded {len(self.approved_mappings)} approved mappings from R2")
                else:
                    logger.warning(f"Could not load approved cache from R2: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Failed to load approved mappings cache from R2: {e}")
                
            # Load rejected mappings from R2
            self.rejected_mappings = {}
            try:
                import requests
                rejected_url = "https://pub-cc78b976831e4f649dd695ffa52d1171.r2.dev/validation/rejected_mappings_cache.json"
                response = requests.get(rejected_url, timeout=10)
                
                if response.status_code == 200:
                    rejected_data = response.json()
                    
                    # Handle canonical schema with entries wrapper  
                    if isinstance(rejected_data, dict) and 'entries' in rejected_data:
                        self.rejected_mappings = rejected_data['entries']
                    else:
                        # Legacy flat structure or other format
                        self.rejected_mappings = rejected_data
                        
                    logger.info(f"Loaded {len(self.rejected_mappings)} rejected mappings from R2")
                else:
                    logger.info(f"Rejected mappings cache not found in R2: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Failed to load rejected mappings cache from R2: {e}")
                
            # Update validation state with approved/rejected status from caches
            self._update_validation_status_from_caches()
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to load validation files: {e}")
            return False
    
    def categorize_by_flags(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize mappings by their attention flags for priority-based review.
        
        Returns:
            Dict containing categorized mappings by flag type
        """
        categories = {
            'high_priority': [],      # Low confidence + ambiguous
            'medium_priority': [],    # Single attention flag
            'low_priority': [],       # High confidence gap or secondary pipeline
            'review_ready': [],       # No attention flags
            'completed': []           # Already reviewed
        }
        
        for mapping_id, state in self.validation_state.items():
            flags = state.get('needs_attention_flags', [])
            status = state.get('validation_status', 'pending_review')
            
            # Skip completed items for priority queues
            if status in ['approved', 'rejected', 'modified']:
                categories['completed'].append(state)
                continue
                
            # Categorize by priority based on flags
            if 'low_confidence' in flags and ('ambiguous' in flags or len(flags) > 2):
                categories['high_priority'].append(state)
            elif len(flags) == 1 and flags[0] in ['low_confidence', 'ambiguous', 'singleton_mapping']:
                categories['medium_priority'].append(state)
            elif 'high_confidence_gap' in flags or 'secondary_pipeline' in flags:
                categories['low_priority'].append(state)
            else:
                categories['review_ready'].append(state)
        
        # Sort each category by confidence score (lowest first for attention)
        for category in ['high_priority', 'medium_priority', 'low_priority']:
            categories[category].sort(
                key=lambda x: x.get('original_mapping', {}).get('components', {}).get('confidence', 1.0)
            )
        
        logger.info(f"Categorized mappings: High={len(categories['high_priority'])}, "
                   f"Medium={len(categories['medium_priority'])}, Low={len(categories['low_priority'])}, "
                   f"Ready={len(categories['review_ready'])}, Completed={len(categories['completed'])}")
        
        return categories
    
    def generate_progress_metrics(self) -> Dict[str, Any]:
        """
        Generate progress and completion metrics for the validation workflow.
        
        Returns:
            Dict containing progress metrics and statistics
        """
        total_mappings = len(self.validation_state)
        if total_mappings == 0:
            return {'error': 'No mappings found in validation state'}
        
        # Count by status
        status_counts = {
            'pending_review': 0,
            'approved': 0,
            'rejected': 0,
            'modified': 0,
            'in_review': 0
        }
        
        # Count by flags
        flag_counts = {
            'low_confidence': 0,
            'ambiguous': 0,
            'singleton_mapping': 0,
            'high_confidence_gap': 0,
            'secondary_pipeline': 0
        }
        
        confidence_scores = []
        
        for state in self.validation_state.values():
            # Count statuses
            status = state.get('validation_status', 'pending_review')
            if status in status_counts:
                status_counts[status] += 1
            
            # Count flags
            flags = state.get('needs_attention_flags', [])
            for flag in flags:
                if flag in flag_counts:
                    flag_counts[flag] += 1
            
            # Collect confidence scores
            confidence = state.get('original_mapping', {}).get('components', {}).get('confidence')
            if confidence is not None:
                confidence_scores.append(confidence)
        
        # Calculate completion rate
        completed = status_counts['approved'] + status_counts['rejected'] + status_counts['modified']
        completion_rate = (completed / total_mappings) * 100 if total_mappings > 0 else 0
        
        # Calculate average confidence
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        # Determine next recommended actions
        recommendations = []
        if flag_counts['low_confidence'] > 0:
            recommendations.append(f"Review {flag_counts['low_confidence']} low confidence mappings first")
        if flag_counts['ambiguous'] > 0:
            recommendations.append(f"Resolve {flag_counts['ambiguous']} ambiguous mappings")
        if completion_rate < 50:
            recommendations.append("Focus on high-priority flagged items to maximize impact")
        
        return {
            'total_mappings': total_mappings,
            'completion_rate': round(completion_rate, 1),
            'status_breakdown': status_counts,
            'flag_breakdown': flag_counts,
            'average_confidence': round(avg_confidence, 3),
            'confidence_distribution': {
                'very_low': len([c for c in confidence_scores if c < 0.7]),
                'low': len([c for c in confidence_scores if 0.7 <= c < 0.85]),
                'good': len([c for c in confidence_scores if 0.85 <= c < 0.95]),
                'high': len([c for c in confidence_scores if c >= 0.95])
            },
            'recommendations': recommendations,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
    
    def create_review_queue(self, max_items: int = 50) -> List[Dict[str, Any]]:
        """
        Create a prioritized review queue for efficient validation workflow.
        
        Args:
            max_items: Maximum number of items to include in the queue
            
        Returns:
            List of mappings ordered by review priority
        """
        categories = self.categorize_by_flags()
        review_queue = []
        
        # Add items in priority order
        priority_order = ['high_priority', 'medium_priority', 'low_priority', 'review_ready']
        
        for category in priority_order:
            items_needed = max_items - len(review_queue)
            if items_needed <= 0:
                break
                
            category_items = categories[category][:items_needed]
            
            # Add priority metadata to each item
            for item in category_items:
                item_with_meta = item.copy()
                item_with_meta['queue_priority'] = category
                item_with_meta['queue_position'] = len(review_queue) + 1
                review_queue.append(item_with_meta)
        
        logger.info(f"Created review queue with {len(review_queue)} items")
        return review_queue
    
    def prepare_ui_data_package(self, max_queue_items: int = 50) -> Dict[str, Any]:
        """
        Prepare complete data package for the validation UI.
        
        Args:
            max_queue_items: Maximum items to include in review queue
            
        Returns:
            Complete UI data package with all necessary information
        """
        if not self.load_validation_files():
            return {'error': 'Failed to load validation files'}
        
        try:
            categories = self.categorize_by_flags()
            progress_metrics = self.generate_progress_metrics()
            review_queue = self.create_review_queue(max_queue_items)
            
            ui_data_package = {
                'metadata': {
                    'generated_at': datetime.utcnow().isoformat() + 'Z',
                    'total_mappings': len(self.validation_state),
                    'data_version': '1.0'
                },
                'progress_metrics': progress_metrics,
                'categorized_mappings': {
                    k: len(v) for k, v in categories.items()
                },
                'review_queue': review_queue,
                'flag_summary': {
                    flag: len([s for s in self.validation_state.values() 
                              if flag in s.get('needs_attention_flags', [])])
                    for flag in ['low_confidence', 'ambiguous', 'singleton_mapping', 
                               'high_confidence_gap', 'secondary_pipeline']
                },
                'validation_statistics': {
                    'pending_count': len([s for s in self.validation_state.values() 
                                        if s.get('validation_status') == 'pending_review']),
                    'approved_count': len(self.approved_mappings),
                    'rejected_count': len(self.rejected_mappings),
                    'avg_flags_per_mapping': sum(len(s.get('needs_attention_flags', [])) 
                                               for s in self.validation_state.values()) / len(self.validation_state)
                    if self.validation_state else 0
                }
            }
            
            logger.info("Successfully prepared UI data package")
            return ui_data_package
            
        except Exception as e:
            logger.error(f"Failed to prepare UI data package: {e}")
            return {'error': f'Data preparation failed: {str(e)}'}
    
    def export_ui_data(self, output_file: str = 'validation/ui_data.json') -> bool:
        """
        Export prepared UI data to JSON file.
        
        Args:
            output_file: Path for the output file
            
        Returns:
            bool: True if export successful
        """
        try:
            ui_data = self.prepare_ui_data_package()
            
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(ui_data, f, indent=2)
            
            logger.info(f"UI data exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export UI data: {e}")
            return False


def main():
    """Main function for running the UI data preparation script."""
    logger.info("Starting validation UI data preparation")
    
    preparer = ValidationUIDataPreparer()
    
    # Prepare and export UI data
    if preparer.export_ui_data():
        logger.info("✅ UI data preparation completed successfully")
        
        # Display summary
        ui_data = preparer.prepare_ui_data_package()
        if 'progress_metrics' in ui_data:
            metrics = ui_data['progress_metrics']
            logger.info(f"📊 Summary: {metrics['total_mappings']} mappings, "
                       f"{metrics['completion_rate']}% complete")
            logger.info(f"🚨 Attention needed: {sum(ui_data['flag_summary'].values())} flagged items")
        
    else:
        logger.error("❌ UI data preparation failed")
        return 1
        
    return 0


if __name__ == "__main__":
    exit(main())