#!/usr/bin/env python3
"""
Test script for the new API-based NLP processor.
Run this to verify Hugging Face API integration is working.
"""

import os
import sys
import logging
from nlp_processor_api import ApiNLPProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_api_processor():
    """Test the API-based NLP processor with sample radiology texts."""
    
    # Check environment variable
    token = os.environ.get('HUGGING_FACE_TOKEN')
    if not token:
        print("❌ ERROR: HUGGING_FACE_TOKEN environment variable not set")
        print("   Please set it with: export HUGGING_FACE_TOKEN=your_token_here")
        return False
    
    print("✅ HUGGING_FACE_TOKEN is set")
    
    # Initialize processor
    print("\n🔄 Initializing API NLP Processor...")
    processor = ApiNLPProcessor()
    
    if not processor.is_available():
        print("❌ ERROR: API processor not available")
        return False
    
    print("✅ API processor initialized")
    
    # Test connection
    print("\n🔄 Testing API connection...")
    if not processor.test_connection():
        print("❌ ERROR: API connection failed")
        return False
    
    print("✅ API connection successful")
    
    # Test with sample radiology texts
    test_texts = [
        "CT chest with contrast",
        "MRI brain without contrast",
        "Chest X-ray PA and lateral",
        "Ultrasound abdomen and pelvis"
    ]
    
    print("\n🔄 Testing text embeddings...")
    embeddings = []
    
    for text in test_texts:
        print(f"   Processing: '{text}'")
        embedding = processor.get_text_embedding(text)
        if embedding is not None:
            embeddings.append(embedding)
            print(f"   ✅ Got embedding with shape: {embedding.shape}")
        else:
            print(f"   ❌ Failed to get embedding")
            return False
    
    # Test similarity calculation
    print("\n🔄 Testing similarity calculation...")
    if len(embeddings) >= 2:
        similarity = processor.calculate_semantic_similarity(embeddings[0], embeddings[1])
        print(f"   Similarity between '{test_texts[0]}' and '{test_texts[1]}': {similarity:.3f}")
        
        # Test similar texts
        similar_texts = ["CT chest with contrast", "CT thorax with IV contrast"]
        emb1 = processor.get_text_embedding(similar_texts[0])
        emb2 = processor.get_text_embedding(similar_texts[1])
        
        if emb1 is not None and emb2 is not None:
            sim_score = processor.calculate_semantic_similarity(emb1, emb2)
            print(f"   Similarity between similar texts: {sim_score:.3f}")
            if sim_score > 0.7:
                print("   ✅ High similarity detected for related texts")
            else:
                print("   ⚠️  Lower than expected similarity for related texts")
        
    print("\n🎉 All tests passed! API integration is working correctly.")
    return True

if __name__ == "__main__":
    print("🚀 Testing Hugging Face API Integration")
    print("=" * 50)
    
    success = test_api_processor()
    
    if success:
        print("\n✅ SUCCESS: API integration is ready to use")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Please check the errors above")
        sys.exit(1)