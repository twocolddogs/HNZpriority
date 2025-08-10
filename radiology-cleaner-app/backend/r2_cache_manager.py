# --- START OF FILE r2_cache_manager.py (Corrected) ---

import os
import logging
import pickle
import boto3
import gzip
import time
import json
from botocore.exceptions import ClientError
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class R2CacheManager:
    def __init__(self):
        self.access_key_id = os.environ.get('R2_ACCESS_KEY_ID')
        self.secret_access_key = os.environ.get('R2_SECRET_ACCESS_KEY')
        self.bucket_name = os.environ.get('R2_BUCKET_NAME')
        self.endpoint_url = os.environ.get('R2_ENDPOINT_URL')
        self.client = None
        if all([self.access_key_id, self.secret_access_key, self.bucket_name, self.endpoint_url]):
            try:
                self.client = boto3.client(
                    's3',
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                    region_name='auto'
                )
                logger.info(f"R2 cache manager initialized for bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize R2 client: {e}")
        else:
            logger.warning("R2 cache manager not configured - missing environment variables")
    
    def is_available(self) -> bool:
        return self.client is not None
    
    # --- NEW GENERIC UPLOAD METHOD ---
    def upload_object(self, object_key: str, data: bytes, content_type: str = None, cors_headers: bool = True) -> bool:
        """Uploads a raw bytes object to R2 with a specific key, optional content type, and CORS headers."""
        if not self.is_available(): return False
        try:
            put_kwargs = {
                'Bucket': self.bucket_name, 
                'Key': object_key, 
                'Body': data
            }
            
            # Set content type if provided
            if content_type:
                put_kwargs['ContentType'] = content_type
            
            # Add headers for frontend access
            if cors_headers:
                # Set cache control for better performance
                put_kwargs['CacheControl'] = 'public, max-age=3600'
                put_kwargs['ContentDisposition'] = 'inline'
                
                # Add metadata to indicate this is a public file
                put_kwargs['Metadata'] = {
                    'access-type': 'public',
                    'cors-enabled': 'true'
                }
            
            self.client.put_object(**put_kwargs)
            logger.info(f"Successfully uploaded object to R2: {object_key}" + 
                       (f" (content-type: {content_type})" if content_type else "") +
                       (" with CORS headers" if cors_headers else ""))
            return True
        except ClientError as e:
            logger.error(f"AWS/R2 error uploading object {object_key}: {e}")
            return False

    def upload_file(self, local_file_path: str, object_key: str, content_type: str = None, cors_headers: bool = True) -> bool:
        """Uploads a local file to R2 using a memory-efficient multipart upload."""
        if not self.is_available(): return False
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            if cors_headers:
                extra_args['CacheControl'] = 'public, max-age=3600'
                extra_args['ContentDisposition'] = 'inline'
                extra_args['Metadata'] = {
                    'access-type': 'public',
                    'cors-enabled': 'true'
                }

            self.client.upload_file(
                Filename=local_file_path,
                Bucket=self.bucket_name,
                Key=object_key,
                ExtraArgs=extra_args
            )
            logger.info(f"Successfully uploaded file to R2: {object_key}")
            return True
        except ClientError as e:
            logger.error(f"AWS/R2 error uploading file {object_key}: {e}")
            return False
        except FileNotFoundError:
            logger.error(f"Local file not found for upload: {local_file_path}")
            return False

    # --- NEW GENERIC DOWNLOAD METHOD ---
    def download_object(self, object_key: str, local_file_path: str) -> bool:
        """Downloads an object from R2 and saves it to a local file."""
        if not self.is_available(): return False
        try:
            temp_file_path = f"{local_file_path}.tmp"
            self.client.download_file(self.bucket_name, object_key, temp_file_path)
            os.rename(temp_file_path, local_file_path)
            logger.info(f"Successfully downloaded {object_key} to {local_file_path}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.warning(f"Object not found in R2: {object_key}")
            else:
                logger.error(f"AWS/R2 error downloading object {object_key}: {e}")
            return False

    # --- NEW GENERIC LIST METHOD ---
    def list_objects(self, prefix: str) -> list:
        """Lists objects in R2 with a given prefix."""
        if not self.is_available(): return []
        try:
            response = self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            return response.get('Contents', [])
        except ClientError as e:
            logger.error(f"Failed to list R2 objects with prefix '{prefix}': {e}")
            return []

    def fetch_json(self, object_key: str) -> dict:
        """
        Fetch and parse JSON data from R2 storage with consistent fallback.
        
        Args:
            object_key: The R2 object key to fetch
            
        Returns:
            dict: Parsed JSON data, or {} if not available or error
        """
        if not self.is_available():
            logger.warning(f"R2 not available, cannot fetch {object_key}")
            return {}
        
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=object_key)
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content) if content.strip() else {}
            logger.info(f"Successfully fetched JSON from R2: {object_key}")
            return data
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.info(f"Object not found in R2: {object_key}")
            else:
                logger.warning(f"AWS/R2 error fetching {object_key}: {e}")
            return {}
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"JSON parsing error for {object_key}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error fetching JSON from R2 {object_key}: {e}")
            return {}

    def cleanup_old_caches(self, model_key: str, keep_latest: int = 3):
        """Removes old cache files for a model, keeping only the latest N versions."""
        if not self.is_available(): return
        prefix = f"caches/{model_key}/"
        objects = self.list_objects(prefix)
        if len(objects) <= keep_latest:
            return
        
        objects.sort(key=lambda x: x['LastModified'], reverse=True)
        to_delete = objects[keep_latest:]
        
        for obj in to_delete:
            logger.info(f"Deleting old R2 cache: {obj['Key']}")
            try:
                self.client.delete_object(Bucket=self.bucket_name, Key=obj['Key'])
            except ClientError as e:
                logger.error(f"Failed to delete old cache object {obj['Key']}: {e}")