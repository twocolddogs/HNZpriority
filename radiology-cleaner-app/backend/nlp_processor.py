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
            self.client = InferenceClient(
                provider="hf-inference",
                api_key=self.api_token
            )
            logger.info(f"Initialized API NLP Processor with model: {model_name}")


    def get_text_similarity(self, source_text: str, target_texts: List[str]) -> List[float]:
        """Get similarity scores between source text and multiple target texts."""
        if not self.is_available() or not source_text or not target_texts:
            return []
        try:
            result = self.client.sentence_similarity(
                {
                    "source_sentence": source_text.strip(),
                    "sentences": [text.strip() for text in target_texts]
                },
                model=self.model_name
            )
            
            if isinstance(result, list):
                return result
            logger.error(f"Unexpected API response: {result}")
            return []
                
        except Exception as e:
            logger.error(f"API request failed for similarity calculation: {e}")
            return []

    def calculate_pairwise_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using the sentence similarity API."""
        if not self.is_available() or not text1 or not text2:
            return 0.0
        try:
            result = self.client.sentence_similarity(
                {
                    "source_sentence": text1.strip(),
                    "sentences": [text2.strip()]
                },
                model=self.model_name
            )
            
            if isinstance(result, list) and len(result) > 0:
                return float(result[0])
            logger.error(f"Unexpected API response for pairwise similarity: {result}")
            return 0.0
                
        except Exception as e:
            logger.error(f"Pairwise similarity calculation failed: {e}")
            return 0.0

    def find_most_similar(self, source_text: str, candidate_texts: List[str]) -> tuple[int, float]:
        """Find the most similar text from a list of candidates.
        
        Returns:
            tuple: (index of most similar text, similarity score)
        """
        if not candidate_texts:
            return -1, 0.0
            
        similarities = self.get_text_similarity(source_text, candidate_texts)
        if not similarities:
            return -1, 0.0
            
        max_index = similarities.index(max(similarities))
        return max_index, similarities[max_index]

    def is_available(self) -> bool:
        """Check if the API processor is configured and ready."""
        return bool(self.api_token and self.client)