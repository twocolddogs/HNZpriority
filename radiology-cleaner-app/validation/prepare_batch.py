#!/usr/bin/env python3
"""
HITL Validation Batch Preparation Script

This script reads the validation state file and creates a list of exams that need processing.
It formats items for the /parse_batch endpoint, including input data, unique_input_id, and reprocessing hints.

Usage:
    python3 validation/prepare_batch.py [--state validation_state.json] [--output _current_batch.json]

Example:
    python3 validation/prepare_batch.py
    python3 validation/prepare_batch.py --state custom_state.json --output my_batch.json
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
            state_data = json.load(f)
        
        print(f"Loaded validation state from: {state_file}")
        
        # Count items by status
        status_counts = {}
        for item_id, item_data in state_data.items():
            if item_id.startswith('_'):  # Skip metadata
                continue
            status = item_data.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"Current status breakdown:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        
        return state_data
        
    except Exception as e:
        print(f"Error loading validation state: {e}")
        sys.exit(1)

def create_batch_item(unique_input_id: str, state_entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a batch processing item from a validation state entry.
    
    Args:
        unique_input_id: Unique identifier for the input
        state_entry: Validation state entry data
        
    Returns:
        Formatted batch item for /parse_batch endpoint
    """
    # Extract source input data
    source_input = state_entry.get('source_input', {})
    
    # Create batch item with required format
    batch_item = {
        "input_data": source_input,
        "unique_input_id": unique_input_id
    }
    
    # Add reprocessing hint if available
    reprocessing_hint = state_entry.get('reprocessing_hint')
    if reprocessing_hint:
        batch_item["reprocessing_hint"] = reprocessing_hint
    
    return batch_item

def prepare_batch_for_processing(state_file: str, output_file: str = None, 
                               include_statuses: List[str] = None) -> str:
    """
    Prepare a batch of exams for processing based on validation state.
    
    Args:
        state_file: Path to validation state JSON file
        output_file: Output path for batch file (default: validation/_current_batch.json)
        include_statuses: List of statuses to include (default: non-approved/non-failed)
        
    Returns:
        Path to created batch file
    """
    if output_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, '_current_batch.json')
    
    if include_statuses is None:
        # Default: include items that are not approved and not failed
        include_statuses = ['unprocessed', 'pending_review', 'needs_reprocessing']
    
    print(f"Preparing batch for statuses: {', '.join(include_statuses)}")
    
    # Load validation state
    validation_state = load_validation_state(state_file)
    
    # Build list of exams to process
    exams_to_process = []
    processed_count = 0
    skipped_count = 0
    
    for item_id, item_data in validation_state.items():
        if item_id.startswith('_'):  # Skip metadata
            continue
        
        item_status = item_data.get('status', 'unprocessed')
        
        # Check if this item should be included
        if item_status in include_statuses:
            try:
                batch_item = create_batch_item(item_id, item_data)
                exams_to_process.append(batch_item)
                processed_count += 1
            except Exception as e:
                print(f"Error processing item {item_id}: {e}")
                skipped_count += 1
        else:
            skipped_count += 1
    
    print(f"Selected {processed_count} items for processing")
    print(f"Skipped {skipped_count} items (already approved/failed or other status)")
    
    # Create batch payload in format expected by /parse_batch endpoint
    batch_payload = {
        "exams": exams_to_process,
        "_batch_metadata": {
            "created_at": datetime.now().isoformat(),
            "source_state_file": state_file,
            "included_statuses": include_statuses,
            "total_items": processed_count,
            "batch_type": "hitl_validation"
        }
    }
    
    # Save batch file
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(batch_payload, f, indent=2, ensure_ascii=False)
        
        print(f"Batch file created: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"Error writing batch file: {e}")
        sys.exit(1)

def validate_batch_format(batch_file: str) -> bool:
    """
    Validate that the batch file has the correct format for /parse_batch endpoint.
    
    Args:
        batch_file: Path to batch JSON file
        
    Returns:
        True if format is valid, False otherwise
    """
    try:
        with open(batch_file, 'r', encoding='utf-8') as f:
            batch_data = json.load(f)
        
        # Check required structure
        if 'exams' not in batch_data:
            print("Error: Batch file missing 'exams' field")
            return False
        
        if not isinstance(batch_data['exams'], list):
            print("Error: 'exams' field must be a list")
            return False
        
        # Check first few items for correct structure
        for i, exam in enumerate(batch_data['exams'][:3]):
            if 'input_data' not in exam:
                print(f"Error: Item {i} missing 'input_data' field")
                return False
            
            if 'unique_input_id' not in exam:
                print(f"Error: Item {i} missing 'unique_input_id' field")
                return False
            
            # Check input_data has required exam_name
            input_data = exam['input_data']
            if 'exam_name' not in input_data:
                print(f"Error: Item {i} input_data missing 'exam_name' field")
                return False
        
        print(f"Batch file format validation passed: {len(batch_data['exams'])} items")
        return True
        
    except Exception as e:
        print(f"Error validating batch file: {e}")
        return False

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Prepare batch of exams for HITL validation processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 validation/prepare_batch.py
  python3 validation/prepare_batch.py --state custom_state.json
  python3 validation/prepare_batch.py --output my_batch.json --include unprocessed needs_reprocessing
        """
    )
    
    parser.add_argument('--state', '-s',
                       default='validation/validation_state.json',
                       help='Path to validation state JSON file (default: validation/validation_state.json)')
    parser.add_argument('--output', '-o',
                       help='Output path for batch file (default: validation/_current_batch.json)')
    parser.add_argument('--include', nargs='*',
                       default=['unprocessed', 'pending_review', 'needs_reprocessing'],
                       help='Status values to include in batch (default: unprocessed pending_review needs_reprocessing)')
    
    args = parser.parse_args()
    
    # Resolve state file path
    if not os.path.isabs(args.state):
        # Relative to script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        state_file = os.path.join(script_dir, args.state)
    else:
        state_file = args.state
    
    # Validate state file exists
    if not os.path.exists(state_file):
        print(f"Error: Validation state file not found: {state_file}")
        print(f"Run 'python3 validation/initialize_state.py' first to create it.")
        sys.exit(1)
    
    # Prepare batch
    batch_file = prepare_batch_for_processing(state_file, args.output, args.include)
    
    # Validate batch format
    if validate_batch_format(batch_file):
        print("\nBatch preparation complete!")
        print(f"Next steps:")
        print(f"1. Process batch with your application:")
        print(f"   curl -X POST http://localhost:10000/parse_batch \\")
        print(f"        -H 'Content-Type: application/json' \\")
        print(f"        -d @{batch_file}")
        print(f"2. Run: python3 validation/generate_view.py")
    else:
        print("Error: Batch file validation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()