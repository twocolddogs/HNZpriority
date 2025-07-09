#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser import RadiologySemanticParser
from database_models import DatabaseManager
from standardization_engine import StandardizationEngine

def test_enhanced_parsing():
    print("Testing Enhanced Radiology Parser...")
    print("="*50)
    
    # Initialize components
    db_manager = DatabaseManager()
    standardization_engine = StandardizationEngine(db_manager=db_manager)
    parser = RadiologySemanticParser(db_manager=db_manager, standardization_engine=standardization_engine)
    
    # Load SNOMED data
    csv_path = 'base_code_set.csv'
    db_manager.load_snomed_from_csv(csv_path)
    
    # Test cases
    test_cases = [
        {
            'exam_name': 'CT Head',
            'modality': 'CT',
            'expected_anatomy': ['Head']
        },
        {
            'exam_name': 'Chest X-ray',
            'modality': 'XR',
            'expected_anatomy': ['Chest']
        },
        {
            'exam_name': 'MRI Brain with contrast',
            'modality': 'MR',
            'expected_anatomy': ['Brain'],
            'expected_contrast': 'with'
        },
        {
            'exam_name': 'Computed tomography of abdomen',  # Should match SNOMED FSN exactly
            'modality': 'CT',
            'expected_clean_name': 'CT Abdomen'
        },
        {
            'exam_name': 'CT chest and abdomen',  # Should fuzzy match
            'modality': 'CT',
            'expected_anatomy': ['Chest', 'Abdomen']
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['exam_name']}")
        print("-" * 30)
        
        result = parser.parse_exam_name(
            test_case['exam_name'], 
            test_case['modality']
        )
        
        print(f"Input: {test_case['exam_name']} ({test_case['modality']})")
        print(f"Clean Name: {result.get('cleanName', 'None')}")
        print(f"Anatomy: {result.get('anatomy', [])}")
        print(f"Laterality: {result.get('laterality', 'None')}")
        print(f"Contrast: {result.get('contrast', 'None')}")
        print(f"Confidence: {result.get('confidence', 0):.2f}")
        
        # Check for SNOMED codes
        snomed = result.get('snomed', {})
        if snomed and snomed.get('snomed_concept_id'):
            print(f"SNOMED Code: {snomed.get('snomed_concept_id')}")
            print(f"SNOMED FSN: {snomed.get('snomed_fsn', 'None')}")
        else:
            print("SNOMED Code: None found")
        
        # Check match info
        match_info = result.get('match_info', {})
        if match_info:
            print(f"Match Type: {match_info.get('type', 'none')}")
            print(f"Similarity Score: {match_info.get('similarity_score', 0):.2f}")
        
        # Validate expectations
        if 'expected_anatomy' in test_case:
            expected = set(test_case['expected_anatomy'])
            actual = set(result.get('anatomy', []))
            if not expected.issubset(actual):
                print(f"❌ ANATOMY MISMATCH: Expected {expected}, got {actual}")
            else:
                print(f"✅ ANATOMY OK: {actual}")
        
        if 'expected_contrast' in test_case:
            expected = test_case['expected_contrast']
            actual = result.get('contrast')
            if expected != actual:
                print(f"❌ CONTRAST MISMATCH: Expected {expected}, got {actual}")
            else:
                print(f"✅ CONTRAST OK: {actual}")
        
        if 'expected_clean_name' in test_case:
            expected = test_case['expected_clean_name']
            actual = result.get('cleanName')
            if expected != actual:
                print(f"❌ CLEAN NAME MISMATCH: Expected {expected}, got {actual}")
            else:
                print(f"✅ CLEAN NAME OK: {actual}")

if __name__ == '__main__':
    test_enhanced_parsing()