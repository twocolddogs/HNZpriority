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
        
        prompt = f"""You are an expert medical terminologist specializing in radiology procedure codes. Your primary goal is to facilitate a **many-to-one mapping** of diverse, messy, real-world exam names to a single, canonical NHS procedure name. You are creating a single source of truth.

**TASK:**
Analyze the **Input Exam** and rank the **Canonical Candidates** to find the most semantically equivalent match. The ranking should reflect which canonical name best represents the core clinical procedure described in the input.

**CORE INSTRUCTIONS:**
- **Focus on Clinical Meaning:** Ignore logistical or administrative terms in the input (e.g., "portable", "ward", "stat", "single view", "department of").
- **Embrace Many-to-One Mapping:** Different input names that describe the same procedure should map to the same canonical candidate. For example, "X-ray Chest", "CXR Portable", and "Chest 1 View" should all strongly match the canonical name "X-ray of Chest".
- **Handle Ambiguity:** If the input is less specific than the candidates (e.g., Input: "Knee MRI", Candidates: "MRI Left Knee", "MRI Right Knee"), the specific candidates are both good matches. Rank them closely.

**INPUT EXAM:**
"{{query}}"

**CANONICAL CANDIDATES (from the standard NHS list):**
{{candidates_text}}

**RANKING CRITERIA (in order of importance):**
1.  **Anatomical & Modality Core:** The fundamental anatomy and imaging modality (e.g., CT of the Head, Ultrasound of the Abdomen) must be a strong match.
    -   Major modality mismatches (e.g., CT vs. MRI) are critical failures.
    -   Minor variations (e.g., CT vs. CTA, MR vs. MRA) are very close matches and should be ranked highly.
2.  **Key Clinical Concepts:** Match critical clinical details precisely. This includes:
    -   **Laterality:** (left, right, bilateral). If the input is non-specific, a bilateral or non-specific candidate is preferred over a specific one (e.g., for input "MRI Knee", the candidate "MRI Knee" is better than "MRI Left Knee").
    -   **Contrast:** (with/without contrast, C+/C-). This must align.
    -   **Procedure Type:** (e.g., angiogram, biopsy, screening, guidance, interventional). These terms are clinically significant.
3.  **Specificity:** The ideal match has a similar level of detail.
    -   Do not penalize a match for lacking non-clinical details found in the input (e.g., "portable").
    -   Slightly prefer candidates that don't introduce significant new clinical details not mentioned in the input.

**RESPONSE FORMAT:**
Return ONLY a JSON array of the candidate numbers in ranked order (best first):
[candidate_number, candidate_number, ...]

**EXAMPLE 1:**
Input: "CT chest with contrast"
Candidates:
1. CT Chest with IV Contrast
2. CT Thorax without Contrast
3. MRI Chest with Contrast
Response: [1, 2, 3]

**EXAMPLE 2:**
Input: "Portable CXR"
Candidates:
1. X-ray of Chest
2. CT of Chest
3. X-ray of Ribs
Response: [1, 3, 2]

**EXAMPLE 3:**
Input: "US guided biopsy of liver"
Candidates:
1. Ultrasound guided biopsy of liver
2. CT guided biopsy of liver
3. Ultrasound of liver
Response: [1, 3, 2]"""

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
        Parse ranking from LLM response and convert to similarity scores.
        
        Args:
            response: Raw LLM response text containing ranked candidate numbers
            expected_count: Expected number of scores
            
        Returns:
            List of normalized scores (0.0-1.0) based on ranking
        """
        try:
            # Try to find JSON array in response
            import re
            
            # Look for JSON array pattern with candidate numbers
            json_match = re.search(r'\[[^\]]+\]', response)
            if json_match:
                json_str = json_match.group(0)
                ranking = json.loads(json_str)
                
                if isinstance(ranking, list) and len(ranking) == expected_count:
                    # Convert ranking to scores (1st place = highest score)
                    scores = [0.0] * expected_count
                    for rank_position, candidate_num in enumerate(ranking):
                        try:
                            candidate_index = int(candidate_num) - 1  # Convert to 0-based index
                            if 0 <= candidate_index < expected_count:
                                # Linear scoring: 1st place = 1.0, last place = 0.1
                                score = 1.0 - (rank_position * 0.9 / (expected_count - 1)) if expected_count > 1 else 1.0
                                scores[candidate_index] = max(0.1, score)
                        except (ValueError, TypeError, IndexError):
                            logger.warning(f"[OPENROUTER] Invalid candidate number in ranking: {candidate_num}")
                    
                    logger.debug(f"[OPENROUTER] Converted ranking {ranking} to scores successfully")
                    return scores
            
            # Fallback: try to extract ranking numbers from response
            numbers = re.findall(r'\b\d+\b', response)
            if len(numbers) == expected_count:
                scores = [0.0] * expected_count
                for rank_position, num_str in enumerate(numbers):
                    try:
                        candidate_index = int(num_str) - 1  # Convert to 0-based index
                        if 0 <= candidate_index < expected_count:
                            # Linear scoring: 1st place = 1.0, last place = 0.1
                            score = 1.0 - (rank_position * 0.9 / (expected_count - 1)) if expected_count > 1 else 1.0
                            scores[candidate_index] = max(0.1, score)
                    except (ValueError, TypeError, IndexError):
                        logger.warning(f"[OPENROUTER] Invalid candidate number: {num_str}")
                
                logger.debug(f"[OPENROUTER] Extracted ranking from text and converted to scores")
                return scores
            
            logger.warning(f"[OPENROUTER] Could not parse ranking from response: {response[:200]}...")
            return [0.5] * expected_count
            
        except Exception as e:
            logger.error(f"[OPENROUTER] Ranking parsing error: {e}")
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