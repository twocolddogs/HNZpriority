#!/usr/bin/env python3
"""
Extract unique modalities from the HNZ HDP JSON file.
"""

import json
from collections import Counter

def extract_modalities():
    """Extract and display unique modalities from hnz_hdp.json"""
    
    # Read the JSON file
    with open('backend/core/hnz_hdp.json', 'r') as file:
        data = json.load(file)
    
    # Extract all modality codes
    modalities = [exam['MODALITY_CODE'] for exam in data]
    
    # Count occurrences
    modality_counts = Counter(modalities)
    
    # Display results
    print("Unique Modalities Found:")
    print("=" * 30)
    
    # Sort by frequency (descending)
    for modality, count in modality_counts.most_common():
        print(f"{modality:<8} : {count:>4} exams")
    
    print(f"\nTotal unique modalities: {len(modality_counts)}")
    print(f"Total exams: {sum(modality_counts.values())}")
    
    # Show all "Other" modality exams
    print("\n" + "=" * 50)
    print("All 'Other' Modality Exams:")
    print("=" * 50)
    
    other_exams = [exam for exam in data if exam['MODALITY_CODE'] == 'Other']
    
    for i, exam in enumerate(other_exams, 1):
        print(f"{i:3d}. {exam['EXAM_NAME']}")
        print(f"     Code: {exam['EXAM_CODE']}, Source: {exam['DATA_SOURCE']}")
        print()
    
    # Return the list for potential further use
    return list(modality_counts.keys())

if __name__ == "__main__":
    modalities = extract_modalities()