#!/usr/bin/env python3
"""
Test script for hash_keys utility functions.
"""

import sys
import os

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from common.hash_keys import normalize_field, build_preimage, compute_request_hash, compute_request_hash_with_preimage


def test_normalize_field():
    """Test field normalization function."""
    print("Testing normalize_field...")
    
    # Test None handling
    assert normalize_field(None) == ""
    
    # Test basic normalization
    assert normalize_field("  HELLO WORLD  ") == "hello world"
    
    # Test whitespace collapse
    assert normalize_field("multiple   spaces    here") == "multiple spaces here"
    
    # Test Unicode normalization
    assert normalize_field("café") == "café"  # Should be consistent
    
    # Test empty string
    assert normalize_field("") == ""
    assert normalize_field("   ") == ""
    
    print("✅ normalize_field tests passed")


def test_build_preimage():
    """Test preimage construction."""
    print("Testing build_preimage...")
    
    # Test basic case
    preimage = build_preimage("SYSTEM1", "CT001", "CT CHEST", "CT")
    expected = "v1|ds:system1|ec:ct001|en:ct chest|mc:ct"
    assert preimage == expected, f"Expected: {expected}, Got: {preimage}"
    
    # Test with None values
    preimage = build_preimage(None, None, "CT CHEST", None)
    expected = "v1|ds:|ec:|en:ct chest|mc:"
    assert preimage == expected, f"Expected: {expected}, Got: {preimage}"
    
    # Test pipe escaping
    preimage = build_preimage("SYS|TEM", "CT|001", "CT|CHEST", "C|T")
    expected = "v1|ds:sys%7Ctem|ec:ct%7C001|en:ct%7Cchest|mc:c%7Ct"
    assert preimage == expected, f"Expected: {expected}, Got: {preimage}"
    
    print("✅ build_preimage tests passed")


def test_compute_request_hash():
    """Test hash computation."""
    print("Testing compute_request_hash...")
    
    # Test basic hash computation
    hash1 = compute_request_hash("SYSTEM1", "CT001", "CT CHEST", "CT")
    hash2 = compute_request_hash("system1", "ct001", "ct chest", "ct")  # Should be same due to normalization
    assert hash1 == hash2, "Normalized inputs should produce same hash"
    
    # Test hash consistency 
    hash_a = compute_request_hash("TEST", "ABC", "EXAM NAME", "MR")
    hash_b = compute_request_hash("TEST", "ABC", "EXAM NAME", "MR")
    assert hash_a == hash_b, "Same inputs should produce same hash"
    
    # Test hash differences
    hash_x = compute_request_hash("TEST", "ABC", "EXAM NAME", "MR")
    hash_y = compute_request_hash("TEST", "ABC", "DIFFERENT NAME", "MR")
    assert hash_x != hash_y, "Different inputs should produce different hashes"
    
    # Test hash format (should be 64 hex characters for SHA-256)
    hash_result = compute_request_hash("TEST", "ABC", "EXAM", "CT")
    assert len(hash_result) == 64, f"Hash should be 64 characters, got {len(hash_result)}"
    assert all(c in "0123456789abcdef" for c in hash_result), "Hash should be lowercase hex"
    
    print("✅ compute_request_hash tests passed")


def test_compute_request_hash_with_preimage():
    """Test hash with preimage computation."""
    print("Testing compute_request_hash_with_preimage...")
    
    hash_hex, preimage = compute_request_hash_with_preimage("SYS", "CODE", "NAME", "MOD")
    
    # Verify hash matches individual computation
    expected_hash = compute_request_hash("SYS", "CODE", "NAME", "MOD")
    assert hash_hex == expected_hash, "Hash should match individual computation"
    
    # Verify preimage format
    expected_preimage = "v1|ds:sys|ec:code|en:name|mc:mod"
    assert preimage == expected_preimage, f"Expected preimage: {expected_preimage}, Got: {preimage}"
    
    print("✅ compute_request_hash_with_preimage tests passed")


def demo_hashing():
    """Demonstrate the hashing functionality."""
    print("\n=== Hash Demo ===")
    
    test_cases = [
        ("PACS", "CT001", "CT CHEST WITHOUT CONTRAST", "CT"),
        ("RIS", "MR201", "MRI BRAIN WITH GADOLINIUM", "MR"),
        (None, None, "X-RAY CHEST PA", "XR"),
        ("SYS|TEM", "CODE|123", "EXAM|NAME", "MOD|AL"),
    ]
    
    for ds, ec, en, mc in test_cases:
        hash_hex, preimage = compute_request_hash_with_preimage(ds, ec, en, mc)
        print(f"Input: ds='{ds}', ec='{ec}', en='{en}', mc='{mc}'")
        print(f"Preimage: {preimage}")
        print(f"Hash: {hash_hex}")
        print()


if __name__ == "__main__":
    test_normalize_field()
    test_build_preimage()
    test_compute_request_hash()
    test_compute_request_hash_with_preimage()
    demo_hashing()
    
    print("🎉 All tests passed!")