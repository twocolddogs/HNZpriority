#!/usr/bin/env python3
"""
Test script for binary complexity filtering implementation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from complexity import ComplexityScorer
from preprocessing import ExamPreprocessor

def test_complexity_scoring():
    """Test the complexity scoring functionality."""
    scorer = ComplexityScorer()
    
    # Test FSN complexity calculation
    simple_fsns = [
        "CT of chest",
        "MRI of head",
        "X-ray of ankle"
    ]
    
    complex_fsns = [
        "CT of chest with intravenous contrast enhancement using multiplanar reconstruction techniques",
        "MRI of brain with gadolinium-enhanced T1-weighted sequences for vascular assessment",
        "Interventional radiology procedure with fluoroscopic guidance and contrast administration"
    ]
    
    print("=== FSN Complexity Testing ===")
    print("\nSimple FSNs:")
    for fsn in simple_fsns:
        complexity = scorer.calculate_fsn_total_complexity(fsn)
        is_complex = complexity > 0.4
        print(f"  '{fsn}' -> complexity={complexity:.3f}, is_complex={is_complex}")
    
    print("\nComplex FSNs:")
    for fsn in complex_fsns:
        complexity = scorer.calculate_fsn_total_complexity(fsn)
        is_complex = complexity > 0.4
        print(f"  '{fsn}' -> complexity={complexity:.3f}, is_complex={is_complex}")

def test_input_complexity():
    """Test input complexity after abbreviation expansion."""
    # Create a minimal preprocessor for testing
    class TestPreprocessor:
        def __init__(self):
            self.complexity_scorer = ComplexityScorer()
        
        def _expand_abbreviations(self, text):
            # Simple abbreviation expansion for testing
            expansions = {
                'CT': 'computed tomography',
                'MR': 'magnetic resonance',
                'CXR': 'chest x-ray',
                'w/': 'with',
                'C+': 'with contrast'
            }
            for abbrev, expansion in expansions.items():
                text = text.replace(abbrev, expansion)
            return text
    
    preprocessor = TestPreprocessor()
    
    simple_inputs = [
        "CT CHEST",
        "MR HEAD", 
        "CXR"
    ]
    
    complex_inputs = [
        "CT CHEST w/ C+ & MPR",
        "MR HEAD w/ GAD + T1 + T2 + FLAIR",
        "IR PROCEDURE + FLUORO + C+"
    ]
    
    print("\n=== Input Complexity Testing ===")
    print("\nSimple Inputs:")
    for input_text in simple_inputs:
        expanded = preprocessor._expand_abbreviations(input_text)
        complexity = preprocessor.complexity_scorer.calculate_input_qualifier_complexity(expanded)
        is_simple = complexity < 0.3
        print(f"  '{input_text}' -> '{expanded}' -> complexity={complexity:.3f}, is_simple={is_simple}")
    
    print("\nComplex Inputs:")
    for input_text in complex_inputs:
        expanded = preprocessor._expand_abbreviations(input_text)
        complexity = preprocessor.complexity_scorer.calculate_input_qualifier_complexity(expanded)
        is_simple = complexity < 0.3
        print(f"  '{input_text}' -> '{expanded}' -> complexity={complexity:.3f}, is_simple={is_simple}")

if __name__ == "__main__":
    print("Testing Binary Complexity Filtering Implementation")
    print("=" * 50)
    
    try:
        test_complexity_scoring()
        test_input_complexity()
        print("\n✅ All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()