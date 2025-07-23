#!/usr/bin/env python3
"""
Upload a specified config.yaml to R2 and trigger a cache rebuild.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from r2_cache_manager import R2CacheManager

def trigger_cache_rebuild():
    """Triggers the build_cache.py script."""
    print("Triggering cache rebuild...")
    try:
        script_path = Path(__file__).parent / 'build_cache.py'
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            check=True,
            timeout=1800  # 30 minutes
        )
        print("✓ Cache rebuild completed successfully.")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("ERROR: Cache rebuild failed.")
        print(e.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("ERROR: Cache rebuild timed out after 30 minutes.")
        return False
    except Exception as e:
        print(f"ERROR: An unexpected error occurred during cache rebuild: {e}")
        return False
    return True

def upload_config(config_path: Path):
    """Upload the specified config.yaml to R2."""
    print(f"Uploading {config_path.name} to R2...")
    
    r2_manager = R2CacheManager()
    
    if not r2_manager.is_available():
        print("ERROR: R2 not available - check environment variables.")
        return False
    
    if not config_path.exists():
        print(f"ERROR: Config file not found at {config_path}")
        return False
        
    try:
        with open(config_path, 'rb') as f:
            config_data = f.read()
        
        r2_key = "config/config.yaml"
        success = r2_manager.upload_object(r2_key, config_data, content_type="text/yaml")
        
        if success:
            print(f"✓ Successfully uploaded config to R2: {r2_key}")
            return trigger_cache_rebuild()
        else:
            print("ERROR: Failed to upload config to R2")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Upload a config file to R2 and rebuild cache.')
    parser.add_argument('file_path', type=str, help='The absolute path to the config.yaml file to upload.')
    args = parser.parse_args()
    
    config_file_path = Path(args.file_path)
    
    if not config_file_path.is_absolute():
        print("ERROR: Please provide an absolute path to the config file.")
        sys.exit(1)

    upload_success = upload_config(config_file_path)
    sys.exit(0 if upload_success else 1)
