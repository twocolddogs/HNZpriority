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
        # Format candidates as JSON object
        candidates_json = {}
        for i, doc in enumerate(documents, 1):
            candidates_json[str(i)] = doc
        
        candidates_json_str = json.dumps(candidates_json, indent=2)
        
        prompt = f"""You are a precision medical coding specialist responsible for mapping real-world radiology exam names to standardized NHS procedures. This is a healthcare-critical system where accuracy is paramount.

**Primary Objective:**
Rank the {len(documents)} candidate procedures from BEST to WORST match for the input exam. Your ranking directly impacts patient care by determining which standardized procedure code is selected. 

---
**INPUTS:**

1.  **`input_exam`**: The real-world exam name to be matched.
    - `{query}`

2.  **`candidate_procedures`**: A JSON object of potential matches from the NHS list.
    - `{candidates_json_str}`

---
**EVALUATION FRAMEWORK:**

Input exams come from legacy radiology systems with character limits, so assume they contain maximum relevant information despite abbreviations.

**RANKING METHODOLOGY - Apply in priority order:**

**Priority 1: Modality Match (BLOCKING - Critical for patient safety)**
- **PERFECT**: Input "CT Head" → Candidate "CT of Head"
- **ACCEPTABLE**: Input "CTA Chest" → Candidate "CT Angiography of Chest"  
- **BLOCKING FAILURE**: Input "CT Head" → Candidate "MRI of Head" (Wrong equipment/procedure)
- **Special Case**: PET/CT studies may be labeled as "NM PET/CT" (Nuclear Medicine)

**Priority 2: Clinical Specifiers (HIGH impact on procedure accuracy)**
- **Procedure Type**: Match critical terms (biopsy, angiography, guidance, interventional, screening)
  - GOOD: Input "US Guided Biopsy Liver" → Candidate "US Guided Biopsy of Liver"
  - BAD: Input "US Guided Biopsy Liver" → Candidate "US Liver" (Missing intervention)
- **Contrast Status**: Match contrast requirements exactly
  - CRITICAL: "with contrast" ≠ "without contrast" (Different clinical information)
- **Laterality Logic**:
  - Input specifies side → Candidate MUST match that side
  - Input non-specific → Prefer bilateral/non-specific over single-sided candidates

**Priority 3: Complexity Matching (Avoid over/under-specification)**
- **IGNORE administrative terms**: "portable", "ward", "stat", "single view" (not clinically relevant)
- **PENALIZE over-specification**: Don't add clinical details not in input
  - BAD: Input "MRI Brain" → Candidate "MRI Brain with Spectroscopy" (adds technique)
  - GOOD: Input "MRI Brain" → Candidate "MRI of Brain" (equivalent)
- **REWARD specific matches**: When input has specific terms, match them
  - EXCELLENT: Input "MRI Brain Diff" → Candidate "MRI Brain with Diffusion"
  - POOR: Input "MRI Brain Diff" → Candidate "MRI Brain" (ignores specificity)

---
**FINAL INSTRUCTIONS:**

1. **Apply priorities in order**: Modality match first, then clinical specifiers, then complexity matching
2. **Rank ALL {len(documents)} candidates**: Even poor matches must be ranked (worst matches go last)
3. **Consider patient safety**: Modality mismatches are dangerous and should rank last
4. **Preserve clinical intent**: The best match captures the same clinical procedure as the input

**RESPONSE FORMAT & CONSTRAINTS:**

- You **MUST** respond with **ONLY** a single, valid JSON object.
- The JSON object must contain a single key, "ranking", with a value being an array of ALL candidate numbers (as integers) in ranked order from best to worst.
- **CRITICAL**: You MUST include ALL {len(documents)} candidate numbers in your ranking. Every candidate from 1 to {len(documents)} must appear exactly once in the ranking array.
- Do not add any explanation, commentary, or markdown formatting before or after the JSON object.

**Example Response Structure for {len(documents)} candidates:**
```json
{{
  "ranking": [{', '.join(map(str, range(1, len(documents) + 1)))}]
}}"""

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
            # Try to find JSON in response (handle markdown code blocks)
            import re
            
            # First try to extract JSON from markdown code blocks
            json_block_match = re.search(r'```(?:json)?\s*(\{[^}]*"ranking"[^}]*\})\s*```', response, re.DOTALL)
            if json_block_match:
                json_str = json_block_match.group(1)
                try:
                    json_obj = json.loads(json_str)
                    if "ranking" in json_obj:
                        ranking = json_obj["ranking"]
                    else:
                        ranking = None
                except json.JSONDecodeError:
                    ranking = None
            else:
                # Fallback: Look for JSON array pattern with candidate numbers
                json_match = re.search(r'\[[^\]]+\]', response)
                if json_match:
                    json_str = json_match.group(0)
                    ranking = json.loads(json_str)
                else:
                    ranking = None
            
            if ranking and isinstance(ranking, list) and len(ranking) <= expected_count:
                # Convert ranking to scores (1st place = highest score)
                scores = [0.3] * expected_count  # Default score for unranked items
                ranked_indices = set()
                
                for rank_position, candidate_num in enumerate(ranking):
                    try:
                        candidate_index = int(candidate_num) - 1  # Convert to 0-based index
                        if 0 <= candidate_index < expected_count:
                            # Linear scoring: 1st place = 1.0, last place = 0.1
                            # Use actual ranking length for scoring, not expected count
                            score = 1.0 - (rank_position * 0.9 / (len(ranking) - 1)) if len(ranking) > 1 else 1.0
                            scores[candidate_index] = max(0.1, score)
                            ranked_indices.add(candidate_index)
                    except (ValueError, TypeError, IndexError):
                        logger.warning(f"[OPENROUTER] Invalid candidate number in ranking: {candidate_num}")
                
                # Log info about partial ranking
                if len(ranking) < expected_count:
                    missing_count = expected_count - len(ranking)
                    logger.info(f"[OPENROUTER] Partial ranking received: {len(ranking)}/{expected_count} candidates ranked, {missing_count} given default score (0.3)")
                
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
            True if connection successful, False otherwiseb
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