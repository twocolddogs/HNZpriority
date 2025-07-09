#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser import RadiologySemanticParser
from database_models import DatabaseManager
from standardization_engine import StandardizationEngine

def test_chest_abdomen():
    print("Testing Chest + Abdomen Matching...")
    print("="*50)
    
    # Initialize components
    db_manager = DatabaseManager()
    standardization_engine = StandardizationEngine(db_manager=db_manager)
    parser = RadiologySemanticParser(db_manager=db_manager, standardization_engine=standardization_engine)
    
    # Test the specific case
    exam_name = "CT chest and abdomen"
    modality = "CT"
    
    print(f"Testing: {exam_name} ({modality})")
    print("-" * 30)
    
    result = parser.parse_exam_name(exam_name, modality)
    
    print(f"Input: {exam_name} ({modality})")
    print(f"Clean Name: {result.get('cleanName', 'None')}")
    print(f"Anatomy: {result.get('anatomy', [])}")
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
        print(f"Generated Clean Name: {match_info.get('generated_clean_name', 'None')}")
        print(f"Matched Clean Name: {match_info.get('matched_clean_name', 'None')}")
    
    # Test fuzzy matching directly
    print(f"\nDirect fuzzy matching test for 'CT Chest Abdomen':")
    fuzzy_matches = db_manager.fuzzy_match_clean_names("CT Chest Abdomen", threshold=0.6)
    for i, match in enumerate(fuzzy_matches[:5]):
        print(f"  {i+1}. {match['clean_name']} (score: {match['similarity_score']:.2f})")

if __name__ == '__main__':
    test_chest_abdomen()