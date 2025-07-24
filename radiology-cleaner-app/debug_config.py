#!/usr/bin/env python3
"""
Debug config loading
"""

import sys
import os
sys.path.insert(0, 'backend')

from preprocessing import ExamPreprocessor
import yaml

def debug_config_loading():
    print("🔍 Debugging Config Loading")
    print("=" * 40)
    
    # Load config directly
    config_path = 'backend/training_testing/config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print("📖 Config structure:")
    print(f"   - Has 'preprocessing' key: {'preprocessing' in config}")
    if 'preprocessing' in config:
        preprocessing = config['preprocessing']
        print(f"   - Has 'medical_abbreviations' key: {'medical_abbreviations' in preprocessing}")
        if 'medical_abbreviations' in preprocessing:
            abbrevs = preprocessing['medical_abbreviations']
            print(f"   - Number of abbreviations: {len(abbrevs)}")
            print(f"   - Has '18F-FDG': {'18F-FDG' in abbrevs}")
            print(f"   - Has 'WB': {'WB' in abbrevs}")
    
    print()
    print("🔧 Testing ExamPreprocessor initialization:")
    preprocessor = ExamPreprocessor(config=config)
    print(f"   - preprocessor.medical_abbreviations is empty: {len(preprocessor.medical_abbreviations) == 0}")
    print(f"   - Number of abbreviations loaded: {len(preprocessor.medical_abbreviations)}")
    
    if len(preprocessor.medical_abbreviations) > 0:
        print(f"   - Has '18F-FDG': {'18F-FDG' in preprocessor.medical_abbreviations}")
        print(f"   - Has 'WB': {'WB' in preprocessor.medical_abbreviations}")
    else:
        print("   ❌ No abbreviations loaded!")

if __name__ == "__main__":
    debug_config_loading()