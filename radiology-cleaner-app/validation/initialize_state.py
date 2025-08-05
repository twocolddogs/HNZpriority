#!/usr/bin/env python3
"""
HITL Validation State Initialization Script

This script initializes the validation state JSON file by reading the source input file
and creating a master record of validation status for every input.

Usage:
    python3 validation/initialize_state.py [input_file] [--output validation_state.json]

Example:
    python3 validation/initialize_state.py backend/core/hnz_hdp.json
"""

import json
import hashlib
import argparse
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

def generate_unique_input_id(exam_data: Dict[str, Any]) -> str:
    """
    Generate a unique SHA256 hash for an input item based on key fields.
    
    Args:
        exam_data: Dictionary containing exam information
        
    Returns:
        SHA256 hash string as unique identifier
    """
    # Use combination of fields that uniquely identify an input
    unique_fields = []
    
    # Add exam_name (required)
    if 'EXAM_NAME' in exam_data:
        unique_fields.append(f"exam_name:{exam_data['EXAM_NAME']}")
    elif 'exam_name' in exam_data:
        unique_fields.append(f"exam_name:{exam_data['exam_name']}")
    else:
        raise ValueError(f"No exam_name found in input data: {exam_data}")
    
    # Add exam_code if available
    if 'EXAM_CODE' in exam_data:
        unique_fields.append(f"exam_code:{exam_data['EXAM_CODE']}")
    elif 'exam_code' in exam_data:
        unique_fields.append(f"exam_code:{exam_data['exam_code']}")
    
    # Add data_source if available
    if 'DATA_SOURCE' in exam_data:
        unique_fields.append(f"data_source:{exam_data['DATA_SOURCE']}")
    elif 'data_source' in exam_data:
        unique_fields.append(f"data_source:{exam_data['data_source']}")
    
    # Add modality_code if available
    if 'MODALITY_CODE' in exam_data:
        unique_fields.append(f"modality_code:{exam_data['MODALITY_CODE']}")
    elif 'modality_code' in exam_data:
        unique_fields.append(f"modality_code:{exam_data['modality_code']}")
    
    # Create unique string and hash it
    unique_string = "|".join(sorted(unique_fields))
    return hashlib.sha256(unique_string.encode('utf-8')).hexdigest()

def normalize_input_data(exam_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize input data to consistent field names and format.
    
    Args:
        exam_data: Raw input data dictionary
        
    Returns:
        Normalized data dictionary
    """
    normalized = {}
    
    # Map various field name formats to standard format
    field_mappings = {
        'exam_name': ['EXAM_NAME', 'exam_name'],
        'exam_code': ['EXAM_CODE', 'exam_code'], 
        'data_source': ['DATA_SOURCE', 'data_source'],
        'modality_code': ['MODALITY_CODE', 'modality_code']
    }
    
    for standard_field, possible_fields in field_mappings.items():
        for field in possible_fields:
            if field in exam_data:
                normalized[standard_field] = exam_data[field]
                break
    
    # Ensure exam_name exists (required field)
    if 'exam_name' not in normalized:
        raise ValueError(f"Required field 'exam_name' not found in input: {exam_data}")
    
    return normalized

def create_validation_state_entry(exam_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a validation state entry for a single input item.
    
    Args:
        exam_data: Normalized input data
        
    Returns:
        Validation state entry dictionary
    """
    unique_id = generate_unique_input_id(exam_data)
    
    return {
        "unique_input_id": unique_id,
        "source_input": exam_data,
        "status": "unprocessed",
        "approved_mapping": None,
        "reprocessing_hint": None,
        "history": [],
        "notes": None
    }

def initialize_validation_state(input_file: str, output_file: str = None) -> str:
    """
    Initialize validation state JSON file from source input data.
    
    Args:
        input_file: Path to source input JSON file
        output_file: Path for output validation state file (default: validation/validation_state.json)
        
    Returns:
        Path to created validation state file
    """
    if output_file is None:
        # Default to validation directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, 'validation_state.json')
    
    print(f"Reading input data from: {input_file}")
    
    # Load source input data
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)
    
    # Handle different input file formats
    if isinstance(input_data, list):
        exam_list = input_data
    elif isinstance(input_data, dict) and 'exams' in input_data:
        exam_list = input_data['exams']
    else:
        # Assume it's a dictionary where each value is an exam
        exam_list = list(input_data.values()) if isinstance(input_data, dict) else [input_data]
    
    print(f"Processing {len(exam_list)} input items...")
    
    # Create validation state entries
    validation_state = {}
    processed_count = 0
    error_count = 0
    
    for i, exam_data in enumerate(exam_list):
        try:
            # Normalize the input data
            normalized_data = normalize_input_data(exam_data)
            
            # Create validation state entry
            state_entry = create_validation_state_entry(normalized_data)
            unique_id = state_entry["unique_input_id"]
            
            # Check for duplicates
            if unique_id in validation_state:
                print(f"Warning: Duplicate unique_input_id found for item {i+1}: {unique_id}")
                print(f"  Original: {validation_state[unique_id]['source_input']}")
                print(f"  Duplicate: {normalized_data}")
                continue
            
            # Add to state
            validation_state[unique_id] = state_entry
            processed_count += 1
            
        except Exception as e:
            print(f"Error processing item {i+1}: {e}")
            print(f"  Data: {exam_data}")
            error_count += 1
    
    print(f"Successfully processed: {processed_count} items")
    if error_count > 0:
        print(f"Errors encountered: {error_count} items")
    
    # Save validation state file
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Add metadata
        metadata = {
            "_metadata": {
                "created_at": datetime.now().isoformat(),
                "source_file": input_file,
                "total_items": processed_count,
                "error_count": error_count,
                "version": "1.0"
            }
        }
        
        # Combine metadata with validation state
        final_data = {**metadata, **validation_state}
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        
        print(f"Validation state file created: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Initialize HITL validation state from source input data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 validation/initialize_state.py backend/core/hnz_hdp.json
  python3 validation/initialize_state.py backend/core/sanity_test.json --output custom_state.json
        """
    )
    
    parser.add_argument('input_file', 
                       help='Path to source input JSON file (e.g., hnz_hdp.json)')
    parser.add_argument('--output', '-o',
                       help='Output path for validation state file (default: validation/validation_state.json)')
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)
    
    # Initialize validation state
    output_path = initialize_validation_state(args.input_file, args.output)
    
    print("\nValidation state initialization complete!")
    print(f"Next steps:")
    print(f"1. Run: python3 validation/prepare_batch.py")
    print(f"2. Process batch with your application")
    print(f"3. Run: python3 validation/generate_view.py") 
    print(f"4. Use validation UI to review and make decisions")
    print(f"5. Run: python3 validation/update_state.py decisions.json")

if __name__ == "__main__":
    main()