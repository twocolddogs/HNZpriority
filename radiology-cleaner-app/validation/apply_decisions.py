#!/usr/bin/env python3
"""
Validation Decision Application Script

This script applies human validation decisions back to the system by:
1. Processing validation decisions from the UI or import files
2. Updating approved_mappings_cache.json and rejected_mappings.json
3. Generating final export mappings with corrections applied
4. Creating audit trail and decision logs
5. Preparing data for system integration or R2 upload

Part of the Human-in-the-Loop (HITL) validation pipeline for radiology cleaner.
"""

import json
import logging
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from pathlib import Path
import hashlib
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ValidationDecisionApplicator:
    """Applies validation decisions and manages the final mapping outputs."""
    
    def __init__(self, validation_dir: str = 'validation'):
        """
        Initialize the decision applicator.
        
        Args:
            validation_dir: Directory containing validation state files
        """
        self.validation_dir = Path(validation_dir)
        self.validation_state = {}
        self.approved_mappings = {}
        self.rejected_mappings = {}
        self.decision_log = []
        
    def load_current_state(self) -> bool:
        """
        Load current validation state and existing decisions.
        
        Returns:
            bool: True if state loaded successfully
        """
        try:
            # Load validation state
            state_file = self.validation_dir / 'validation_state.json'
            if state_file.exists():
                with open(state_file, 'r') as f:
                    self.validation_state = json.load(f)
                logger.info(f"Loaded {len(self.validation_state)} mappings from validation state")
            else:
                logger.error("validation_state.json not found")
                return False
                
            # Load existing approved mappings
            approved_file = self.validation_dir / 'approved_mappings_cache.json'
            if approved_file.exists():
                with open(approved_file, 'r') as f:
                    approved_data = json.load(f)
                    
                # Handle canonical schema with entries wrapper
                if isinstance(approved_data, dict) and 'entries' in approved_data:
                    self.approved_mappings = approved_data['entries']
                else:
                    # Legacy flat structure or other format
                    self.approved_mappings = approved_data
                    
                logger.info(f"Loaded {len(self.approved_mappings)} existing approved mappings")
            else:
                self.approved_mappings = {}
                
            # Load existing rejected mappings
            rejected_file = self.validation_dir / 'rejected_mappings.json'
            if rejected_file.exists():
                with open(rejected_file, 'r') as f:
                    rejected_data = json.load(f)
                    
                # Handle canonical schema with entries wrapper  
                if isinstance(rejected_data, dict) and 'entries' in rejected_data:
                    self.rejected_mappings = rejected_data['entries']
                else:
                    # Legacy flat structure or other format
                    self.rejected_mappings = rejected_data
                    
                logger.info(f"Loaded {len(self.rejected_mappings)} existing rejected mappings")
            else:
                self.rejected_mappings = {}
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to load current state: {e}")
            return False
    
    def apply_validation_decisions(self, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply a list of validation decisions to the current state.
        
        Args:
            decisions: List of decision objects with mapping_id, decision, notes, etc.
            
        Returns:
            Dict containing results of applying decisions
        """
        results = {
            'processed_count': 0,
            'approved_count': 0,
            'rejected_count': 0,
            'modified_count': 0,
            'error_count': 0,
            'errors': []
        }
        
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        for decision_data in decisions:
            try:
                mapping_id = decision_data.get('mapping_id')
                decision = decision_data.get('decision')
                notes = decision_data.get('notes', '')
                corrected_mapping = decision_data.get('corrected_mapping')
                
                if not mapping_id or not decision:
                    results['errors'].append(f"Missing mapping_id or decision in: {decision_data}")
                    results['error_count'] += 1
                    continue
                
                if mapping_id not in self.validation_state:
                    results['errors'].append(f"Mapping ID {mapping_id} not found in validation state")
                    results['error_count'] += 1
                    continue
                
                # Update validation state
                self.validation_state[mapping_id]['validator_decision'] = decision
                self.validation_state[mapping_id]['validation_notes'] = notes
                self.validation_state[mapping_id]['timestamp_reviewed'] = timestamp
                
                # Apply decision
                original_mapping = self.validation_state[mapping_id]['original_mapping']
                
                if decision == 'approve':
                    self.validation_state[mapping_id]['validation_status'] = 'approved'
                    self.approved_mappings[mapping_id] = {
                        'mapping_data': original_mapping,
                        'validation_notes': notes,
                        'approved_at': timestamp,
                        'original_flags': self.validation_state[mapping_id]['needs_attention_flags']
                    }
                    results['approved_count'] += 1
                    
                elif decision == 'reject':
                    self.validation_state[mapping_id]['validation_status'] = 'rejected'
                    self.rejected_mappings[mapping_id] = {
                        'mapping_data': original_mapping,
                        'rejection_reason': notes,
                        'rejected_at': timestamp,
                        'original_flags': self.validation_state[mapping_id]['needs_attention_flags']
                    }
                    results['rejected_count'] += 1
                    
                elif decision == 'modify' and corrected_mapping:
                    self.validation_state[mapping_id]['validation_status'] = 'modified'
                    self.validation_state[mapping_id]['corrected_mapping'] = corrected_mapping
                    self.approved_mappings[mapping_id] = {
                        'mapping_data': corrected_mapping,  # Use corrected version
                        'original_mapping': original_mapping,  # Keep original for audit
                        'validation_notes': notes,
                        'approved_at': timestamp,
                        'was_modified': True,
                        'original_flags': self.validation_state[mapping_id]['needs_attention_flags']
                    }
                    results['modified_count'] += 1
                    
                else:
                    results['errors'].append(f"Invalid decision '{decision}' or missing corrected_mapping")
                    results['error_count'] += 1
                    continue
                
                # Log the decision
                decision_log_entry = {
                    'mapping_id': mapping_id,
                    'decision': decision,
                    'notes': notes,
                    'timestamp': timestamp,
                    'original_flags': self.validation_state[mapping_id]['needs_attention_flags']
                }
                if corrected_mapping:
                    decision_log_entry['had_corrections'] = True
                    
                self.decision_log.append(decision_log_entry)
                results['processed_count'] += 1
                
                logger.debug(f"Applied decision '{decision}' for mapping {mapping_id}")
                
            except Exception as e:
                error_msg = f"Error processing decision for mapping {decision_data.get('mapping_id', 'unknown')}: {str(e)}"
                results['errors'].append(error_msg)
                results['error_count'] += 1
                logger.error(error_msg)
        
        logger.info(f"Applied {results['processed_count']} decisions: "
                   f"{results['approved_count']} approved, {results['rejected_count']} rejected, "
                   f"{results['modified_count']} modified, {results['error_count']} errors")
        
        return results
    
    def save_updated_state(self) -> bool:
        """
        Save updated validation state and decision files.
        
        Returns:
            bool: True if save successful
        """
        try:
            # Save updated validation state
            state_file = self.validation_dir / 'validation_state.json'
            with open(state_file, 'w') as f:
                json.dump(self.validation_state, f, indent=2)
            logger.info(f"Updated validation state saved to {state_file}")
            
            # Save approved mappings in canonical schema format
            approved_file = self.validation_dir / 'approved_mappings_cache.json'
            approved_cache_data = {
                "meta": {
                    "version": 1,
                    "last_updated": datetime.utcnow().isoformat() + 'Z',
                    "schema": "approved_mappings_cache.v1"
                },
                "entries": self.approved_mappings
            }
            with open(approved_file, 'w') as f:
                json.dump(approved_cache_data, f, indent=2)
            logger.info(f"Approved mappings saved to {approved_file}")
            
            # Save rejected mappings in canonical schema format
            rejected_file = self.validation_dir / 'rejected_mappings.json'
            rejected_cache_data = {
                "meta": {
                    "version": 1,
                    "last_updated": datetime.utcnow().isoformat() + 'Z',
                    "schema": "rejected_mappings_cache.v1"
                },
                "entries": self.rejected_mappings
            }
            with open(rejected_file, 'w') as f:
                json.dump(rejected_cache_data, f, indent=2)
            logger.info(f"Rejected mappings saved to {rejected_file}")
            
            # Save decision log
            if self.decision_log:
                log_file = self.validation_dir / f'decision_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                with open(log_file, 'w') as f:
                    json.dump({
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'total_decisions': len(self.decision_log),
                        'decisions': self.decision_log
                    }, f, indent=2)
                logger.info(f"Decision log saved to {log_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save updated state: {e}")
            return False
    
    def generate_final_export_mappings(self) -> List[Dict[str, Any]]:
        """
        Generate final export mappings combining approved and corrected mappings.
        
        Returns:
            List of approved mappings ready for system integration
        """
        final_mappings = []
        
        for mapping_id, approved_data in self.approved_mappings.items():
            mapping = approved_data['mapping_data'].copy()
            
            # Add validation metadata
            mapping['validation_metadata'] = {
                'validated_at': approved_data['approved_at'],
                'was_modified': approved_data.get('was_modified', False),
                'original_flags': approved_data.get('original_flags', []),
                'validation_notes': approved_data.get('validation_notes', ''),
                'mapping_id': mapping_id
            }
            
            # Add confidence boost for validated mappings
            if 'components' in mapping and 'confidence' in mapping['components']:
                original_confidence = mapping['components']['confidence']
                # Boost confidence for human-validated mappings
                boosted_confidence = min(0.98, original_confidence + 0.1)
                mapping['components']['confidence'] = boosted_confidence
                mapping['validation_metadata']['confidence_boost'] = boosted_confidence - original_confidence
            
            final_mappings.append(mapping)
        
        logger.info(f"Generated {len(final_mappings)} final export mappings")
        return final_mappings
    
    def create_validation_summary_report(self) -> Dict[str, Any]:
        """
        Create comprehensive validation summary report.
        
        Returns:
            Dict containing validation summary and statistics
        """
        total_mappings = len(self.validation_state)
        approved_count = len(self.approved_mappings)
        rejected_count = len(self.rejected_mappings)
        pending_count = total_mappings - approved_count - rejected_count
        
        # Analyze decision patterns
        decision_summary = {'approve': 0, 'reject': 0, 'modify': 0}
        flag_analysis = {'resolved_flags': {}, 'common_rejection_reasons': {}}
        
        for entry in self.decision_log:
            decision = entry['decision']
            if decision in decision_summary:
                decision_summary[decision] += 1
            
            # Track which flags were resolved
            for flag in entry.get('original_flags', []):
                if flag not in flag_analysis['resolved_flags']:
                    flag_analysis['resolved_flags'][flag] = {'approve': 0, 'reject': 0, 'modify': 0}
                if decision in flag_analysis['resolved_flags'][flag]:
                    flag_analysis['resolved_flags'][flag][decision] += 1
        
        # Calculate validation quality metrics
        completion_rate = ((approved_count + rejected_count) / total_mappings * 100) if total_mappings > 0 else 0
        approval_rate = (approved_count / (approved_count + rejected_count) * 100) if (approved_count + rejected_count) > 0 else 0
        
        report = {
            'validation_summary': {
                'total_mappings_processed': total_mappings,
                'completion_rate': round(completion_rate, 1),
                'approval_rate': round(approval_rate, 1),
                'final_counts': {
                    'approved': approved_count,
                    'rejected': rejected_count,
                    'pending': pending_count
                }
            },
            'decision_analysis': {
                'decision_breakdown': decision_summary,
                'flag_resolution': flag_analysis['resolved_flags'],
                'total_decisions_applied': len(self.decision_log)
            },
            'quality_metrics': {
                'mappings_ready_for_production': approved_count,
                'confidence_improvements': len([m for m in self.approved_mappings.values() 
                                              if m.get('validation_notes')]),
                'corrected_mappings': len([m for m in self.approved_mappings.values() 
                                         if m.get('was_modified', False)])
            },
            'recommendations': [],
            'report_generated_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Add recommendations based on results
        if approval_rate < 70:
            report['recommendations'].append("Low approval rate suggests need for pipeline improvements")
        if completion_rate < 100:
            report['recommendations'].append(f"{pending_count} mappings still need review")
        if report['quality_metrics']['corrected_mappings'] > 0:
            report['recommendations'].append("Review corrected mappings for pattern analysis")
        
        return report
    
    def export_final_results(self, output_dir: str = None) -> Dict[str, str]:
        """
        Export final validation results to files.
        
        Args:
            output_dir: Directory for output files (defaults to validation dir)
            
        Returns:
            Dict mapping output types to file paths
        """
        if output_dir is None:
            output_dir = self.validation_dir
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_files = {}
        
        try:
            # Export final mappings for production use
            final_mappings = self.generate_final_export_mappings()
            final_mappings_file = output_dir / f'final_export_mappings_{timestamp}.json'
            with open(final_mappings_file, 'w') as f:
                json.dump({
                    'export_timestamp': datetime.utcnow().isoformat() + 'Z',
                    'mapping_count': len(final_mappings),
                    'validation_completed': True,
                    'mappings': final_mappings
                }, f, indent=2)
            output_files['final_mappings'] = str(final_mappings_file)
            
            # Export validation summary report
            summary_report = self.create_validation_summary_report()
            summary_file = output_dir / f'validation_summary_{timestamp}.json'
            with open(summary_file, 'w') as f:
                json.dump(summary_report, f, indent=2)
            output_files['summary_report'] = str(summary_file)
            
            # Export rejected mappings analysis
            if self.rejected_mappings:
                rejected_analysis_file = output_dir / f'rejected_mappings_analysis_{timestamp}.json'
                with open(rejected_analysis_file, 'w') as f:
                    json.dump({
                        'export_timestamp': datetime.utcnow().isoformat() + 'Z',
                        'rejected_count': len(self.rejected_mappings),
                        'rejected_mappings': self.rejected_mappings
                    }, f, indent=2)
                output_files['rejected_analysis'] = str(rejected_analysis_file)
            
            logger.info(f"Exported validation results to {len(output_files)} files")
            return output_files
            
        except Exception as e:
            logger.error(f"Failed to export final results: {e}")
            return {}


def load_decisions_from_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Load validation decisions from a JSON file.
    
    Args:
        file_path: Path to decisions file
        
    Returns:
        List of decision objects
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Handle different file formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'decisions' in data:
            return data['decisions']
        elif isinstance(data, dict) and 'validation_state' in data:
            # Extract decisions from validation state
            decisions = []
            for mapping_id, state in data['validation_state'].items():
                if state.get('validator_decision'):
                    decisions.append({
                        'mapping_id': mapping_id,
                        'decision': state['validator_decision'],
                        'notes': state.get('validation_notes', ''),
                        'corrected_mapping': state.get('corrected_mapping')
                    })
            return decisions
        else:
            logger.error("Unrecognized decisions file format")
            return []
            
    except Exception as e:
        logger.error(f"Failed to load decisions from {file_path}: {e}")
        return []


def main():
    """Main function for applying validation decisions."""
    parser = argparse.ArgumentParser(description='Apply validation decisions to mapping data')
    parser.add_argument('--decisions-file', type=str, 
                       help='JSON file containing validation decisions')
    parser.add_argument('--validation-dir', type=str, default='validation',
                       help='Directory containing validation state files')
    parser.add_argument('--output-dir', type=str,
                       help='Directory for output files (defaults to validation-dir)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without saving')
    
    args = parser.parse_args()
    
    logger.info("Starting validation decision application")
    
    # Initialize applicator
    applicator = ValidationDecisionApplicator(args.validation_dir)
    
    # Load current state
    if not applicator.load_current_state():
        logger.error("Failed to load validation state")
        return 1
    
    # Load decisions
    decisions = []
    if args.decisions_file:
        decisions = load_decisions_from_file(args.decisions_file)
        logger.info(f"Loaded {len(decisions)} decisions from {args.decisions_file}")
    else:
        # Extract decisions from current validation state
        for mapping_id, state in applicator.validation_state.items():
            if state.get('validator_decision'):
                decisions.append({
                    'mapping_id': mapping_id,
                    'decision': state['validator_decision'],
                    'notes': state.get('validation_notes', ''),
                    'corrected_mapping': state.get('corrected_mapping')
                })
        logger.info(f"Found {len(decisions)} existing decisions in validation state")
    
    if not decisions:
        logger.warning("No validation decisions found to apply")
        return 0
    
    # Apply decisions
    results = applicator.apply_validation_decisions(decisions)
    
    # Display results
    logger.info(f"✅ Processing complete: {results['processed_count']} decisions applied")
    logger.info(f"   📊 Approved: {results['approved_count']}")
    logger.info(f"   📊 Rejected: {results['rejected_count']}")
    logger.info(f"   📊 Modified: {results['modified_count']}")
    
    if results['error_count'] > 0:
        logger.warning(f"   ⚠️  Errors: {results['error_count']}")
        for error in results['errors']:
            logger.error(f"      - {error}")
    
    # Save results (unless dry run)
    if not args.dry_run:
        if applicator.save_updated_state():
            logger.info("✅ Updated validation state saved successfully")
            
            # Export final results
            output_files = applicator.export_final_results(args.output_dir)
            if output_files:
                logger.info("✅ Final results exported:")
                for result_type, file_path in output_files.items():
                    logger.info(f"   📄 {result_type}: {file_path}")
            
            # Generate and display summary
            summary = applicator.create_validation_summary_report()
            completion_rate = summary['validation_summary']['completion_rate']
            approval_rate = summary['validation_summary']['approval_rate']
            
            logger.info(f"🎯 Validation Summary:")
            logger.info(f"   📈 Completion Rate: {completion_rate}%")
            logger.info(f"   ✅ Approval Rate: {approval_rate}%")
            logger.info(f"   🚀 Ready for Production: {results['approved_count']} mappings")
            
        else:
            logger.error("❌ Failed to save updated state")
            return 1
    else:
        logger.info("🔍 Dry run complete - no files were modified")
    
    return 0


if __name__ == "__main__":
    exit(main())