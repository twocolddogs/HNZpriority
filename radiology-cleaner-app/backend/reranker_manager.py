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
            # Load the existing MedCPT processor - avoid circular import by initializing directly
            from nlp_processor import NLPProcessor
            medcpt_processor = NLPProcessor(model_key='experimental')
            
            if medcpt_processor and medcpt_processor.is_available():
                self.rerankers['medcpt'] = medcpt_processor
                self.available_rerankers['medcpt'] = {
                    'name': 'MedCPT (HuggingFace)',
                    'description': 'NCBI Medical Clinical Practice Text cross-encoder',
                    'type': 'huggingface',
                    'model_id': medcpt_processor.hf_model_name,
                    'status': 'available'
                }
                logger.info("✅ [RERANKER-MGR] MedCPT reranker available")
            else:
                self.available_rerankers['medcpt'] = {
                    'name': 'MedCPT (HuggingFace)',
                    'description': 'NCBI Medical Clinical Practice Text cross-encoder',
                    'type': 'huggingface',
                    'model_id': 'ncbi/MedCPT-Cross-Encoder',
                    'status': 'unavailable'
                }
                logger.warning("⚠️ [RERANKER-MGR] MedCPT reranker unavailable (missing HF token)")
                
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
        Prefers MedCPT if available, otherwise falls back to first available OpenRouter model.
        
        Returns:
            Default reranker key
        """
        # Prefer MedCPT if available
        if 'medcpt' in self.rerankers:
            return 'medcpt'
        
        # Fall back to first available OpenRouter model
        for key, info in self.available_rerankers.items():
            if info['status'] == 'available' and key in self.rerankers:
                return key
        
        # Last resort - return medcpt even if unavailable (for compatibility)
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
        
        reranker = self.get_reranker(reranker_key)
        if not reranker:
            logger.warning(f"[RERANKER-MGR] Reranker '{reranker_key}' not available, using neutral scores")
            return [0.5] * len(documents)
        
        logger.info(f"[RERANKER-MGR] Using {self.available_rerankers.get(reranker_key, {}).get('name', reranker_key)} for reranking")
        
        try:
            return reranker.get_rerank_scores(query, documents)
        except Exception as e:
            logger.error(f"[RERANKER-MGR] Error getting rerank scores with {reranker_key}: {e}")
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