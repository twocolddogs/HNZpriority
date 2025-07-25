#!/usr/bin/env python3
"""
Test script to trace preprocessing and parsing for FDG PET example
"""

import sys
import os
sys.path.insert(0, 'backend')

from preprocessing import ExamPreprocessor
from parser import RadiologySemanticParser
from parsing_utils import *
import yaml

def test_fdg_pet_processing():
    print("🧪 Testing FDG PET Processing Pipeline")
    print("=" * 60)
    
    # Test input
    input_exam = "PET/CT 18F-FDG WB Scan"
    print(f"📥 Input: '{input_exam}'")
    print()
    
    # Load config
    config_path = 'backend/training_testing/config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Step 1: Preprocessing
    print("🔧 STEP 1: PREPROCESSING")
    print("-" * 30)
    
    preprocessor = ExamPreprocessor(config=config)
    
    # Show each preprocessing step
    print(f"1. Original: '{input_exam}'")
    
    # Remove no report suffix
    after_no_report = preprocessor._remove_no_report_suffix(input_exam)
    print(f"2. After no-report removal: '{after_no_report}'")
    
    # Remove admin qualifiers  
    after_admin = preprocessor._remove_admin_qualifiers(after_no_report)
    print(f"3. After admin removal: '{after_admin}'")
    
    # Expand abbreviations
    after_abbrev = preprocessor._expand_abbreviations(after_admin)
    print(f"4. After abbreviation expansion: '{after_abbrev}'")
    
    # Deduplicate modalities
    after_dedup = preprocessor._deduplicate_modalities(after_abbrev)
    print(f"5. After modality deduplication: '{after_dedup}'")
    
    # Handle special characters
    after_special = preprocessor._handle_special_characters(after_dedup)
    print(f"6. After special characters: '{after_special}'")
    
    # Normalize ordinals
    after_ordinals = preprocessor._normalize_ordinals(after_special)
    print(f"7. After ordinal normalization: '{after_ordinals}'")
    
    # Final whitespace
    final_clean = preprocessor._normalize_whitespace(after_ordinals)
    print(f"8. Final clean name: '{final_clean}'")
    
    print()
    
    # Step 2: Parsing
    print("🔍 STEP 2: SEMANTIC PARSING")
    print("-" * 30)
    
    # Initialize parser components
    abbreviation_expander = AbbreviationExpander()
    anatomy_extractor = AnatomyExtractor()
    laterality_detector = LateralityDetector()
    contrast_mapper = ContrastMapper()
    
    parser = RadiologySemanticParser(
        abbreviation_expander=abbreviation_expander,
        anatomy_extractor=anatomy_extractor,
        laterality_detector=laterality_detector, 
        contrast_mapper=contrast_mapper
    )
    
    # Parse the clean name
    components = parser.parse(final_clean)
    
    print("📊 Extracted Components:")
    for key, value in components.items():
        print(f"   {key}: {value}")
    
    print()
    print("🔍 Analysis:")
    print(f"   ✅ Modality preserved: {'PET' in str(components.get('modality', []))}")
    print(f"   ✅ CT preserved: {'CT' in str(components.get('modality', []))}")
    print(f"   ✅ FDG preserved: {'FDG' in str(components.get('technique', []))}")
    print(f"   ✅ Whole body preserved: {'whole body' in str(components.get('anatomy', []))}")

if __name__ == "__main__":
    test_fdg_pet_processing()