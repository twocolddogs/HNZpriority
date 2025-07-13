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
    This architecture is designed to be lightweight, offloading the memory-intensive
    ML model to prevent out-of-memory errors in constrained environments like Render.
    """

    # Using a standard, highly-available Sentence-Transformer model to ensure reliability.
    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
        self.api_token = os.environ.get('HUGGING_FACE_TOKEN')
        self.model_name = model_name
        
        if not self.api_token:
            logger.error("HUGGING_FACE_TOKEN not set. API-based NLP processing is disabled.")
            self.client = None
        else:
            # CORRECTED INITIALIZATION:
            # By passing the model ID to the constructor, we ensure the client targets the
            # modern and correct API endpoint (e.g., /models/model-name) instead of the
            # legacy /pipeline/task/model-name endpoint that was causing the 404 errors.
            self.client = InferenceClient(model=self.model_name, token=self.api_token)
            logger.info(f"Initialized API NLP Processor with model: {model_name}")

    def get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get text embedding for a single string using the Hugging Face API."""
        if not self.is_available() or not text or not text.strip():
            return None
        try:
            # The 'model' parameter is no longer needed here as the client is now
            # pre-configured for a specific model. This call is lightweight.
            result = self.client.feature_extraction(text.strip())
            
            if isinstance(result, (np.ndarray, list)):
                return np.array(result)

            logger.error(f"Unexpected API response for single text: {type(result)}")
            return None
                
        except Exception as e:
            logger.error(f"API request failed for '{text[:50]}...': {e}")
            return None

    def batch_get_embeddings(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """Get embeddings for multiple texts in a single batch API call."""
        if not self.is_available() or not texts:
            return []
        try:
            # The 'model' parameter is also removed from this call.
            results = self.client.feature_extraction([text.strip() for text in texts])
            
            if isinstance(results, list):
                return [np.array(emb) if emb is not None else None for emb in results]
            else:
                logger.error(f"Unexpected batch API response format: {type(results)}")
                return [None] * len(texts)

        except Exception as e:
            logger.error(f"Batch API call failed: {e}")
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
        """Check if the API processor is configured and ready."""
        return bool(self.api_token and self.client)