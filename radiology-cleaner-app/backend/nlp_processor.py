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

    # **UPDATED MODEL**: The original 'NeuML/pubmedbert-base-embeddings' causes a 404 error
    # with the 'feature_extraction' task required by this application's architecture.
    # While it's available for the 'sentence_similarity' task, using that would be
    # architecturally inefficient. We are switching to 'sentence-transformers/all-MiniLM-L6-v2',
    # a standard, highly-available model for the 'feature_extraction' task to ensure
    # the application functions correctly.
    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
        self.api_token = os.environ.get('HUGGING_FACE_TOKEN')
        self.model_name = model_name
        
        if not self.api_token:
            logger.error("HUGGING_FACE_TOKEN not set. API-based NLP processing is disabled.")
            self.client = None
        else:
            self.client = InferenceClient(token=self.api_token)
            logger.info(f"Initialized API NLP Processor with model: {model_name}")

    # The _create_sentence_embedding helper is removed. The old implementation was incorrect
    # for Sentence-Transformer models, which return a final sentence vector directly from the
    # feature_extraction pipeline, making manual pooling unnecessary and erroneous.

    def get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Get text embedding for a single string using the Hugging Face API.
        This method is now corrected to handle the direct vector output from Sentence-Transformer models.
        """
        if not self.is_available() or not text or not text.strip():
            return None
        try:
            # For Sentence-Transformer models, the feature_extraction API returns the final sentence vector.
            result = self.client.feature_extraction(
                text.strip(),
                model=self.model_name
            )
            
            # The client returns a numpy array or a list of floats. We wrap it for consistency.
            if isinstance(result, (np.ndarray, list)):
                return np.array(result)

            logger.error(f"Unexpected API response for single text: {type(result)}")
            return None
                
        except Exception as e:
            # This catch block correctly handles the 404 error seen in the log.
            logger.error(f"API request failed for '{text[:50]}...': {e}")
            return None

    def batch_get_embeddings(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """
        Get embeddings for multiple texts in a single batch API call.
        This method is now corrected to handle batch responses from Sentence-Transformer models.
        """
        if not self.is_available() or not texts:
            return []
        try:
            # For a batch, the API returns a list of sentence vectors.
            results = self.client.feature_extraction(
                [text.strip() for text in texts],
                model=self.model_name
            )
            
            # Expected response is a list of lists (vectors) or list of numpy arrays.
            if isinstance(results, list):
                return [np.array(emb) if emb is not None else None for emb in results]
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
            # Ensure inputs are numpy arrays for consistent calculations
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
        """Check if the API processor is configured and ready."""
        return bool(self.api_token and self.client)