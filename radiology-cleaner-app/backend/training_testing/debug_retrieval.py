#!/usr/bin/env python3
"""
Debug script to see exactly which 25 entries are retrieved for a specific input.
Run this from the training_testing directory using the .venv environment.
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Set up logging to see detailed output
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_retrieval_for_input(input_exam: str, modality_code: str = "CT"):
    """
    Debug the retrieval process for a specific input to see exactly which 25 entries are returned.
    """
    try:
        # Import after adding path
        from app import _ensure_app_is_initialized, nhs_lookup_engine, semantic_parser
        from preprocessing import get_preprocessor
        
        print("=" * 60)
        print(f"DEBUGGING RETRIEVAL FOR: '{input_exam}' (modality: {modality_code})")
        print("=" * 60)
        
        # Initialize the app components
        print("1. Initializing app components...")
        _ensure_app_is_initialized()
        
        # Re-import globals after initialization
        from app import nhs_lookup_engine as nhs_engine, semantic_parser as parser
        
        print(f"   nhs_lookup_engine: {'✅ Ready' if nhs_engine else '❌ Not initialized'}")
        print(f"   semantic_parser: {'✅ Ready' if parser else '❌ Not initialized'}")
        
        if not nhs_engine or not parser:
            print("❌ Core components not initialized")
            return
            
        # Use the re-imported variables
        nhs_lookup_engine = nhs_engine
        semantic_parser = parser
            
        preprocessor = get_preprocessor()
        if not preprocessor:
            print("❌ Preprocessor not initialized")
            return
            
        print("✅ App components initialized successfully")
        print()
        
        # Process the input
        print("2. Processing input...")
        if preprocessor.should_exclude_exam(input_exam):
            print(f"❌ Input would be excluded as non-clinical: {input_exam}")
            return
            
        # Use complexity-aware preprocessing
        cleaned_exam_name, is_input_simple = preprocessor.preprocess_with_complexity(input_exam)
        parsed_input_components = semantic_parser.parse_exam_name(cleaned_exam_name, modality_code)
        
        print(f"   Original input: '{input_exam}'")
        print(f"   Cleaned input:  '{cleaned_exam_name}'")
        print(f"   Is simple:      {is_input_simple}")
        print(f"   Parsed components: {json.dumps(parsed_input_components, indent=4)}")
        print()
        
        # Get the retrieval engine and perform Stage 1 retrieval manually
        print("3. Performing Stage 1 retrieval...")
        
        # Check if retriever is available
        if not nhs_lookup_engine.retriever_processor or not nhs_lookup_engine.retriever_processor.is_available():
            print("❌ Retriever processor not available")
            return
            
        # Load FAISS index if needed
        if not nhs_lookup_engine._embeddings_loaded:
            print("   Loading FAISS index...")
            nhs_lookup_engine.nlp_processor = nhs_lookup_engine.retriever_processor
            nhs_lookup_engine._load_index_from_local_disk()
            nhs_lookup_engine._embeddings_loaded = True
            
        if not nhs_lookup_engine.vector_index:
            print("❌ Vector index not loaded")
            return
            
        # Generate embedding and search
        print(f"   Generating embedding using {nhs_lookup_engine.retriever_processor.model_key}...")
        input_embedding = nhs_lookup_engine.retriever_processor.get_text_embedding(cleaned_exam_name)
        
        if input_embedding is None:
            print("❌ Failed to generate embedding")
            return
            
        # Prepare ensemble embedding and search
        import numpy as np
        import faiss
        
        input_ensemble_embedding = np.concatenate([input_embedding, input_embedding]).astype('float32')
        faiss.normalize_L2(input_ensemble_embedding.reshape(1, -1))
        
        top_k = nhs_lookup_engine.config.get('retriever_top_k', 25)
        distances, indices = nhs_lookup_engine.vector_index.search(input_ensemble_embedding.reshape(1, -1), top_k)
        
        # Get candidate entries
        candidate_snomed_ids = [nhs_lookup_engine.index_to_snomed_id[i] for i in indices[0] if i < len(nhs_lookup_engine.index_to_snomed_id)]
        candidate_entries = [nhs_lookup_engine.snomed_lookup[str(sid)] for sid in candidate_snomed_ids if str(sid) in nhs_lookup_engine.snomed_lookup]
        
        print(f"✅ Retrieved {len(candidate_entries)} candidates")
        print()
        
        # Display all 25 retrieved entries with details
        print("4. RETRIEVED ENTRIES (Top 25):")
        print("-" * 100)
        print(f"{'Rank':<4} {'Distance':<8} {'SNOMED ID':<12} {'Complex':<7} {'Primary Source Name':<50} {'FSN'}")
        print("-" * 100)
        
        for i, (entry, distance) in enumerate(zip(candidate_entries, distances[0])):
            rank = i + 1
            snomed_id = entry.get('snomed_concept_id', 'N/A')
            primary_name = entry.get('primary_source_name', 'N/A')[:47] + "..." if len(entry.get('primary_source_name', '')) > 50 else entry.get('primary_source_name', 'N/A')
            fsn = entry.get('snomed_fsn', 'N/A')[:50] + "..." if len(entry.get('snomed_fsn', '')) > 53 else entry.get('snomed_fsn', 'N/A')
            is_complex = entry.get('_is_complex_fsn', 'N/A')
            
            print(f"{rank:<4} {distance:<8.4f} {snomed_id:<12} {is_complex:<7} {primary_name:<50} {fsn}")
            
        print("-" * 100)
        print()
        
        # Show complexity filtering impact if applicable
        if is_input_simple:
            print("5. COMPLEXITY FILTERING ANALYSIS:")
            print(f"   Input is simple - complexity filtering would be applied")
            
            simple_entries = [e for e in candidate_entries if not e.get('_is_complex_fsn', False)]
            complex_entries = [e for e in candidate_entries if e.get('_is_complex_fsn', False)]
            
            print(f"   Simple FSNs: {len(simple_entries)}")
            print(f"   Complex FSNs: {len(complex_entries)}")
            
            if simple_entries:
                print("   Top 5 Simple FSNs:")
                for i, entry in enumerate(simple_entries[:5]):
                    print(f"     {i+1}. {entry.get('primary_source_name', 'N/A')} (SNOMED: {entry.get('snomed_concept_id', 'N/A')})")
            
            if complex_entries:
                print("   Top 5 Complex FSNs:")
                for i, entry in enumerate(complex_entries[:5]):
                    print(f"     {i+1}. {entry.get('primary_source_name', 'N/A')} (SNOMED: {entry.get('snomed_concept_id', 'N/A')})")
        else:
            print("5. No complexity filtering (input is complex)")
            
        print()
        print("✅ Retrieval debug completed successfully!")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to run retrieval debugging."""
    
    # Test cases
    test_cases = [
        ("CT Cervical Spine", "CT"),
        ("MRI Brain", "MR"),
        ("Chest X-ray", "XR"),
    ]
    
    print("RETRIEVAL DEBUG SCRIPT")
    print("=" * 60)
    print("This script shows exactly which 25 entries are retrieved for each input")
    print()
    
    # Allow custom input or use test cases
    if len(sys.argv) > 1:
        if len(sys.argv) == 3:
            # Two arguments: exam_name and modality
            custom_input = sys.argv[1]
            modality = sys.argv[2]
        else:
            # One or more arguments: treat as exam_name
            custom_input = " ".join(sys.argv[1:])
            modality = "CT"  # Default modality
        debug_retrieval_for_input(custom_input, modality)
    else:
        print("Usage: python debug_retrieval.py <exam_name> [modality]")
        print("Example: python debug_retrieval.py 'CT Cervical Spine' CT")
        print()
        print("Running default test case: CT Cervical Spine")
        debug_retrieval_for_input("CT Cervical Spine", "CT")

if __name__ == "__main__":
    main()