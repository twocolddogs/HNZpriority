# --- START OF FILE r2_cache_manager.py (Timestamp-aware version) ---

import os
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class R2CacheManager:
    def __init__(self):
        # ... (initialization is the same) ...
        self.access_key_id = os.environ.get('R2_ACCESS_KEY_ID')
        self.secret_access_key = os.environ.get('R2_SECRET_ACCESS_KEY')
        self.bucket_name = os.environ.get('R2_BUCKET_NAME')
        self.endpoint_url = os.environ.get('R2_ENDPOINT_URL')
        self.client = None
        self._available = False
        if all([self.access_key_id, self.secret_access_key, self.bucket_name, self.endpoint_url]):
            try:
                self.client = boto3.client('s3', endpoint_url=self.endpoint_url, aws_access_key_id=self.access_key_id, aws_secret_access_key=self.secret_access_key, region_name='auto')
                self._available = True
                logger.info(f"R2 cache manager initialized for bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize R2 client: {e}")
        else:
            logger.warning("R2 cache manager not configured - missing environment variables")

    def is_available(self) -> bool:
        return self._available and self.client is not None

    def upload_cache(self, object_key: str, cache_bytes: bytes) -> bool:
        """Uploads raw cache bytes to a specific key in R2."""
        if not self.is_available(): return False
        try:
            logger.info(f"Uploading cache to R2: {object_key} ({len(cache_bytes)/(1024*1024):.1f}MB)")
            self.client.put_object(Bucket=self.bucket_name, Key=object_key, Body=cache_bytes)
            logger.info(f"Successfully uploaded cache to R2: {object_key}")
            return True
        except ClientError as e:
            logger.error(f"AWS/R2 error uploading cache: {e}")
            return False
        return False

    def download_cache(self, object_key: str, local_file_path: str) -> bool:
        """Downloads a specific object key from R2 to a local file path."""
        if not self.is_available(): return False
        try:
            logger.info(f"Downloading cache from R2: {object_key}")
            temp_file_path = f"{local_file_path}.tmp"
            self.client.download_file(self.bucket_name, object_key, temp_file_path)
            os.rename(temp_file_path, local_file_path)
            logger.info(f"Successfully downloaded and saved cache to {local_file_path}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.warning(f"Cache not found in R2 with key: {object_key}")
            else:
                logger.error(f"AWS/R2 error downloading cache {object_key}: {e}")
            if os.path.exists(temp_file_path): os.remove(temp_file_path)
            return False
        return False

    def list_objects(self, prefix: str) -> List[Dict]:
        """Lists all objects in R2 with a given prefix."""
        if not self.is_available(): return []
        try:
            response = self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            return response.get('Contents', [])
        except ClientError as e:
            logger.error(f"Failed to list R2 objects with prefix '{prefix}': {e}")
            return []

    def cleanup_old_caches(self, model_key: str, keep: int = 3):
        """Deletes all but the N most recent cache files for a model in R2."""
        if not self.is_available(): return
        prefix = f"caches/{model_key}/"
        objects = self.list_objects(prefix)
        if len(objects) <= keep:
            logger.info(f"Cleanup not needed for '{model_key}', found {len(objects)} caches (keeping {keep}).")
            return

        # Sort by filename (timestamp) descending to find the newest
        objects.sort(key=lambda x: x['Key'], reverse=True)
        to_delete = objects[keep:]
        
        if not to_delete: return
        
        delete_keys = [{'Key': obj['Key']} for obj in to_delete]
        logger.info(f"Cleaning up {len(to_delete)} old cache(s) for model '{model_key}'.")
        try:
            self.client.delete_objects(Bucket=self.bucket_name, Delete={'Objects': delete_keys})
            logger.info("Cleanup successful.")
        except ClientError as e:
            logger.error(f"Error during R2 cache cleanup: {e}")