"""
Validation cache manager for approved/rejected exam mappings.

This module manages validation caches stored in R2 that track:
- Previously approved exam mappings (hash -> result)  
- Previously rejected exam mappings (hash -> rejection reason)

Enables preflight skipping of already validated requests.
"""

import json
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
from r2_cache_manager import R2CacheManager
import hashlib

logger = logging.getLogger(__name__)


def get_validation_cache_version() -> str:
    """
    Get validation cache version based on validation_cache_manager.py file hash.
    This is more lightweight than the full cache versioning system and doesn't 
    require R2 config access.
    
    Returns:
        8-character validation cache version hash
    """
    try:
        # Get the hash of this file to detect changes in validation logic
        import os
        file_path = os.path.abspath(__file__)
        
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            hasher.update(f.read())
        
        # Also include nhs_lookup_engine.py since it handles cache normalization
        nhs_engine_path = os.path.join(os.path.dirname(file_path), 'nhs_lookup_engine.py')
        if os.path.exists(nhs_engine_path):
            with open(nhs_engine_path, 'rb') as f:
                hasher.update(f.read())
        
        # Return first 8 characters for consistency with main cache versioning
        return hasher.hexdigest()[:8]
        
    except Exception as e:
        logger.warning(f"Failed to calculate validation cache version: {e}")
        # Fallback to a static version that changes when code is updated
        return "fallback"


class ValidationCacheManager:
    """Manages validation caches for approved and rejected exam mappings."""
    
    def __init__(self, r2_cache_manager: Optional[R2CacheManager] = None):
        """
        Initialize validation cache manager.
        
        Args:
            r2_cache_manager: Optional R2 cache manager instance (creates new if None)
        """
        self.r2_manager = r2_cache_manager or R2CacheManager()
        self.approved_cache_key = "validation/approved_mappings_cache.json"
        self.rejected_cache_key = "validation/rejected_mappings_cache.json"
        
        # In-memory caches for performance
        self._approved_cache: Optional[Dict] = None
        self._rejected_cache: Optional[Dict] = None
        self._cache_loaded = False
    
    def is_available(self) -> bool:
        """Check if validation caching is available."""
        return self.r2_manager.is_available()
    
    def _load_caches(self) -> None:
        """Load both validation caches from R2 into memory."""
        if self._cache_loaded:
            return
        
        # Load approved cache (always try local files even if R2 not available)
        self._approved_cache = self._load_cache_file(self.approved_cache_key, "approved")
        
        # Load rejected cache  
        self._rejected_cache = self._load_cache_file(self.rejected_cache_key, "rejected")
        
        self._cache_loaded = True
        logger.info(f"Loaded validation caches: {len(self._approved_cache['entries'])} approved, {len(self._rejected_cache['entries'])} rejected")
    
    def reload_caches(self) -> Dict:
        """
        Force reload validation caches from R2, clearing any cached data.
        
        Returns:
            Dict with reload statistics
        """
        logger.info("Force reloading validation caches from R2...")
        
        # Clear existing caches and force reload
        old_approved_count = len(self._approved_cache['entries']) if self._approved_cache else 0
        old_rejected_count = len(self._rejected_cache['entries']) if self._rejected_cache else 0
        
        self._approved_cache = None
        self._rejected_cache = None
        self._cache_loaded = False
        
        # Reload from R2
        self._load_caches()
        
        new_approved_count = len(self._approved_cache['entries'])
        new_rejected_count = len(self._rejected_cache['entries'])
        
        result = {
            'status': 'success',
            'approved_count': new_approved_count,
            'rejected_count': new_rejected_count,
            'previous_approved_count': old_approved_count,
            'previous_rejected_count': old_rejected_count,
            'approved_delta': new_approved_count - old_approved_count,
            'rejected_delta': new_rejected_count - old_rejected_count,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Validation cache reload complete: approved={new_approved_count} (Δ{result['approved_delta']:+d}), rejected={new_rejected_count} (Δ{result['rejected_delta']:+d})")
        return result
    
    def _load_cache_file(self, cache_key: str, cache_type: str) -> Dict:
        """Load a single cache file from R2 ONLY - no local file usage."""
        current_version = get_validation_cache_version()
        cache_data = {
            "version": "v1", 
            "cache_version": current_version,
            "entries": {}
        }
        
        # Load from R2 if available (ignore local files completely)
        try:
            if self.r2_manager.client:
                response = self.r2_manager.client.get_object(
                    Bucket=self.r2_manager.bucket_name,
                    Key=cache_key
                )
                r2_cache_data = json.loads(response['Body'].read().decode('utf-8'))
                
                # Check cache version compatibility
                r2_cache_version = r2_cache_data.get('cache_version', 'unknown')
                if r2_cache_version != current_version:
                    logger.warning(f"Cache version mismatch for {cache_type}: R2={r2_cache_version}, current={current_version}. Using R2 data but marking as potentially stale.")
                    # Still use the data but log the version mismatch
                
                logger.info(f"Loaded {cache_type} cache from R2: {len(r2_cache_data.get('entries', {}))} entries (version: {r2_cache_version})")
                return r2_cache_data
        except Exception as e:
            if "NoSuchKey" in str(e) or "404" in str(e):
                logger.info(f"No existing {cache_type} cache found in R2")
            else:
                logger.warning(f"Failed to load {cache_type} cache from R2: {e}")
        
        # Return empty cache structure if nothing found in R2
        logger.info(f"No {cache_type} cache found in R2, creating empty cache with version {current_version}")
        return cache_data
    
    def _save_cache_file(self, cache_data: Dict, cache_key: str, cache_type: str) -> bool:
        """Save a cache file to R2 ONLY - no local file usage."""
        # Ensure cache data includes current version
        current_version = get_validation_cache_version()
        cache_data['cache_version'] = current_version
        cache_data['last_updated'] = datetime.utcnow().isoformat() + "Z"
        
        # Save to R2 if available
        if self.is_available():
            try:
                cache_json = json.dumps(cache_data, indent=2, sort_keys=True)
                cache_bytes = cache_json.encode('utf-8')
                
                r2_success = self.r2_manager.upload_object(
                    object_key=cache_key,
                    data=cache_bytes,
                    content_type='application/json'
                )
                
                if r2_success:
                    logger.info(f"Saved {cache_type} cache to R2: {len(cache_data.get('entries', {}))} entries (version: {current_version})")
                    return True
                else:
                    logger.error(f"Failed to save {cache_type} cache to R2")
                    return False
                    
            except Exception as e:
                logger.error(f"Error saving {cache_type} cache to R2: {e}")
                return False
        else:
            logger.error(f"R2 not available - cannot save {cache_type} cache")
            return False
    
    def check_approved(self, request_hash: str) -> Optional[Dict]:
        """
        Check if a request hash has been previously approved.
        
        Args:
            request_hash: The SHA-256 hash of the request
            
        Returns:
            The cached result if found, None otherwise
        """
        self._load_caches()
        cached_entry = self._approved_cache['entries'].get(request_hash)
        
        if cached_entry is None:
            return None
            
        # Handle legacy format from validation system: {mapping_data, validation_notes, approved_at, ...}
        if 'mapping_data' in cached_entry and 'result' not in cached_entry:
            logger.debug(f"Converting legacy cache format for hash: {request_hash}")
            return {
                'result': cached_entry['mapping_data'],
                'cached_at': cached_entry.get('approved_at', datetime.utcnow().isoformat() + "Z"),
                'preimage': f"legacy_validation_entry_{request_hash[:8]}",
                'validation_notes': cached_entry.get('validation_notes', ''),
                'legacy_format': True
            }
        
        # Return new format as-is
        return cached_entry
    
    def check_rejected(self, request_hash: str) -> Optional[Dict]:
        """
        Check if a request hash has been previously rejected.
        
        Args:
            request_hash: The SHA-256 hash of the request
            
        Returns:
            The rejection info if found, None otherwise
        """
        self._load_caches()
        cached_entry = self._rejected_cache['entries'].get(request_hash)
        
        if cached_entry is None:
            return None
            
        # Handle legacy format from validation system: {mapping_data, rejection_reason, rejected_at, ...}
        if 'rejection_reason' in cached_entry and 'reason' not in cached_entry:
            logger.debug(f"Converting legacy rejected cache format for hash: {request_hash}")
            return {
                'reason': cached_entry['rejection_reason'],
                'cached_at': cached_entry.get('rejected_at', datetime.utcnow().isoformat() + "Z"),
                'preimage': f"legacy_validation_entry_{request_hash[:8]}",
                'legacy_format': True
            }
        
        # Return new format as-is
        return cached_entry
    
    def add_approved(self, request_hash: str, result: Dict, preimage: str) -> bool:
        """
        Add an approved mapping to the cache.
        
        Args:
            request_hash: The SHA-256 hash of the request
            result: The approved result to cache
            preimage: The original preimage for debugging
            
        Returns:
            True if successfully saved, False otherwise
        """
        self._load_caches()
        
        # Extract validation_author from result for consistent top-level storage
        validation_author = result.get('validation_author', '')
        
        cache_entry = {
            "mapping_data": result,
            "cached_at": datetime.utcnow().isoformat() + "Z",
            "preimage": preimage,
            "validation_author": validation_author
        }
        
        self._approved_cache['entries'][request_hash] = cache_entry
        return self._save_cache_file(self._approved_cache, self.approved_cache_key, "approved")
    
    def add_rejected(self, request_hash: str, reason: str, preimage: str, validation_author: str = '') -> bool:
        """
        Add a rejected mapping to the cache.
        
        Args:
            request_hash: The SHA-256 hash of the request
            reason: The rejection reason
            preimage: The original preimage for debugging
            validation_author: The author who made the validation decision
            
        Returns:
            True if successfully saved, False otherwise
        """
        self._load_caches()
        
        cache_entry = {
            "reason": reason,
            "cached_at": datetime.utcnow().isoformat() + "Z", 
            "preimage": preimage,
            "validation_author": validation_author
        }
        
        self._rejected_cache['entries'][request_hash] = cache_entry
        return self._save_cache_file(self._rejected_cache, self.rejected_cache_key, "rejected")
    
    def get_cache_stats(self) -> Dict:
        """Get statistics about the validation caches."""
        self._load_caches()
        
        approved_entries = self._approved_cache['entries']
        rejected_entries = self._rejected_cache['entries']
        
        # Count legacy format entries
        approved_legacy = sum(1 for entry in approved_entries.values() 
                            if 'mapping_data' in entry and 'result' not in entry)
        rejected_legacy = sum(1 for entry in rejected_entries.values() 
                            if 'rejection_reason' in entry and 'reason' not in entry)
        
        return {
            "approved_count": len(approved_entries),
            "rejected_count": len(rejected_entries),
            "total_cached": len(approved_entries) + len(rejected_entries),
            "legacy_format_approved": approved_legacy,
            "legacy_format_rejected": rejected_legacy,
            "new_format_approved": len(approved_entries) - approved_legacy,
            "new_format_rejected": len(rejected_entries) - rejected_legacy,
            "r2_available": self.is_available(),
            "cache_version": self._approved_cache.get('version', 'unknown'),
            "cache_code_version": self._approved_cache.get('cache_version', 'unknown'),
            "current_code_version": get_validation_cache_version()
        }
    
    def get_detailed_cache_info(self) -> Dict:
        """Get detailed information about cache entries for debugging."""
        self._load_caches()
        
        sample_approved = {}
        sample_rejected = {}
        
        # Get a few sample entries for inspection
        for hash_key, entry in list(self._approved_cache['entries'].items())[:3]:
            sample_approved[hash_key] = {
                "has_mapping_data": "mapping_data" in entry,
                "has_result": "result" in entry, 
                "has_validation_notes": "validation_notes" in entry,
                "has_approved_at": "approved_at" in entry,
                "entry_keys": list(entry.keys())
            }
            
        for hash_key, entry in list(self._rejected_cache['entries'].items())[:3]:
            sample_rejected[hash_key] = {
                "has_rejection_reason": "rejection_reason" in entry,
                "has_reason": "reason" in entry,
                "has_rejected_at": "rejected_at" in entry, 
                "entry_keys": list(entry.keys())
            }
        
        return {
            "sample_approved_entries": sample_approved,
            "sample_rejected_entries": sample_rejected,
            "cache_stats": self.get_cache_stats()
        }