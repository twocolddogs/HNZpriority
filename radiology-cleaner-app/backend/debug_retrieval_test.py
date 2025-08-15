#!/usr/bin/env python3
"""
Debug script to test actual retrieval and see why bilateral entry is missing.

This script will simulate the exact retrieval process with a test query
to see if the bilateral "XR Leg length measurement Both" entry appears in the candidates.
"""

import json
import sys
import os
import logging
import numpy as np
import faiss

# Add backend to path
sys.path.append('/Users/alrumballsmith/Documents/GitHub/HNZpriority/radiology-cleaner-app/backend')

from nlp_processor import NLPProcessor
from parser import RadiologySemanticParser
from parsing_utils import AbbreviationExpander, AnatomyExtractor, LateralityDetector, ContrastMapper
from preprocessing import initialize_preprocessor, get_preprocessor
from config_manager import get_config
from nhs_lookup_engine import NHSLookupEngine
from reranker_manager import RerankerManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_actual_retrieval():
    """Test actual retrieval with a leg length query."""
    print("=" * 70)
    print("TESTING ACTUAL RETRIEVAL FOR LEG LENGTH MEASUREMENT")
    print("=" * 70)
    
    try:
        # Initialize all components
        print("\n1. INITIALIZING COMPONENTS")
        print("-" * 30)
        
        config = get_config()
        preprocessing_config = config.get_section('preprocessing')
        
        abbreviation_expander = AbbreviationExpander()
        initialize_preprocessor(abbreviation_expander, config=preprocessing_config)
        
        anatomy_vocab = preprocessing_config.get('anatomy_vocabulary', {})
        anatomy_extractor = AnatomyExtractor(anatomy_vocabulary=anatomy_vocab)
        laterality_detector = LateralityDetector()
        contrast_mapper = ContrastMapper()
        
        nlp_processor = NLPProcessor(model_key='retriever')
        
        semantic_parser = RadiologySemanticParser(
            nlp_processor=nlp_processor,
            anatomy_extractor=anatomy_extractor,
            laterality_detector=laterality_detector,
            contrast_mapper=contrast_mapper
        )
        
        # Initialize reranker manager (minimal setup)
        reranker_manager = RerankerManager()
        
        nhs_json_path = '/Users/alrumballsmith/Documents/GitHub/HNZpriority/radiology-cleaner-app/backend/core/NHS.json'
        
        engine = NHSLookupEngine(
            nhs_json_path=nhs_json_path,
            retriever_processor=nlp_processor,
            reranker_manager=reranker_manager,
            semantic_parser=semantic_parser
        )
        
        print("✅ Components initialized successfully")
        
        # Load the FAISS index manually since we don't have a pre-built cache
        print("\n2. BUILDING FAISS INDEX FOR TESTING")
        print("-" * 40)
        
        # Get embeddings for all entries
        primary_names = [e.get("_clean_primary_name_for_embedding", "") for e in engine.nhs_data]
        fsn_names = [e.get("_clean_fsn_for_embedding", "") for e in engine.nhs_data]
        
        print("Getting embeddings for primary names...")
        primary_embeddings_raw = nlp_processor.batch_get_embeddings(primary_names)
        print("Getting embeddings for FSN names...")
        fsn_embeddings_raw = nlp_processor.batch_get_embeddings(fsn_names)
        
        # Filter out None values and track valid indices
        valid_indices = []
        valid_primary_embeddings = []
        valid_fsn_embeddings = []
        valid_snomed_ids = []
        
        bilateral_entry_included = False
        bilateral_faiss_idx = None
        
        for i, (primary_emb, fsn_emb) in enumerate(zip(primary_embeddings_raw, fsn_embeddings_raw)):
            if primary_emb is not None and fsn_emb is not None:
                valid_indices.append(i)
                valid_primary_embeddings.append(primary_emb)
                valid_fsn_embeddings.append(fsn_emb)
                valid_snomed_ids.append(engine.nhs_data[i].get('snomed_concept_id'))
                
                # Check if this is our bilateral entry
                entry = engine.nhs_data[i]
                if (entry.get('primary_source_name') == 'XR Leg length measurement Both' and 
                    entry.get('snomed_laterality_concept_id') == 51440002):
                    bilateral_entry_included = True
                    bilateral_faiss_idx = len(valid_indices) - 1  # Index in the FAISS index
                    print(f"✅ Bilateral entry included in FAISS index at position {bilateral_faiss_idx}")
            else:
                entry = engine.nhs_data[i]
                primary_name = entry.get('primary_source_name', 'N/A')
                if 'XR Leg length' in primary_name:
                    print(f"⚠️  Leg length entry excluded: '{primary_name}' (primary_emb={primary_emb is not None}, fsn_emb={fsn_emb is not None})")
        
        if not bilateral_entry_included:
            print("❌ PROBLEM: Bilateral entry NOT included in FAISS index!")
            return False
        
        # Build the FAISS index
        primary_embeddings = np.array(valid_primary_embeddings, dtype='float32')
        fsn_embeddings = np.array(valid_fsn_embeddings, dtype='float32')
        ensemble_embeddings = np.concatenate([primary_embeddings, fsn_embeddings], axis=1)
        faiss.normalize_L2(ensemble_embeddings)
        
        dimension = ensemble_embeddings.shape[1]
        vector_index = faiss.IndexFlatIP(dimension)
        vector_index.add(ensemble_embeddings)
        
        # Set up the engine's index
        engine.vector_index = vector_index
        engine.index_to_snomed_id = valid_snomed_ids
        engine._embeddings_loaded = True
        
        print(f"✅ FAISS index built with {len(valid_indices)} entries")
        
        # Test different query variations
        test_queries = [
            "leg length measurement",
            "XR leg length",
            "xray leg length both",
            "leg length bilateral", 
            "long leg both",
            "Long Legs Bilateral"  # This is the original query from the issue
        ]
        
        print("\n3. TESTING RETRIEVAL WITH DIFFERENT QUERIES")
        print("-" * 50)
        
        for query in test_queries:
            print(f"\nTesting query: '{query}'")
            print("-" * (15 + len(query)))
            
            # Generate embedding for the query
            query_embedding = nlp_processor.get_text_embedding(query)
            if query_embedding is None:
                print(f"❌ Failed to generate embedding for query: {query}")
                continue
            
            # Prepare ensemble embedding and search FAISS index
            query_ensemble = np.concatenate([query_embedding, query_embedding]).astype('float32')
            faiss.normalize_L2(query_ensemble.reshape(1, -1))
            
            # Search with top-20 to see more results
            top_k = 20
            distances, indices = vector_index.search(query_ensemble.reshape(1, -1), top_k)
            
            # Get candidate entries
            candidate_snomed_ids = [valid_snomed_ids[i] for i in indices[0] if i < len(valid_snomed_ids)]
            
            print(f"Top {len(candidate_snomed_ids)} candidates:")
            bilateral_found = False
            
            for rank, snomed_id in enumerate(candidate_snomed_ids):
                # Find the original entry
                entry = engine.snomed_lookup.get(str(snomed_id))
                if entry:
                    primary_name = entry.get('primary_source_name', 'N/A')
                    score = distances[0][rank]
                    
                    # Check if this is a leg length entry
                    if 'leg length' in primary_name.lower() or 'XR Leg length' in primary_name:
                        lat_id = entry.get('snomed_laterality_concept_id')
                        marker = ""
                        if (entry.get('primary_source_name') == 'XR Leg length measurement Both' and 
                            lat_id == 51440002):
                            marker = " ⭐ BILATERAL TARGET"
                            bilateral_found = True
                        print(f"  {rank+1:2d}. {primary_name} (score: {score:.4f}, lat_id: {lat_id}){marker}")
                    elif rank < 5:  # Show top 5 non-leg-length entries
                        print(f"  {rank+1:2d}. {primary_name} (score: {score:.4f})")
            
            if bilateral_found:
                print(f"✅ Bilateral entry FOUND in top {top_k} candidates")
            else:
                print(f"❌ Bilateral entry NOT FOUND in top {top_k} candidates")
                
                # Check if bilateral entry would have been found with higher k
                if bilateral_faiss_idx is not None:
                    all_distances = np.dot(query_ensemble.reshape(1, -1), ensemble_embeddings.T)[0]
                    bilateral_score = all_distances[bilateral_faiss_idx]
                    bilateral_rank = np.sum(all_distances > bilateral_score) + 1
                    print(f"  ℹ️  Bilateral entry would be rank {bilateral_rank} with score {bilateral_score:.4f}")
        
        print("\n" + "=" * 70)
        print("RETRIEVAL TEST SUMMARY")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during retrieval test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main debug function."""
    success = test_actual_retrieval()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)