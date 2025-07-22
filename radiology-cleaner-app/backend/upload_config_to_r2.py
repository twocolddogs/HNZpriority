#!/usr/bin/env python3
"""
Upload current config.yaml to R2 for remote configuration management.
Run this script whenever you want to update the R2-hosted config.
"""

import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from r2_cache_manager import R2CacheManager

def upload_config():
    """Upload the current config.yaml to R2."""
    print("Uploading config.yaml to R2...")
    
    # Initialize R2 manager
    r2_manager = R2CacheManager()
    
    if not r2_manager.is_available():
        print("ERROR: R2 not available - check environment variables:")
        print(f"- R2_ACCESS_KEY_ID: {'✓' if os.getenv('R2_ACCESS_KEY_ID') else '✗'}")
        print(f"- R2_SECRET_ACCESS_KEY: {'✓' if os.getenv('R2_SECRET_ACCESS_KEY') else '✗'}")
        print(f"- R2_BUCKET_NAME: {'✓' if os.getenv('R2_BUCKET_NAME') else '✗'}")
        print(f"- R2_ENDPOINT_URL: {'✓' if os.getenv('R2_ENDPOINT_URL') else '✗'}")
        return False
    
    # Read config.yaml
    config_path = Path(__file__).parent / 'config.yaml'
    if not config_path.exists():
        print(f"ERROR: Config file not found at {config_path}")
        return False
        
    try:
        with open(config_path, 'rb') as f:
            config_data = f.read()
        
        # Upload to R2 with proper content type
        r2_key = "config/config.yaml"
        success = r2_manager.upload_object(r2_key, config_data, content_type="text/yaml")
        
        if success:
            print(f"✓ Successfully uploaded config to R2: {r2_key}")
            print(f"✓ Config will be available at: https://pub-cc78b976831e4f649dd695ffa52d1171.r2.dev/{r2_key}")
            print("✓ Backend will now use R2 config on next startup/reload")
            return True
        else:
            print("ERROR: Failed to upload config to R2")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = upload_config()
    sys.exit(0 if success else 1)