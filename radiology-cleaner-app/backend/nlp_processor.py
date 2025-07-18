# nlp_processor.py

import os
import logging
import numpy as np
import requests
from typing import Optional, List
import json
import time # Added for retry logic

logger = logging.getLogger(__name__)

class NLPProcessor:
    """
    API-based NLP processor that uses direct 'requests' calls to the Hugging Face
    Inference API. This version is robust enough to handle BOTH sentence-level models
    (like BioLORD) and token-level models (like MedCPT) by automatically applying
    mean pooling to token-level outputs.
    """

    # Available model configurations
    MODELS = {
        'default': {
            'hf_name': 'FremyCompany/BioLORD-2023',
            'name': 'BioLORD (Default)',
            'description': 'BioLORD - Advanced biomedical language model (default)',
            'status': 'available'
        },
        'experimental': {
            'hf_name': 'ncbi/MedCPT-Query-Encoder',
            'name': 'MedCPT (Experimental)',
            'description': 'NCBI Medical Clinical Practice Text encoder (experimental)',
            'status': 'available'
        }
    }

    def __init__(self, model_key: str = 'default'):
        self.api_token = os.environ.get('HUGGING_FACE_TOKEN')
        
        model_info = self.MODELS.get(model_key)
        if not model_info:
            logger.warning(f"Model key '{model_key}' not found. Falling back to 'default' model.")
            model_info = self.MODELS['default']
            model_key = 'default'
            
        self.model_key = model_key
        self.hf_model_name = model_info['hf_name']
        self.model_description = model_info['description']
        
        self.api_url = f"https://router.huggingface.co/hf-inference/models/{self.hf_model_name}/pipeline/feature-extraction"
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        if not self.api_token:
            logger.error("HUGGING_FACE_TOKEN not set. API-based NLP processing is disabled.")
        else:
            logger.info(f"Initialized API NLP Processor for model '{self.model_key}': {self.hf_model_name} using direct requests.")

    def _make_api_call(self, inputs: list[str]) -> Optional[list]:
        """Helper function to make a POST request and robustly handle the response."""
        payload = {"inputs": inputs, "options": {"wait_for_model": True}}
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=120)
            response.raise_for_status()
            return response.json()
        except json.JSONDecodeError:
            logger.error(f"API call to {self.api_url} returned non-JSON response. Status: {response.status_code}, Body: {response.text[:200]}")
            return None
        except requests.exceptions.HTTPError as e:
            if "currently loading" in e.response.text and e.response.status_code == 503:
                logger.warning(f"Model {self.hf_model_name} is loading, retrying in 20 seconds...")
                time.sleep(20)
                return self._make_api_call(inputs) # Retry once
            logger.error(f"API request failed with status {e.response.status_code} to URL {self.api_url}: {e.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed due to a network issue: {e}")
            return None

    # --- START OF ADDED LOGIC ---
    def _pool_embedding(self, embedding_output) -> Optional[np.ndarray]:
        """
        Pools token-level embeddings into a single sentence-level embedding.
        Handles both sentence-level (1D) and token-level (2D) model outputs.
        """
        if embedding_output is None:
            return None

        embedding_array = np.array(embedding_output)
        
        if embedding_array.ndim == 1:
            return embedding_array
            
        elif embedding_array.ndim == 2:
            return np.mean(embedding_array, axis=0)
            
        else:
            logger.error(f"Unexpected embedding format with {embedding_array.ndim} dimensions.")
            return None
    # --- END OF ADDED LOGIC ---

    def get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get text embedding for a single string, with pooling for token-level models."""
        if not self.is_available() or not text or not text.strip():
            return None

        result = self._make_api_call([text.strip()])
        
        if isinstance(result, list) and result:
            # MODIFICATION: Pass the raw embedding output to the pooling function
            return self._pool_embedding(result[0])
        
        logger.error(f"Unexpected API response format for single text: {result}")
        return None

    def batch_get_embeddings(self, texts: List[str], chunk_size: int = 25, chunk_delay: float = 0.5) -> List[Optional[np.ndarray]]:
        """Get embeddings for multiple texts, with pooling for token-level models."""
        if not self.is_available() or not texts:
            return []

        stripped_texts = [text.strip() for text in texts]
        all_embeddings = []
        
        for i in range(0, len(stripped_texts), chunk_size):
            chunk = stripped_texts[i:i + chunk_size]
            chunk_num = i // chunk_size + 1
            total_chunks = (len(stripped_texts) + chunk_size - 1) // chunk_size
            
            logger.info(f"Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} items) for model '{self.model_key}'")
            
            batch_results = self._make_api_call(chunk)
            
            if isinstance(batch_results, list) and all(isinstance(r, list) for r in batch_results):
                # MODIFICATION: Apply pooling to each text's embedding result in the batch
                pooled_embeddings = [self._pool_embedding(emb) for emb in batch_results]
                all_embeddings.extend(pooled_embeddings)
            else:
                logger.error(f"Unexpected batch API response format for chunk {chunk_num}. Type: {type(batch_results)}, Results: {str(batch_results)[:200]}")
                all_embeddings.extend([None] * len(chunk))
            
            if chunk_num < total_chunks and chunk_delay > 0:
                pass
        
        return all_embeddings

    def calculate_semantic_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two POOLED embeddings."""
        if embedding1 is None or embedding2 is None: return 0.0
        try:
            v1, v2 = np.array(embedding1), np.array(embedding2)
            if v1.shape != v2.shape:
                logger.warning(f"Cannot calculate similarity for embeddings with mismatched shapes: {v1.shape} vs {v2.shape}")
                return 0.0
            norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
            if norm1 == 0 or norm2 == 0: return 0.0
            return float(np.dot(v1, v2) / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0

    def is_available(self) -> bool:
        """Check if the API processor is configured."""
        return bool(self.api_token)
    
    def test_connection(self) -> bool:
        """Test the API connection with a simple request."""
        if not self.is_available():
            return False
        
        try:
            test_result = self.get_text_embedding("test")
            if test_result is not None:
                logger.info(f"API connection test successful for model '{self.model_key}'. Pooled embedding shape: {test_result.shape}")
                return True
            else:
                logger.error(f"API connection test failed for model '{self.model_key}' - no embedding returned")
                return False
        except Exception as e:
            logger.error(f"API connection test failed for model '{self.model_key}' with exception: {e}")
            return False
    
    @classmethod
    def get_available_models(cls) -> dict:
        """Return available model configurations with their details."""
        return cls.MODELS.copy()
    
    @classmethod
    def create_experimental(cls) -> 'NLPProcessor':
        """Create an instance using the experimental model."""
        return cls(model_key='experimental')