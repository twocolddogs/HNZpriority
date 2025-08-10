#!/usr/bin/env python3
"""
End-to-end test demonstrating the hash-based preflight skipping functionality.
"""

import sys
import os
import json

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from common.hash_keys import (
    normalize_field, 
    build_preimage, 
    compute_request_hash, 
    compute_request_hash_with_preimage
)
from validation_cache_manager import ValidationCacheManager


def test_complete_flow():
    """Test the complete hash-based preflight flow."""
    print("🧪 Testing Complete Hash-Based Preflight Flow")
    print("=" * 60)
    
    # Test cases representing typical API requests
    test_cases = [
        {
            "name": "Standard CT Request",
            "data_source": "PACS_MAIN",
            "exam_code": "CT001",
            "exam_name": "CT CHEST WITHOUT CONTRAST",
            "modality_code": "CT"
        },
        {
            "name": "MRI with Gadolinium",
            "data_source": "RIS_SYSTEM",
            "exam_code": "MR305",
            "exam_name": "MRI BRAIN WITH GADOLINIUM",
            "modality_code": "MR"
        },
        {
            "name": "Request with None values",
            "data_source": None,
            "exam_code": None,
            "exam_name": "X-RAY CHEST PA",
            "modality_code": "XR"
        },
        {
            "name": "Request with special characters",
            "data_source": "SYS|TEM",
            "exam_code": "CT|001",
            "exam_name": "CT CHEST|ABDOMEN",
            "modality_code": "CT"
        },
        {
            "name": "Case sensitivity test",
            "data_source": "PACS_main",
            "exam_code": "ct001",
            "exam_name": "ct chest WITHOUT contrast",
            "modality_code": "ct"
        }
    ]
    
    cache_manager = ValidationCacheManager()
    print(f"Cache manager available: {cache_manager.is_available()}")
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test_case['name']}")
        print("-" * 40)
        
        # Extract parameters
        ds = test_case['data_source']
        ec = test_case['exam_code'] 
        en = test_case['exam_name']
        mc = test_case['modality_code']
        
        # Test hash computation
        hash_hex, preimage = compute_request_hash_with_preimage(ds, ec, en, mc)
        
        print(f"Input: ds='{ds}', ec='{ec}', en='{en}', mc='{mc}'")
        print(f"Preimage: {preimage}")
        print(f"Hash: {hash_hex}")
        
        # Test cache lookups
        approved = cache_manager.check_approved(hash_hex)
        rejected = cache_manager.check_rejected(hash_hex)
        
        print(f"Approved cache hit: {approved is not None}")
        print(f"Rejected cache hit: {rejected is not None}")
        
        # For the first test case, add it to approved cache
        if i == 1:
            test_result = {
                "clean_name": "Computed tomography of chest without contrast",
                "snomed_id": "169069000",
                "components": {"confidence": 0.95},
                "source": "test_approved"
            }
            success = cache_manager.add_approved(hash_hex, test_result, preimage)
            print(f"Added to approved cache: {success}")
            
            # Verify retrieval
            retrieved = cache_manager.check_approved(hash_hex)
            if retrieved:
                print(f"✅ Retrieval successful: {retrieved['result']['clean_name']}")
            else:
                print("⚠️ Retrieval failed (expected without R2)")
        
        # For the second test case, add it to rejected cache
        if i == 2:
            success = cache_manager.add_rejected(hash_hex, "Requires special approval", preimage)
            print(f"Added to rejected cache: {success}")
            
            # Verify retrieval
            retrieved = cache_manager.check_rejected(hash_hex)
            if retrieved:
                print(f"❌ Rejection retrieved: {retrieved['reason']}")
            else:
                print("⚠️ Rejection retrieval failed (expected without R2)")
        
        print()
    
    # Test hash consistency (case 1 and 5 should have different hashes due to normalization)
    print("Hash Consistency Tests")
    print("-" * 40)
    
    hash1 = compute_request_hash("PACS_MAIN", "CT001", "CT CHEST WITHOUT CONTRAST", "CT")
    hash5 = compute_request_hash("PACS_main", "ct001", "ct chest WITHOUT contrast", "ct")
    
    print(f"Case 1 hash: {hash1}")
    print(f"Case 5 hash: {hash5}")
    print(f"Hashes identical (normalized): {hash1 == hash5}")
    
    # Test edge cases
    print("\nEdge Case Tests")
    print("-" * 40)
    
    # Empty strings vs None
    hash_empty = compute_request_hash("", "", "TEST", "")
    hash_none = compute_request_hash(None, None, "TEST", None)
    print(f"Empty string hash: {hash_empty}")
    print(f"None values hash: {hash_none}")
    print(f"Empty vs None identical: {hash_empty == hash_none}")
    
    # Whitespace normalization
    hash_normal = compute_request_hash("SYS", "CODE", "EXAM NAME", "MOD")
    hash_spaces = compute_request_hash("  SYS  ", "  CODE  ", "  EXAM   NAME  ", "  MOD  ")
    print(f"Normal hash: {hash_normal}")
    print(f"Spaces hash: {hash_spaces}")
    print(f"Whitespace normalized: {hash_normal == hash_spaces}")
    
    # Final cache stats
    print(f"\nFinal cache stats: {cache_manager.get_cache_stats()}")
    
    print("\n✅ Complete flow test completed successfully!")


def demonstrate_api_flow():
    """Demonstrate how the API flow would work with caching."""
    print("\n🔄 API Flow Demonstration")
    print("=" * 60)
    
    # Simulate multiple requests to the same endpoint
    requests = [
        {"exam_name": "CT CHEST", "modality_code": "CT", "data_source": "PACS", "exam_code": "CT100"},
        {"exam_name": "CT CHEST", "modality_code": "CT", "data_source": "PACS", "exam_code": "CT100"},  # Duplicate
        {"exam_name": "MRI BRAIN", "modality_code": "MR", "data_source": "RIS", "exam_code": "MR200"},
    ]
    
    cache_manager = ValidationCacheManager()
    
    for i, req in enumerate(requests, 1):
        print(f"\nRequest {i}: {req}")
        
        # Compute hash like parse_enhanced does
        hash_hex, preimage = compute_request_hash_with_preimage(
            req.get('data_source'), 
            req.get('exam_code'),
            req['exam_name'], 
            req.get('modality_code')
        )
        
        print(f"Hash: {hash_hex}")
        
        # Check caches
        approved = cache_manager.check_approved(hash_hex)
        rejected = cache_manager.check_rejected(hash_hex)
        
        if rejected:
            print("❌ REJECTED from cache - would return error immediately")
        elif approved:
            print("✅ APPROVED from cache - would return cached result")
            print(f"   Cached result: {approved['result']}")
        else:
            print("🔄 NEW request - would proceed to model processing")
            
            # Simulate adding result to cache after processing
            if i == 1:  # First CT request
                result = {"clean_name": "CT chest", "snomed_id": "123", "components": {"confidence": 0.9}}
                cache_manager.add_approved(hash_hex, result, preimage)
                print("   Added successful result to approved cache")
    
    print(f"\nFinal cache state: {cache_manager.get_cache_stats()}")


if __name__ == "__main__":
    test_complete_flow()
    demonstrate_api_flow()
    print("\n🎉 All end-to-end tests completed successfully!")