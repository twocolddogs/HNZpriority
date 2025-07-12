#!/usr/bin/env python3
"""
Test script for the preprocessing fixes.
"""

import json
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.comprehensive_preprocessor import ComprehensivePreprocessor

def test_with_sanity_data():
    """Test the fixes using the sanity_test.json data"""
    
    # Initialize preprocessor
    nhs_json_path = "backend/core/NHS.json"
    usa_json_path = "backend/core/USA.json"
    
    if not os.path.exists(nhs_json_path):
        print(f"Error: NHS.json not found at {nhs_json_path}")
        return
    
    try:
        preprocessor = ComprehensivePreprocessor(nhs_json_path, usa_json_path if os.path.exists(usa_json_path) else None)
        print("✅ Preprocessor initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize preprocessor: {e}")
        return
    
    # Test cases from sanity_test.json
    test_cases = [
        {"exam_name": "Chest (single projection)", "modality_code": "XR"},
        {"exam_name": "CT Head", "modality_code": "CT"}, 
        {"exam_name": "CT HEAD C-", "modality_code": "CT"},
        {"exam_name": "CT Abdomen and Pelvis", "modality_code": "CT"},
        {"exam_name": "CT Pulmonary Angiogram", "modality_code": "CT"},
        {"exam_name": "MR Head", "modality_code": "MR"},
        {"exam_name": "MRI Brain", "modality_code": "MR"},
        {"exam_name": "MR Lumbar Spine", "modality_code": "MR"},
        {"exam_name": "US Abdomen", "modality_code": "US"},
        {"exam_name": "XR Right Knee", "modality_code": "XR"},
        {"exam_name": "XR Left Knee", "modality_code": "XR"},
        {"exam_name": "XR Bilateral Knee", "modality_code": "XR"},
    ]
    
    print("\n🧪 Testing preprocessing fixes...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        exam_name = test_case["exam_name"]
        modality_code = test_case["modality_code"]
        
        print(f"Test {i}: {exam_name} (modality: {modality_code})")
        
        try:
            result = preprocessor.preprocess_exam_name(exam_name, modality_code)
            components = result['components']
            
            print(f"  Modality: {components['modality']} (mapped: {components.get('mapped_modality', 'N/A')})")
            print(f"  Anatomy: {components['anatomy']}")
            print(f"  Laterality: {components['laterality']}")
            print(f"  Contrast: {components['contrast']}")
            print(f"  Confidence: {result['confidence']:.3f}")
            
            # Check if we got sensible results
            issues = []
            if not components['modality']:
                issues.append("No modality detected")
            if not components['anatomy'] and "head" in exam_name.lower():
                issues.append("No anatomy detected for head exam")
            if not components['anatomy'] and "chest" in exam_name.lower():
                issues.append("No anatomy detected for chest exam")
            if "bilateral" in exam_name.lower() and components['laterality'] != 'bilateral':
                issues.append("Bilateral not detected")
            if "right" in exam_name.lower() and components['laterality'] != 'right':
                issues.append("Right laterality not detected")
            if "left" in exam_name.lower() and components['laterality'] != 'left':
                issues.append("Left laterality not detected")
            
            if issues:
                print(f"  ⚠️  Issues: {', '.join(issues)}")
            else:
                print(f"  ✅ Looks good!")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        print()

if __name__ == "__main__":
    test_with_sanity_data()