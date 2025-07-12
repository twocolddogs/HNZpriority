# nlp_processor.py

import logging
from typing import Optional, List
from sentence_transformers import SentenceTransformer, util
import numpy as np
import torch

logger = logging.getLogger(__name__)

class NLPProcessor:
    """
    A modern NLP processor using Sentence-Transformers to generate high-quality
    semantic embeddings for entire phrases, not just individual words.
    """
    def __init__(self, model_name: str = 'UCSD-VA-health/RadBERT-RoBERTa-4m'): # <-- UPDATED MODEL NAME
        """
        Initializes the processor by loading a Sentence-Transformer compatible model.

        Args:
            model_name: The name of a transformer model from Hugging Face.
                        'UCSD-VA-health/RadBERT-RoBERTa-4m' is chosen for its
                        specialization in the radiology domain.
        """
        self.model: Optional[SentenceTransformer] = None
        try:
            # Check for CUDA availability for faster processing
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.info(f"Loading transformer model '{model_name}' onto device: {device}")
            # The SentenceTransformer library can wrap base models like RadBERT
            # and automatically add a pooling layer to create sentence embeddings.
            self.model = SentenceTransformer(model_name, device=device)
            logger.info("Transformer model loaded successfully via Sentence-Transformer.")
        except Exception as e:
            logger.error(f"FATAL: Failed to load transformer model '{model_name}'. "
                         f"Semantic similarity will be disabled. Error: {e}", exc_info=True)

    def get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Computes the embedding (vector) for a given text string.

        Args:
            text: The text to embed.

        Returns:
            A numpy array representing the embedding, or None if the model is not loaded.
        """
        if not self.model:
            return None
        try:
            # The encode method directly returns the embedding for the text.
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Failed to encode text: '{text}'. Error: {e}")
            return None

    def calculate_semantic_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculates the cosine similarity between two embeddings.

        Args:
            embedding1: The first embedding vector.
            embedding2: The second embedding vector.

        Returns:
            A float between -1 and 1 representing the similarity.
        """
        try:
            # util.cos_sim returns a tensor, we extract the float value.
            similarity_score = util.cos_sim(embedding1, embedding2).item()
            return similarity_score
        except Exception as e:
            logger.error(f"Failed to calculate similarity. Error: {e}")
            return 0.0