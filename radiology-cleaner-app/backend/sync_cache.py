# --- START OF FILE sync_cache.py (Corrected) ---

import os
import logging
import time
from datetime import datetime
from r2_cache_manager import R2CacheManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [CacheSync] - %(message)s')

def sync_cache_from_r2():
    """
    Ensures the local persistent disk has the single latest cache from R2 for each model.
    """
    logging.info("Starting timestamp-based cache synchronization from R2.")

    persistent_disk_path = os.environ.get('RENDER_DISK_PATH', 'embedding-caches')
    os.makedirs(persistent_disk_path, exist_ok=True)
    logging.info(f"Local persistent disk path: {persistent_disk_path}")

    r2_manager = R2CacheManager()
    if not r2_manager.is_available():
        logging.warning("R2 Cache Manager not available. App may fail if no local cache exists.")
        return

    from nlp_processor import NLPProcessor
    model_keys = NLPProcessor.get_available_models().keys()
    logging.info(f"Found models to sync: {list(model_keys)}")

    for model_key in model_keys:
        logging.info(f"--- Syncing cache for model: {model_key} ---")
        
        prefix = f"caches/{model_key}/"
        r2_objects = r2_manager.list_objects(prefix) # <-- USES NEW GENERIC METHOD
        
        if not r2_objects:
            logging.warning(f"No cache objects found in R2 for model '{model_key}'.")
            continue
        
        # Sort by LastModified timestamp to get truly newest file
        r2_objects.sort(key=lambda x: x.get('LastModified', ''), reverse=True)
        latest_r2_object_key = r2_objects[0]['Key']
        latest_r2_filename = os.path.basename(latest_r2_object_key)
        logging.info(f"Latest R2 version identified: {latest_r2_filename}")

        local_file_path = os.path.join(persistent_disk_path, latest_r2_filename)
        
        # Find existing local cache files for this model
        local_cache_files = []
        if os.path.exists(persistent_disk_path):
            for filename in os.listdir(persistent_disk_path):
                if filename.startswith(f"{model_key}_") and filename.endswith('.cache'):
                    local_cache_files.append(filename)
        
        # Compare timestamps to determine if R2 version is actually newer
        needs_download = True
        
        if local_cache_files:
            # Find the newest local file by modification time
            newest_local_file = None
            newest_local_mtime = 0
            
            for filename in local_cache_files:
                filepath = os.path.join(persistent_disk_path, filename)
                mtime = os.path.getmtime(filepath)
                if mtime > newest_local_mtime:
                    newest_local_mtime = mtime
                    newest_local_file = filename
            
            # Get R2 object timestamp
            r2_timestamp = r2_objects[0].get('LastModified')
            if r2_timestamp:
                # Convert R2 timestamp to epoch time for comparison
                if hasattr(r2_timestamp, 'timestamp'):  # boto3 datetime object
                    r2_epoch = r2_timestamp.timestamp()
                else:  # string timestamp
                    r2_epoch = datetime.fromisoformat(r2_timestamp.replace('Z', '+00:00')).timestamp()
                
                if newest_local_mtime >= r2_epoch:
                    needs_download = False
                    logging.info(f"Local cache '{newest_local_file}' is up to date (local: {datetime.fromtimestamp(newest_local_mtime)}, R2: {r2_timestamp})")
                else:
                    logging.info(f"R2 cache is newer (local: {datetime.fromtimestamp(newest_local_mtime)}, R2: {r2_timestamp})")
        
        if needs_download:
            logging.info("Downloading newer version from R2...")
            download_success = r2_manager.download_object(latest_r2_object_key, local_file_path) # <-- USES NEW GENERIC METHOD
            
            if download_success:
                # Remove old local cache files after successful download
                for filename in os.listdir(persistent_disk_path):
                    if filename.startswith(f"{model_key}_") and filename != latest_r2_filename:
                        old_file_path = os.path.join(persistent_disk_path, filename)
                        logging.info(f"Removing old local cache file: {filename}")
                        os.remove(old_file_path)
            else:
                logging.error(f"Failed to download latest cache {latest_r2_filename} from R2.")
        else:
            logging.info("Local cache is up to date. No download needed.")

    logging.info("Cache synchronization complete.")

if __name__ == "__main__":
    sync_cache_from_r2()