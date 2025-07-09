from database_models import DatabaseManager

def debug_fuzzy():
    db = DatabaseManager()
    
    # Test fuzzy matching for generated clean name
    generated = "CT Abdomen Chest"
    print(f"Generated clean name: {generated}")
    print("="*40)
    
    fuzzy_matches = db.fuzzy_match_clean_names(generated, threshold=0.6)
    print(f"Top fuzzy matches:")
    for i, match in enumerate(fuzzy_matches[:10]):
        print(f"  {i+1}. {match['clean_name']:30} | {match['similarity_score']:.3f} | seq:{match['sequence_similarity']:.2f} word:{match['word_similarity']:.2f} prefix:{match['prefix_similarity']:.2f}")

if __name__ == '__main__':
    debug_fuzzy()