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
from r2_cache_manager import R2CacheManager

logger = logging.getLogger(__name__)


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
            
        if not self.is_available():
            logger.warning("Validation cache manager not available - R2 not configured")
            self._approved_cache = {"version": "v1", "entries": {}}
            self._rejected_cache = {"version": "v1", "entries": {}}
            self._cache_loaded = True
            return
        
        # Load approved cache
        self._approved_cache = self._load_cache_file(self.approved_cache_key, "approved")
        
        # Load rejected cache  
        self._rejected_cache = self._load_cache_file(self.rejected_cache_key, "rejected")
        
        self._cache_loaded = True
        logger.info(f"Loaded validation caches: {len(self._approved_cache['entries'])} approved, {len(self._rejected_cache['entries'])} rejected")
    
    def _load_cache_file(self, cache_key: str, cache_type: str) -> Dict:
        """Load a single cache file from R2."""
        try:
            if self.r2_manager.client:
                response = self.r2_manager.client.get_object(
                    Bucket=self.r2_manager.bucket_name,
                    Key=cache_key
                )
                cache_data = json.loads(response['Body'].read().decode('utf-8'))
                logger.info(f"Loaded {cache_type} cache from R2: {len(cache_data.get('entries', {}))} entries")
                return cache_data
        except Exception as e:
            if "NoSuchKey" in str(e) or "404" in str(e):
                logger.info(f"No existing {cache_type} cache found in R2, creating new")
            else:
                logger.warning(f"Failed to load {cache_type} cache from R2: {e}")
        
        # Return empty cache structure
        return {"version": "v1", "entries": {}}
    
    def _save_cache_file(self, cache_data: Dict, cache_key: str, cache_type: str) -> bool:
        """Save a cache file to R2."""
        if not self.is_available():
            logger.warning(f"Cannot save {cache_type} cache - R2 not available")
            return False
            
        try:
            cache_json = json.dumps(cache_data, indent=2, sort_keys=True)
            cache_bytes = cache_json.encode('utf-8')
            
            success = self.r2_manager.upload_object(
                object_key=cache_key,
                data=cache_bytes,
                content_type='application/json'
            )
            
            if success:
                logger.info(f"Saved {cache_type} cache to R2: {len(cache_data.get('entries', {}))} entries")
            else:
                logger.error(f"Failed to save {cache_type} cache to R2")
                
            return success
            
        except Exception as e:
            logger.error(f"Error saving {cache_type} cache: {e}")
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
        return self._approved_cache['entries'].get(request_hash)
    
    def check_rejected(self, request_hash: str) -> Optional[Dict]:
        """
        Check if a request hash has been previously rejected.
        
        Args:
            request_hash: The SHA-256 hash of the request
            
        Returns:
            The rejection info if found, None otherwise
        """
        self._load_caches()
        return self._rejected_cache['entries'].get(request_hash)
    
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
        
        cache_entry = {
            "mapping_data": result,
            "cached_at": datetime.utcnow().isoformat() + "Z",
            "preimage": preimage
        }
        
        self._approved_cache['entries'][request_hash] = cache_entry
        return self._save_cache_file(self._approved_cache, self.approved_cache_key, "approved")
    
    def add_rejected(self, request_hash: str, reason: str, preimage: str) -> bool:
        """
        Add a rejected mapping to the cache.
        
        Args:
            request_hash: The SHA-256 hash of the request
            reason: The rejection reason
            preimage: The original preimage for debugging
            
        Returns:
            True if successfully saved, False otherwise
        """
        self._load_caches()
        
        cache_entry = {
            "reason": reason,
            "cached_at": datetime.utcnow().isoformat() + "Z", 
            "preimage": preimage
        }
        
        self._rejected_cache['entries'][request_hash] = cache_entry
        return self._save_cache_file(self._rejected_cache, self.rejected_cache_key, "rejected")
    
    def get_cache_stats(self) -> Dict:
        """Get statistics about the validation caches."""
        self._load_caches()
        
        return {
            "approved_count": len(self._approved_cache['entries']),
            "rejected_count": len(self._rejected_cache['entries']),
            "total_cached": len(self._approved_cache['entries']) + len(self._rejected_cache['entries']),
            "r2_available": self.is_available()
        }