#!/usr/bin/env python3
"""
HITL Validation State Update Script

This script applies human validation decisions to the master state file and regenerates caches.
It implements the "Approve by Default" principle where items without explicit decisions are approved.

Usage:
    python3 validation/update_state.py decisions.json [--state validation_state.json] [--results consolidated_results.json]

Example:
    python3 validation/update_state.py decisions.json
    python3 validation/update_state.py my_decisions.json --state custom_state.json
"""

import json
import argparse
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

def load_validation_state(state_file: str) -> Dict[str, Any]:
    """
    Load validation state from JSON file.
    
    Args:
        state_file: Path to validation state JSON file
        
    Returns:
        Validation state dictionary
    """
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading validation state: {e}")
        sys.exit(1)

def load_decisions(decisions_file: str) -> Dict[str, Any]:
    """
    Load human validation decisions from JSON file.
    
    Args:
        decisions_file: Path to decisions JSON file
        
    Returns:
        Decisions dictionary mapping unique_input_id to decision objects
    """
    try:
        with open(decisions_file, 'r', encoding='utf-8') as f:
            decisions = json.load(f)
        
        print(f"Loaded {len(decisions)} validation decisions from: {decisions_file}")
        
        # Validate decision format
        valid_actions = {'fail', 'review', 'defer', 'approve'}
        for unique_id, decision in decisions.items():
            action = decision.get('action')
            if action not in valid_actions:
                print(f"Warning: Invalid action '{action}' for {unique_id}. Valid actions: {valid_actions}")
        
        return decisions
        
    except Exception as e:
        print(f"Error loading decisions: {e}")
        sys.exit(1)

def load_processing_results(results_file: str) -> Dict[str, Any]:
    """
    Load processing results from the last batch run.
    
    Args:
        results_file: Path to consolidated results JSON file
        
    Returns:
        Dictionary mapping unique_input_id to processing results
    """
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            results_data = json.load(f)
        
        # Handle different result file formats
        if isinstance(results_data, list):
            results_list = results_data
        elif isinstance(results_data, dict):
            if 'results' in results_data:
                results_list = results_data['results']
            elif 'exams' in results_data:
                results_list = results_data['exams']
            else:
                print(f"Warning: Unexpected results file format")
                return {}
        else:
            return {}
        
        # Create mapping from unique_input_id to result
        results_by_id = {}
        for result in results_list:
            unique_id = result.get('unique_input_id')
            if unique_id:
                results_by_id[unique_id] = result
        
        print(f"Loaded {len(results_by_id)} processing results from: {results_file}")
        return results_by_id
        
    except Exception as e:
        print(f"Warning: Could not load processing results: {e}")
        print(f"Continuing without processing results (only explicit decisions will be applied)")
        return {}

def apply_decision_to_state(unique_input_id: str, decision: Dict[str, Any], 
                          state_entry: Dict[str, Any], processing_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Apply a validation decision to a state entry.
    
    Args:
        unique_input_id: Unique identifier for the input
        decision: Human validation decision
        state_entry: Current validation state entry
        processing_result: Processing result from last batch run (if available)
        
    Returns:
        Updated state entry
    """
    action = decision.get('action')
    timestamp = datetime.now().isoformat()
    
    # Create history entry
    history_entry = {
        'timestamp': timestamp,
        'action': action,
        'note': decision.get('note', ''),
        'decision_data': decision
    }
    
    # Add processing result to history if available
    if processing_result:
        history_entry['processing_result'] = processing_result
    
    # Update state based on action
    updated_entry = state_entry.copy()
    updated_entry['history'].append(history_entry)
    
    if action == 'fail':
        updated_entry['status'] = 'failed'
        updated_entry['notes'] = decision.get('note', 'Marked as failed by validator')
        updated_entry['approved_mapping'] = None
        updated_entry['reprocessing_hint'] = None
        
    elif action == 'review':
        updated_entry['status'] = 'needs_reprocessing'
        updated_entry['reprocessing_hint'] = decision.get('hint', {})
        updated_entry['notes'] = decision.get('note', 'Flagged for reprocessing by validator')
        
    elif action == 'defer':
        updated_entry['status'] = 'pending_review'
        updated_entry['notes'] = decision.get('note', 'Deferred for future review')
        
    elif action == 'approve':
        updated_entry['status'] = 'approved'
        updated_entry['notes'] = decision.get('note', 'Explicitly approved by validator')
        # Store the approved mapping from processing result
        if processing_result and 'error' not in processing_result:
            updated_entry['approved_mapping'] = extract_mapping_from_result(processing_result)
    
    return updated_entry

def apply_auto_approval(unique_input_id: str, state_entry: Dict[str, Any], 
                       processing_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply automatic approval for items without explicit decisions (Approve by Default).
    
    Args:
        unique_input_id: Unique identifier for the input
        state_entry: Current validation state entry
        processing_result: Processing result from last batch run
        
    Returns:
        Updated state entry with auto-approval
    """
    timestamp = datetime.now().isoformat()
    
    # Check if result is suitable for auto-approval
    if 'error' in processing_result:
        # Don't auto-approve errors
        return state_entry
    
    # Create history entry for auto-approval
    history_entry = {
        'timestamp': timestamp,
        'action': 'auto_approve',
        'note': 'Automatically approved (no explicit decision)',
        'processing_result': processing_result
    }
    
    # Update state
    updated_entry = state_entry.copy()
    updated_entry['history'].append(history_entry)
    updated_entry['status'] = 'approved'
    updated_entry['notes'] = 'Auto-approved by validation pipeline'
    updated_entry['approved_mapping'] = extract_mapping_from_result(processing_result)
    
    return updated_entry

def extract_mapping_from_result(processing_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract the approved mapping data from a processing result.
    
    Args:
        processing_result: Processing result dictionary
        
    Returns:
        Mapping data suitable for storage as approved_mapping
    """
    if 'error' in processing_result:
        return None
    
    # Extract key mapping fields
    mapping = {}
    
    # SNOMED information
    if 'snomed_id' in processing_result:
        mapping['snomed_id'] = processing_result['snomed_id']
    if 'clean_name' in processing_result:
        mapping['clean_name'] = processing_result['clean_name']
    if 'snomed_fsn' in processing_result:
        mapping['snomed_fsn'] = processing_result['snomed_fsn']
    
    # Component information
    if 'components' in processing_result:
        mapping['components'] = processing_result['components']
    
    # Confidence and metadata
    if 'confidence' in processing_result:
        mapping['confidence'] = processing_result['confidence']
    
    # Processing metadata
    mapping['processing_metadata'] = {
        'timestamp': datetime.now().isoformat(),
        'pipeline_version': processing_result.get('pipeline_version', 'unknown')
    }
    
    return mapping if mapping else None

def regenerate_caches(validation_state: Dict[str, Any], cache_dir: str = None) -> tuple:
    """
    Regenerate gold standard and failed mappings caches from validation state.
    
    Args:
        validation_state: Updated validation state
        cache_dir: Directory for cache files (default: same as validation state)
        
    Returns:
        Tuple of (gold_standard_cache_path, failed_mappings_cache_path)
    """
    if cache_dir is None:
        cache_dir = os.path.dirname(os.path.abspath(__file__))
    
    gold_standard_cache = {}
    failed_mappings = {}
    
    approved_count = 0
    failed_count = 0
    
    for unique_id, state_entry in validation_state.items():
        if unique_id.startswith('_'):  # Skip metadata
            continue
        
        status = state_entry.get('status')
        
        if status == 'approved':
            approved_mapping = state_entry.get('approved_mapping')
            if approved_mapping:
                gold_standard_cache[unique_id] = approved_mapping
                approved_count += 1
        
        elif status == 'failed':
            failed_mappings[unique_id] = {
                'reason': state_entry.get('notes', 'Marked as failed'),
                'timestamp': datetime.now().isoformat()
            }
            failed_count += 1
    
    # Save gold standard cache
    gold_cache_path = os.path.join(cache_dir, 'gold_standard_cache.json')
    with open(gold_cache_path, 'w', encoding='utf-8') as f:
        json.dump(gold_standard_cache, f, indent=2, ensure_ascii=False)
    
    # Save failed mappings cache
    failed_cache_path = os.path.join(cache_dir, 'failed_mappings.json')
    with open(failed_cache_path, 'w', encoding='utf-8') as f:
        json.dump(failed_mappings, f, indent=2, ensure_ascii=False)
    
    print(f"Regenerated caches:")
    print(f"  Gold standard: {approved_count} entries -> {gold_cache_path}")
    print(f"  Failed mappings: {failed_count} entries -> {failed_cache_path}")
    
    return gold_cache_path, failed_cache_path

def update_validation_state(decisions_file: str, state_file: str = None, results_file: str = None) -> str:
    """
    Update validation state with human decisions and regenerate caches.
    
    Args:
        decisions_file: Path to decisions JSON file
        state_file: Path to validation state file (default: validation/validation_state.json)
        results_file: Path to processing results file (default: consolidated_results.json)
        
    Returns:
        Path to updated validation state file
    """
    if state_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        state_file = os.path.join(script_dir, 'validation_state.json')
    
    if results_file is None:
        results_file = 'consolidated_results.json'
    
    print(f"Updating validation state: {state_file}")
    
    # Load data
    validation_state = load_validation_state(state_file)
    decisions = load_decisions(decisions_file)
    processing_results = load_processing_results(results_file) if os.path.exists(results_file) else {}
    
    # Apply decisions and auto-approvals
    explicit_decisions = 0
    auto_approvals = 0
    errors_encountered = 0
    
    for unique_id, state_entry in validation_state.items():
        if unique_id.startswith('_'):  # Skip metadata
            continue
        
        processing_result = processing_results.get(unique_id)
        
        # Check if there's an explicit decision for this item
        if unique_id in decisions:
            try:
                validation_state[unique_id] = apply_decision_to_state(
                    unique_id, decisions[unique_id], state_entry, processing_result
                )
                explicit_decisions += 1
            except Exception as e:
                print(f"Error applying decision for {unique_id}: {e}")
                errors_encountered += 1
        
        # Apply auto-approval if item was processed but has no explicit decision
        elif processing_result and state_entry.get('status') not in ['approved', 'failed']:
            try:
                validation_state[unique_id] = apply_auto_approval(
                    unique_id, state_entry, processing_result
                )
                auto_approvals += 1
            except Exception as e:
                print(f"Error auto-approving {unique_id}: {e}")
                errors_encountered += 1
    
    print(f"Applied {explicit_decisions} explicit decisions")
    print(f"Applied {auto_approvals} auto-approvals")
    if errors_encountered > 0:
        print(f"Encountered {errors_encountered} errors")
    
    # Update metadata
    if '_metadata' not in validation_state:
        validation_state['_metadata'] = {}
    
    validation_state['_metadata']['last_updated'] = datetime.now().isoformat()
    validation_state['_metadata']['last_decision_file'] = decisions_file
    validation_state['_metadata']['explicit_decisions'] = explicit_decisions
    validation_state['_metadata']['auto_approvals'] = auto_approvals
    
    # Save updated state
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(validation_state, f, indent=2, ensure_ascii=False)
        
        print(f"Updated validation state saved: {state_file}")
        
    except Exception as e:
        print(f"Error saving validation state: {e}")
        sys.exit(1)
    
    # Regenerate caches
    cache_dir = os.path.dirname(state_file)
    regenerate_caches(validation_state, cache_dir)
    
    return state_file

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Update validation state with human decisions and regenerate caches",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 validation/update_state.py decisions.json
  python3 validation/update_state.py my_decisions.json --state custom_state.json
  python3 validation/update_state.py decisions.json --results batch_output.json
        """
    )
    
    parser.add_argument('decisions_file',
                       help='Path to JSON file containing validation decisions')
    parser.add_argument('--state', '-s',
                       help='Path to validation state JSON file (default: validation/validation_state.json)')
    parser.add_argument('--results', '-r',
                       help='Path to processing results JSON file (default: consolidated_results.json)')
    
    args = parser.parse_args()
    
    # Validate decisions file exists
    if not os.path.exists(args.decisions_file):
        print(f"Error: Decisions file not found: {args.decisions_file}")
        sys.exit(1)
    
    # Update validation state
    updated_state_file = update_validation_state(args.decisions_file, args.state, args.results)
    
    print("\nValidation state update complete!")
    print(f"Next steps:")
    print(f"1. Run: python3 validation/prepare_batch.py (to process remaining items)")
    print(f"2. Or review the updated caches:")
    print(f"   - validation/gold_standard_cache.json (approved mappings)")
    print(f"   - validation/failed_mappings.json (rejected mappings)")

if __name__ == "__main__":
    main()