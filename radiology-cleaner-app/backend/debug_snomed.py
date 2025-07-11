from database_models import DatabaseManager

def debug_snomed():
    db = DatabaseManager()
    db.load_snomed_from_json('code_set.json')
    
    # Test exact match
    test_name = "Computed tomography of abdomen (procedure)"
    exact_match = db.get_snomed_reference_by_exam_name(test_name)
    print(f"Exact match for '{test_name}': {exact_match}")
    
    # Test fuzzy match for generated clean name
    test_clean = "CT Abdomen"
    fuzzy_matches = db.fuzzy_match_clean_names(test_clean, threshold=0.6)
    print(f"\nFuzzy matches for '{test_clean}':")
    for match in fuzzy_matches[:5]:
        print(f"  - {match['clean_name']} (score: {match['similarity_score']:.2f})")
    
    # Test direct clean name lookup
    exact_clean = db.get_snomed_code(test_clean)
    print(f"\nDirect clean name lookup for '{test_clean}': {exact_clean}")

if __name__ == '__main__':
    debug_snomed()