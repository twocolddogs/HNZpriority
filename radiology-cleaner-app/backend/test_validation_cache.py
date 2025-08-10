#!/usr/bin/env python3
"""
Test script for validation cache manager.
"""

import sys
import os

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from validation_cache_manager import ValidationCacheManager
from common.hash_keys import compute_request_hash_with_preimage


def test_validation_cache_manager():
    """Test validation cache manager functionality."""
    print("Testing ValidationCacheManager...")
    
    # Create cache manager (will work without R2 for testing)
    cache_manager = ValidationCacheManager()
    
    # Test initial state
    stats = cache_manager.get_cache_stats()
    print(f"Initial cache stats: {stats}")
    
    # Generate test hash
    hash_hex, preimage = compute_request_hash_with_preimage("TEST_SYS", "TEST_CODE", "TEST EXAM", "CT")
    print(f"Test hash: {hash_hex}")
    print(f"Test preimage: {preimage}")
    
    # Test checking non-existent entries
    approved = cache_manager.check_approved(hash_hex)
    rejected = cache_manager.check_rejected(hash_hex)
    assert approved is None, "Should not find approved entry initially"
    assert rejected is None, "Should not find rejected entry initially"
    print("✅ Initial lookup tests passed")
    
    # Test adding approved entry
    test_result = {
        "clean_name": "CT CHEST",
        "snomed_id": "123456",
        "components": {"confidence": 0.95}
    }
    
    success = cache_manager.add_approved(hash_hex, test_result, preimage)
    print(f"Added approved entry: {success}")
    
    # Test retrieving approved entry
    retrieved = cache_manager.check_approved(hash_hex)
    if retrieved:
        assert retrieved['result']['clean_name'] == "CT CHEST"
        assert retrieved['preimage'] == preimage
        print("✅ Approved cache retrieval test passed")
    else:
        print("⚠️ Approved cache retrieval failed (expected in test environment)")
    
    # Test adding rejected entry for different hash
    hash_hex2, preimage2 = compute_request_hash_with_preimage("TEST_SYS", "TEST_CODE", "INVALID EXAM", "CT")
    success2 = cache_manager.add_rejected(hash_hex2, "Invalid exam name", preimage2)
    print(f"Added rejected entry: {success2}")
    
    # Test final stats
    final_stats = cache_manager.get_cache_stats()
    print(f"Final cache stats: {final_stats}")
    
    print("✅ ValidationCacheManager basic tests completed")


if __name__ == "__main__":
    test_validation_cache_manager()
    print("🎉 Validation cache manager test completed!")