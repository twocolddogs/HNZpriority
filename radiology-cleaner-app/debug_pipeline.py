#!/usr/bin/env python3
"""
Debug pipeline script to analyze scoring for specific entry.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from complexity import ComplexityScorer
from preprocessing import ExamPreprocessor

def debug_ct_cervical_spine():
    """Debug the CT Cervical Spine example."""
    
    # Test data
    input_exam = "CT Cervical Spine"
    matched_fsn = "Computed tomography of cervical spine for radiotherapy planning (procedure)"
    matched_clean_name = "Ct Radiotherapy Plan Cervical Spine"  # This is the preprocessed primary_source_name
    
    scorer = ComplexityScorer()
    
    print("=== CT CERVICAL SPINE PIPELINE DEBUG ===")
    print(f"Input: '{input_exam}'")
    print(f"Matched FSN: '{matched_fsn}'")
    print(f"Matched Clean Name: '{matched_clean_name}'")
    print()
    
    # Step 1: Input complexity after abbreviation expansion
    # Simulate abbreviation expansion
    expanded_input = input_exam.replace("CT", "computed tomography")
    input_complexity = scorer.calculate_input_qualifier_complexity(expanded_input)
    is_input_simple = input_complexity < 0.3
    
    print(f"1. INPUT COMPLEXITY ANALYSIS:")
    print(f"   Original: '{input_exam}'")
    print(f"   Expanded: '{expanded_input}'")
    print(f"   Complexity Score: {input_complexity:.3f}")
    print(f"   Is Simple: {is_input_simple}")
    print()
    
    # Step 2: FSN complexity (what would be pre-calculated)
    fsn_complexity = scorer.calculate_fsn_total_complexity(matched_fsn)
    is_complex_fsn = fsn_complexity > 0.4
    
    print(f"2. FSN COMPLEXITY ANALYSIS:")
    print(f"   FSN: '{matched_fsn}'")
    print(f"   Complexity Score: {fsn_complexity:.3f}")
    print(f"   Is Complex: {is_complex_fsn}")
    print()
    
    # Step 3: Semantic similarity check (fuzzy matching)
    from fuzzywuzzy import fuzz
    semantic_similarity = fuzz.ratio(expanded_input.lower(), matched_clean_name.lower()) / 100.0
    high_similarity = semantic_similarity > 0.85
    
    print(f"3. SEMANTIC SIMILARITY CHECK:")
    print(f"   Input (expanded): '{expanded_input}'")
    print(f"   Clean Name: '{matched_clean_name}'")
    print(f"   Similarity: {semantic_similarity:.3f}")
    print(f"   High Similarity (>0.85): {high_similarity}")
    print()
    
    # Step 4: Complexity filtering decision
    print(f"4. COMPLEXITY FILTERING DECISION:")
    if is_input_simple:
        if high_similarity:
            decision = "PRESERVE - High semantic similarity overrides complexity mismatch"
            action = "Keep in top results"
        elif is_complex_fsn:
            decision = "DEPRIORITIZE - Simple input, complex FSN, low similarity"
            action = "Move down in ranking"
        else:
            decision = "FAVOR - Simple input, simple FSN"
            action = "Keep prioritized"
    else:
        decision = "NO FILTERING - Complex input continues normal matching"
        action = "Normal processing"
    
    print(f"   Decision: {decision}")
    print(f"   Action: {action}")
    print()
    
    # Step 5: Analysis of the problem
    print(f"5. PROBLEM ANALYSIS:")
    print(f"   - Input is simple: {is_input_simple}")
    print(f"   - FSN is complex: {is_complex_fsn}")
    print(f"   - Semantic similarity is low: {semantic_similarity:.3f} < 0.85")
    print(f"   - Result: This complex FSN would be DEPRIORITIZED for simple input")
    print(f"   - Issue: The match 'radiotherapy planning' is highly specific but not")
    print(f"     semantically similar to simple 'CT Cervical Spine' input")
    print()
    
    # Step 6: Suggested improvements
    print(f"6. POTENTIAL IMPROVEMENTS:")
    print(f"   A. Lower semantic similarity threshold (e.g., 0.75 instead of 0.85)")
    print(f"   B. Add anatomy-specific semantic matching")
    print(f"   C. Consider technique-aware complexity scoring")
    print(f"   D. Use different thresholds for different anatomical regions")

if __name__ == "__main__":
    try:
        debug_ct_cervical_spine()
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()