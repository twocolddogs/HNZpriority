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
    """

    def __init__(self, model_name: str = 'FremyCompany/BioLORD-2023'):
        self.api_token = os.environ.get('HUGGING_FACE_TOKEN')
        self.model_name = model_name
        
        # CORRECTED URL: Using the router endpoint format which is proven to work for this task.
        self.api_url = f"https://router.huggingface.co/hf-inference/models/{self.model_name}/pipeline/feature-extraction"
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        if not self.api_token:
            logger.error("HUGGING_FACE_TOKEN not set. API-based NLP processing is disabled.")
        else:
            logger.info(f"Initialized API NLP Processor for model: {self.model_name} using direct requests.")

    def _make_api_call(self, inputs: list[str]) -> Optional[list]:
        """Helper function to make a POST request and robustly handle the response."""
        payload = {"inputs": inputs, "options": {"wait_for_model": True}}
        try:
            # Small delay to respect API rate limits in concurrent scenarios
            import time
            time.sleep(0.1)  # 100ms delay
            
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=30)
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

    def batch_get_embeddings(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """Get embeddings for multiple texts in a single batch API call."""
        if not self.is_available() or not texts:
            return []

        # For batch processing, pass the list directly (not wrapped in another list)
        stripped_texts = [text.strip() for text in texts]
        results = self._make_api_call(stripped_texts)

        if isinstance(results, list) and all(isinstance(r, list) for r in results):
            return [np.array(emb) for emb in results]
             
        logger.error(f"Unexpected batch API response format for {len(texts)} items. Type: {type(results)}, Results: {results}")
        return [None] * len(texts)

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
                logger.info(f"API connection test successful. Embedding shape: {test_result.shape}")
                return True
            else:
                logger.error("API connection test failed - no embedding returned")
                return False
        except Exception as e:
            logger.error(f"API connection test failed with exception: {e}")
            return False