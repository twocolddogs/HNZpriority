import requests
import os
import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

class ApiNLPProcessor:
    """
    API-based NLP processor using Hugging Face Inference API.
    Uses feature extraction endpoint for generating embeddings from biomedical BERT models.
    """
    
    def __init__(self, model_name: str = 'microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext'):
        """
        Initialize the API-based processor.
        
        Args:
            model_name: The Hugging Face model to use for embeddings
        """
        # Use direct model endpoint for BERT models
        self.api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        self.api_token = os.environ.get('HUGGING_FACE_TOKEN')
        self.headers = {"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}
        self.model_name = model_name
        
        if not self.api_token:
            logger.error("HUGGING_FACE_TOKEN not set. API-based NLP processing will be disabled.")
        else:
            logger.info(f"Initialized API NLP Processor with model: {model_name}")

    def get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Get text embedding using Hugging Face API.
        
        Args:
            text: Input text to embed
            
        Returns:
            Numpy array of the embedding or None if failed
        """
        if not self.api_token:
            logger.error("HUGGING_FACE_TOKEN not set. Cannot use API.")
            return None
        
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
            
        try:
            response = requests.post(
                self.api_url, 
                headers=self.headers, 
                json={
                    "inputs": text.strip(),
                    "options": {"wait_for_model": True}
                },
                timeout=30  # 30 second timeout
            )
            response.raise_for_status()
            
            # The API returns embeddings - for BERT models this is typically a 3D array
            # [batch_size, sequence_length, hidden_size]
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                # Take the mean of token embeddings to get sentence embedding
                embeddings = np.array(result[0])  # Shape: [seq_len, hidden_size]
                sentence_embedding = np.mean(embeddings, axis=0)  # Mean pooling
                return sentence_embedding
            else:
                logger.error(f"Unexpected API response format: {type(result)}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"API call timed out for text: '{text[:50]}...'")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"API call to Hugging Face failed: {e}")
            return None

    def calculate_semantic_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        if embedding1 is None or embedding2 is None:
            logger.warning("Cannot calculate similarity with None embeddings")
            return 0.0
            
        try:
            # Cosine similarity calculation
            v1 = np.array(embedding1)
            v2 = np.array(embedding2)
            
            # Normalize vectors
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            
            if norm1 == 0 or norm2 == 0:
                logger.warning("Zero norm vector encountered in similarity calculation")
                return 0.0
                
            similarity = np.dot(v1, v2) / (norm1 * norm2)
            
            # Ensure result is between 0 and 1
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0

    def batch_get_embeddings(self, texts: list) -> list:
        """
        Get embeddings for multiple texts in a single API call.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embeddings (numpy arrays) or None values for failed texts
        """
        if not self.api_token:
            logger.error("HUGGING_FACE_TOKEN not set. Cannot use API.")
            return [None] * len(texts)
            
        if not texts:
            return []
            
        try:
            response = requests.post(
                self.api_url, 
                headers=self.headers, 
                json={
                    "inputs": [text.strip() for text in texts], 
                    "options": {"wait_for_model": True}
                },
                timeout=60  # Longer timeout for batch processing
            )
            response.raise_for_status()
            
            result = response.json()
            if isinstance(result, list):
                return [np.array(emb) if emb is not None else None for emb in result]
            else:
                logger.error(f"Unexpected batch API response format: {type(result)}")
                return [None] * len(texts)
                
        except Exception as e:
            logger.error(f"Batch API call failed: {e}")
            return [None] * len(texts)
            
    def is_available(self) -> bool:
        """
        Check if the API processor is available and configured.
        
        Returns:
            True if API token is set and processor is ready
        """
        return bool(self.api_token)
        
    def test_connection(self) -> bool:
        """
        Test the API connection with a simple request.
        
        Returns:
            True if API is accessible and working
        """
        if not self.is_available():
            return False
            
        try:
            test_embedding = self.get_text_embedding("test")
            return test_embedding is not None
        except Exception:
            return False