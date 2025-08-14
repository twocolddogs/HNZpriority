"""
Cache Version Management System

Automatically generates cache version based on critical file checksums.
When any processing rule files change, the cache version changes,
effectively invalidating all previous cache entries.
"""

import hashlib
import os
import logging
import requests
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Critical files that should trigger cache invalidation when modified
CRITICAL_FILES = [
  
    
    # Processing logic files
    'nhs_lookup_engine.py',
    'nlp_processor.py',
    'parsing_utils.py',
    'parser.py',
    'app.py',
    'context_detection.py',
    'config.yaml',
    'preprocessing.py',
    
    # Validation logic files
    'validation_cache_manager.py',
    
    # Data files
    'core/NHS.json',
 
]

def get_r2_config_hash() -> Optional[str]:
    """
    Get SHA-256 hash of the R2 config.yaml file.
    
    Returns:
        Hex digest of config hash or None if fetch fails
    """
    try:
        r2_config_url = "https://pub-cc78b976831e4f649dd695ffa52d1171.r2.dev/config/config.yaml"
        response = requests.get(r2_config_url, timeout=10)
        response.raise_for_status()
        
        hasher = hashlib.sha256()
        hasher.update(response.content)
        
        config_hash = hasher.hexdigest()
        logger.debug(f"R2 config hash: {config_hash[:12]}...")
        return config_hash
        
    except Exception as e:
        logger.error(f"Error fetching R2 config for hash calculation: {e}")
        # This is critical - cache version must be consistent
        raise RuntimeError(f"Cannot calculate cache version without R2 config: {e}")

def get_file_hash(file_path: str) -> Optional[str]:
    """
    Get SHA-256 hash of a file's contents.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Hex digest of file hash or None if file doesn't exist
    """
    try:
        if not os.path.exists(file_path):
            return None
            
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    except Exception as e:
        logger.warning(f"Error hashing file {file_path}: {e}")
        return None

def get_cache_version(base_dir: Optional[str] = None) -> str:
    """
    Generate cache version based on checksums of critical processing files.
    
    Args:
        base_dir: Base directory path (defaults to current script directory)
        
    Returns:
        8-character cache version hash
    """
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Collect hashes from all critical files
    version_components = []
    files_found = 0
    files_missing = 0
    
    for file_path in CRITICAL_FILES:
        if file_path == 'config.yaml':
            # Special handling for config.yaml - always fetch from R2
            try:
                config_hash = get_r2_config_hash()
                version_components.append(f"{file_path}:{config_hash}")
                files_found += 1
            except Exception as e:
                logger.error(f"Failed to get R2 config hash: {e}")
                # Fail fast - this is critical for cache consistency
                raise RuntimeError(f"Cache version calculation failed due to R2 config unavailability: {e}")
        else:
            full_path = os.path.join(base_dir, file_path)
            file_hash = get_file_hash(full_path)
            
            if file_hash:
                version_components.append(f"{file_path}:{file_hash}")
                files_found += 1
            else:
                # Include file path even if missing to detect when files are added/removed
                version_components.append(f"{file_path}:MISSING")
                files_missing += 1
    
    # Sort to ensure consistent ordering
    version_components.sort()
    
    # Create combined hash
    combined_hash = hashlib.sha256()
    for component in version_components:
        combined_hash.update(component.encode('utf-8'))
    
    cache_version = combined_hash.hexdigest()[:8]
    
    logger.info(f"Cache version generated: {cache_version} "
               f"(from {files_found} files, {files_missing} missing)")
    
    return cache_version

def get_cache_version_info(base_dir: Optional[str] = None) -> dict:
    """
    Get detailed cache version information for debugging.
    
    Args:
        base_dir: Base directory path (defaults to current script directory)
        
    Returns:
        Dictionary with version info and file details
    """
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    file_details = []
    files_found = 0
    files_missing = 0
    
    for file_path in CRITICAL_FILES:
        if file_path == 'config.yaml':
            # Special handling for config.yaml - always fetch from R2
            try:
                config_hash = get_r2_config_hash()
                file_details.append({
                    'path': file_path,
                    'hash': config_hash[:12] + '...',  # Truncate for display
                    'size': 'R2',
                    'modified': 'R2',
                    'exists': True,
                    'source': 'R2'
                })
                files_found += 1
            except Exception as e:
                file_details.append({
                    'path': file_path,
                    'hash': None,
                    'size': None,
                    'modified': None,
                    'exists': False,
                    'source': 'R2',
                    'error': str(e)
                })
                files_missing += 1
        else:
            full_path = os.path.join(base_dir, file_path)
            file_hash = get_file_hash(full_path)
            
            if file_hash:
                file_size = os.path.getsize(full_path)
                modified_time = os.path.getmtime(full_path)
                file_details.append({
                    'path': file_path,
                    'hash': file_hash[:12] + '...',  # Truncate for display
                    'size': file_size,
                    'modified': modified_time,
                    'exists': True,
                    'source': 'local'
                })
                files_found += 1
            else:
                file_details.append({
                    'path': file_path,
                    'hash': None,
                    'size': None,
                    'modified': None,
                    'exists': False,
                    'source': 'local'
                })
                files_missing += 1
    
    return {
        'cache_version': get_cache_version(base_dir),
        'files_tracked': len(CRITICAL_FILES),
        'files_found': files_found,
        'files_missing': files_missing,
        'file_details': file_details
    }

def format_cache_key(endpoint: str, cache_version: str, *args) -> str:
    """
    Format a cache key with version and arguments.
    
    Args:
        endpoint: API endpoint name (e.g., 'parse', 'batch', 'enhanced')
        cache_version: Cache version string
        *args: Additional cache key components
        
    Returns:
        Formatted cache key
    """
    key_parts = [f"{endpoint}_v{cache_version}"]
    key_parts.extend(str(arg) for arg in args)
    return "_".join(key_parts)

# Cache the version for the duration of the application run
# This avoids recalculating file hashes on every request
_cached_version = None

def get_current_cache_version() -> str:
    """
    Get the current cache version, using cached value if available.
    
    Returns:
        Current cache version string
    """
    global _cached_version
    
    if _cached_version is None:
        _cached_version = get_cache_version()
        logger.info(f"Initialized cache version: {_cached_version}")
    
    return _cached_version

def refresh_cache_version() -> str:
    """
    Force refresh of the cached version (useful for testing or after file updates).
    
    Returns:
        New cache version string
    """
    global _cached_version
    _cached_version = None
    return get_current_cache_version()

if __name__ == "__main__":
    # For testing and debugging
    import json
    
    print("Cache Version Management System")
    print("=" * 40)
    
    version_info = get_cache_version_info()
    
    print(f"Current cache version: {version_info['cache_version']}")
    print(f"Files tracked: {version_info['files_tracked']}")
    print(f"Files found: {version_info['files_found']}")
    print(f"Files missing: {version_info['files_missing']}")
    print()
    
    print("File Details:")
    print("-" * 40)
    for file_detail in version_info['file_details']:
        status = "✓" if file_detail['exists'] else "✗"
        print(f"{status} {file_detail['path']}")
        if file_detail['exists']:
            print(f"    Hash: {file_detail['hash']}")
            print(f"    Size: {file_detail['size']:,} bytes")
    
    print()
    print("Example cache keys:")
    cache_version = version_info['cache_version']
    print(f"  Parse: {format_cache_key('parse', cache_version, 'CT_CHEST', 'CT')}")
    print(f"  Batch: {format_cache_key('batch', cache_version, 'MRI_BRAIN', 'MR')}")
    print(f"  Enhanced: {format_cache_key('enhanced', cache_version, 'XRAY_HAND', 'XR')}")