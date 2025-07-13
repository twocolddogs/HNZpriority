import os
import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

class HybridNLPProcessor:
    """
    Hybrid NLP processor that tries API first, then falls back to local transformers.
    Optimized for biomedical text processing.
    """
    
    def __init__(self, model_name: str = 'microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext'):
        """
        Initialize the hybrid processor.
        
        Args:
            model_name: The Hugging Face model to use
        """
        self.model_name = model_name
        self.api_token = os.environ.get('HUGGING_FACE_TOKEN')
        self.model = None
        self.tokenizer = None
        self.use_local = False
        
        # Try to initialize transformers locally
        try:
            logger.info(f"Initializing local transformers model: {model_name}")
            from transformers import AutoTokenizer, AutoModel
            import torch
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name)
            self.device = 'cpu'  # Use CPU to avoid GPU dependencies
            self.model.to(self.device)
            self.model.eval()
            self.use_local = True
            
            logger.info("Local transformers model initialized successfully")
            
        except ImportError:
            logger.warning("transformers library not available, API-only mode")
        except Exception as e:
            logger.warning(f"Failed to load local model: {e}")
    
    def get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Get text embedding using local transformers model.
        
        Args:
            text: Input text to embed
            
        Returns:
            Numpy array of the embedding or None if failed
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
            
        if not self.use_local:
            logger.error("Local model not available")
            return None
            
        try:
            import torch
            
            # Tokenize text
            inputs = self.tokenizer(
                text.strip(), 
                return_tensors='pt', 
                truncation=True, 
                padding=True, 
                max_length=512
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Get embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
                
            # Use [CLS] token embedding (first token) or mean pooling
            # [CLS] token is typically used for sentence-level representations
            last_hidden_states = outputs.last_hidden_state  # Shape: [1, seq_len, hidden_size]
            
            # Option 1: Use [CLS] token
            cls_embedding = last_hidden_states[0, 0, :].cpu().numpy()
            
            # Option 2: Mean pooling (alternative)
            # attention_mask = inputs['attention_mask']
            # masked_embeddings = last_hidden_states * attention_mask.unsqueeze(-1)
            # pooled_embedding = masked_embeddings.sum(dim=1) / attention_mask.sum(dim=1, keepdim=True)
            # cls_embedding = pooled_embedding[0].cpu().numpy()
            
            return cls_embedding
            
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
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

    def is_available(self) -> bool:
        """
        Check if the processor is available.
        
        Returns:
            True if local model is loaded
        """
        return self.use_local and self.model is not None
        
    def test_connection(self) -> bool:
        """
        Test the processor with a simple request.
        
        Returns:
            True if processor is working
        """
        if not self.is_available():
            return False
            
        try:
            test_embedding = self.get_text_embedding("test")
            return test_embedding is not None
        except Exception:
            return False