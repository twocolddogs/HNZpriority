#!/usr/bin/env python3
"""
Load Mappings Script for HITL Validation Pipeline
================================================

This script loads exported mappings JSON (from Export Mappings tool) and initializes
the validation state for human review.

Usage:
    python load_mappings.py <mappings_file.json>
    python load_mappings.py --from-stdin  # For direct pipeline integration

Input Format: JSON array of mapping objects from Export Mappings tool
Output: validation_state.json with flagged items requiring attention
"""

import json
import hashlib
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional


def generate_unique_mapping_id(mapping: Dict[str, Any]) -> str:
    """Generate unique ID for a mapping based on key fields."""
    # Use key fields to create unique identifier
    key_fields = [
        mapping.get('exam_code', ''),
        mapping.get('exam_name', ''), 
        mapping.get('data_source', ''),
        mapping.get('clean_name', '')
    ]
    
    # Create hash from concatenated fields
    hash_input = '|'.join(str(field).strip().lower() for field in key_fields)
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()


def apply_attention_flags(mapping: Dict[str, Any]) -> List[str]:
    """Apply automatic flagging rules to identify mappings needing attention."""
    flags = []
    
    # Low confidence flag - check components.confidence
    components = mapping.get('components', {})
    confidence = components.get('confidence', 0)
    if confidence < 0.85:
        flags.append('low_confidence')
    
    # Ambiguous mapping flag
    if mapping.get('ambiguous', False):
        flags.append('ambiguous')
    
    # SNOMED not found flag
    snomed = mapping.get('snomed', {})
    if not snomed.get('found', False):
        flags.append('snomed_not_found')
    
    # Missing components flag
    if not components:
        flags.append('missing_components')
    
    # Secondary pipeline applied (might need review)
    if mapping.get('secondary_pipeline_applied', False):
        flags.append('secondary_pipeline_used')
        
    # Multiple high-confidence candidates (potential ambiguity)
    all_candidates = mapping.get('all_candidates', [])
    high_conf_candidates = [c for c in all_candidates if c.get('confidence', 0) > 0.8]
    if len(high_conf_candidates) > 1:
        flags.append('multiple_high_confidence')
        
    return flags


def detect_singletons(mappings: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count occurrences of each clean_name to identify singletons."""
    clean_name_counts = {}
    
    for mapping in mappings:
        clean_name = mapping.get('clean_name', '')
        if clean_name:
            clean_name_counts[clean_name] = clean_name_counts.get(clean_name, 0) + 1
    
    return clean_name_counts


def create_validation_state_entry(mapping: Dict[str, Any], flags: List[str], is_singleton: bool) -> Dict[str, Any]:
    """Create a validation state entry for a single mapping."""
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Add singleton flag if applicable
    final_flags = flags.copy()
    if is_singleton:
        final_flags.append('singleton_mapping')
    
    return {
        "unique_mapping_id": generate_unique_mapping_id(mapping),
        "original_mapping": mapping,
        "validation_status": "pending_review",
        "validator_decision": None,
        "validation_notes": None,
        "needs_attention_flags": final_flags,
        "timestamp_created": timestamp,
        "timestamp_reviewed": None
    }


def load_mappings_from_file(file_path: str) -> List[Dict[str, Any]]:
    """Load mappings from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different possible formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'mappings' in data:
            return data['mappings']
        elif isinstance(data, dict) and 'results' in data:
            return data['results']
        else:
            raise ValueError("Unexpected JSON format - expected array of mappings")
            
    except Exception as e:
        print(f"Error loading mappings file: {e}")
        sys.exit(1)


def load_mappings_from_stdin() -> List[Dict[str, Any]]:
    """Load mappings from stdin (for direct pipeline integration)."""
    try:
        data = json.load(sys.stdin)
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'mappings' in data:
            return data['mappings']
        else:
            raise ValueError("Unexpected JSON format from stdin")
            
    except Exception as e:
        print(f"Error loading mappings from stdin: {e}")
        sys.exit(1)


def load_existing_caches() -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Load existing approved and rejected mappings caches."""
    approved_mappings = {}
    rejected_mappings = {}
    
    # Load approved mappings cache
    approved_file = Path('validation/approved_mappings_cache.json')
    if approved_file.exists():
        try:
            with open(approved_file, 'r') as f:
                approved_data = json.load(f)
            
            # Handle canonical schema with entries wrapper
            if isinstance(approved_data, dict) and 'entries' in approved_data:
                approved_mappings = approved_data['entries']
            else:
                approved_mappings = approved_data
            print(f"Loaded {len(approved_mappings)} approved mappings from cache")
        except Exception as e:
            print(f"Warning: Could not load approved mappings cache: {e}")
    
    # Load rejected mappings cache
    rejected_file = Path('validation/rejected_mappings_cache.json')
    if rejected_file.exists():
        try:
            with open(rejected_file, 'r') as f:
                rejected_data = json.load(f)
                
            # Handle canonical schema with entries wrapper
            if isinstance(rejected_data, dict) and 'entries' in rejected_data:
                rejected_mappings = rejected_data['entries']
            else:
                rejected_mappings = rejected_data
            print(f"Loaded {len(rejected_mappings)} rejected mappings from cache")
        except Exception as e:
            print(f"Warning: Could not load rejected mappings cache: {e}")
    
    return approved_mappings, rejected_mappings


def initialize_validation_state(mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Initialize validation state from mappings."""
    print(f"Processing {len(mappings)} mappings...")
    
    # Load existing cache data
    approved_cache, rejected_cache = load_existing_caches()
    
    # Detect singletons
    clean_name_counts = detect_singletons(mappings)
    
    # Create validation state
    validation_state = {}
    stats = {
        'total_mappings': len(mappings),
        'flagged_for_attention': 0,
        'singletons': 0,
        'low_confidence': 0,
        'ambiguous': 0,
        'snomed_not_found': 0,
        'secondary_pipeline_used': 0,
        'multiple_high_confidence': 0,
        'already_approved': 0,
        'already_rejected': 0
    }
    
    for mapping in mappings:
        # Apply attention flags
        flags = apply_attention_flags(mapping)
        
        # Check if singleton
        clean_name = mapping.get('clean_name', '')
        is_singleton = clean_name_counts.get(clean_name, 0) == 1
        
        # Generate unique ID to check against existing caches
        unique_id = generate_unique_mapping_id(mapping)
        
        # Check if this mapping is already in approved or rejected cache
        validation_status = "pending_review"
        if unique_id in approved_cache:
            validation_status = "approved"
            stats['already_approved'] += 1
        elif unique_id in rejected_cache:
            validation_status = "rejected"
            stats['already_rejected'] += 1
        
        # Create validation entry with proper status
        entry = create_validation_state_entry(mapping, flags, is_singleton)
        entry['validation_status'] = validation_status  # Override default status
        entry['unique_mapping_id'] = unique_id  # Ensure consistency
        validation_state[unique_id] = entry
        
        # Update statistics
        if flags or is_singleton:
            stats['flagged_for_attention'] += 1
        if is_singleton:
            stats['singletons'] += 1
        if 'low_confidence' in flags:
            stats['low_confidence'] += 1
        if 'ambiguous' in flags:
            stats['ambiguous'] += 1
        if 'snomed_not_found' in flags:
            stats['snomed_not_found'] += 1
        if 'secondary_pipeline_used' in flags:
            stats['secondary_pipeline_used'] += 1
        if 'multiple_high_confidence' in flags:
            stats['multiple_high_confidence'] += 1
    
    return validation_state, stats


def save_validation_state(validation_state: Dict[str, Any], output_path: str):
    """Save validation state to JSON file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(validation_state, f, indent=2, ensure_ascii=False)
        print(f"✅ Validation state saved to: {output_path}")
    except Exception as e:
        print(f"❌ Error saving validation state: {e}")
        sys.exit(1)


def print_summary_report(stats: Dict[str, Any]):
    """Print summary report of initialization."""
    print("\n" + "="*60)
    print("VALIDATION INITIALIZATION SUMMARY")
    print("="*60)
    print(f"Total mappings processed: {stats['total_mappings']}")
    print(f"Already approved: {stats['already_approved']}")
    print(f"Already rejected: {stats['already_rejected']}")
    print(f"Flagged for attention: {stats['flagged_for_attention']}")
    print(f"  - Low confidence (<85%): {stats['low_confidence']}")
    print(f"  - Ambiguous mappings: {stats['ambiguous']}")  
    print(f"  - Singleton mappings: {stats['singletons']}")
    print(f"  - SNOMED not found: {stats['snomed_not_found']}")
    print(f"  - Secondary pipeline used: {stats['secondary_pipeline_used']}")
    print(f"  - Multiple high-confidence candidates: {stats['multiple_high_confidence']}")
    
    new_for_review = stats['total_mappings'] - stats['already_approved'] - stats['already_rejected']
    print(f"New mappings requiring review: {new_for_review}")
    
    if stats['total_mappings'] > 0:
        approved_percentage = (stats['already_approved'] / stats['total_mappings']) * 100
        print(f"\nAlready completed: {approved_percentage + (stats['already_rejected'] / stats['total_mappings'] * 100):.1f}% of mappings")
        if new_for_review > 0:
            attention_percentage = (stats['flagged_for_attention'] / new_for_review) * 100
            print(f"Of new mappings, attention required: {attention_percentage:.1f}%")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Initialize validation state from exported mappings')
    parser.add_argument('input_file', nargs='?', help='JSON file with exported mappings')
    parser.add_argument('--from-stdin', action='store_true', help='Read mappings from stdin')
    parser.add_argument('--output', '-o', default='validation/validation_state.json', 
                       help='Output path for validation state (default: validation/validation_state.json)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.from_stdin and not args.input_file:
        parser.error("Must provide either input file or --from-stdin")
    
    if args.from_stdin and args.input_file:
        parser.error("Cannot use both input file and --from-stdin")
    
    # Load mappings
    if args.from_stdin:
        print("Loading mappings from stdin...")
        mappings = load_mappings_from_stdin()
    else:
        print(f"Loading mappings from: {args.input_file}")
        mappings = load_mappings_from_file(args.input_file)
    
    # Initialize validation state
    validation_state, stats = initialize_validation_state(mappings)
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save validation state
    save_validation_state(validation_state, str(output_path))
    
    # Print summary
    print_summary_report(stats)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())