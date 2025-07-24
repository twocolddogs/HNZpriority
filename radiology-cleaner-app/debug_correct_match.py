#!/usr/bin/env python3
"""
Debug why the correct NHS entry wasn't selected.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from complexity import ComplexityScorer
from fuzzywuzzy import fuzz

def compare_matches():
    """Compare the wrong match vs correct match."""
    
    input_exam = "CT Cervical Spine"
    expanded_input = "computed tomography Cervical Spine"
    
    # Wrong match (what was selected)
    wrong_fsn = "Computed tomography of cervical spine for radiotherapy planning (procedure)"
    wrong_clean_name = "Ct Radiotherapy Plan Cervical Spine"
    
    # Correct match (what should have been selected)  
    correct_fsn = "Computed tomography of cervical spine (procedure)"
    correct_clean_name = "CT Spine cervical"  # This is the primary_source_name
    
    scorer = ComplexityScorer()
    
    print("=== MATCH COMPARISON ANALYSIS ===")
    print(f"Input: '{input_exam}' -> Expanded: '{expanded_input}'")
    print()
    
    # Compare FSN complexity
    wrong_fsn_complexity = scorer.calculate_fsn_total_complexity(wrong_fsn)
    correct_fsn_complexity = scorer.calculate_fsn_total_complexity(correct_fsn)
    
    print("FSN COMPLEXITY COMPARISON:")
    print(f"  Wrong FSN:   '{wrong_fsn}' -> {wrong_fsn_complexity:.3f}")
    print(f"  Correct FSN: '{correct_fsn}' -> {correct_fsn_complexity:.3f}")
    print()
    
    # Compare semantic similarity with input
    wrong_similarity = fuzz.ratio(expanded_input.lower(), wrong_clean_name.lower()) / 100.0
    correct_similarity = fuzz.ratio(expanded_input.lower(), correct_clean_name.lower()) / 100.0
    
    print("SEMANTIC SIMILARITY WITH INPUT:")
    print(f"  Wrong match:   '{expanded_input}' vs '{wrong_clean_name}' -> {wrong_similarity:.3f}")
    print(f"  Correct match: '{expanded_input}' vs '{correct_clean_name}' -> {correct_similarity:.3f}")
    print()
    
    # Test different similarity metrics
    wrong_partial = fuzz.partial_ratio(expanded_input.lower(), wrong_clean_name.lower()) / 100.0
    correct_partial = fuzz.partial_ratio(expanded_input.lower(), correct_clean_name.lower()) / 100.0
    
    wrong_token = fuzz.token_sort_ratio(expanded_input.lower(), wrong_clean_name.lower()) / 100.0
    correct_token = fuzz.token_sort_ratio(expanded_input.lower(), correct_clean_name.lower()) / 100.0
    
    print("ALTERNATIVE SIMILARITY METRICS:")
    print(f"  Partial Ratio - Wrong: {wrong_partial:.3f}, Correct: {correct_partial:.3f}")
    print(f"  Token Sort    - Wrong: {wrong_token:.3f}, Correct: {correct_token:.3f}")
    print()
    
    # Analyze why wrong match might have been selected
    print("ROOT CAUSE ANALYSIS:")
    print("  The issue is likely in the RETRIEVAL stage (Stage 1) - the vector")
    print("  similarity search may be returning the radiotherapy entry higher")
    print("  than the basic CT entry, possibly due to:")
    print("  1. Training data bias in the embedding model")
    print("  2. More specific entries having stronger embeddings")
    print("  3. 'Radiotherapy planning' appearing in more training contexts")
    print()
    
    print("COMPLEXITY FILTERING IMPACT:")
    if wrong_fsn_complexity > 0.4 and correct_fsn_complexity <= 0.4:
        print("  ✅ Complexity filtering WOULD help - it would deprioritize the wrong")
        print("     (complex) match and favor the correct (simple) match")
    else:
        print("  ❌ Complexity filtering alone won't fix this - both matches have")
        print("     similar complexity levels")

if __name__ == "__main__":
    try:
        compare_matches()
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()