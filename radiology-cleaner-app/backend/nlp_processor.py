# nlp_processor.py

import os
import logging
import numpy as np
import requests
from typing import Optional, List
import json
import time  # Added for retry logic and performance monitoring
from functools import lru_cache

logger = logging.getLogger(__name__)

class NLPProcessor:
    """
    API-based NLP processor that uses direct 'requests' calls to the Hugging Face
    Inference API. This version is robust enough to handle BOTH sentence-level models
    (like BioLORD) and token-level models (like MedCPT) by automatically applying
    mean pooling to token-level outputs.
    """

    # Available model configurations
    MODELS = {
        'retriever': {
            'hf_name': 'FremyCompany/BioLORD-2023',
            'name': 'BioLORD',
            'description': 'BioLORD - Advanced biomedical language model for retrieval',
            'pipeline': 'feature-extraction',
            'status': 'available'
        }
    }

    def __init__(self, model_key: str = 'retriever'):
        self.api_token = os.environ.get('HUGGING_FACE_TOKEN')
        
        model_info = self.MODELS.get(model_key)
        if not model_info:
            logger.warning(f"Model key '{model_key}' not found. Falling back to 'default' model.")
            model_info = self.MODELS['default']
            model_key = 'default'
            
        self.model_key = model_key
        self.hf_model_name = model_info['hf_name']
        self.model_description = model_info['description']
        self.pipeline = model_info['pipeline']
        
        self.api_url = f"https://router.huggingface.co/hf-inference/models/{self.hf_model_name}/pipeline/{self.pipeline}"
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        if not self.api_token:
            logger.error("HUGGING_FACE_TOKEN not set. API-based NLP processing is disabled.")
        else:
            logger.info(f"Initialized API NLP Processor for model '{self.model_key}': {self.hf_model_name} using direct requests.")

    def _make_api_call(self, inputs: list[str]) -> Optional[list]:
        """
        Helper function to make a POST request with an exponential-back-off retry
        strategy. Retries up to `max_retries` times on transient errors.
        """
        payload = {"inputs": inputs, "options": {"wait_for_model": True}}
        max_retries = 3
        delay = 2.0  # initial delay in seconds

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=120
                )
                response.raise_for_status()
                return response.json()

            except json.JSONDecodeError:
                logger.error(
                    f"API call to {self.api_url} returned non-JSON response. "
                    f"Status: {response.status_code}, Body: {response.text[:200]}"
                )
                return None

            except requests.exceptions.HTTPError as e:
                # 503 while model loads is considered transient
                if e.response is not None and e.response.status_code == 503:
                    logger.warning(
                        f"Attempt {attempt}/{max_retries}: model loading or 503 error "
                        f"for {self.hf_model_name}. Retrying in {delay} s…"
                    )
                else:
                    logger.error(
                        f"API request failed with status {e.response.status_code} "
                        f"to URL {self.api_url}: {e.response.text}"
                    )
                    return None

            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"Attempt {attempt}/{max_retries}: network error '{e}'. "
                    f"Retrying in {delay} s…"
                )

            # back-off and retry if attempts remain
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2  # exponential back-off
            else:
                logger.error("Max retries reached. Giving up on API request.")
                return None

    # --- START OF ADDED LOGIC ---
    def _pool_embedding(self, embedding_output) -> Optional[np.ndarray]:
        """
        Pools token-level embeddings into a single sentence-level embedding.
        Handles both sentence-level (1D) and token-level (2D) model outputs.
        """
        if embedding_output is None:
            return None

        embedding_array = np.array(embedding_output)
        
        if embedding_array.ndim == 1:
            return embedding_array
            
        elif embedding_array.ndim == 2:
            return np.mean(embedding_array, axis=0)
            
        else:
            logger.error(f"Unexpected embedding format with {embedding_array.ndim} dimensions.")
            return None
    # --- END OF ADDED LOGIC ---

    # --------------------------------------------------------------------- #
    #                               CACHING                                 #
    # --------------------------------------------------------------------- #

    def _get_embedding_uncached(self, text: str) -> Optional[np.ndarray]:
        """
        Internal helper that performs the real API call and pooling without
        caching. Split out so we can wrap a cached version around it.
        """
        if not self.is_available() or not text or not text.strip():
            return None

        result = self._make_api_call([text.strip()])
        if isinstance(result, list) and result:
            return self._pool_embedding(result[0])

        logger.error(f"Unexpected API response format for single text: {result}")
        return None

    @lru_cache(maxsize=1024)
    def _cached_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        LRU-cached wrapper around `_get_embedding_uncached`.
        Cache size 1024 should comfortably hold the most common radiology terms.
        """
        return self._get_embedding_uncached(text)

    def get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Public method to obtain (and cache) the embedding for a single text."""
        return self._cached_text_embedding(text)

    def batch_get_embeddings(self, texts: List[str], chunk_size: int = 25, chunk_delay: float = 0.5, context_label: str = "items") -> List[Optional[np.ndarray]]:
        """Get embeddings for multiple texts, with pooling for token-level models."""
        if not self.is_available() or not texts:
            return []

        stripped_texts = [text.strip() for text in texts]
        all_embeddings = []
        
        for i in range(0, len(stripped_texts), chunk_size):
            chunk = stripped_texts[i:i + chunk_size]
            chunk_num = i // chunk_size + 1
            total_chunks = (len(stripped_texts) + chunk_size - 1) // chunk_size
            
            logger.info(f"Processing {context_label} chunk {chunk_num}/{total_chunks} ({len(chunk)} items) for model '{self.model_key}'")
            
            batch_results = self._make_api_call(chunk)
            
            if isinstance(batch_results, list) and len(batch_results) == len(chunk):
                # MODIFICATION: Apply pooling to each text's embedding result in the batch
                pooled_embeddings = []
                for j, emb in enumerate(batch_results):
                    if isinstance(emb, list):
                        pooled = self._pool_embedding(emb)
                        pooled_embeddings.append(pooled)
                    else:
                        logger.warning(f"Unexpected embedding format for item {j} in chunk {chunk_num}: {type(emb)}")
                        pooled_embeddings.append(None)
                all_embeddings.extend(pooled_embeddings)
            else:
                logger.error(f"Unexpected batch API response format for chunk {chunk_num}. Expected {len(chunk)} embeddings, got {len(batch_results) if isinstance(batch_results, list) else 'non-list'}. Type: {type(batch_results)}")
                all_embeddings.extend([None] * len(chunk))
            
            if chunk_num < total_chunks and chunk_delay > 0:
                pass
        
        return all_embeddings

    def calculate_semantic_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two POOLED embeddings."""
        if embedding1 is None or embedding2 is None: return 0.0
        try:
            v1, v2 = np.array(embedding1), np.array(embedding2)
            if v1.shape != v2.shape:
                logger.warning(f"Cannot calculate similarity for embeddings with mismatched shapes: {v1.shape} vs {v2.shape}")
                return 0.0
            norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
            if norm1 == 0 or norm2 == 0: return 0.0
            return float(np.dot(v1, v2) / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0

    def _sigmoid(self, logit: float) -> float:
        """Convert logit to probability using sigmoid function."""
        try:
            return 1.0 / (1.0 + np.exp(-logit))
        except OverflowError:
            # Handle extreme negative values
            return 0.0 if logit < 0 else 1.0

    def _make_rerank_api_call(self, query: str, documents: List[str]) -> Optional[list]:
        """
        Specialized API call for cross-encoder reranking using sentence-similarity pipeline.
        HuggingFace sentence-similarity expects: {"source_sentence": query, "sentences": [docs]}
        """
        # Use correct HuggingFace sentence-similarity API format
        payload = {
            "inputs": {
                "source_sentence": query,
                "sentences": documents
            },
            "options": {"wait_for_model": True}
        }
        
        max_retries = 3
        delay = 2.0
        
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=120
                )
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                logger.error(f"[V3-RERANK] HTTP error (attempt {attempt}): {e} - Response: {response.text[:200]}")
                if attempt == max_retries:
                    return None
                time.sleep(delay)
                delay *= 2
                
            except Exception as e:
                logger.error(f"[V3-RERANK] API call error (attempt {attempt}): {e}")
                if attempt == max_retries:
                    return None
                time.sleep(delay)
                delay *= 2
        
        return None

    def get_rerank_scores(self, query: str, documents: List[str]) -> List[float]:
        """
        Get reranking scores for query-document pairs using cross-encoder model.
        
        Args:
            query: The query string
            documents: List of document strings to score against the query
            
        Returns:
            List of similarity scores (0.0-1.0) corresponding to input documents
        """
        logger.info(f"[V3-RERANK] Starting cross-encoder scoring with {self.model_key} for {len(documents)} candidates")
        logger.debug(f"[V3-RERANK] Query: '{query[:50]}{'...' if len(query) > 50 else ''}'")
        
        if not self.is_available() or not query or not documents:
            logger.warning(f"[V3-RERANK] Invalid input - available: {self.is_available()}, query: {bool(query)}, documents: {len(documents) if documents else 0}")
            return [0.0] * len(documents)
        
        if self.pipeline != 'sentence-similarity':
            logger.error(f"[V3-RERANK] Wrong pipeline '{self.pipeline}' for reranking. Expected 'sentence-similarity'.")
            return [0.0] * len(documents)
        
        try:
            # Make specialized API call for cross-encoder
            logger.debug(f"[V3-RERANK] Sending query-document pairs to {self.hf_model_name}")
            start_time = time.time()
            result = self._make_rerank_api_call(query.strip(), [doc.strip() for doc in documents])
            api_time = time.time() - start_time
            
            if result is None:
                logger.error("[V3-RERANK] API call returned None - likely model unavailable or API error")
                return [0.0] * len(documents)
            
            if not isinstance(result, list) or len(result) != len(documents):
                logger.error(f"[V3-RERANK] API response mismatch - expected {len(documents)} scores, got {type(result)} of length {len(result) if isinstance(result, list) else 'unknown'}")
                return [0.0] * len(documents)
            
            logger.info(f"[V3-RERANK] API call completed in {api_time:.2f}s - processing {len(result)} scores")
            
            # Convert logits to probabilities using sigmoid
            scores = []
            score_stats = {"min": float('inf'), "max": float('-inf'), "avg": 0}
            
            for i, logit in enumerate(result):
                try:
                    if isinstance(logit, (int, float)):
                        score = self._sigmoid(float(logit))
                        scores.append(score)
                        # Track statistics
                        score_stats["min"] = min(score_stats["min"], score)
                        score_stats["max"] = max(score_stats["max"], score)
                        score_stats["avg"] += score
                    else:
                        logger.warning(f"[V3-RERANK] Invalid score format at index {i}: {type(logit)} = {logit}")
                        scores.append(0.0)
                except (ValueError, TypeError) as e:
                    logger.warning(f"[V3-RERANK] Score processing error at index {i}: {e}")
                    scores.append(0.0)
            
            if scores:
                score_stats["avg"] /= len(scores)
                logger.info(f"[V3-RERANK] Score statistics - Min: {score_stats['min']:.3f}, Max: {score_stats['max']:.3f}, Avg: {score_stats['avg']:.3f}")
            
            return scores
            
        except Exception as e:
            logger.error(f"[V3-RERANK] Critical error in reranking: {e}")
            return [0.0] * len(documents)

    def is_available(self) -> bool:
        """Check if the API processor is configured."""
        return bool(self.api_token)
    
    def test_connection(self) -> bool:
        """Test the API connection with a simple request."""
        if not self.is_available():
            return False
        
        try:
            test_result = self.get_text_embedding("test")
            if test_result is not None:
                logger.info(f"API connection test successful for model '{self.model_key}'. Pooled embedding shape: {test_result.shape}")
                return True
            else:
                logger.error(f"API connection test failed for model '{self.model_key}' - no embedding returned")
                return False
        except Exception as e:
            logger.error(f"API connection test failed for model '{self.model_key}' with exception: {e}")
            return False
    
    @classmethod
    def get_available_models(cls) -> dict:
        """Return available model configurations with their details."""
        return cls.MODELS.copy()
    
    @classmethod
    def create_experimental(cls) -> 'NLPProcessor':
        """Create an instance using the experimental model."""
        return cls(model_key='experimental')