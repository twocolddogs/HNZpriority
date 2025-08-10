#!/usr/bin/env python3
"""
Test script for preflight checking integration.
"""

import sys
import os
import json

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from common.hash_keys import compute_request_hash_with_preimage
from validation_cache_manager import ValidationCacheManager


def test_preflight_logic():
    """Test the preflight checking logic."""
    print("Testing preflight checking logic...")
    
    # Test hash computation for typical request
    data_source = "TEST_SYSTEM"
    exam_code = "CT001"
    exam_name = "CT CHEST WITHOUT CONTRAST"
    modality_code = "CT"
    
    hash_hex, preimage = compute_request_hash_with_preimage(data_source, exam_code, exam_name, modality_code)
    
    print(f"Test request:")
    print(f"  data_source: {data_source}")
    print(f"  exam_code: {exam_code}")
    print(f"  exam_name: {exam_name}")
    print(f"  modality_code: {modality_code}")
    print(f"Generated hash: {hash_hex}")
    print(f"Generated preimage: {preimage}")
    
    # Test cache manager
    cache_manager = ValidationCacheManager()
    print(f"Cache manager available: {cache_manager.is_available()}")
    
    # Test adding approved result to cache
    test_result = {
        "clean_name": "CT chest without contrast",
        "snomed_id": "169069000",
        "snomed_fsn": "Computed tomography of chest without contrast",
        "components": {
            "confidence": 0.92,
            "anatomy_score": 0.95,
            "modality_score": 1.0
        },
        "processing_metadata": {
            "model_used": "retriever",
            "reranker_used": "medcpt"
        }
    }
    
    # Simulate approval workflow
    success = cache_manager.add_approved(hash_hex, test_result, preimage)
    print(f"Added approved result to cache: {success}")
    
    # Test retrieval
    retrieved = cache_manager.check_approved(hash_hex)
    if retrieved:
        print("✅ Successfully retrieved approved result from cache")
        print(f"   Cached result: {retrieved['result']['clean_name']}")
        print(f"   Confidence preserved: {retrieved['result']['components']['confidence']}")
    else:
        print("⚠️ Could not retrieve from cache (expected without R2)")
    
    # Test rejection workflow
    hash_hex2, preimage2 = compute_request_hash_with_preimage(data_source, "INV999", "INVALID EXAM NAME", modality_code)
    success2 = cache_manager.add_rejected(hash_hex2, "Invalid or non-clinical exam name", preimage2)
    print(f"Added rejected result to cache: {success2}")
    
    rejected = cache_manager.check_rejected(hash_hex2)
    if rejected:
        print("✅ Successfully retrieved rejected result from cache")
        print(f"   Rejection reason: {rejected['reason']}")
    else:
        print("⚠️ Could not retrieve rejection from cache (expected without R2)")
    
    # Test cache stats
    stats = cache_manager.get_cache_stats()
    print(f"Final cache stats: {stats}")
    
    print("✅ Preflight checking logic test completed")


def simulate_api_request():
    """Simulate the new API request flow with preflight checking."""
    print("\n=== Simulating API Request Flow ===")
    
    # Simulate request payload like what parse_enhanced would receive
    request_data = {
        "exam_name": "CT ABDOMEN PELVIS WITH CONTRAST",
        "modality_code": "CT",
        "data_source": "PACS_MAIN",
        "exam_code": "CT123",
        "model": "retriever",
        "reranker": "medcpt",
        "debug": True
    }
    
    print(f"Simulated request: {json.dumps(request_data, indent=2)}")
    
    # Extract parameters like parse_enhanced does
    exam_name = request_data['exam_name']
    modality_code = request_data.get('modality_code')
    data_source = request_data.get('data_source')
    exam_code = request_data.get('exam_code')
    
    # Compute hash like the updated parse_enhanced does
    request_hash, preimage = compute_request_hash_with_preimage(data_source, exam_code, exam_name, modality_code)
    
    print(f"Request hash: {request_hash}")
    print(f"Preimage: {preimage}")
    
    # Check caches like parse_enhanced does
    cache_manager = ValidationCacheManager()
    cached_approved = cache_manager.check_approved(request_hash)
    cached_rejected = cache_manager.check_rejected(request_hash)
    
    if cached_rejected:
        print("❌ Would return rejected result from cache")
        response = {
            'error': 'PREFLIGHT_REJECTED',
            'message': cached_rejected['reason'],
            'exam_name': exam_name,
            'cached_skip': True,
            'cache_type': 'rejected',
            'request_hash': request_hash
        }
        print(f"Response: {json.dumps(response, indent=2)}")
    elif cached_approved:
        print("✅ Would return approved result from cache")
        response = cached_approved['result'].copy()
        response['cached_skip'] = True
        response['cache_type'] = 'approved'
        response['request_hash'] = request_hash
        print(f"Response: {json.dumps(response, indent=2)}")
    else:
        print("🔄 Would proceed to normal processing")
        response = {
            "message": "Would call process_exam_request() here",
            "cached_skip": False,
            "cache_type": None,
            "request_hash": request_hash
        }
        print(f"Response flags: {json.dumps(response, indent=2)}")


if __name__ == "__main__":
    test_preflight_logic()
    simulate_api_request()
    print("🎉 All preflight integration tests completed!")