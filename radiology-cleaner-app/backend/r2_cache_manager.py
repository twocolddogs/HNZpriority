"""
Cloudflare R2 Cache Manager for NHS Embedding Storage

This module handles uploading and downloading embedding cache files to/from 
Cloudflare R2 object storage, solving the build vs runtime separation issue
where build environment can't access persistent disks.

Environment Variables Required:
- R2_ACCESS_KEY_ID: Cloudflare R2 access key
- R2_SECRET_ACCESS_KEY: Cloudflare R2 secret key  
- R2_BUCKET_NAME: R2 bucket name
- R2_ENDPOINT_URL: R2 endpoint (e.g., https://accountid.r2.cloudflarestorage.com)
"""

import os
import logging
import pickle
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, Dict
import hashlib

logger = logging.getLogger(__name__)

class R2CacheManager:
    def __init__(self):
        """Initialize R2 client with environment variables."""
        self.access_key_id = os.environ.get('R2_ACCESS_KEY_ID')
        self.secret_access_key = os.environ.get('R2_SECRET_ACCESS_KEY')
        self.bucket_name = os.environ.get('R2_BUCKET_NAME')
        self.endpoint_url = os.environ.get('R2_ENDPOINT_URL')
        
        self.client = None
        self._available = False
        
        if all([self.access_key_id, self.secret_access_key, self.bucket_name, self.endpoint_url]):
            try:
                self.client = boto3.client(
                    's3',
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                    region_name='auto'  # R2 uses 'auto' for region
                )
                self._available = True
                logger.info(f"R2 cache manager initialized for bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize R2 client: {e}")
        else:
            logger.warning("R2 cache manager not configured - missing environment variables")
    
    def is_available(self) -> bool:
        """Check if R2 storage is available."""
        return self._available and self.client is not None
    
    def _get_cache_key(self, model_key: str, data_hash: str) -> str:
        """Generate R2 object key for cache file."""
        return f"nhs-embeddings/{model_key}/{data_hash}.pkl"
    
    def upload_cache(self, cache_data: Dict, model_key: str, data_hash: str) -> bool:
        """
        Upload cache data to R2.
        
        Args:
            cache_data: Cache data dictionary with embeddings and metadata
            model_key: Model identifier (e.g., 'default', 'experimental')
            data_hash: Hash of the NHS data for cache invalidation
            
        Returns:
            True if upload successful, False otherwise
        """
        if not self.is_available():
            logger.warning("R2 not available for cache upload")
            return False
        
        try:
            # Serialize cache data
            cache_bytes = pickle.dumps(cache_data)
            cache_size_mb = len(cache_bytes) / (1024 * 1024)
            
            object_key = self._get_cache_key(model_key, data_hash)
            
            logger.info(f"Uploading cache to R2: {object_key} ({cache_size_mb:.1f}MB)")
            
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=cache_bytes,
                Metadata={
                    'model_key': model_key,
                    'data_hash': data_hash,
                    'embeddings_count': str(cache_data.get('cache_metadata', {}).get('total_embeddings', 0))
                }
            )
            
            logger.info(f"Successfully uploaded cache to R2: {object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"AWS/R2 error uploading cache: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to upload cache to R2: {e}")
            return False
    
    def download_cache(self, model_key: str, data_hash: str) -> Optional[Dict]:
        """
        Download cache data from R2.
        
        Args:
            model_key: Model identifier
            data_hash: Hash of the NHS data
            
        Returns:
            Cache data dictionary if found and valid, None otherwise
        """
        if not self.is_available():
            logger.warning("R2 not available for cache download")
            return None
        
        try:
            object_key = self._get_cache_key(model_key, data_hash)
            
            logger.info(f"Downloading cache from R2: {object_key}")
            
            response = self.client.get_object(Bucket=self.bucket_name, Key=object_key)
            cache_bytes = response['Body'].read()
            cache_data = pickle.loads(cache_bytes)
            
            # Validate cache metadata
            metadata = cache_data.get('cache_metadata', {})
            if metadata.get('data_hash') == data_hash:
                logger.info(f"Successfully downloaded valid cache from R2: {object_key}")
                return cache_data
            else:
                logger.warning(f"Cache data hash mismatch for {object_key}")
                return None
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.info(f"No cache found in R2 for {model_key} with hash {data_hash}")
            else:
                logger.error(f"AWS/R2 error downloading cache: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to download cache from R2: {e}")
            return None
    
    def cache_exists(self, model_key: str, data_hash: str) -> bool:
        """Check if cache exists in R2 without downloading."""
        if not self.is_available():
            return False
        
        try:
            object_key = self._get_cache_key(model_key, data_hash)
            self.client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError:
            return False
        except Exception as e:
            logger.error(f"Error checking cache existence: {e}")
            return False
    
    def list_cached_models(self) -> list:
        """List all cached model keys in R2."""
        if not self.is_available():
            return []
        
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='nhs-embeddings/',
                Delimiter='/'
            )
            
            models = []
            for prefix in response.get('CommonPrefixes', []):
                model_key = prefix['Prefix'].split('/')[-2]
                models.append(model_key)
            
            return models
        except Exception as e:
            logger.error(f"Error listing cached models: {e}")
            return []
    
    def cleanup_old_caches(self, model_key: str, keep_latest: int = 3):
        """Remove old cache files for a model, keeping only the latest N versions."""
        if not self.is_available():
            return
        
        try:
            prefix = f"nhs-embeddings/{model_key}/"
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            objects = response.get('Contents', [])
            if len(objects) <= keep_latest:
                return
            
            # Sort by last modified, keep newest
            objects.sort(key=lambda x: x['LastModified'], reverse=True)
            to_delete = objects[keep_latest:]
            
            for obj in to_delete:
                logger.info(f"Deleting old cache: {obj['Key']}")
                self.client.delete_object(Bucket=self.bucket_name, Key=obj['Key'])
                
        except Exception as e:
            logger.error(f"Error cleaning up old caches: {e}")