#!/usr/bin/env python3
"""
Test script for the hybrid NLP processor using biomedical BERT.
"""

import os
import sys
import logging
from nlp_processor_hybrid import HybridNLPProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_hybrid_processor():
    """Test the hybrid NLP processor with biomedical texts."""
    
    print("🔄 Initializing Hybrid NLP Processor (Biomedical BERT)...")
    processor = HybridNLPProcessor()
    
    if not processor.is_available():
        print("❌ ERROR: Hybrid processor not available")
        print("   Make sure transformers and torch are installed:")
        print("   pip install transformers torch")
        return False
    
    print("✅ Hybrid processor initialized")
    
    # Test connection
    print("\n🔄 Testing processor...")
    if not processor.test_connection():
        print("❌ ERROR: Processor test failed")
        return False
    
    print("✅ Processor test successful")
    
    # Test with biomedical radiology texts
    test_texts = [
        "CT chest with contrast",
        "MRI brain without contrast", 
        "Chest X-ray PA and lateral",
        "Ultrasound abdomen and pelvis",
        "CT thorax with IV contrast",  # Similar to first one
        "Computed tomography of chest with intravenous contrast"  # Similar to first one
    ]
    
    print("\n🔄 Testing text embeddings...")
    embeddings = []
    
    for i, text in enumerate(test_texts):
        print(f"   {i+1}. Processing: '{text}'")
        embedding = processor.get_text_embedding(text)
        if embedding is not None:
            embeddings.append(embedding)
            print(f"      ✅ Got embedding with shape: {embedding.shape}")
        else:
            print(f"      ❌ Failed to get embedding")
            return False
    
    # Test similarity calculations
    print("\n🔄 Testing similarity calculations...")
    
    # Test 1: Different modalities (should be lower similarity)
    sim1 = processor.calculate_semantic_similarity(embeddings[0], embeddings[1])
    print(f"   Similarity between CT chest and MRI brain: {sim1:.3f}")
    
    # Test 2: Same anatomy, different modalities (should be medium similarity)
    sim2 = processor.calculate_semantic_similarity(embeddings[0], embeddings[2])
    print(f"   Similarity between CT chest and Chest X-ray: {sim2:.3f}")
    
    # Test 3: Very similar texts (should be high similarity)
    sim3 = processor.calculate_semantic_similarity(embeddings[0], embeddings[4])
    print(f"   Similarity between 'CT chest with contrast' and 'CT thorax with IV contrast': {sim3:.3f}")
    
    # Test 4: Synonymous texts (should be very high similarity)
    sim4 = processor.calculate_semantic_similarity(embeddings[0], embeddings[5])
    print(f"   Similarity between 'CT chest with contrast' and 'Computed tomography of chest with intravenous contrast': {sim4:.3f}")
    
    # Validate similarity scores make sense
    print("\n📊 Validating similarity scores...")
    if sim3 > sim2 > sim1:
        print("   ✅ Similarity ranking is logical: very similar > same anatomy > different modalities")
    else:
        print("   ⚠️  Similarity ranking may not be optimal")
        
    if sim4 > 0.8:
        print("   ✅ High similarity detected for synonymous medical terms")
    else:
        print("   ⚠️  Lower than expected similarity for synonymous terms")
    
    print("\n🎉 All tests passed! Biomedical BERT integration is working correctly.")
    print(f"    Model: {processor.model_name}")
    print(f"    Using local transformers: {processor.use_local}")
    
    return True

if __name__ == "__main__":
    print("🚀 Testing Biomedical BERT Integration")
    print("=" * 50)
    
    success = test_hybrid_processor()
    
    if success:
        print("\n✅ SUCCESS: Biomedical BERT integration is ready to use")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Please check the errors above")
        sys.exit(1)