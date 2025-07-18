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
import gzip
import time
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
        
        # Compression settings
        self.compression_threshold_mb = 50  # Compress files larger than 50MB
        self.use_compression = True
        
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
    
    def _get_cache_key(self, model_key: str, data_hash: str, compressed: bool = False) -> str:
        """Generate R2 object key for cache file."""
        extension = ".pkl.gz" if compressed else ".pkl"
        return f"nhs-embeddings/{model_key}/{data_hash}{extension}"
    
    def _should_compress(self, data_size_mb: float) -> bool:
        """Determine if data should be compressed based on size."""
        return self.use_compression and data_size_mb > self.compression_threshold_mb
    
    def _compress_cache_data(self, cache_data: Dict) -> bytes:
        """Compress cache data using gzip."""
        start_time = time.time()
        pickled_data = pickle.dumps(cache_data)
        original_size_mb = len(pickled_data) / (1024 * 1024)
        
        compressed_data = gzip.compress(pickled_data, compresslevel=6)
        compressed_size_mb = len(compressed_data) / (1024 * 1024)
        compression_time = time.time() - start_time
        
        compression_ratio = compressed_size_mb / original_size_mb
        
        logger.info(f"Compression: {original_size_mb:.1f}MB → {compressed_size_mb:.1f}MB "
                   f"({compression_ratio:.1%} of original, {compression_time:.2f}s)")
        
        return compressed_data
    
    def _decompress_cache_data(self, compressed_data: bytes) -> Dict:
        """Decompress cache data using gzip."""
        start_time = time.time()
        decompressed_data = gzip.decompress(compressed_data)
        cache_data = pickle.loads(decompressed_data)
        decompression_time = time.time() - start_time
        
        logger.info(f"Decompression completed in {decompression_time:.2f}s")
        return cache_data
    
    def upload_cache(self, cache_data: Dict, model_key: str, data_hash: str) -> bool:
        """
        Upload cache data to R2, with automatic compression for large files.
        
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
            # First, determine if we should compress
            temp_bytes = pickle.dumps(cache_data)
            uncompressed_size_mb = len(temp_bytes) / (1024 * 1024)
            should_compress = self._should_compress(uncompressed_size_mb)
            
            if should_compress:
                cache_bytes = self._compress_cache_data(cache_data)
                object_key = self._get_cache_key(model_key, data_hash, compressed=True)
                compression_info = " (compressed)"
            else:
                cache_bytes = temp_bytes
                object_key = self._get_cache_key(model_key, data_hash, compressed=False)
                compression_info = ""
            
            final_size_mb = len(cache_bytes) / (1024 * 1024)
            
            logger.info(f"Uploading cache to R2: {object_key} ({final_size_mb:.1f}MB{compression_info})")
            
            metadata = {
                'model_key': model_key,
                'data_hash': data_hash,
                'embeddings_count': str(cache_data.get('cache_metadata', {}).get('total_embeddings', 0)),
                'compressed': 'true' if should_compress else 'false',
                'original_size_mb': f"{uncompressed_size_mb:.1f}"
            }
            
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=cache_bytes,
                Metadata=metadata
            )
            
            logger.info(f"Successfully uploaded cache to R2: {object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"AWS/R2 error uploading cache: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to upload cache to R2: {e}")
            return False
    
    def download_cache(self, model_key: str, data_hash: str, local_file_path: str) -> bool:
        """
        Download cache data from R2 and save it directly to a local file, 
        with automatic decompression support.
        
        Args:
            model_key: Model identifier
            data_hash: Hash of the NHS data
            local_file_path: The absolute path to save the decompressed cache file.
            
        Returns:
            True if download and save successful, False otherwise
        """
        if not self.is_available():
            logger.warning("R2 not available for cache download")
            return False
        
        # Try compressed file first, then uncompressed for backward compatibility
        for compressed in [True, False]:
            object_key = self._get_cache_key(model_key, data_hash, compressed=compressed)
            
            try:
                logger.info(f"Downloading cache from R2: {object_key}")
                
                response = self.client.get_object(Bucket=self.bucket_name, Key=object_key)
                
                # Stream the content to a temporary file first
                temp_file_path = f"{local_file_path}.tmp"
                
                if compressed:
                    # Stream and decompress directly to the final file path
                    with open(temp_file_path, 'wb') as f_out:
                        with gzip.GzipFile(fileobj=response['Body'], mode='rb') as f_in:
                            while True:
                                chunk = f_in.read(8192) # Read in chunks
                                if not chunk:
                                    break
                                f_out.write(chunk)
                    logger.info(f"Successfully downloaded and decompressed cache from R2 to {temp_file_path}")
                else:
                    # For uncompressed, directly stream to the temporary file
                    with open(temp_file_path, 'wb') as f_out:
                        for chunk in response['Body'].iter_chunks():
                            f_out.write(chunk)
                    logger.info(f"Successfully downloaded cache from R2 to {temp_file_path}")
                
                # Atomically move the temporary file to the final destination
                os.rename(temp_file_path, local_file_path)
                logger.info(f"Successfully saved cache to {local_file_path}")
                return True
                    
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    continue  # Try the other format
                else:
                    logger.error(f"AWS/R2 error downloading cache {object_key}: {e}")
                    if os.path.exists(temp_file_path): os.remove(temp_file_path)
                    continue
            except Exception as e:
                logger.error(f"Failed to download cache from R2 {object_key}: {e}", exc_info=True)
                if os.path.exists(temp_file_path): os.remove(temp_file_path)
                continue
        
        logger.info(f"No valid cache found in R2 for {model_key} with hash {data_hash}")
        return False
    
    def cache_exists(self, model_key: str, data_hash: str) -> bool:
        """Check if cache exists in R2 without downloading (checks both compressed and uncompressed)."""
        if not self.is_available():
            return False
        
        # Check for both compressed and uncompressed versions
        for compressed in [True, False]:
            try:
                object_key = self._get_cache_key(model_key, data_hash, compressed=compressed)
                self.client.head_object(Bucket=self.bucket_name, Key=object_key)
                return True
            except ClientError:
                continue
            except Exception as e:
                logger.error(f"Error checking cache existence for {object_key}: {e}")
                continue
        
        return False
    
    def get_cache_metadata(self, model_key: str, data_hash: str) -> Optional[Dict]:
        """Get cache metadata without downloading the full cache file."""
        if not self.is_available():
            return None
        
        # Check for both compressed and uncompressed versions
        for compressed in [True, False]:
            try:
                object_key = self._get_cache_key(model_key, data_hash, compressed=compressed)
                response = self.client.head_object(Bucket=self.bucket_name, Key=object_key)
                
                # Return metadata from S3 object
                return {
                    'last_modified': response['LastModified'],
                    'size': response['ContentLength'],
                    'object_key': object_key,
                    'compressed': compressed,
                    'metadata': response.get('Metadata', {})
                }
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchKey':
                    logger.error(f"Error getting cache metadata for {object_key}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error getting cache metadata for {object_key}: {e}")
                continue
        
        return None
    
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