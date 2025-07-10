#!/usr/bin/env python3

import json
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

from comprehensive_preprocessor import ComprehensivePreprocessor

def test_sample_data():
    """Test the sample data to verify modality detection"""
    
    # Sample data from user
    sample_data = [
        { "DATA_SOURCE": "CO", "MODALITY_CODE": "XR", "EXAM_CODE": "D06", "EXAM_NAME": "Chest (single projection)" },
        { "DATA_SOURCE": "K", "MODALITY_CODE": "XR", "EXAM_CODE": "XRCHEST", "EXAM_NAME": "Xray Chest" },
        { "DATA_SOURCE": "C", "MODALITY_CODE": "CT", "EXAM_CODE": "CHED", "EXAM_NAME": "CT Head" },
        { "DATA_SOURCE": "CO", "MODALITY_CODE": "CT", "EXAM_CODE": "Q01", "EXAM_NAME": "CT HEAD C-" },
        { "DATA_SOURCE": "C", "MODALITY_CODE": "XR", "EXAM_CODE": "XRKN", "EXAM_NAME": "XR Right Knee" }
    ]
    
    print("Testing modality detection with sample data...")
    print("=" * 60)
    
    # Initialize preprocessor (will use dummy data if NHS.json not found)
    try:
        nhs_path = "../core/NHS.json"
        usa_path = "../core/USA.json"
        
        if os.path.exists(nhs_path):
            preprocessor = ComprehensivePreprocessor(nhs_path, usa_path if os.path.exists(usa_path) else None)
        else:
            print("Warning: NHS.json not found, creating dummy preprocessor")
            from comprehensive_preprocessor import ModalityExtractor
            preprocessor = type('DummyPreprocessor', (), {
                'preprocess_exam_name': lambda self, exam_name, modality=None: {
                    'components': {
                        'modality': ModalityExtractor().extract(exam_name) or modality,
                        'provided_modality': modality,
                        'detected_modality': ModalityExtractor().extract(exam_name)
                    }
                }
            })()
        
        for i, item in enumerate(sample_data, 1):
            exam_name = item['EXAM_NAME']
            provided_modality = item['MODALITY_CODE']
            
            print(f"\n{i}. Testing: '{exam_name}'")
            print(f"   Expected modality: {provided_modality}")
            
            # Test without provided modality (old way)
            try:
                result_without = preprocessor.preprocess_exam_name(exam_name)
                detected_only = result_without['components'].get('modality')
                print(f"   Detected only: {detected_only or 'None'}")
            except:
                detected_only = None
                print(f"   Detected only: None (error)")
            
            # Test with provided modality (new way)
            try:
                result_with = preprocessor.preprocess_exam_name(exam_name, provided_modality)
                final_modality = result_with['components'].get('modality')
                print(f"   Final modality: {final_modality}")
                
                # Check if it matches expected
                status = "✅ PASS" if final_modality == provided_modality else "❌ FAIL"
                print(f"   Status: {status}")
                
            except Exception as e:
                print(f"   Final modality: Error - {e}")
                print(f"   Status: ❌ FAIL")
    
    except Exception as e:
        print(f"Error initializing preprocessor: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("Test complete!")

if __name__ == "__main__":
    test_sample_data()