# nlp_processor.py

import os
import logging
import numpy as np
from typing import Optional, List
from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)

class NLPProcessor:
    """
    API-based NLP processor using Hugging Face Inference API to generate embeddings.
    This architecture keeps the application lightweight by offloading the ML model.
    """

    # **UPDATED MODEL**: Using PubMedBERT embeddings for better medical domain performance.
    # This model is specifically trained for biomedical text understanding.
    def __init__(self, model_name: str = 'NeuML/pubmedbert-base-embeddings'):
        self.api_token = os.environ.get('HUGGING_FACE_TOKEN')
        self.model_name = model_name
        
        if not self.api_token:
            logger.error("HUGGING_FACE_TOKEN not set. API-based NLP processing is disabled.")
            self.client = None
        else:
            self.client = InferenceClient(token=self.api_token)
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
            result = self.client.feature_extraction(
                text.strip(),
                model=self.model_name
            )
            
            if isinstance(result, list) and result and isinstance(result[0], list):
                return self._create_sentence_embedding(result)
            logger.error(f"Unexpected API response for single text: {result}")
            return None
                
        except Exception as e:
            logger.error(f"API request failed for '{text[:50]}...': {e}")
            return None

    def batch_get_embeddings(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """Get embeddings for multiple texts in a single batch API call."""
        if not self.is_available() or not texts:
            return []
        try:
            results = self.client.feature_extraction(
                [text.strip() for text in texts],
                model=self.model_name
            )
            
            if isinstance(results, list):
                return [self._create_sentence_embedding(token_embeddings) for token_embeddings in results]
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
        return bool(self.api_token and self.client)