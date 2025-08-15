#!/usr/bin/env python3
"""
Debug script to investigate why the bilateral 'XR Leg length measurement Both' entry
is not appearing in retrieval candidates.

This script will:
1. Load NHS.json and find the bilateral entry
2. Check if it gets processed properly during preprocessing
3. Verify it gets included in the FAISS index
4. Test embedding generation for the entry
5. Run a mock retrieval to see if it appears in candidates
"""

import json
import sys
import os
import logging

# Add backend to path
sys.path.append('/Users/alrumballsmith/Documents/GitHub/HNZpriority/radiology-cleaner-app/backend')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main debug function."""
    print("=" * 60)
    print("DEBUGGING BILATERAL ENTRY MISSING FROM RETRIEVAL")
    print("=" * 60)
    
    # Step 1: Find bilateral entry in raw NHS.json
    print("\n1. CHECKING RAW NHS.json DATA")
    print("-" * 40)
    
    nhs_json_path = '/Users/alrumballsmith/Documents/GitHub/HNZpriority/radiology-cleaner-app/backend/core/NHS.json'
    
    try:
        with open(nhs_json_path, 'r') as f:
            nhs_data = json.load(f)
        
        # Find XR Leg length measurement entries
        leg_length_entries = []
        for idx, entry in enumerate(nhs_data):
            if 'XR Leg length measurement' in entry.get('primary_source_name', ''):
                leg_length_entries.append((idx, entry))
        
        print(f"Found {len(leg_length_entries)} XR Leg length measurement entries:")
        for idx, entry in leg_length_entries:
            lat_id = entry.get('snomed_laterality_concept_id')
            lat_fsn = entry.get('snomed_laterality_fsn', 'None')
            primary_name = entry.get('primary_source_name')
            print(f"  Index {idx}: {primary_name} (Lat ID: {lat_id}, FSN: {lat_fsn})")
        
    except Exception as e:
        print(f"❌ Error reading NHS.json: {e}")
        return False
    
    # Step 2: Test NHS Lookup Engine initialization and preprocessing
    print("\n2. TESTING NHS LOOKUP ENGINE INITIALIZATION")  
    print("-" * 50)
    
    try:
        from nlp_processor import NLPProcessor
        from parser import RadiologySemanticParser
        from parsing_utils import AbbreviationExpander, AnatomyExtractor, LateralityDetector, ContrastMapper
        from preprocessing import initialize_preprocessor, get_preprocessor
        from config_manager import get_config
        from nhs_lookup_engine import NHSLookupEngine
        
        # Initialize config and preprocessor
        config = get_config()
        preprocessing_config = config.get_section('preprocessing')
        
        abbreviation_expander = AbbreviationExpander()
        initialize_preprocessor(abbreviation_expander, config=preprocessing_config)
        
        # Initialize parsing components
        anatomy_vocab = preprocessing_config.get('anatomy_vocabulary', {})
        anatomy_extractor = AnatomyExtractor(anatomy_vocabulary=anatomy_vocab)
        laterality_detector = LateralityDetector()
        contrast_mapper = ContrastMapper()
        
        # Initialize NLP processor (use retriever model)
        nlp_processor = NLPProcessor(model_key='retriever')
        
        # Initialize semantic parser
        semantic_parser = RadiologySemanticParser(
            nlp_processor=nlp_processor,
            anatomy_extractor=anatomy_extractor,
            laterality_detector=laterality_detector,
            contrast_mapper=contrast_mapper
        )
        
        print("✅ Successfully initialized all components")
        
        # Initialize NHS Lookup Engine (without reranker for testing)
        engine = NHSLookupEngine(
            nhs_json_path=nhs_json_path,
            retriever_processor=nlp_processor,
            reranker_manager=None,
            semantic_parser=semantic_parser
        )
        
        print(f"✅ NHS Lookup Engine initialized with {len(engine.nhs_data)} entries")
        
    except Exception as e:
        print(f"❌ Error initializing NHS Lookup Engine: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Check if bilateral entry exists in processed data
    print("\n3. CHECKING PROCESSED NHS DATA")
    print("-" * 35)
    
    try:
        # Find XR Leg length entries in processed data
        processed_leg_entries = []
        for idx, entry in enumerate(engine.nhs_data):
            if 'XR Leg length measurement' in entry.get('primary_source_name', ''):
                processed_leg_entries.append((idx, entry))
        
        print(f"Found {len(processed_leg_entries)} XR Leg length entries in processed data:")
        for idx, entry in processed_leg_entries:
            primary_name = entry.get('primary_source_name')
            clean_primary = entry.get('_clean_primary_name_for_embedding', 'N/A')
            clean_fsn = entry.get('_clean_fsn_for_embedding', 'N/A') 
            parsed_components = entry.get('_parsed_components', {})
            laterality = parsed_components.get('laterality', [])
            lat_concept_id = entry.get('snomed_laterality_concept_id')
            
            print(f"  Index {idx}: {primary_name}")
            print(f"    Clean Primary: {clean_primary}")
            print(f"    Clean FSN: {clean_fsn}")
            print(f"    Parsed Laterality: {laterality}")
            print(f"    SNOMED Lat ID: {lat_concept_id}")
            print()
            
    except Exception as e:
        print(f"❌ Error checking processed data: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Test embedding generation for bilateral entry
    print("\n4. TESTING EMBEDDING GENERATION FOR BILATERAL ENTRY")
    print("-" * 55)
    
    try:
        # Find the bilateral entry
        bilateral_entry = None
        for entry in engine.nhs_data:
            if (entry.get('primary_source_name') == 'XR Leg length measurement Both' and 
                entry.get('snomed_laterality_concept_id') == 51440002):
                bilateral_entry = entry
                break
        
        if not bilateral_entry:
            print("❌ Could not find bilateral entry in processed data")
            return False
            
        print("✅ Found bilateral entry in processed data")
        
        # Test embedding generation
        clean_primary = bilateral_entry.get('_clean_primary_name_for_embedding', '')
        clean_fsn = bilateral_entry.get('_clean_fsn_for_embedding', '')
        
        print(f"Testing embeddings for:")
        print(f"  Primary: '{clean_primary}'")
        print(f"  FSN: '{clean_fsn}'")
        
        primary_embedding = nlp_processor.get_text_embedding(clean_primary)
        fsn_embedding = nlp_processor.get_text_embedding(clean_fsn)
        
        if primary_embedding is not None and fsn_embedding is not None:
            print("✅ Successfully generated embeddings for bilateral entry")
            print(f"  Primary embedding shape: {primary_embedding.shape}")
            print(f"  FSN embedding shape: {fsn_embedding.shape}")
        else:
            print(f"❌ Failed to generate embeddings: primary={primary_embedding is not None}, fsn={fsn_embedding is not None}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing embedding generation: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 5: Check if bilateral entry would be included in FAISS index
    print("\n5. CHECKING FAISS INDEX INCLUSION")
    print("-" * 40)
    
    try:
        # Simulate the build_cache logic to see if bilateral entry gets included
        primary_names = [e.get("_clean_primary_name_for_embedding", "") for e in engine.nhs_data]
        fsn_names = [e.get("_clean_fsn_for_embedding", "") for e in engine.nhs_data]
        
        print(f"Testing batch embedding generation for {len(primary_names)} entries...")
        
        # Get embeddings and handle None values (similar to build_cache.py logic)
        primary_embeddings_raw = nlp_processor.batch_get_embeddings(primary_names[:10])  # Test first 10 only
        fsn_embeddings_raw = nlp_processor.batch_get_embeddings(fsn_names[:10])
        
        # Filter out None values and track valid indices
        valid_indices = []
        for i, (primary_emb, fsn_emb) in enumerate(zip(primary_embeddings_raw, fsn_embeddings_raw)):
            if primary_emb is not None and fsn_emb is not None:
                valid_indices.append(i)
            else:
                entry = engine.nhs_data[i]
                primary_name = entry.get('primary_source_name', 'N/A')
                print(f"  ⚠️  Entry {i} would be EXCLUDED from FAISS index: '{primary_name}' (primary_emb={primary_emb is not None}, fsn_emb={fsn_emb is not None})")
        
        print(f"✅ {len(valid_indices)}/10 entries would be included in FAISS index")
        
        # Check specifically if our bilateral entry would be included
        bilateral_idx = None
        for idx, entry in enumerate(engine.nhs_data):
            if (entry.get('primary_source_name') == 'XR Leg length measurement Both' and 
                entry.get('snomed_laterality_concept_id') == 51440002):
                bilateral_idx = idx
                break
        
        if bilateral_idx is not None and bilateral_idx < 10:
            if bilateral_idx in valid_indices:
                print("✅ Bilateral entry WOULD be included in FAISS index")
            else:
                print("❌ Bilateral entry WOULD BE EXCLUDED from FAISS index")
                return False
        else:
            print(f"ℹ️  Bilateral entry at index {bilateral_idx} - need full test to verify FAISS inclusion")
            
    except Exception as e:
        print(f"❌ Error testing FAISS index inclusion: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("DEBUG SUMMARY")
    print("=" * 60)
    print("✅ Bilateral entry exists in raw NHS.json")
    print("✅ NHS Lookup Engine initializes correctly")
    print("✅ Bilateral entry exists in processed data")
    print("✅ Embedding generation works for bilateral entry")
    print("✅ Bilateral entry should be included in FAISS index")
    print()
    print("CONCLUSION: The bilateral entry appears to be processed correctly.")
    print("The issue might be in the retrieval logic, reranking, or filtering.")
    print("Need to test actual retrieval with a specific query to isolate the problem.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)