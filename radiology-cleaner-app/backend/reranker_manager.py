"""
Reranker Manager for handling multiple reranker backends.
Supports both HuggingFace models (MedCPT) and OpenRouter LLMs (GPT/Claude/Gemini).
"""

import logging
from typing import List, Dict, Optional, Union
from openrouter_reranker import OpenRouterReranker
from nlp_processor import NLPProcessor

logger = logging.getLogger(__name__)

class RerankerManager:
    """
    Manages multiple reranker backends and provides a unified interface.
    Supports HuggingFace cross-encoders and OpenRouter LLM rerankers.
    """
    
    def __init__(self):
        """Initialize the reranker manager with available backends."""
        self.rerankers = {}
        self.available_rerankers = {}
        
        # Initialize HuggingFace reranker (existing MedCPT)
        self._init_huggingface_rerankers()
        
        # Initialize OpenRouter rerankers
        self._init_openrouter_rerankers()
        
        logger.info(f"🔄 [RERANKER-MGR] Initialized with {len(self.available_rerankers)} reranker options")
    
    def _init_huggingface_rerankers(self):
        """Initialize HuggingFace-based rerankers."""
        try:
            # Create MedCPT reranker directly for reranking (not available in retriever pipeline)
            # We'll initialize it directly with the HuggingFace model since it's not in NLPProcessor anymore
            self.available_rerankers['medcpt'] = {
                'name': 'MedCPT (HuggingFace)',
                'description': 'NCBI Medical Clinical Practice Text cross-encoder for reranking',
                'type': 'huggingface',
                'model_id': 'ncbi/MedCPT-Cross-Encoder',
                'status': 'available'  # Will be available if HF token is set
            }
            
            # Note: We don't initialize the actual processor here since MedCPT is removed from NLPProcessor
            # The reranking will be handled by a dedicated MedCPT implementation if needed
            logger.info("✅ [RERANKER-MGR] MedCPT reranker registered (HuggingFace)")
                
        except Exception as e:
            logger.error(f"[RERANKER-MGR] Error initializing HuggingFace rerankers: {e}")
    
    def _init_openrouter_rerankers(self):
        """Initialize OpenRouter-based rerankers."""
        try:
            openrouter_models = OpenRouterReranker.get_available_models()
            
            for model_key, model_info in openrouter_models.items():
                try:
                    reranker = OpenRouterReranker(model_key=model_key)
                    
                    if reranker.is_available():
                        self.rerankers[model_key] = reranker
                        status = 'available'
                        logger.info(f"✅ [RERANKER-MGR] {model_info['name']} reranker available")
                    else:
                        status = 'unavailable'
                        logger.warning(f"⚠️ [RERANKER-MGR] {model_info['name']} reranker unavailable (missing OpenRouter API key)")
                    
                    self.available_rerankers[model_key] = {
                        'name': model_info['name'],
                        'description': model_info['description'],
                        'type': 'openrouter',
                        'model_id': model_info['model_id'],
                        'status': status,
                        'cost_per_1k_tokens': model_info.get('cost_per_1k_tokens', 0)
                    }
                    
                except Exception as e:
                    logger.error(f"[RERANKER-MGR] Error initializing {model_key}: {e}")
                    self.available_rerankers[model_key] = {
                        'name': model_info['name'],
                        'description': f"Error: {str(e)}",
                        'type': 'openrouter',
                        'model_id': model_info['model_id'],
                        'status': 'error'
                    }
                    
        except Exception as e:
            logger.error(f"[RERANKER-MGR] Error initializing OpenRouter rerankers: {e}")
    
    def get_reranker(self, reranker_key: str) -> Optional[Union[NLPProcessor, OpenRouterReranker]]:
        """
        Get a reranker by key.
        
        Args:
            reranker_key: Key identifying the reranker (e.g., 'medcpt', 'gpt-4o-mini')
            
        Returns:
            Reranker instance or None if not available
        """
        return self.rerankers.get(reranker_key)
    
    def get_available_rerankers(self) -> Dict[str, Dict]:
        """
        Get information about all available rerankers.
        
        Returns:
            Dictionary mapping reranker keys to their info
        """
        return self.available_rerankers.copy()
    
    def get_default_reranker_key(self) -> str:
        """
        Get the default reranker key to use.
        Prefers MedCPT for medical accuracy, falls back to OpenRouter models.
        
        Returns:
            Default reranker key
        """
        # Prefer MedCPT for medical domain accuracy
        if 'medcpt' in self.available_rerankers:
            return 'medcpt'
        
        # Fall back to GPT-4o Mini if available
        if 'gpt-4o-mini' in self.rerankers:
            return 'gpt-4o-mini'
        
        # Fall back to first available OpenRouter model
        for key, info in self.available_rerankers.items():
            if info['status'] == 'available' and key in self.rerankers:
                return key
        
        # Last resort - return medcpt for compatibility
        return 'medcpt'
    
    def get_rerank_scores(self, query: str, documents: List[str], reranker_key: Optional[str] = None) -> List[float]:
        """
        Get reranking scores using the specified reranker.
        
        Args:
            query: Input query/exam name
            documents: List of candidate documents to rank
            reranker_key: Which reranker to use (defaults to default_reranker)
            
        Returns:
            List of similarity scores (0.0-1.0)
        """
        if not reranker_key:
            reranker_key = self.get_default_reranker_key()
        
        logger.info(f"[RERANKER-MGR] Using {self.available_rerankers.get(reranker_key, {}).get('name', reranker_key)} for reranking")
        
        # Handle MedCPT specially since it's no longer in NLPProcessor
        if reranker_key == 'medcpt':
            return self._get_medcpt_scores(query, documents)
        
        # Handle OpenRouter rerankers
        reranker = self.get_reranker(reranker_key)
        if not reranker:
            logger.warning(f"[RERANKER-MGR] Reranker '{reranker_key}' not available, using neutral scores")
            return [0.5] * len(documents)
        
        try:
            return reranker.get_rerank_scores(query, documents)
        except Exception as e:
            logger.error(f"[RERANKER-MGR] Error getting rerank scores with {reranker_key}: {e}")
            return [0.5] * len(documents)
    
    def _get_medcpt_scores(self, query: str, documents: List[str]) -> List[float]:
        """
        Get MedCPT reranking scores using direct HuggingFace API.
        
        Args:
            query: Input query/exam name
            documents: List of candidate documents to rank
            
        Returns:
            List of similarity scores (0.0-1.0)
        """
        try:
            import os
            import requests
            import json
            
            api_token = os.environ.get('HUGGING_FACE_TOKEN')
            if not api_token:
                logger.warning("[RERANKER-MGR] MedCPT requires HUGGING_FACE_TOKEN, using neutral scores")
                return [0.5] * len(documents)
            
            # Prepare query-document pairs for MedCPT cross-encoder
            pairs = [[query, doc] for doc in documents]
            
            headers = {"Authorization": f"Bearer {api_token}"}
            api_url = "https://api-inference.huggingface.co/models/ncbi/MedCPT-Cross-Encoder"
            
            response = requests.post(
                api_url,
                headers=headers,
                json={"inputs": pairs, "options": {"wait_for_model": True}},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) == len(documents):
                    # Convert logits to probabilities using sigmoid
                    import math
                    scores = [1.0 / (1.0 + math.exp(-float(logit))) for logit in result]
                    logger.info(f"[RERANKER-MGR] MedCPT scored {len(scores)} candidates")
                    return scores
                else:
                    logger.error(f"[RERANKER-MGR] MedCPT unexpected response format: {result}")
                    return [0.5] * len(documents)
            else:
                logger.error(f"[RERANKER-MGR] MedCPT API error {response.status_code}: {response.text}")
                return [0.5] * len(documents)
                
        except Exception as e:
            logger.error(f"[RERANKER-MGR] MedCPT scoring error: {e}")
            return [0.5] * len(documents)
    
    def test_reranker(self, reranker_key: str) -> bool:
        """
        Test a specific reranker with a simple query.
        
        Args:
            reranker_key: Key identifying the reranker to test
            
        Returns:
            True if test successful, False otherwise
        """
        reranker = self.get_reranker(reranker_key)
        if not reranker:
            return False
        
        try:
            if hasattr(reranker, 'test_connection'):
                return reranker.test_connection()
            else:
                # Simple test for HuggingFace rerankers
                test_scores = reranker.get_rerank_scores("CT chest", ["CT Chest", "MRI Brain"])
                return len(test_scores) == 2 and all(0.0 <= score <= 1.0 for score in test_scores)
        except Exception as e:
            logger.error(f"[RERANKER-MGR] Test failed for {reranker_key}: {e}")
            return False