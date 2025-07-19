# --- START OF FILE sync_cache.py ---

import os
import logging
from r2_cache_manager import R2CacheManager

# Configure logging for the sync script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [CacheSync] - %(message)s')

def sync_cache_from_r2():
    """
    Ensures the local persistent disk has the single latest embedding cache from R2 for each model.
    This script is intended to be run at application startup, before the main app starts.
    It uses timestamped filenames for versioning.
    """
    logging.info("Starting timestamp-based cache synchronization from R2.")

    # Get the path to the persistent disk where caches are stored
    persistent_disk_path = os.environ.get('RENDER_DISK_PATH', 'embedding-caches')
    os.makedirs(persistent_disk_path, exist_ok=True)
    logging.info(f"Local persistent disk path: {persistent_disk_path}")

    # Initialize the R2 manager to communicate with Cloudflare R2
    r2_manager = R2CacheManager()
    if not r2_manager.is_available():
        logging.warning("R2 Cache Manager is not available. Cannot sync cache. The application might fail if no local cache exists.")
        return

    # Dynamically get the list of models the application supports
    from nlp_processor import NLPProcessor
    model_keys = NLPProcessor.get_available_models().keys()
    if not model_keys:
        logging.warning("No models configured in NLPProcessor. Nothing to sync.")
        return
        
    logging.info(f"Found models to check for cache updates: {list(model_keys)}")

    for model_key in model_keys:
        logging.info(f"--- Syncing cache for model: {model_key} ---")
        
        # 1. Find the latest cache file in R2 by filename
        # The prefix defines the "folder" for this model's caches in R2
        prefix = f"caches/{model_key}/"
        r2_objects = r2_manager.list_objects(prefix)
        
        if not r2_objects:
            logging.warning(f"No cache objects found in R2 for model '{model_key}'.")
            continue
        
        # Sort by the object key (filename) in descending order.
        # Since the filename starts with a timestamp, this finds the newest file.
        r2_objects.sort(key=lambda x: x['Key'], reverse=True)
        latest_r2_object_key = r2_objects[0]['Key']
        latest_r2_filename = os.path.basename(latest_r2_object_key)
        logging.info(f"Latest R2 version identified: {latest_r2_filename}")

        # 2. Check if this exact file already exists locally
        local_file_path = os.path.join(persistent_disk_path, latest_r2_filename)
        
        if os.path.exists(local_file_path):
            logging.info("Local cache is already the latest version. Sync not needed.")
        else:
            logging.info("Newer version found in R2. Starting download...")
            download_success = r2_manager.download_cache(latest_r2_object_key, local_file_path)
            
            if download_success:
                # 3. After a successful download, clean up any old local cache files for this model
                for filename in os.listdir(persistent_disk_path):
                    # Check for files that belong to the current model but are not the one we just downloaded
                    if filename.startswith(f"{model_key}_") and filename != latest_r2_filename:
                        old_file_path = os.path.join(persistent_disk_path, filename)
                        logging.info(f"Removing old local cache file: {filename}")
                        try:
                            os.remove(old_file_path)
                        except OSError as e:
                            logging.error(f"Error removing old cache file {old_file_path}: {e}")
            else:
                logging.error(f"Failed to download latest cache {latest_r2_filename} from R2.")

    logging.info("Cache synchronization complete.")

if __name__ == "__main__":
    sync_cache_from_r2()