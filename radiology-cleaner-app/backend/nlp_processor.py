# nlp_processor.py

import requests
import os
import logging
import numpy as np
from typing import Optional, List

logger = logging.getLogger(__name__)

class NLPProcessor:
    """
    API-based NLP processor using Hugging Face Inference API.
    This architecture keeps the application lightweight by offloading the ML model.
    """
    # Using a model fine-tuned for similarity often performs better than base models.
    # 'GPL/biobert-nli-sts' is an excellent choice for this.
    def __init__(self, model_name: str = 'GPL/biobert-nli-sts'):
        self.api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model_name}"
        self.api_token = os.environ.get('HUGGING_FACE_TOKEN')
        self.headers = {"Authorization": f"Bearer {self.api_token}"}
        
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
        """Get embedding for a single string via API."""
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
            
            token_embeddings_list = response.json()
            # API for feature extraction returns a list containing one set of token embeddings
            if isinstance(token_embeddings_list, list) and token_embeddings_list:
                return self._create_sentence_embedding(token_embeddings_list[0])
                
            logger.error(f"Unexpected API response for single text: {token_embeddings_list}")
            return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for '{text[:50]}...': {e}")
            return None

    def batch_get_embeddings(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """Get embeddings for multiple texts in a single batch API call."""
        if not self.is_available() or not texts:
            return [None] * len(texts)
            
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"inputs": [t.strip() for t in texts], "options": {"wait_for_model": True}},
                timeout=60  # Longer timeout for batch processing
            )
            response.raise_for_status()

            results = response.json()
            # The API returns a list of token-embedding-lists.
            # We iterate through it and apply mean pooling to each item.
            if isinstance(results, list):
                return [self._create_sentence_embedding(token_embs) for token_embs in results]
                
            logger.error(f"Unexpected batch API response format: {type(results)}")
            return [None] * len(texts)

        except Exception as e:
            logger.error(f"Batch API call failed: {e}")
            return [None] * len(texts)

    def calculate_semantic_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
        if emb1 is None or emb2 is None:
            return 0.0
        try:
            v1, v2 = np.array(emb1), np.array(emb2)
            norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(np.dot(v1, v2) / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0

    def is_available(self) -> bool:
        """Check if the API processor is configured and ready."""
        return bool(self.api_token)