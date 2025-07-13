#!/usr/bin/env python3

import json
import os
import sys

# Add the backend directory to Python path
sys.path.append('/Users/alrumballsmith/Documents/GitHub/HNZpriority/radiology-cleaner-app/backend')

from nlp_processor import NLPProcessor
from nhs_lookup_engine import NHSLookupEngine

def test_shoulder_matching():
    """Test that 'Shoulder' correctly matches XR shoulder entries instead of XR Sternum."""
    
    # Initialize components
    nlp_processor = NLPProcessor()
    
    # Path to NHS data
    nhs_json_path = '/Users/alrumballsmith/Documents/GitHub/HNZpriority/radiology-cleaner-app/backend/core/NHS.json'
    
    # Initialize NHS lookup engine
    nhs_lookup_engine = NHSLookupEngine(nhs_json_path, nlp_processor)
    
    # Test case: "Shoulder" with XR modality
    input_exam = "Shoulder"
    extracted_components = {
        'modality': ['xr'],  # Should be XR based on exam code A06
        'anatomy': ['shoulder'],
        'laterality': [],  # No laterality specified
        'contrast': []
    }
    
    print(f"Testing input: '{input_exam}'")
    print(f"Extracted components: {extracted_components}")
    print("=" * 50)
    
    # Get standardization result
    result = nhs_lookup_engine.standardize_exam(input_exam, extracted_components)
    
    print(f"Clean Name: {result['clean_name']}")
    print(f"SNOMED ID: {result['snomed_id']}")
    print(f"SNOMED FSN: {result['snomed_fsn']}")
    print(f"Confidence: {result['confidence']:.4f}")
    print(f"Source: {result['source']}")
    
    # Check if result is correct
    clean_name = result['clean_name']
    is_correct = 'shoulder' in clean_name.lower() and 'xr' in clean_name.lower()
    is_wrong = 'sternum' in clean_name.lower()
    
    print("\n" + "=" * 50)
    if is_correct:
        print("✅ SUCCESS: Correctly matched to XR shoulder entry")
    elif is_wrong:
        print("❌ FAILURE: Incorrectly matched to sternum")
    else:
        print("⚠️  UNKNOWN: Matched to unexpected entry")
    
    return result

if __name__ == "__main__":
    print("Testing shoulder matching fix...")
    print()
    
    try:
        result = test_shoulder_matching()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()