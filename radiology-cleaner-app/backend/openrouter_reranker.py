"""
OpenRouter-based reranker for radiology code semantic matching.
Supports GPT, Claude, and Gemini models via OpenRouter API.
"""

import os
import json
import time
import logging
from typing import List, Dict, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class OpenRouterReranker:
    """
    OpenRouter-based reranker that uses LLMs to score query-document pairs.
    Supports multiple models for easy A/B testing and performance comparison.
    """
    
    # Available reranker models via OpenRouter
    SUPPORTED_MODELS = {
        'gpt-4o-mini': {
            'name': 'GPT-4o Mini',
            'model_id': 'openai/gpt-4o-mini',
            'description': 'Fast and cost-effective OpenAI model',
            'cost_per_1k_tokens': 0.00015
        },
        'claude-3-haiku': {
            'name': 'Claude 3 Haiku',
            'model_id': 'anthropic/claude-3-haiku',
            'description': 'Fast Anthropic model optimized for speed',
            'cost_per_1k_tokens': 0.00025
        },
        'gemini-2.5-flash-lite': {
            'name': 'Gemini 2.5 Flash Lite',
            'model_id': 'google/gemini-2.5-flash-lite',
            'description': 'Google\'s lightweight Gemini model',
            'cost_per_1k_tokens': 0.000075
        }
    }
    
    def __init__(self, model_key: str = 'gpt-4o-mini', api_key: Optional[str] = None, timeout: int = 30):
        """
        Initialize OpenRouter reranker.
        
        Args:
            model_key: Key from SUPPORTED_MODELS
            api_key: OpenRouter API key (or from env var OPENROUTER_API_KEY)
            timeout: API request timeout in seconds
        """
        self.model_key = model_key
        self.model_info = self.SUPPORTED_MODELS.get(model_key)
        
        if not self.model_info:
            raise ValueError(f"Unsupported model: {model_key}. Supported: {list(self.SUPPORTED_MODELS.keys())}")
        
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            logger.warning(f"No OpenRouter API key found for {model_key}. Set OPENROUTER_API_KEY environment variable.")
        
        self.timeout = timeout
        self.base_url = "https://openrouter.ai/api/v1"
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        logger.info(f"🔄 [OPENROUTER] Initialized {self.model_info['name']} reranker")
    
    def is_available(self) -> bool:
        """Check if OpenRouter reranker is properly configured."""
        return bool(self.api_key and self.model_info)
    
    def get_rerank_scores(self, query: str, documents: List[str]) -> List[float]:
        """
        Get reranking scores for query-document pairs using OpenRouter LLM.
        
        Args:
            query: The input query/exam name
            documents: List of candidate NHS standard names
            
        Returns:
            List of similarity scores (0.0-1.0) for each document
        """
        if not self.is_available():
            logger.warning(f"[OPENROUTER] Reranker not available - API key missing")
            return [0.5] * len(documents)
        
        if not query or not documents:
            logger.warning(f"[OPENROUTER] Invalid input - query: {bool(query)}, documents: {len(documents) if documents else 0}")
            return [0.0] * len(documents)
        
        logger.info(f"[OPENROUTER] Starting reranking with {self.model_info['name']} for {len(documents)} candidates")
        
        try:
            start_time = time.time()
            
            # Build the prompt for LLM-based reranking
            prompt = self._build_reranking_prompt(query, documents)
            
            # Make API call to OpenRouter
            response = self._make_api_call(prompt)
            
            if not response:
                logger.error(f"[OPENROUTER] API call failed")
                return [0.5] * len(documents)
            
            # Parse scores from LLM response
            scores = self._parse_scores_from_response(response, len(documents))
            
            api_time = time.time() - start_time
            logger.info(f"[OPENROUTER] Completed reranking in {api_time:.2f}s")
            
            return scores
            
        except Exception as e:
            logger.error(f"[OPENROUTER] Critical error in reranking: {e}")
            return [0.5] * len(documents)
    
    def _build_reranking_prompt(self, query: str, documents: List[str]) -> str:
        """
        Build a prompt for LLM-based reranking of medical exam names.
        
        Args:
            query: Original exam name to match
            documents: List of standard NHS exam names
            
        Returns:
            Formatted prompt string
        """
        # Format candidates with indices
        candidates_text = ""
        for i, doc in enumerate(documents, 1):
            candidates_text += f"{i}. {doc}\n"
        
        prompt = f"""You are a medical imaging specialist tasked with ranking radiology exam names by semantic similarity.

Given this input exam name: "{query}"

Rank these NHS standard exam names by how well they match the input exam (1 = best match):

{candidates_text}

IMPORTANT: 
- Consider medical terminology, anatomy, imaging modality, and clinical context
- "CT" = "CAT" = Computed Tomography 
- "MR" = "MRI" = Magnetic Resonance Imaging
- Consider anatomical synonyms (e.g., "brain" = "head", "cardiac" = "heart")
- Prioritize exact clinical matches over partial matches

Respond with ONLY a JSON array of scores from 0.0 to 1.0, where 1.0 is perfect match:
[score1, score2, score3, ...]

Example response: [0.95, 0.3, 0.8, 0.1, 0.6]"""

        return prompt
    
    def _make_api_call(self, prompt: str) -> Optional[str]:
        """
        Make API call to OpenRouter.
        
        Args:
            prompt: The reranking prompt
            
        Returns:
            Response text from the API, or None if failed
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://hnzradtools.nz",
            "X-Title": "HNZ Radiology Cleaner"
        }
        
        payload = {
            "model": self.model_info['model_id'],
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,  # Low temperature for consistent scoring
            "max_tokens": 500,   # Enough for score arrays
            "top_p": 0.9
        }
        
        try:
            logger.debug(f"[OPENROUTER] Making API call to {self.model_info['model_id']}")
            
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    content = data['choices'][0]['message']['content']
                    logger.debug(f"[OPENROUTER] API response: {content[:100]}...")
                    return content
                else:
                    logger.error(f"[OPENROUTER] Unexpected response format: {data}")
                    return None
            else:
                logger.error(f"[OPENROUTER] API error {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"[OPENROUTER] API timeout after {self.timeout}s")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[OPENROUTER] Network error: {e}")
            return None
        except Exception as e:
            logger.error(f"[OPENROUTER] Unexpected error: {e}")
            return None
    
    def _parse_scores_from_response(self, response: str, expected_count: int) -> List[float]:
        """
        Parse similarity scores from LLM response.
        
        Args:
            response: Raw LLM response text
            expected_count: Expected number of scores
            
        Returns:
            List of normalized scores (0.0-1.0)
        """
        try:
            # Try to find JSON array in response
            import re
            
            # Look for JSON array pattern
            json_match = re.search(r'\[[\d\.,\s]+\]', response)
            if json_match:
                json_str = json_match.group(0)
                scores = json.loads(json_str)
                
                if isinstance(scores, list) and len(scores) == expected_count:
                    # Normalize scores to 0.0-1.0 range
                    normalized_scores = []
                    for score in scores:
                        try:
                            normalized_score = max(0.0, min(1.0, float(score)))
                            normalized_scores.append(normalized_score)
                        except (ValueError, TypeError):
                            normalized_scores.append(0.5)  # Default fallback
                    
                    logger.debug(f"[OPENROUTER] Parsed {len(normalized_scores)} scores successfully")
                    return normalized_scores
            
            # Fallback: try to extract numbers from response
            numbers = re.findall(r'0?\.\d+|\d+\.?\d*', response)
            if len(numbers) == expected_count:
                normalized_scores = []
                for num_str in numbers:
                    try:
                        score = max(0.0, min(1.0, float(num_str)))
                        normalized_scores.append(score)
                    except (ValueError, TypeError):
                        normalized_scores.append(0.5)
                
                logger.debug(f"[OPENROUTER] Extracted {len(normalized_scores)} scores from text")
                return normalized_scores
            
            logger.warning(f"[OPENROUTER] Could not parse scores from response: {response[:200]}...")
            return [0.5] * expected_count
            
        except Exception as e:
            logger.error(f"[OPENROUTER] Score parsing error: {e}")
            return [0.5] * expected_count
    
    def test_connection(self) -> bool:
        """
        Test the OpenRouter connection with a simple query.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            test_query = "CT chest"
            test_docs = ["CT Chest", "MRI Brain"]
            scores = self.get_rerank_scores(test_query, test_docs)
            
            return len(scores) == 2 and all(0.0 <= score <= 1.0 for score in scores)
            
        except Exception as e:
            logger.error(f"[OPENROUTER] Connection test failed: {e}")
            return False
    
    @classmethod
    def get_available_models(cls) -> Dict[str, Dict]:
        """Get information about all supported reranker models."""
        return cls.SUPPORTED_MODELS.copy()