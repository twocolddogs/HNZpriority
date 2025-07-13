# nlp_processor.py

import logging
from typing import Optional
from sentence_transformers import SentenceTransformer, util
import numpy as np
import torch

logger = logging.getLogger(__name__)

class NLPProcessor:
    """
    A modern NLP processor using Sentence-Transformers to generate high-quality
    semantic embeddings for entire phrases, not just individual words.
    """
    # UPDATED MODEL NAME to the powerful PubMedBERT model
    def __init__(self, model_name: str = 'microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext'):
        """
        Initializes the processor by loading a Sentence-Transformer compatible model.

        Args:
            model_name: The name of a transformer model from Hugging Face.
                        'microsoft/BiomedNLP-PubMedBERT-base...' is a powerful model
                        pre-trained from scratch on biomedical text.
        """
        self.model: Optional[SentenceTransformer] = None
        try:
            # Use CPU for local testing; Render will use whatever is available.
            device = 'cpu'
            logger.info(f"Loading Sentence-Transformer model '{model_name}' onto device: {device}")
            self.model = SentenceTransformer(model_name, device=device)
            logger.info("Sentence-Transformer model loaded successfully.")
        except Exception as e:
            logger.error(f"FATAL: Failed to load Sentence-Transformer model '{model_name}'. "
                         f"Semantic similarity will be disabled. Error: {e}", exc_info=True)

    def get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Computes the embedding (vector) for a given text string."""
        if not self.model:
            return None
        try:
            return self.model.encode(text, convert_to_numpy=True)
        except Exception as e:
            logger.error(f"Failed to encode text: '{text}'. Error: {e}")
            return None

    def calculate_semantic_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculates the cosine similarity between two embeddings."""
        try:
            return util.cos_sim(embedding1, embedding2).item()
        except Exception as e:
            logger.error(f"Failed to calculate similarity. Error: {e}")
            return 0.0