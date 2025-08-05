#!/usr/bin/env python3
"""
HITL Validation View Generation Script

This script takes the output from batch processing and prepares it for the validation UI.
It groups results by SNOMED ID, flags singleton mappings, and applies smart highlighting
for items that need human attention.

Usage:
    python3 validation/generate_view.py [--input consolidated_results.json] [--output view_data.json]

Example:
    python3 validation/generate_view.py
    python3 validation/generate_view.py --input batch_results.json --output ui_data.json
"""

import json
import argparse
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

def load_batch_results(results_file: str) -> List[Dict[str, Any]]:
    """
    Load batch processing results from JSON file.
    
    Args:
        results_file: Path to consolidated results JSON file
        
    Returns:
        List of processing results
    """
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            results_data = json.load(f)
        
        print(f"Loaded batch results from: {results_file}")
        
        # Handle different result file formats
        if isinstance(results_data, list):
            results = results_data
        elif isinstance(results_data, dict):
            if 'results' in results_data:
                results = results_data['results']
            elif 'exams' in results_data:
                results = results_data['exams']
            else:
                # Assume it's a single result
                results = [results_data]
        else:
            raise ValueError(f"Unexpected results file format: {type(results_data)}")
        
        print(f"Found {len(results)} processing results")
        return results
        
    except Exception as e:
        print(f"Error loading batch results: {e}")
        sys.exit(1)

def group_results_by_snomed(results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group processing results by their matched SNOMED ID.
    
    Args:
        results: List of processing results
        
    Returns:
        Dictionary mapping SNOMED IDs to lists of results
    """
    grouped_by_snomed = defaultdict(list)
    
    for result in results:
        # Extract SNOMED ID from result
        snomed_id = None
        
        if 'snomed_id' in result:
            snomed_id = result['snomed_id']
        elif 'matched_snomed_id' in result:
            snomed_id = result['matched_snomed_id']
        elif 'best_match' in result and isinstance(result['best_match'], dict):
            snomed_id = result['best_match'].get('snomed_id')
        elif 'error' in result:
            # Group errors separately
            snomed_id = 'ERROR'
        
        if snomed_id is None:
            # No match found - group as unmatched
            snomed_id = 'UNMATCHED'
        
        grouped_by_snomed[snomed_id].append(result)
    
    print(f"Grouped results into {len(grouped_by_snomed)} SNOMED groups")
    
    # Print group size distribution
    group_sizes = [len(items) for items in grouped_by_snomed.values()]
    group_sizes.sort(reverse=True)
    
    print(f"Group size distribution:")
    print(f"  Largest group: {group_sizes[0] if group_sizes else 0}")
    print(f"  Singleton groups: {sum(1 for size in group_sizes if size == 1)}")
    print(f"  Total groups: {len(grouped_by_snomed)}")
    
    return grouped_by_snomed

def apply_suspicion_flags(grouped_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Apply suspicion flags to results that need human attention.
    
    Args:
        grouped_results: Results grouped by SNOMED ID
        
    Returns:
        Results with suspicion flags added
    """
    flagged_results = {}
    
    singleton_count = 0
    
    for snomed_id, results_list in grouped_results.items():
        # Create a copy of the results list
        flagged_list = []
        
        for result in results_list:
            # Create a copy of the result
            flagged_result = result.copy()
            
            # Apply singleton suspicion flag
            if len(results_list) == 1:
                flagged_result['suspicion_flag'] = 'singleton_mapping'
                singleton_count += 1
            
            flagged_list.append(flagged_result)
        
        flagged_results[snomed_id] = flagged_list
    
    print(f"Applied singleton flags to {singleton_count} results")
    return flagged_results

def apply_smart_highlighting(grouped_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Apply smart highlighting logic to flag items that need attention.
    
    Items are flagged if:
    - Confidence < 0.85
    - Ambiguous flag is true
    - Suspicion flag exists
    - Error occurred during processing
    
    Args:
        grouped_results: Results grouped by SNOMED ID with suspicion flags
        
    Returns:
        Results with needs_attention flags added
    """
    highlighted_results = {}
    needs_attention_count = 0
    
    for snomed_id, results_list in grouped_results.items():
        highlighted_list = []
        
        for result in results_list:
            # Create a copy of the result
            highlighted_result = result.copy()
            
            # Initialize needs_attention flag
            needs_attention = False
            attention_reasons = []
            
            # Check confidence threshold
            confidence = result.get('confidence', 0.0)
            if confidence < 0.85:
                needs_attention = True
                attention_reasons.append(f'low_confidence_{confidence:.2f}')
            
            # Check ambiguous flag
            if result.get('ambiguous', False):
                needs_attention = True
                attention_reasons.append('ambiguous_match')
            
            # Check suspicion flag
            if 'suspicion_flag' in result:
                needs_attention = True
                attention_reasons.append(f"suspicion_{result['suspicion_flag']}")
            
            # Check for errors
            if 'error' in result:
                needs_attention = True
                attention_reasons.append('processing_error')
            
            # Check for unmatched results
            if snomed_id in ['UNMATCHED', 'ERROR']:
                needs_attention = True
                attention_reasons.append('no_match_found')
            
            # Add flags to result
            if needs_attention:
                highlighted_result['needs_attention'] = True
                highlighted_result['attention_reasons'] = attention_reasons
                needs_attention_count += 1
            else:
                highlighted_result['needs_attention'] = False
            
            highlighted_list.append(highlighted_result)
        
        highlighted_results[snomed_id] = highlighted_list
    
    print(f"Flagged {needs_attention_count} results as needing attention")
    return highlighted_results

def create_view_data(grouped_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Create final view data structure for the validation UI.
    
    Args:
        grouped_results: Processed and flagged results
        
    Returns:
        View data dictionary ready for UI consumption
    """
    # Calculate summary statistics
    total_items = sum(len(results) for results in grouped_results.values())
    needs_attention_items = sum(
        sum(1 for result in results if result.get('needs_attention', False))
        for results in grouped_results.values()
    )
    singleton_groups = sum(1 for results in grouped_results.values() if len(results) == 1)
    error_items = len(grouped_results.get('ERROR', []))
    unmatched_items = len(grouped_results.get('UNMATCHED', []))
    
    # Create summary
    summary = {
        'total_items': total_items,
        'total_groups': len(grouped_results),
        'needs_attention_items': needs_attention_items,
        'singleton_groups': singleton_groups,
        'error_items': error_items,
        'unmatched_items': unmatched_items,
        'approval_rate': (total_items - needs_attention_items) / total_items if total_items > 0 else 0.0
    }
    
    # Sort groups by attention priority (needs attention first, then by group size)
    def group_sort_key(item):
        snomed_id, results = item
        has_attention = any(result.get('needs_attention', False) for result in results)
        group_size = len(results)
        # Priority: attention items first, then singleton, then by size descending
        return (not has_attention, group_size != 1, -group_size)
    
    sorted_groups = dict(sorted(grouped_results.items(), key=group_sort_key))
    
    # Create final view data
    view_data = {
        '_metadata': {
            'generated_at': datetime.now().isoformat(),
            'version': '1.0',
            'summary': summary
        },
        'grouped_results': sorted_groups
    }
    
    return view_data

def generate_validation_view(results_file: str, output_file: str = None) -> str:
    """
    Generate validation view data from batch processing results.
    
    Args:
        results_file: Path to consolidated results JSON file
        output_file: Output path for view data (default: validation/view_data.json)
        
    Returns:
        Path to created view data file
    """
    if output_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, 'view_data.json')
    
    print(f"Generating validation view from: {results_file}")
    
    # Load and process results
    results = load_batch_results(results_file)
    
    # Group by SNOMED ID
    grouped_results = group_results_by_snomed(results)
    
    # Apply suspicion flags
    flagged_results = apply_suspicion_flags(grouped_results)
    
    # Apply smart highlighting
    highlighted_results = apply_smart_highlighting(flagged_results)
    
    # Create final view data
    view_data = create_view_data(highlighted_results)
    
    # Save view data file
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(view_data, f, indent=2, ensure_ascii=False)
        
        print(f"View data file created: {output_file}")
        
        # Print summary
        summary = view_data['_metadata']['summary']
        print(f"\nValidation View Summary:")
        print(f"  Total items: {summary['total_items']}")
        print(f"  Groups: {summary['total_groups']}")
        print(f"  Need attention: {summary['needs_attention_items']} ({summary['needs_attention_items']/summary['total_items']*100:.1f}%)")
        print(f"  Singleton groups: {summary['singleton_groups']}")
        print(f"  Errors: {summary['error_items']}")
        print(f"  Unmatched: {summary['unmatched_items']}")
        print(f"  Auto-approval rate: {summary['approval_rate']*100:.1f}%")
        
        return output_file
        
    except Exception as e:
        print(f"Error writing view data file: {e}")
        sys.exit(1)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate validation view data from batch processing results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 validation/generate_view.py
  python3 validation/generate_view.py --input consolidated_results.json
  python3 validation/generate_view.py --input batch_output.json --output custom_view.json
        """
    )
    
    parser.add_argument('--input', '-i',
                       default='consolidated_results.json',
                       help='Path to batch processing results JSON file (default: consolidated_results.json)')
    parser.add_argument('--output', '-o',
                       help='Output path for view data file (default: validation/view_data.json)')
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not os.path.exists(args.input):
        print(f"Error: Results file not found: {args.input}")
        print(f"Run batch processing first to generate this file.")
        sys.exit(1)
    
    # Generate view data
    view_file = generate_validation_view(args.input, args.output)
    
    print("\nView generation complete!")
    print(f"Next steps:")
    print(f"1. Open validation_ui/index.html in a browser")
    print(f"2. Load the view data file: {view_file}")
    print(f"3. Review and make validation decisions")
    print(f"4. Save decisions and run: python3 validation/update_state.py decisions.json")

if __name__ == "__main__":
    main()