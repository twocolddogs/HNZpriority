import os
import logging
import pickle
from datetime import datetime, timezone

# Assumes r2_cache_manager is in the same directory and is importable
from r2_cache_manager import R2CacheManager

# Configure logging for the sync script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [CacheSync] - %(message)s')

def get_latest_r2_object_for_model(r2_manager, model_key):
    """Finds the most recent cache object in R2 for a given model by checking modification times."""
    try:
        prefix = f"nhs-embeddings/{model_key}/"
        response = r2_manager.client.list_objects_v2(
            Bucket=r2_manager.bucket_name,
            Prefix=prefix
        )
        objects = response.get('Contents', [])
        if not objects:
            return None
        
        # Sort by last modified to find the newest object
        objects.sort(key=lambda x: x['LastModified'], reverse=True)
        return objects[0]
    except Exception as e:
        logging.error(f"Failed to list R2 objects for model '{model_key}': {e}")
        return None

def sync_cache_from_r2():
    """
    Ensures the local persistent disk has the latest embedding caches from R2.
    This script is intended to be run at application startup, before Gunicorn starts.
    """
    logging.info("Starting cache synchronization from R2 to persistent disk.")

    persistent_disk_path = os.environ.get('RENDER_DISK_PATH')
    if not persistent_disk_path:
        logging.info("RENDER_DISK_PATH environment variable not set. Skipping cache sync.")
        return

    if not os.path.exists(persistent_disk_path):
        logging.info(f"Creating persistent disk directory: {persistent_disk_path}")
        os.makedirs(persistent_disk_path)

    r2_manager = R2CacheManager()
    if not r2_manager.is_available():
        logging.warning("R2 Cache Manager is not available. Cannot sync cache.")
        return

    model_keys = r2_manager.list_cached_models()
    if not model_keys:
        logging.warning("No models found in R2. Nothing to sync.")
        return
        
    logging.info(f"Found models in R2 to check: {model_keys}")

    for model_key in model_keys:
        logging.info(f"--- Processing model: {model_key} ---")
        latest_r2_object = get_latest_r2_object_for_model(r2_manager, model_key)

        if not latest_r2_object:
            logging.warning(f"No R2 cache object found for model '{model_key}'.")
            continue

        r2_object_key = latest_r2_object['Key']
        r2_last_modified = latest_r2_object['LastModified']
        
        # Local file is decompressed, so we remove .gz from the name
        # Ensure unique local filename by including model_key
        base_filename = f"{model_key}_{os.path.basename(r2_object_key).replace('.gz', '')}"
        local_file_path = os.path.join(persistent_disk_path, base_filename)

        should_download = False
        if not os.path.exists(local_file_path):
            logging.info(f"Local cache '{base_filename}' not found. Will download from R2.")
            should_download = True
        else:
            local_last_modified_ts = os.path.getmtime(local_file_path)
            local_last_modified_dt = datetime.fromtimestamp(local_last_modified_ts, tz=timezone.utc)
            if r2_last_modified > local_last_modified_dt:
                logging.info(f"R2 cache for '{model_key}' is newer. Will re-download.")
                should_download = True
            else:
                logging.info(f"Local cache for '{model_key}' is up to date.")

        if should_download:
            try:
                # Extract the data hash from the filename to pass to the download function
                data_hash = os.path.splitext(base_filename)[0].split('_')[-1]
                logging.info(f"Downloading cache for model '{model_key}' with hash '{data_hash}'...")
                
                # download_cache returns the decompressed Python object
                cache_data = r2_manager.download_cache(model_key, data_hash)
                
                if cache_data:
                    # Clean up any other versions for this model on the local disk
                    for f in os.listdir(persistent_disk_path):
                        if f.startswith(f"nhs_embeddings_{model_key}_") and f != base_filename:
                            logging.info(f"Removing old local cache file: {f}")
                            os.remove(os.path.join(persistent_disk_path, f))
                    
                    # Save the new cache data using pickle
                    with open(local_file_path, 'wb') as f:
                        pickle.dump(cache_data, f)
                    logging.info(f"Successfully saved cache to {local_file_path}")
                else:
                    logging.error(f"Download from R2 for model '{model_key}' returned no data.")
            except Exception as e:
                logging.error(f"An error occurred during download/save for model '{model_key}': {e}", exc_info=True)

    logging.info("Cache synchronization complete.")

if __name__ == "__main__":
    sync_cache_from_r2()