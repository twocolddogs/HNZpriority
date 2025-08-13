#!/usr/bin/env python3
"""
Test script to verify the validation cache fix works properly.
"""

import json
import os
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent / "radiology-cleaner-app" / "backend"))

def test_validation_cache_manager():
    """Test ValidationCacheManager local file saving functionality."""
    print("Testing ValidationCacheManager local file saving...")
    
    try:
        from validation_cache_manager import ValidationCacheManager
        from r2_cache_manager import R2CacheManager
        
        # Create ValidationCacheManager without R2 to test local-only functionality
        print("Creating ValidationCacheManager...")
        r2_manager = R2CacheManager()
        cache_manager = ValidationCacheManager(r2_manager)
        
        # Test data
        test_hash = "test_hash_123"
        test_result = {
            "exam_name": "CT Head without contrast",
            "clean_name": "CT of head without contrast",
            "snomed": {"id": "123456"},
            "confidence": 0.95
        }
        test_preimage = "TEST|CT001|CT Head|CT"
        
        print(f"Adding test approved mapping with hash: {test_hash}")
        success = cache_manager.add_approved(test_hash, test_result, test_preimage)
        print(f"Add approved result: {success}")
        
        # Check if local file was updated
        possible_paths = [
            Path("radiology-cleaner-app/validation/validation/approved_mappings_cache.json"),
            Path("radiology-cleaner-app/validation/approved_mappings_cache.json")
        ]
        
        for path in possible_paths:
            if path.exists():
                print(f"Checking local cache file: {path}")
                with open(path, 'r') as f:
                    data = json.load(f)
                print(f"Cache file structure: {list(data.keys())}")
                if "entries" in data:
                    print(f"Number of entries: {len(data['entries'])}")
                    if test_hash in data['entries']:
                        print("✅ Test hash found in local cache!")
                        print(f"Entry data: {data['entries'][test_hash]}")
                    else:
                        print("❌ Test hash not found in local cache entries")
                        print(f"Available entries: {list(data['entries'].keys())}")
                else:
                    print("❌ No 'entries' key found in cache file")
                break
        else:
            print("❌ No local cache files found")
            
        return success
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_current_cache_state():
    """Check the current state of validation cache files."""
    print("\nChecking current validation cache files...")
    
    cache_files = [
        "radiology-cleaner-app/validation/validation/approved_mappings_cache.json",
        "radiology-cleaner-app/validation/validation/rejected_mappings_cache.json"
    ]
    
    for cache_file in cache_files:
        path = Path(cache_file)
        if path.exists():
            print(f"\n📁 {cache_file}:")
            with open(path, 'r') as f:
                data = json.load(f)
            print(f"  Structure: {list(data.keys())}")
            if "entries" in data:
                print(f"  Entry count: {len(data['entries'])}")
                if data['entries']:
                    print(f"  Sample entries: {list(data['entries'].keys())[:3]}")
                else:
                    print("  No entries found")
            if "meta" in data:
                print(f"  Last updated: {data['meta'].get('last_updated', 'Unknown')}")
        else:
            print(f"❌ {cache_file} not found")

if __name__ == "__main__":
    print("🧪 Testing Validation Cache Fix")
    print("=" * 50)
    
    # Check current state
    check_current_cache_state()
    
    # Test the ValidationCacheManager
    print("\n" + "=" * 50)
    test_result = test_validation_cache_manager()
    
    if test_result:
        print("\n✅ ValidationCacheManager test passed!")
    else:
        print("\n❌ ValidationCacheManager test failed!")
    
    # Check state after test
    print("\n" + "=" * 50)
    print("State after test:")
    check_current_cache_state()