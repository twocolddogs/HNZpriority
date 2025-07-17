# nlp_processor.py

import os
import logging
import numpy as np
import requests
from typing import Optional, List
import json

logger = logging.getLogger(__name__)

class NLPProcessor:
    """
    API-based NLP processor that uses direct 'requests' calls to the correct Hugging Face
    Inference API endpoint. This approach is the most robust and reliable, bypassing
    client library issues while keeping the application lightweight to prevent memory errors.
    
    Supported Models:
    - FremyCompany/BioLORD-2023 (default): Production model optimized for biomedical text
    - ncbi/MedCPT-Query-Encoder (experimental): NCBI's Medical Clinical Practice Text encoder
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
        
        # Resolve the Hugging Face model name from the model_key
        model_info = self.MODELS.get(model_key)
        if not model_info:
            logger.warning(f"Model key '{model_key}' not found. Falling back to 'default' model.")
            model_info = self.MODELS['default']
            model_key = 'default' # Update model_key to 'default' for logging
            
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
            # Skip delay for faster cache building (Pro account has higher limits)
            
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=120)
            response.raise_for_status()
            # The JSONDecodeError indicates the response body can be empty or non-JSON on error.
            # We must handle this explicitly.
            return response.json()
        except json.JSONDecodeError:
            logger.error(f"API call to {self.api_url} returned non-JSON response. Status: {response.status_code}, Body: {response.text[:200]}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"API request failed with status {e.response.status_code} to URL {self.api_url}: {e.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed due to a network issue: {e}")
            return None

    def get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get text embedding for a single string using a direct API call."""
        if not self.is_available() or not text or not text.strip():
            return None

        result = self._make_api_call([text.strip()])
        
        if isinstance(result, list) and result and isinstance(result[0], list):
            return np.array(result[0])
        
        logger.error(f"Unexpected API response format for single text: {result}")
        return None

    def batch_get_embeddings(self, texts: List[str], chunk_size: int = 25, chunk_delay: float = 0.5) -> List[Optional[np.ndarray]]:
        """Get embeddings for multiple texts using chunked batch API calls.
        
        Args:
            texts: List of text strings to get embeddings for
            chunk_size: Number of texts to process in each API call (default: 25)
            chunk_delay: Delay in seconds between chunks (default: 0.5)
        """
        if not self.is_available() or not texts:
            return []

        stripped_texts = [text.strip() for text in texts]
        all_results = []
        
        # Process in chunks to avoid API limits and timeouts
        for i in range(0, len(stripped_texts), chunk_size):
            chunk = stripped_texts[i:i + chunk_size]
            chunk_num = i//chunk_size + 1
            total_chunks = (len(stripped_texts) + chunk_size - 1)//chunk_size
            
            logger.info(f"Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} items)")
            
            results = self._make_api_call(chunk)
            
            if isinstance(results, list) and all(isinstance(r, list) for r in results):
                all_results.extend([np.array(emb) for emb in results])
            else:
                logger.error(f"Unexpected batch API response format for chunk {chunk_num}. Type: {type(results)}, Results: {results}")
                all_results.extend([None] * len(chunk))
            
            # Skip delays for faster cache building (Pro account has higher limits)
            if chunk_num < total_chunks and chunk_delay > 0:
                logger.info(f"Skipping {chunk_delay}s delay for faster processing...")
        
        return all_results

    def calculate_semantic_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
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
            # Test with a simple text
            test_result = self.get_text_embedding("test")
            if test_result is not None:
                logger.info(f"API connection test successful for model '{self.model_key}'. Embedding shape: {test_result.shape}")
                return True
            else:
                logger.error("API connection test failed - no embedding returned")
                return False
        except Exception as e:
            logger.error(f"API connection test failed with exception: {e}")
            return False
    
    @classmethod
    def get_available_models(cls) -> dict:
        """Return available model configurations with their details."""
        return cls.MODELS.copy()
    
    @classmethod
    def create_experimental(cls) -> 'NLPProcessor':
        """Create an instance using the experimental model."""
        return cls(model_key='experimental')