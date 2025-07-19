# --- START OF FILE sync_cache.py (Corrected) ---

import os
import logging
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
        
        r2_objects.sort(key=lambda x: x['Key'], reverse=True)
        latest_r2_object_key = r2_objects[0]['Key']
        latest_r2_filename = os.path.basename(latest_r2_object_key)
        logging.info(f"Latest R2 version identified: {latest_r2_filename}")

        local_file_path = os.path.join(persistent_disk_path, latest_r2_filename)
        
        if os.path.exists(local_file_path):
            logging.info("Local cache is already the latest version. Sync not needed.")
        else:
            logging.info("Newer version found in R2. Starting download...")
            download_success = r2_manager.download_object(latest_r2_object_key, local_file_path) # <-- USES NEW GENERIC METHOD
            
            if download_success:
                for filename in os.listdir(persistent_disk_path):
                    if filename.startswith(f"{model_key}_") and filename != latest_r2_filename:
                        old_file_path = os.path.join(persistent_disk_path, filename)
                        logging.info(f"Removing old local cache file: {filename}")
                        os.remove(old_file_path)
            else:
                logging.error(f"Failed to download latest cache {latest_r2_filename} from R2.")

    logging.info("Cache synchronization complete.")

if __name__ == "__main__":
    sync_cache_from_r2()