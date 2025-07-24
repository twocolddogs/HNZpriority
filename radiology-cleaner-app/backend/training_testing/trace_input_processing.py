#!/usr/bin/env python3
"""
Trace input exam codes through preprocessing and parsing pipeline.
This script shows how raw exam names from example_codes.json are processed.
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
from context_detection import detect_all_contexts

def trace_input_processing():
    """Trace input exam codes through the preprocessing and parsing pipeline."""
    
    # Load the example codes data
    example_file = Path(__file__).parent / 'example_codes.json'
    if not example_file.exists():
        print(f"❌ Example codes file not found: {example_file}")
        return
    
    with open(example_file, 'r', encoding='utf-8') as f:
        example_data = json.load(f)
    
    # Load config from current directory (Training and Testing)
    config_path = Path(__file__).parent / 'config.yaml'
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return
        
    with open(config_path, 'r') as f:
        full_config = yaml.safe_load(f)
        preprocessing_config = full_config.get('preprocessing', {})
    
    print("=" * 80)
    print("INPUT EXAM CODES - PREPROCESSING & PARSING TRACE")
    print("=" * 80)
    print(f"Running from: {Path(__file__).parent}")
    print(f"Backend directory: {backend_dir}")
    print(f"Example codes file: {example_file}")
    print(f"Config file: {config_path}")
    print(f"Total exam codes to process: {len(example_data)}")
    print()
    
    # Initialize preprocessing components
    print("🔧 INITIALIZING PREPROCESSING COMPONENTS...")
    abbreviation_expander = AbbreviationExpander()
    initialize_preprocessor(abbreviation_expander, config=preprocessing_config)
    
    anatomy_vocab = preprocessing_config.get('anatomy_vocabulary', {})
    anatomy_extractor = AnatomyExtractor(anatomy_vocabulary=anatomy_vocab)
    laterality_detector = LateralityDetector()
    contrast_mapper = ContrastMapper()
    
    # Initialize NLP processor and semantic parser
    nlp_processor = NLPProcessor(model_key='default')
    semantic_parser = RadiologySemanticParser(
        nlp_processor=nlp_processor,
        anatomy_extractor=anatomy_extractor,
        laterality_detector=laterality_detector,
        contrast_mapper=contrast_mapper
    )
    print("✅ All components initialized")
    print()
    
    # Process all entries in detail
    for i, entry in enumerate(example_data, 1):
        print(f"{'='*70}")
        print(f"INPUT PROCESSING - ENTRY {i}/{len(example_data)}")
        print(f"{'='*70}")
        
        # Raw input data
        data_source = entry.get('DATA_SOURCE', '')
        modality_code = entry.get('MODALITY_CODE', '')
        exam_code = entry.get('EXAM_CODE', '')
        exam_name = entry.get('EXAM_NAME', '')
        
        print("📦 RAW INPUT:")
        print(f"  Data Source: '{data_source}'")
        print(f"  Modality Code: '{modality_code}'")
        print(f"  Exam Code: '{exam_code}'")
        print(f"  Exam Name: '{exam_name}'")
        print()
        
        # Step 1: Context Detection
        print("🔍 STEP 1: CONTEXT DETECTION")
        print("-" * 28)
        try:
            contexts = detect_all_contexts(exam_name)
            print(f"  Gender context: {contexts.get('gender_context', [])}")
            print(f"  Age context: {contexts.get('age_context', [])}")
            print(f"  Clinical context: {contexts.get('clinical_context', [])}")
        except Exception as e:
            print(f"  ❌ Context detection error: {e}")
            contexts = {}
        print()
        
        # Step 2: Preprocessing
        print("🔧 STEP 2: PREPROCESSING")
        print("-" * 25)
        try:
            preprocessed_name = preprocess_exam_name(exam_name)
            print(f"  Original: '{exam_name}'")
            print(f"  Preprocessed: '{preprocessed_name}'")
            
            # Show what changed
            if exam_name != preprocessed_name:
                print(f"  Changes applied: Yes")
            else:
                print(f"  Changes applied: None")
                
        except Exception as e:
            print(f"  ❌ Preprocessing error: {e}")
            preprocessed_name = exam_name
        print()
        
        # Step 3: Semantic parsing
        print("🧠 STEP 3: SEMANTIC PARSING")
        print("-" * 27)
        try:
            parsed_result = semantic_parser.parse_exam_name(preprocessed_name, modality_code)
            
            print(f"  Input modality code: '{modality_code}'")
            print(f"  Parsed modality: {parsed_result.get('modality', [])}")
            print(f"  Detected anatomy: {parsed_result.get('anatomy', [])}")
            print(f"  Detected laterality: {parsed_result.get('laterality', [])}")
            print(f"  Detected contrast: {parsed_result.get('contrast', [])}")
            print(f"  Detected technique: {parsed_result.get('technique', [])}")
            print(f"  Clean name: '{parsed_result.get('clean_name', preprocessed_name)}'")
            
            # Show parsing effectiveness
            total_components = len(parsed_result.get('modality', [])) + len(parsed_result.get('anatomy', [])) + \
                             len(parsed_result.get('laterality', [])) + len(parsed_result.get('contrast', [])) + \
                             len(parsed_result.get('technique', []))
            print(f"  Total components extracted: {total_components}")
            
        except Exception as e:
            print(f"  ❌ Semantic parsing error: {e}")
            parsed_result = {'clean_name': preprocessed_name}
        print()
        
        # Step 4: Embedding preparation
        print("🎯 STEP 4: EMBEDDING PREPARATION")
        print("-" * 33)
        try:
            # Show what would be embedded
            clean_name = parsed_result.get('clean_name', preprocessed_name)
            print(f"  Text for embedding: '{clean_name}'")
            
            # Generate actual embedding to test
            embedding = nlp_processor.get_text_embedding(clean_name)
            if embedding is not None:
                print(f"  Embedding: {len(embedding)}-dimensional vector ✅")
                print(f"  Sample values: [{embedding[0]:.4f}, {embedding[1]:.4f}, ..., {embedding[-1]:.4f}]")
            else:
                print(f"  Embedding: Failed to generate ❌")
                
        except Exception as e:
            print(f"  ❌ Embedding error: {e}")
        print()
        
        # Step 5: Search readiness
        print("🔎 STEP 5: SEARCH READINESS")
        print("-" * 27)
        final_name = parsed_result.get('clean_name', preprocessed_name)
        search_terms = [final_name.lower().strip()]
        
        print(f"  Final processed name: '{final_name}'")
        print(f"  Search terms: {search_terms}")
        print(f"  Ready for NHS matching: {'✅' if embedding is not None else '❌'}")
        print()
        
        print("✅ INPUT PROCESSING COMPLETE")
        if i < len(example_data):
            print("\n" + "⬇️ " * 25 + "\n")
    
    print(f"{'='*80}")
    print("🎯 INPUT PROCESSING SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully processed {len(example_data)} input exam codes")
    print()
    
    # Summary statistics
    successful_preprocessing = 0
    successful_parsing = 0
    successful_embeddings = 0
    
    for entry in example_data:
        exam_name = entry.get('EXAM_NAME', '')
        modality_code = entry.get('MODALITY_CODE', '')
        
        try:
            # Test preprocessing
            preprocessed = preprocess_exam_name(exam_name)
            successful_preprocessing += 1
            
            # Test parsing
            parsed = semantic_parser.parse_exam_name(preprocessed, modality_code)
            successful_parsing += 1
            
            # Test embedding
            clean_name = parsed.get('clean_name', preprocessed)
            embedding = nlp_processor.get_text_embedding(clean_name)
            if embedding is not None:
                successful_embeddings += 1
                
        except Exception:
            pass
    
    print(f"📊 Processing Success Rates:")
    print(f"   Preprocessing: {successful_preprocessing}/{len(example_data)} ({successful_preprocessing/len(example_data)*100:.1f}%)")
    print(f"   Semantic Parsing: {successful_parsing}/{len(example_data)} ({successful_parsing/len(example_data)*100:.1f}%)")
    print(f"   Embedding Generation: {successful_embeddings}/{len(example_data)} ({successful_embeddings/len(example_data)*100:.1f}%)")
    print()
    print("🔮 These processed inputs are now ready for:")
    print("   • Semantic similarity matching against NHS reference data")
    print("   • Real-time standardization via FAISS lookup")
    print("   • Clinical workflow integration")

if __name__ == "__main__":
    trace_input_processing()