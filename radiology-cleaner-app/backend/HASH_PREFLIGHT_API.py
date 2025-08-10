#!/usr/bin/env python3
"""
API Documentation for Hash-Based Preflight Skipping

This script demonstrates the new API contract for the enhanced parse_enhanced endpoint
with hash-based preflight skipping and validation caches.
"""

import json


def demonstrate_api_contract():
    """Demonstrate the API request/response contract."""
    
    print("🔗 Hash-Based Preflight Skipping API Contract")
    print("=" * 60)
    
    print("\n📝 REQUEST FORMAT (unchanged):")
    request_example = {
        "exam_name": "CT CHEST WITHOUT CONTRAST",       # Required
        "modality_code": "CT",                          # Optional  
        "data_source": "PACS_MAIN",                    # Optional
        "exam_code": "CT001",                           # Optional
        "model": "retriever",                           # Optional (default: retriever)
        "reranker": "medcpt",                          # Optional (default: medcpt)
        "debug": False                                  # Optional (default: false)
    }
    print(json.dumps(request_example, indent=2))
    
    print("\n📋 RESPONSE FORMATS:")
    
    print("\n1️⃣ APPROVED CACHE HIT (preflight skip):")
    approved_response = {
        "clean_name": "Computed tomography of chest without contrast",
        "snomed_id": "169069000", 
        "snomed_fsn": "Computed tomography of chest without contrast",
        "components": {
            "confidence": 0.95,  # ⚠️ PRESERVED unchanged from cache
            "anatomy_score": 0.98,
            "modality_score": 1.0
        },
        "cached_skip": True,     # 🆕 NEW: Indicates cache hit
        "cache_type": "approved", # 🆕 NEW: Cache type
        "request_hash": "a1b2c3...", # 🆕 NEW: Request hash
        "metadata": {
            "processing_time_ms": 5,  # Fast due to cache hit
            "model_used": "retriever",
            "reranker_used": "medcpt", 
            "preflight_skipped": True  # 🆕 NEW: Skipped flag
        }
    }
    print(json.dumps(approved_response, indent=2))
    
    print("\n2️⃣ REJECTED CACHE HIT (strict skip):")
    rejected_response = {
        "error": "PREFLIGHT_REJECTED",
        "message": "Previously rejected: Invalid exam name",
        "exam_name": "INVALID EXAM NAME",
        "cached_skip": True,     # 🆕 NEW: Indicates cache hit  
        "cache_type": "rejected", # 🆕 NEW: Cache type
        "request_hash": "d4e5f6...", # 🆕 NEW: Request hash
        "metadata": {
            "processing_time_ms": 3,  # Very fast rejection
            "model_used": "retriever",
            "reranker_used": "medcpt",
            "preflight_skipped": True  # 🆕 NEW: Skipped flag
        }
    }
    print(json.dumps(rejected_response, indent=2))
    
    print("\n3️⃣ NORMAL PROCESSING (cache miss):")
    normal_response = {
        "clean_name": "MRI brain with gadolinium",
        "snomed_id": "241615005",
        "snomed_fsn": "Magnetic resonance imaging of brain with contrast",
        "components": {
            "confidence": 0.87,  # Normal confidence from processing
            "anatomy_score": 0.92,
            "modality_score": 0.95
        },
        "cached_skip": False,    # 🆕 NEW: Indicates no cache hit
        "cache_type": None,      # 🆕 NEW: No cache type
        "request_hash": "g7h8i9...", # 🆕 NEW: Request hash
        "metadata": {
            "processing_time_ms": 1250,  # Normal processing time
            "model_used": "retriever",
            "reranker_used": "medcpt",
            "preflight_skipped": False    # 🆕 NEW: Not skipped
        }
    }
    print(json.dumps(normal_response, indent=2))
    
    print("\n🔑 KEY FEATURES:")
    features = [
        "✅ Deterministic SHA-256 hashing of (data_source, exam_code, exam_name, modality_code)",
        "✅ Strict skipping for previously rejected hashes",  
        "✅ Confidence preservation for approved cache hits",
        "✅ Transparent cache flags on all responses",
        "✅ R2-backed validation caches (greenfield)",
        "✅ Unicode normalization and case-insensitive hashing",
        "✅ Special character escaping (| → %7C)",
        "✅ Graceful fallback when R2 unavailable"
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    print("\n📊 HASH COMPUTATION EXAMPLE:")
    print("Input: ds='PACS', ec='CT001', en='CT CHEST', mc='CT'")
    print("Preimage: v1|ds:pacs|ec:ct001|en:ct chest|mc:ct")
    print("Hash: SHA-256(UTF-8(preimage)) = a1b2c3d4e5f6...")
    
    print("\n🎯 BACKWARD COMPATIBILITY:")
    print("  ✅ Existing API clients work unchanged")
    print("  ✅ All responses include new optional fields")
    print("  ✅ No breaking changes to request format")
    print("  ✅ Error responses maintain existing structure")


def demonstrate_hash_examples():
    """Show hash computation examples."""
    print("\n\n🧮 Hash Computation Examples")
    print("=" * 60)
    
    examples = [
        ("Standard request", "PACS", "CT001", "CT CHEST", "CT"),
        ("Missing fields", None, None, "X-RAY CHEST", "XR"), 
        ("Special chars", "SYS|TEM", "CT|001", "CT|CHEST", "CT"),
        ("Case variations", "pacs", "ct001", "ct chest", "ct"),
    ]
    
    from common.hash_keys import compute_request_hash_with_preimage
    
    for desc, ds, ec, en, mc in examples:
        hash_hex, preimage = compute_request_hash_with_preimage(ds, ec, en, mc)
        print(f"\n{desc}:")
        print(f"  Input: ds='{ds}', ec='{ec}', en='{en}', mc='{mc}'")
        print(f"  Preimage: {preimage}")
        print(f"  Hash: {hash_hex}")


if __name__ == "__main__":
    demonstrate_api_contract()
    
    # Only run hash examples if modules are available
    try:
        import sys
        import os
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, backend_dir)
        demonstrate_hash_examples()
    except ImportError:
        print("\n⚠️ Hash computation examples skipped (modules not available)")
    
    print("\n🎉 API contract demonstration complete!")