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
    
    def __init__(self, model_key: str = 'gemini-2.5-flash-lite', api_key: Optional[str] = None, timeout: int = 30):
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
Evaluate the `input_exam`. If it represents a valid clinical procedure, rank the candidate procedures from BEST to WORST match. If it is NOT a valid procedure, indicate that no match is possible.

---
**INPUTS:**

1.  **`input_exam`**: The real-world exam name to be matched.
    - `{query}`

2.  **`candidate_procedures`**: A JSON object where keys are the candidate numbers and values are the procedure descriptions.
    ```json
    {candidates_json_str}
    ```

---
**EVALUATION FRAMEWORK:**

### ### NEW SECTION START ### ###
**Priority 0: Triage for Clinical Validity (CRITICAL FIRST STEP)**
First, analyze the `input_exam` for keywords that indicate it is NOT a diagnostic or interventional procedure. These are typically administrative or status updates.

- **Keywords to look for**: `declined`, `cancelled`, `did not arrive`, `abandoned`, `unprocessed order`, `unable to contact`, `dna`, `no report`.

- **Action**: If you find any of these keywords, the input is considered clinically invalid for matching. You **MUST** stop and return a JSON object with an empty "ranking" array. This signals that no procedure should be coded.
    - **Example**: If `input_exam` is "MRI Did Not Arrive", your entire response must be `{{"ranking": []}}`.

**If and ONLY IF the `input_exam` passes this triage step, proceed to the ranking methodology below.**
### ### NEW SECTION END ### ###

**Guiding Principle: Parsimony (STRONGLY FAVOR SIMPLICITY)**
The ideal candidate has **NO MORE clinical detail** than explicitly stated in the input. **When in doubt between two reasonable matches, ALWAYS choose the SIMPLER option.** This is a core principle of clinical coding - avoid assumptions and over-interpretation.

- **Generic Input → Generic Candidate:** If the input is simple (e.g., "XR Chest"), the best match is the simplest canonical name ("XR Chest"), not a more detailed one ("XR Chest PA View").
- **Specific Input → Specific Candidate:** If the input contains explicit details (e.g., "XR Chest PA View"), those details **must** be present in the best match.
- **CRITICAL PARSIMONY RULE**: **Never add specificity not explicitly in the input.** If the input says "C+" (generic contrast), prefer "CT with contrast" over "CT with oral contrast" unless "oral" is explicitly mentioned.
- **Ambiguity Resolution**: When input terms are ambiguous (like "C+", "contrast", "guided"), default to the **simplest interpretation** that captures the core procedure without adding assumptions.
- **Confidence Gap Override**: A simpler match should be preferred over a more complex match **even if the complex match has slightly higher confidence** (up to 0.15 difference). Parsimony trumps minor confidence differences.

**RANKING METHODOLOGY - Apply in priority order:**

**Priority 1: Modality Match (BLOCKING - Critical for patient safety)**
- **PERFECT**: Input "CT Head" → Candidate "CT of Head"
- **ACCEPTABLE**: Input "CTA Chest" → Candidate "CT Angiography of Chest"  
- **BLOCKING FAILURE**: Input "CT Head" → Candidate "MRI of Head" (Wrong equipment/procedure)
- **Hybrid Modality Handling**: An input like "NM PET/CT" is a **PERFECT** match for a candidate like "PET/CT of Chest". Treat 'NM' (Nuclear Medicine) in this context as a correct high-level category for a PET scan.

**Priority 2: Clinical Specifiers (HIGH impact on procedure accuracy)**
- **Procedure Type**: Match critical terms (biopsy, angiography, guidance, interventional, screening).
  - **CRITICAL**: If the input contains diagnostic terms like "standard", "routine", or "plain film", it **must not** be matched to a candidate that is clearly interventional (e.g., contains "biopsy", "guided", "insertion"). This is a **BLOCKING FAILURE**.
  - GOOD: Input "US Guided Biopsy Liver" → Candidate "US Guided Biopsy of Liver"
  - BAD: Input "US Guided Biopsy Liver" → Candidate "US Liver" (Missing intervention)
- **Contrast Status**: Handle contrast intelligently with parsimony
  - **Explicit contrast**: "with IV contrast" or "oral contrast only" → Match exactly
  - **Ambiguous contrast**: "C+", "contrast", "with contrast" → Prefer simpler "with contrast" over specific types ("oral only", "IV only") unless explicitly stated
  - **No contrast specified**: Prefer non-contrast procedures
  - **PARSIMONY OVERRIDE**: When contrast type is ambiguous, choose the **simpler base procedure** over specific contrast assumptions
- **Laterality Logic**:
  - Input specifies side → Candidate MUST match that side
  - Input non-specific → Prefer bilateral/non-specific over single-sided candidates
- **Angiography Logic**:
  - If the input uses a generic term like "Angiography", "Angio", "CTA", or "MRA", you **must** prioritize candidates that specify **arteries** (e.g., "CT Angiography of Aorta").
  - Penalize or rank lower any candidates that specify **veins** (e.g., "CT Venography").

**Priority 3: Parsimony Enforcement (CRITICAL - Often Most Important)**
- **Apply Parsimony Principle:** Use the **"Parsimony"** principle aggressively to rank candidates that have passed the above checks.
- **IGNORE administrative terms**: "portable", "ward", "stat", "single view" (not clinically relevant)
- **HEAVILY PENALIZE over-specification**: Adding clinical details not in input is a **MAJOR ERROR**. **This is the most common mistake - simpler matches are almost always better.**
  - **SEVERE PENALTY**: Input "CT Chest C+" → Candidate "CT Chest oral contrast only" (assumes specific contrast type)
  - **PREFERRED**: Input "CT Chest C+" → Candidate "CT Chest with contrast" (doesn't assume type)
  - **SEVERE PENALTY**: Input "MRI Brain" → Candidate "MRI Brain with Spectroscopy" (adds technique)
  - **SEVERE PENALTY**: Input "US upper limb" → Candidate "US Doppler Vein Map Upper Limb" (adds flow mapping)
  - **PREFERRED**: Input "US upper limb" → Candidate "US Upper Limb" (simple and direct)
- **REWARD explicit specificity**: When input has explicit specific terms, find the candidate that also has them.
  - EXCELLENT: Input "MRI Brain with Diffusion" → Candidate "MRI Brain with Diffusion"
- **PARSIMONY ALWAYS WINS**: If two candidates are clinically equivalent but one is simpler, **always rank the simpler one higher**. This is not negotiable.
- **Confidence Override Rule**: Prefer a simpler match even if a more complex match has up to 15% higher confidence. Parsimony is more important than minor confidence differences.

---
**CRITICAL PARSING EXAMPLES FOR AMBIGUOUS INPUTS:**

- **"CT Chest C+"** → PREFER "CT Chest" or "CT Chest with contrast" over "CT Chest oral contrast only" or "CT Chest IV contrast only"
- **"MRI Brain with contrast"** → PREFER "MRI Brain with contrast" over "MRI Brain with gadolinium"
- **"US guided biopsy"** → PREFER "US guided biopsy" over "US guided core biopsy" (unless "core" explicitly stated)
- **"XR chest portable"** → PREFER "XR Chest" (ignore administrative "portable")

**FINAL INSTRUCTIONS:**

1. **Perform Triage First**: This is the most important step.
2. **Apply ranking priorities in order**: If triage passes, use Modality -> Clinical Specifiers -> **PARSIMONY ENFORCEMENT**.
3. **Rank ALL {len(documents)} candidates**: If the input is valid, even poor matches must be ranked.
4. **Preserve clinical intent**: The best match captures the **core clinical procedure** as the input without adding assumptions.
5. **When in doubt, go simpler**: This is the most important rule for healthcare coding accuracy.

**RESPONSE FORMAT & CONSTRAINTS:**

- You **MUST** respond with **ONLY** a single, valid JSON object.
- **Case 1 (Valid Input)**: The JSON object must contain a single key, "ranking", with a value being an array of ALL candidate numbers (as integers) in ranked order from best to worst. The array **must** be a permutation of the numbers from 1 to {len(documents)}.
- **Case 2 (Invalid Input)**: The JSON object must contain a single key, "ranking", with a value of an **empty array `[]`**.
- Do not add any explanation, commentary, or markdown formatting before or after the JSON object.

**Example Response Structures:**
- **Valid Input**: `{{"ranking": [3, 1, 4, 2]}}`
- **Invalid Input**: `{{"ranking": []}}`"""

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
    
    # In class OpenRouterReranker

    def _parse_scores_from_response(self, response: str, expected_count: int) -> List[float]:
        """
        Parse ranking from LLM response and convert to similarity scores.
        Handles a special case for invalid inputs where an empty ranking is returned.
        
        Args:
            response: Raw LLM response text containing ranked candidate numbers
            expected_count: Expected number of scores
            
        Returns:
            List of normalized scores (0.0-1.0) based on ranking
        """
        try:
            import re
            
            # This regex is more robust and finds a JSON object containing the "ranking" key,
            # even if it's surrounded by other text or markdown.
            json_match = re.search(r'(\{.*?"ranking"\s*:\s*\[.*?\]\s*\})', response, re.DOTALL)
            
            if not json_match:
                logger.warning(f"[OPENROUTER] Could not parse a valid JSON object with a 'ranking' key from response: {response[:200]}...")
                return [0.5] * expected_count
                
            json_str = json_match.group(0)
            data = json.loads(json_str)
            ranking = data.get("ranking")

            # --- NEW LOGIC START ---
            # Handle the "no match found" signal from the LLM.
            # An empty list is the specific instruction we gave for invalid inputs.
            if ranking == []:
                logger.info(f"[OPENROUTER] Model identified input as clinically invalid. Returning zero scores for all {expected_count} candidates.")
                return [0.0] * expected_count
            # --- NEW LOGIC END ---

            if ranking is None or not isinstance(ranking, list):
                 logger.warning(f"[OPENROUTER] Parsed JSON but 'ranking' key is missing or not a list. Response: {json_str}")
                 return [0.5] * expected_count

            # Convert the ranking order into a list of scores
            scores = [0.3] * expected_count  # Default score for any unranked items

            # Ensure all items in ranking are integers
            try:
                ranking = [int(r) for r in ranking]
            except (ValueError, TypeError):
                logger.error(f"[OPENROUTER] Ranking contains non-integer values: {ranking}. Aborting score calculation.")
                return [0.5] * expected_count

            num_ranked_items = len(ranking)
            if num_ranked_items == 0: # Should be caught above, but as a safeguard
                 return [0.0] * expected_count

            for rank_position, candidate_num in enumerate(ranking):
                candidate_index = candidate_num - 1  # Convert to 0-based index
                
                if 0 <= candidate_index < expected_count:
                    # Linear scoring: 1st place = 1.0, last place = ~0.1
                    # This ensures the top-ranked item gets a high score.
                    score = 1.0 - (rank_position * 0.9 / (num_ranked_items - 1)) if num_ranked_items > 1 else 1.0
                    scores[candidate_index] = max(0.1, score)
                else:
                    logger.warning(f"[OPENROUTER] Ranking contained an out-of-bounds candidate number: {candidate_num}")

            if num_ranked_items < expected_count:
                missing_count = expected_count - num_ranked_items
                logger.warning(f"[OPENROUTER] Partial ranking received: {num_ranked_items}/{expected_count} candidates ranked. {missing_count} will have default score (0.3).")
            
            logger.debug(f"[OPENROUTER] Converted ranking {ranking} to scores successfully.")
            return scores
                
        except json.JSONDecodeError as e:
            logger.error(f"[OPENROUTER] Failed to decode JSON from response. Error: {e}. Response snippet: {response[:200]}...")
            return [0.5] * expected_count
        except Exception as e:
            logger.error(f"[OPENROUTER] An unexpected error occurred during ranking parsing: {e}")
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