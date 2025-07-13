# nlp_processor.py

import requests
import os
import logging
import numpy as np
from typing import Optional, List

logger = logging.getLogger(__name__)

class NLPProcessor:
    """
    API-based NLP processor using Hugging Face Inference API to generate embeddings.
    This architecture keeps the application lightweight by offloading the ML model.
    """

    # **FINAL MODEL**: Using a flagship sentence-transformer model that is
    # guaranteed to be available on the Inference API and provides excellent performance.
    def __init__(self, model_name: str = 'sentence-transformers/all-mpnet-base-v2'):
        self.api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model_name}"
        self.api_token = os.environ.get('HUGGING_FACE_TOKEN')
        self.headers = {"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}
        self.model_name = model_name

        if not self.api_token:
            logger.error("HUGGING_FACE_TOKEN not set. API-based NLP processing is disabled.")
        else:
            logger.info(f"Initialized API NLP Processor with model: {model_name}")

    def _create_sentence_embedding(self, token_embeddings: List[List[float]]) -> Optional[np.ndarray]:
        """Helper to create a single sentence embedding from token embeddings via mean pooling."""
        if not token_embeddings or not isinstance(token_embeddings[0], list):
            logger.warning(f"Cannot create sentence embedding from invalid input of type {type(token_embeddings)}")
            return None
        
        embeddings_array = np.array(token_embeddings)
        return np.mean(embeddings_array, axis=0)

    def get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get text embedding for a single string using the Hugging Face API."""
        if not self.is_available() or not text or not text.strip():
            return None
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"inputs": text.strip(), "options": {"wait_for_model": True}},
                timeout=30
            )
            response.raise_for_status()
            
            # This pipeline returns a single vector for the whole sentence directly
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return np.array(result)
            logger.error(f"Unexpected API response for single text: {result}")
            return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for '{text[:50]}...': {e}")
            return None

    def batch_get_embeddings(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """Get embeddings for multiple texts in a single batch API call."""
        if not self.is_available() or not texts:
            return []
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"inputs": [text.strip() for text in texts], "options": {"wait_for_model": True}},
                timeout=120 # Longer timeout for batch
            )
            response.raise_for_status()

            results = response.json()
            if isinstance(results, list):
                # This pipeline returns a list of vectors directly
                return [np.array(embedding) for embedding in results]
            else:
                logger.error(f"Unexpected batch API response format: {type(results)}")
                return [None] * len(texts)

        except Exception as e:
            logger.error(f"Batch API call failed: {e}")
            return [None] * len(texts)

    def calculate_semantic_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
        if embedding1 is None or embedding2 is None: return 0.0
        try:
            v1, v2 = np.array(embedding1), np.array(embedding2)
            norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
            if norm1 == 0 or norm2 == 0: return 0.0
            return float(np.dot(v1, v2) / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0

    def is_available(self) -> bool:
        """Check if the API processor is configured and ready."""
        return bool(self.api_token)