#!/usr/bin/env python3
"""
Test validation batch decision processing logic without Flask dependencies.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def test_batch_validation_decisions():
    """Test the batch validation logic similar to the API endpoint."""
    
    try:
        from validation_cache_manager import ValidationCacheManager
        from r2_cache_manager import R2CacheManager
        from common.hash_keys import compute_request_hash_with_preimage
        
        print("Testing batch validation decisions processing...")
        
        # Create ValidationCacheManager
        r2_manager = R2CacheManager()
        validation_cache_manager = ValidationCacheManager(r2_manager)
        
        if not validation_cache_manager:
            print("❌ ValidationCacheManager not available")
            return False
        
        # Mock validation decisions similar to frontend data
        test_decisions = [
            {
                'mapping_id': 'test_mapping_001',
                'decision': 'approve',
                'notes': 'Mapping is correct and appropriate',
                'validation_author': 'test_validator',
                'original_mapping': {
                    'exam_name': 'CT Head without contrast',
                    'clean_name': 'CT of head without contrast',
                    'data_source': 'TEST_HOSPITAL',
                    'exam_code': 'CTH001',
                    'modality_code': 'CT',
                    'snomed': {'id': '12345'},
                    'confidence': 0.95
                },
                'data_source': 'TEST_HOSPITAL',
                'exam_code': 'CTH001',
                'exam_name': 'CT Head without contrast',
                'modality_code': 'CT'
            },
            {
                'mapping_id': 'test_mapping_002',
                'decision': 'reject',
                'notes': 'Incorrect mapping - should be abdomen not head',
                'validation_author': 'test_validator',
                'original_mapping': {
                    'exam_name': 'CT Abdomen',
                    'clean_name': 'CT of head', # Wrong!
                    'data_source': 'TEST_HOSPITAL',
                    'exam_code': 'CTA001',
                    'modality_code': 'CT',
                    'snomed': {'id': '67890'},
                    'confidence': 0.85
                },
                'data_source': 'TEST_HOSPITAL',
                'exam_code': 'CTA001',
                'exam_name': 'CT Abdomen',
                'modality_code': 'CT'
            }
        ]
        
        # Helper function from the API
        def _first_modality(val):
            if isinstance(val, list) and val:
                return val[0]
            return val

        def _compute_request_hash(decision_obj):
            # Prefer explicit fields from decision; fall back to original_mapping when needed
            ds = decision_obj.get('data_source') or decision_obj.get('original_mapping', {}).get('data_source') or ''
            ex_code = decision_obj.get('exam_code') or decision_obj.get('original_mapping', {}).get('exam_code') or ''
            ex_name = decision_obj.get('exam_name') or decision_obj.get('original_mapping', {}).get('exam_name') or ''
            modality = (
                decision_obj.get('modality_code')
                or _first_modality(decision_obj.get('original_mapping', {}).get('modality_code'))
                or _first_modality(decision_obj.get('original_mapping', {}).get('modality'))
                or None
            )
            req_hash, _preimage = compute_request_hash_with_preimage(ds, ex_code, ex_name, modality)
            return req_hash, ds, ex_code, ex_name
        
        # Process decisions
        processed_count = 0
        approved_count = 0
        rejected_count = 0
        errors = []
        
        for item in test_decisions:
            try:
                decision = item.get('decision')
                timestamp = datetime.utcnow().isoformat() + 'Z'
                item['timestamp_reviewed'] = timestamp
                
                req_hash, ds, ex_code, ex_name = _compute_request_hash(item)
                print(f"Processing {decision} decision for {ex_name} (hash: {req_hash})")
                
                if decision == 'approve':
                    # Build the complete mapping result including decision metadata
                    mapping_result = item.get('original_mapping', {}).copy()
                    mapping_result.update({
                        'validation_notes': item.get('notes', ''),
                        'approved_at': item.get('timestamp_reviewed'),
                        'validation_author': item.get('validation_author', ''),
                        'decision_metadata': {
                            'data_source': ds,
                            'exam_code': ex_code,
                            'exam_name': ex_name
                        }
                    })
                    
                    preimage = f"{ds}|{ex_code}|{ex_name}|{item.get('modality_code', '')}"
                    success = validation_cache_manager.add_approved(req_hash, mapping_result, preimage)
                    
                    if success:
                        print(f"✅ Added approved mapping to cache: {req_hash}")
                        approved_count += 1
                    else:
                        errors.append(f"Failed to save approved mapping for {item.get('mapping_id')}")
                        
                elif decision == 'reject':
                    reason = item.get('notes', 'No reason provided')
                    preimage = f"{ds}|{ex_code}|{ex_name}|{item.get('modality_code', '')}"
                    
                    success = validation_cache_manager.add_rejected(req_hash, reason, preimage)
                    
                    if success:
                        print(f"✅ Added rejected mapping to cache: {req_hash}")
                        rejected_count += 1
                    else:
                        errors.append(f"Failed to save rejected mapping for {item.get('mapping_id')}")
                
                processed_count += 1
                        
            except Exception as e:
                errors.append(f"Failed to process decision for {item.get('mapping_id')}: {e}")
                print(f"❌ Error processing {item.get('mapping_id')}: {e}")
        
        print(f"\n📊 Results:")
        print(f"  Processed: {processed_count}")
        print(f"  Approved: {approved_count}")
        print(f"  Rejected: {rejected_count}")
        print(f"  Errors: {len(errors)}")
        
        if errors:
            print("❌ Errors:")
            for error in errors:
                print(f"  - {error}")
        
        # Check cache files
        print(f"\n📁 Checking cache files:")
        cache_files = [
            "../validation/validation/approved_mappings_cache.json",
            "../validation/validation/rejected_mappings_cache.json"
        ]
        
        for cache_file in cache_files:
            path = Path(cache_file)
            if path.exists():
                with open(path, 'r') as f:
                    data = json.load(f)
                entry_count = len(data.get('entries', {}))
                print(f"  {cache_file}: {entry_count} entries")
                if entry_count > 0:
                    print(f"    Sample entries: {list(data['entries'].keys())[:3]}")
            else:
                print(f"  {cache_file}: Not found")
        
        return len(errors) == 0
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing Batch Validation Decisions")
    print("=" * 50)
    
    # Change to backend directory for proper path resolution
    original_cwd = Path.cwd()
    backend_dir = Path(__file__).parent / "backend"
    
    import os
    os.chdir(backend_dir)
    print(f"Working directory: {Path.cwd()}")
    
    try:
        success = test_batch_validation_decisions()
        
        if success:
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Some tests failed!")
    finally:
        os.chdir(original_cwd)