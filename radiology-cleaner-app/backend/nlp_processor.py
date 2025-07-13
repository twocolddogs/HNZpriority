# nlp_processor.py

import os
import logging
import numpy as np
# Using InferenceApi as it is the correct class for this use case.
from huggingface_hub import InferenceApi
from typing import Optional, List

logger = logging.getLogger(__name__)

class NLPProcessor:
    """
    API-based NLP processor that uses the 'InferenceApi' from huggingface_hub.
    This version correctly handles raw responses for the feature-extraction task
    as required by the API, preventing both connection and parsing errors while
    maintaining a lightweight footprint to avoid out-of-memory issues.
    """

    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
        self.api_token = os.environ.get('HUGGING_FACE_TOKEN')
        self.model_name = model_name
        self.client = None
        
        if not self.api_token:
            logger.error("HUGGING_FACE_TOKEN not set. API-based NLP processing is disabled.")
        else:
            try:
                self.client = InferenceApi(
                    repo_id=self.model_name,
                    task="feature-extraction",
                    token=self.api_token
                )
                logger.info(f"Initialized InferenceApi NLP Processor for model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize InferenceApi: {e}")
                self.client = None


    def get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get text embedding for a single string using the InferenceApi client."""
        if not self.is_available() or not text or not text.strip():
            return None
        try:
            # CORRECTED API CALL: The error log instructs us to handle the raw response.
            # We add `raw_response=True` to get the raw Response object.
            response = self.client(inputs=text.strip(), raw_response=True)
            
            # The embeddings are in the JSON body of the response.
            result = response.json()
            
            if isinstance(result, list) and result and isinstance(result[0], list):
                return np.array(result[0])
            logger.error(f"Unexpected API response for single text: {result}")
            return None
        except Exception as e:
            logger.error(f"API request via InferenceApi failed for '{text[:50]}...': {e}")
            return None

    def batch_get_embeddings(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """Get embeddings for multiple texts using a single batch call via InferenceApi."""
        if not self.is_available() or not texts:
            return []
        try:
            # CORRECTED API CALL: We also use `raw_response=True` for batch calls as per the error.
            response = self.client(inputs=[text.strip() for text in texts], raw_response=True)
            
            # Parse the JSON from the response body.
            results = response.json()
            
            if isinstance(results, list) and all(isinstance(item, list) for item in results):
                return [np.array(emb) for emb in results]
            
            logger.error(f"Unexpected batch API response format for {len(texts)} items. Type: {type(results)}")
            return [None] * len(texts)
        except Exception as e:
            logger.error(f"Batch API call via InferenceApi failed: {e}")
            return [None] * len(texts)

    def calculate_semantic_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings. This is a local, fast operation."""
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
        """Check if the API client was initialized successfully."""
        return self.client is not None