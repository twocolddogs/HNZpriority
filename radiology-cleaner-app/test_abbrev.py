#!/usr/bin/env python3
"""
Test abbreviation expansion specifically
"""

import sys
import os
sys.path.insert(0, 'backend')

from preprocessing import ExamPreprocessor
import yaml

def test_abbreviation_expansion():
    print("🧪 Testing Abbreviation Expansion")
    print("=" * 40)
    
    # Load config
    config_path = 'backend/training_testing/config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    preprocessor = ExamPreprocessor(config=config)
    
    # Test the abbreviations we care about
    test_cases = [
        "18F-FDG",
        "WB", 
        "PET/CT 18F-FDG WB Scan"
    ]
    
    print("📖 Available abbreviations (subset):")
    abbrevs = config.get('preprocessing', {}).get('medical_abbreviations', {})
    for abbrev in ['18F-FDG', 'WB', 'WBSP', 'FDG']:
        if abbrev in abbrevs:
            print(f"   '{abbrev}' → '{abbrevs[abbrev]}'")
    print()
    
    print("🔧 Testing expansion:")
    for test in test_cases:
        expanded = preprocessor._expand_abbreviations(test)
        print(f"   '{test}' → '{expanded}'")

if __name__ == "__main__":
    test_abbreviation_expansion()