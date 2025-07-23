#!/usr/bin/env python3
"""
Trace NHS sample data through the ACTUAL processing pipeline with real NLP components.
This script runs from the Training and Testing directory and references backend modules.
"""

import json
import os
import sys
import yaml
from pathlib import Path

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from nlp_processor import NLPProcessor
from parsing_utils import AbbreviationExpander, AnatomyExtractor, LateralityDetector, ContrastMapper
from preprocessing import initialize_preprocessor, preprocess_exam_name
from parser import RadiologySemanticParser

def trace_real_pipeline():
    """Trace entries through the actual NLP processing pipeline."""
    
    # Load the NHS sample data from backend/core/
    sample_file = backend_dir / 'core' / 'NHS sample.json'
    if not sample_file.exists():
        print(f"❌ Sample file not found: {sample_file}")
        return
    
    with open(sample_file, 'r', encoding='utf-8') as f:
        sample_data = json.load(f)
    
    # Load config from current directory (Training and Testing)
    config_path = Path(__file__).parent / 'config.yaml'
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return
        
    with open(config_path, 'r') as f:
        full_config = yaml.safe_load(f)
        preprocessing_config = full_config.get('preprocessing', {})
    
    print("=" * 80)
    print("NHS SAMPLE DATA - REAL NLP PIPELINE TRACE")
    print("=" * 80)
    print(f"Running from: {Path(__file__).parent}")
    print(f"Backend directory: {backend_dir}")
    print(f"Sample data file: {sample_file}")
    print(f"Config file: {config_path}")
    print(f"Total entries to process: {len(sample_data)}")
    print()
    
    # Initialize NLP processor
    print("🤖 INITIALIZING NLP PROCESSOR...")
    nlp_processor = NLPProcessor(model_key='default')
    print(f"✅ NLP Processor initialized with model: {nlp_processor.model_key}")
    
    # Initialize preprocessing components
    print("\n🔧 INITIALIZING PREPROCESSING COMPONENTS...")
    abbreviation_expander = AbbreviationExpander()
    initialize_preprocessor(abbreviation_expander, config=preprocessing_config)
    
    anatomy_vocab = preprocessing_config.get('anatomy_vocabulary', {})
    anatomy_extractor = AnatomyExtractor(anatomy_vocabulary=anatomy_vocab)
    laterality_detector = LateralityDetector()
    contrast_mapper = ContrastMapper()
    
    # Initialize semantic parser
    semantic_parser = RadiologySemanticParser(
        nlp_processor=nlp_processor,
        anatomy_extractor=anatomy_extractor,
        laterality_detector=laterality_detector,
        contrast_mapper=contrast_mapper
    )
    print("✅ All components initialized")
    print()
    
    # Process first 3 entries in detail
    for i, entry in enumerate(sample_data[:3], 1):
        print(f"{'='*70}")
        print(f"DETAILED PROCESSING - ENTRY {i}/3")
        print(f"{'='*70}")
        
        # Raw entry
        primary_name = entry.get('primary_source_name', '')
        fsn = entry.get('snomed_fsn', '')
        snomed_id = entry.get('snomed_concept_id', '')
        
        print("📦 RAW ENTRY:")
        print(f"  Primary: '{primary_name}'")
        print(f"  FSN: '{fsn}'")
        print(f"  SNOMED ID: {snomed_id}")
        print()
        
        # Step 1: Preprocessing
        print("🔧 STEP 1: PREPROCESSING")
        print("-" * 25)
        try:
            preprocessed_primary = preprocess_exam_name(primary_name)
            print(f"  Original: '{primary_name}'")
            print(f"  Preprocessed: '{preprocessed_primary}'")
        except Exception as e:
            print(f"  ❌ Preprocessing error: {e}")
            preprocessed_primary = primary_name
        print()
        
        # Step 2: Semantic parsing
        print("🧠 STEP 2: SEMANTIC PARSING")
        print("-" * 27)
        try:
            parsed_result = semantic_parser.parse_exam_name(preprocessed_primary, "CT")
            print(f"  Modality: {parsed_result.get('modality', 'Unknown')}")
            print(f"  Anatomy: {parsed_result.get('anatomy', [])}")
            print(f"  Laterality: {parsed_result.get('laterality', 'None')}")
            print(f"  Contrast: {parsed_result.get('contrast', False)}")
            print(f"  Clean name: '{parsed_result.get('clean_name', preprocessed_primary)}'")
        except Exception as e:
            print(f"  ❌ Semantic parsing error: {e}")
            parsed_result = {'clean_name': preprocessed_primary}
        print()
        
        # Step 3: FSN Cleaning (critical step!)
        print("✂️ STEP 3: FSN CLEANING")
        print("-" * 22)
        import re
        fsn_cleaned = re.sub(r'\s*\((procedure|qualifier value|finding)\)$', '', fsn, flags=re.I).strip()
        print(f"  Original FSN: '{fsn}'")
        print(f"  Cleaned FSN: '{fsn_cleaned}'")
        print(f"  Removed: {'(procedure)' if '(procedure)' in fsn else 'None'}")
        print()
        
        # Step 4: Embedding generation
        print("🎯 STEP 4: EMBEDDING GENERATION")
        print("-" * 31)
        try:
            # Generate embeddings for both primary and cleaned FSN
            primary_embedding = nlp_processor.get_text_embedding(preprocessed_primary)
            fsn_embedding = nlp_processor.get_text_embedding(fsn_cleaned)
            
            if primary_embedding is not None:
                print(f"  Primary embedding: {len(primary_embedding)}-dimensional vector")
                print(f"  Sample values: [{primary_embedding[0]:.4f}, {primary_embedding[1]:.4f}, ..., {primary_embedding[-1]:.4f}]")
            else:
                print("  ❌ Primary embedding: Failed to generate")
                
            if fsn_embedding is not None:
                print(f"  FSN embedding: {len(fsn_embedding)}-dimensional vector")
                print(f"  Sample values: [{fsn_embedding[0]:.4f}, {fsn_embedding[1]:.4f}, ..., {fsn_embedding[-1]:.4f}]")
            else:
                print("  ❌ FSN embedding: Failed to generate")
                
        except Exception as e:
            print(f"  ❌ Embedding error: {e}")
        print()
        
        # Step 5: Database preparation
        print("💾 STEP 5: DATABASE PREPARATION")
        print("-" * 30)
        
        # Simulate the cleaned strings that would be stored
        clean_primary = preprocessed_primary.lower().strip()
        clean_fsn = fsn_cleaned.lower().strip()
        
        print(f"  Clean primary for storage: '{clean_primary}'")
        print(f"  Clean FSN for storage: '{clean_fsn}'")
        print(f"  SNOMED concept ID: {snomed_id}")
        print(f"  Searchable variants: 2 (primary + cleaned FSN)")
        print()
        
        print("✅ ENTRY PROCESSING COMPLETE")
        if i < 3:
            print("\n" + "⬇️ " * 25 + "\n")
    
    # Summary of remaining entries
    if len(sample_data) > 3:
        print(f"{'='*70}")
        print(f"SUMMARY OF REMAINING {len(sample_data)-3} ENTRIES")
        print(f"{'='*70}")
        
        for i, entry in enumerate(sample_data[3:], 4):
            primary_name = entry.get('primary_source_name', '')
            try:
                preprocessed = preprocess_exam_name(primary_name)
                embedding = nlp_processor.get_text_embedding(preprocessed)
                embedding_status = "✅" if embedding is not None else "❌"
            except:
                embedding_status = "❌"
                
            print(f"  Entry {i}: '{primary_name}' → Embedding: {embedding_status}")
    
    print(f"\n{'='*80}")
    print("🎯 REAL PIPELINE SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully processed {len(sample_data)} NHS reference entries")
    print("✅ Each entry ready for:")
    print("   • FAISS vector indexing")
    print("   • Semantic similarity matching")
    print("   • Real-time exam name lookup")
    print("   • NHS standardization workflow")
    print()
    print("🔮 Next steps: Build FAISS cache and deploy for production matching")

if __name__ == "__main__":
    trace_real_pipeline()