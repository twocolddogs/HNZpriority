# =============================================================================
# NHS LOOKUP ENGINE - Radiology Exam Name Standardization Pipeline
# =============================================================================
# 
# This engine implements a two-stage pipeline for standardizing radiology exam names:
# 
# STAGE 1 - RETRIEVAL: Uses BioLORD embeddings + FAISS index to find candidate matches
# STAGE 2 - RERANKING: Uses configurable rerankers (MedCPT/GPT/Claude/Gemini) + 
#                      component-based scoring to select the best match
#
# SAFETY FEATURES:
# - Hard modality filtering prevents dangerous mismatches
# - Anatomical compatibility constraints prevent impossible mappings
# - Diagnostic protection prevents diagnostic→interventional mapping errors
# - Component thresholds prevent semantic similarity from overriding clinical accuracy
#
# ARCHITECTURE:
# - Config-driven scoring with weights loaded from R2 cloud storage
# - Multiple reranker support via RerankerManager
# - Complexity filtering for simple inputs
# - Context-aware bonuses (gender, age, clinical)
# - Bilateral peer detection for laterality handling
#
# =============================================================================

import json
import logging
import re
import os
import pickle
import time
import yaml
import hashlib
import numpy as np
import faiss
from typing import Dict, List, Optional
from collections import defaultdict
from fuzzywuzzy import fuzz
from typing import TYPE_CHECKING

# Core application components
from nlp_processor import NLPProcessor
from context_detection import detect_interventional_procedure_terms
from preprocessing import get_preprocessor
from complexity import ComplexityScorer
from r2_cache_manager import R2CacheManager
from common.hash_keys import compute_request_hash_with_preimage

if TYPE_CHECKING:
    from parser import RadiologySemanticParser

logger = logging.getLogger(__name__)

class NHSLookupEngine:
    """
    Two-stage pipeline for standardizing radiology exam names against NHS SNOMED database.
    
    PIPELINE OVERVIEW:
    1. RETRIEVAL: BioLORD embeddings + FAISS search → top-k candidates
    2. RERANKING: Configurable rerankers + component scoring → best match
    
    SAFETY SYSTEMS:
    - Hard modality filtering
    - Anatomical compatibility constraints  
    - Diagnostic protection rules
    - Component score thresholds
    """
    
    def __init__(self, nhs_json_path: str, retriever_processor: NLPProcessor, reranker_manager, semantic_parser: 'RadiologySemanticParser'):
        """Initialize the NHS lookup engine with required processors and data."""
        # Core data structures
        self.nhs_data = []
        self.snomed_lookup = {}
        self.index_to_snomed_id: List[str] = []
        self.vector_index: Optional[faiss.Index] = None
        
        # Pipeline components
        self.nhs_json_path = nhs_json_path
        self.retriever_processor = retriever_processor  # BioLORD for FAISS retrieval
        self.reranker_manager = reranker_manager       # Manages multiple rerankers
        self.nlp_processor = retriever_processor       # Backward compatibility
        self.semantic_parser = semantic_parser         # Parses components from exam names
        self.complexity_scorer = ComplexityScorer()    # Scores FSN complexity
        
        # Load configuration and initialize data
        self._load_config_from_manager()
        self._load_nhs_data()
        self._build_lookup_tables()
        self._preprocess_and_parse_nhs_data()
        
        # Runtime state
        self._embeddings_loaded = False
        self._specificity_stop_words = {
            'a', 'an', 'the', 'and', 'or', 'with', 'without', 'for', 'of', 'in', 'on', 'to',
            'ct', 'mr', 'mri', 'us', 'xr', 'x-ray', 'nm', 'pet', 'scan', 'imaging', 'procedure',
            'examination', 'study', 'left', 'right', 'bilateral', 'contrast', 'view'
        }
        
        # Load validation caches for human-in-the-loop feedback  
        self.r2_manager = R2CacheManager()
        self._load_validation_caches()
        
        logger.info("NHSLookupEngine initialized with two-stage pipeline architecture.")

    # =============================================================================
    # INITIALIZATION & DATA LOADING
    # =============================================================================

    def _load_config_from_manager(self):
        """
        Load scoring configuration from R2 cloud storage via ConfigManager.
        
        Loads configuration sections for:
        - scoring: Main scoring weights and thresholds
        - modality_similarity: Cross-modality similarity matrices
        - context_scoring: Clinical context bonuses
        - preprocessing: Medical abbreviations and synonyms
        
        Falls back to safe defaults if cloud config unavailable.
        """
        try:
            from config_manager import get_config
            config_manager = get_config()
            self.config = config_manager.get_section('scoring')
            self.modality_similarity = config_manager.get_section('modality_similarity')
            self.context_scoring = config_manager.get_section('context_scoring')
            self.preprocessing_config = config_manager.get_section('preprocessing')
            logger.info("Loaded enhanced scoring configuration from R2 cloud storage")
        except Exception as e:
            logger.error(f"Could not load configuration from R2. Using default weights. Error: {e}")
            self.config = {
                'retriever_top_k': 25, 'weights_component': {'anatomy': 0.35, 'modality': 0.25, 'laterality': 0.15, 'contrast': 0.15, 'technique': 0.10},
                'weights_final': {'component': 0.55, 'semantic': 0.35, 'frequency': 0.10}, 'interventional_bonus': 0.15, 'interventional_penalty': -0.20,
                'specificity_penalty_weight': 0.05, 'exact_match_bonus': 0.25, 'synonym_match_bonus': 0.15, 'context_match_bonus': 0.10,
                'contrast_mismatch_score': 0.3, 'contrast_null_score': 0.7
            }
            self.modality_similarity, self.context_scoring, self.preprocessing_config = {}, {}, {}

    def _load_nhs_data(self):
        """
        Load NHS SNOMED database from JSON file.
        
        Each entry contains:
        - snomed_concept_id: Unique SNOMED identifier
        - primary_source_name: Standardized exam name
        - snomed_fsn: Full SNOMED Fully Specified Name
        - Additional metadata fields
        """
        try:
            with open(self.nhs_json_path, 'r', encoding='utf-8') as f:
                self.nhs_data = json.load(f)
            logger.info(f"Loaded {len(self.nhs_data)} NHS entries from {self.nhs_json_path}")
        except Exception as e:
            logger.critical(f"Failed to load NHS data: {e}", exc_info=True); raise

    def _build_lookup_tables(self):
        """
        Build SNOMED ID → NHS entry lookup table for fast access.
        Used during candidate retrieval to convert FAISS indices to NHS entries.
        """
        for entry in self.nhs_data:
            if snomed_id := entry.get("snomed_concept_id"):
                self.snomed_lookup[str(snomed_id)] = entry
        logger.info(f"Built SNOMED lookup table with {len(self.snomed_lookup)} entries")

    def _preprocess_and_parse_nhs_data(self):
        """
        Preprocess and parse all NHS entries to prepare for matching pipeline.
        
        This method enriches each NHS entry with:
        - _clean_fsn_for_embedding: Preprocessed SNOMED FSN for embeddings
        - _clean_primary_name_for_embedding: Preprocessed primary name for embeddings
        - _interventional_terms: Detected interventional procedure indicators
        - _parsed_components: Semantic components (anatomy, modality, etc.)
        - _is_complex_fsn: Binary complexity flag for filtering
        
        This preprocessing enables efficient scoring during the matching pipeline.
        """
        if not self.semantic_parser: 
            raise RuntimeError("Semantic Parser required for component parsing.")
        preprocessor = get_preprocessor()
        if not preprocessor: 
            raise RuntimeError("Preprocessor not initialized.")
        
        for entry in self.nhs_data:
            snomed_fsn_raw = entry.get("snomed_fsn", "").strip()
            primary_name_raw = entry.get("primary_source_name", "").strip()
            
            # Clean SNOMED FSN by removing type qualifiers
            snomed_fsn_clean = re.sub(r'\s*\((procedure|qualifier value|finding)\)$', '', snomed_fsn_raw, flags=re.I).strip()

            # Preprocess names for embedding generation and semantic matching
            entry["_clean_fsn_for_embedding"] = preprocessor.preprocess(snomed_fsn_clean)
            entry["_clean_primary_name_for_embedding"] = preprocessor.preprocess(primary_name_raw)
            
            # Detect interventional procedure terms for scoring bonuses/penalties
            entry["_interventional_terms"] = detect_interventional_procedure_terms(entry["_clean_primary_name_for_embedding"])
            
            # Parse semantic components (anatomy, modality, laterality, contrast, technique)
            entry['_parsed_components'] = self.semantic_parser.parse_exam_name(entry["_clean_primary_name_for_embedding"], 'Other')
            
            # Calculate complexity flag for simple input filtering (threshold 0.67)
            fsn_complexity_score = self.complexity_scorer.calculate_fsn_total_complexity(snomed_fsn_clean)
            entry["_is_complex_fsn"] = fsn_complexity_score > 0.67
    
    def _normalize_approved_cache(self, raw_data: dict) -> dict:
        """
        Normalize approved cache data to consistent internal structure.
        
        Expects canonical schema but supports legacy formats:
        - Canonical: {"entries": {hash: {"mapping_data": {...}}}}
        - Legacy: {"entries": {hash: {"result": {...}}}} (backward compatibility)
        - Legacy: {"entries": [{hash: "...", "mapping_data": {...}}]}
        - Legacy: flat {hash: {"mapping_data": {...}}}
        - Legacy: flat {hash: {...}} where value is the mapping itself
        
        Args:
            raw_data: Raw JSON data from R2
            
        Returns:
            dict: Normalized mapping as {hash: mapping_data}
        """
        if not raw_data:
            return {}
        
        normalized = {}
        
        # Check if data has 'entries' wrapper
        if 'entries' in raw_data:
            entries = raw_data['entries']
            
            # Handle list format: [{"hash": "...", "mapping_data": {...}}]
            if isinstance(entries, list):
                for item in entries:
                    if isinstance(item, dict) and 'hash' in item:
                        hash_key = item['hash']
                        if 'mapping_data' in item:
                            normalized[hash_key] = item['mapping_data']
                        elif 'result' in item:
                            # Legacy support: 'result' key instead of 'mapping_data'
                            normalized[hash_key] = item['result']
                        else:
                            # Treat the entire item (minus hash) as mapping data
                            mapping_data = {k: v for k, v in item.items() if k != 'hash'}
                            normalized[hash_key] = mapping_data
            
            # Handle dict format: {"hash": {"mapping_data": {...}}} or {"hash": {"result": {...}}}
            elif isinstance(entries, dict):
                for hash_key, entry in entries.items():
                    if isinstance(entry, dict):
                        if 'mapping_data' in entry:
                            normalized[hash_key] = entry['mapping_data']
                        elif 'result' in entry:
                            # Legacy support: 'result' key instead of 'mapping_data'
                            normalized[hash_key] = entry['result']
                        else:
                            # Treat the entire entry as mapping data
                            normalized[hash_key] = entry
        
        # Handle flat format without 'entries' wrapper (legacy)
        else:
            for hash_key, entry in raw_data.items():
                if isinstance(entry, dict):
                    if 'mapping_data' in entry:
                        normalized[hash_key] = entry['mapping_data']
                    elif 'result' in entry:
                        # Legacy support: 'result' key instead of 'mapping_data'
                        normalized[hash_key] = entry['result']
                    else:
                        # Treat the entire entry as mapping data
                        normalized[hash_key] = entry
        
        return normalized
    
    def _normalize_rejected_cache(self, raw_data: dict) -> dict:
        """
        Normalize rejected cache data to consistent internal structure.
        
        Supports multiple input schemas:
        - {"entries": {hash: {rejected_snomed_ids: [...]}}}
        - {"entries": [{hash: "...", rejected_snomed_ids: [...]}]}
        - flat {hash: {rejected_snomed_ids: [...]}}
        - flat {hash: [...]} where value is the rejection list itself
        
        Args:
            raw_data: Raw JSON data from R2
            
        Returns:
            dict: Normalized mapping as {hash: set(rejected_snomed_ids)}
        """
        if not raw_data:
            return {}
        
        normalized = {}
        
        # Check if data has 'entries' wrapper
        if 'entries' in raw_data:
            entries = raw_data['entries']
            
            # Handle list format: [{"hash": "...", "rejected_snomed_ids": [...]}]
            if isinstance(entries, list):
                for item in entries:
                    if isinstance(item, dict) and 'hash' in item:
                        hash_key = item['hash']
                        if 'rejected_snomed_ids' in item:
                            rejected_ids = item['rejected_snomed_ids']
                            if isinstance(rejected_ids, list):
                                normalized[hash_key] = set(rejected_ids)
            
            # Handle dict format: {"hash": {"rejected_snomed_ids": [...]}}
            elif isinstance(entries, dict):
                for hash_key, entry in entries.items():
                    if isinstance(entry, dict):
                        if 'rejected_snomed_ids' in entry:
                            rejected_ids = entry['rejected_snomed_ids']
                            if isinstance(rejected_ids, list):
                                normalized[hash_key] = set(rejected_ids)
                    elif isinstance(entry, list):
                        # Flat format where value is directly the list
                        normalized[hash_key] = set(entry)
        
        # Handle flat format without 'entries' wrapper
        else:
            for hash_key, entry in raw_data.items():
                if isinstance(entry, dict) and 'rejected_snomed_ids' in entry:
                    rejected_ids = entry['rejected_snomed_ids']
                    if isinstance(rejected_ids, list):
                        normalized[hash_key] = set(rejected_ids)
                elif isinstance(entry, list):
                    # Flat format where value is directly the list
                    normalized[hash_key] = set(entry)
        
        return normalized

    def _fetch_json_from_r2(self, object_key: str) -> dict:
        """Fetch and parse JSON data from R2 storage."""
        if not self.r2_manager.is_available():
            logger.warning(f"R2 not available, cannot fetch {object_key}")
            return {}
        
        try:
            # Download to temporary location
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.json') as temp_file:
                temp_path = temp_file.name
            
            if self.r2_manager.download_object(object_key, temp_path):
                with open(temp_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                os.unlink(temp_path)  # Clean up temp file
                return data
            else:
                logger.warning(f"Failed to download {object_key} from R2")
                return {}
        except Exception as e:
            logger.error(f"Error fetching JSON from R2 {object_key}: {e}")
            return {}

    def _load_validation_caches(self):
        """
        Load validation caches from R2 cloud storage for human-in-the-loop feedback.
        
        Loads only the new cache filenames:
        - validation/approved_mappings_cache.json: Hash -> complete mapping data
        - validation/rejected_mappings_cache.json: Hash -> set of rejected SNOMED IDs
        
        Normalizes the JSON payloads to robust internal structures regardless of schema format.
        """
        # Initialize validation caches
        self.approved_mappings = {}
        self.rejected_mappings = {}
        
        # Load approved mappings cache from R2 using new filename
        approved_data = self._fetch_json_from_r2('validation/approved_mappings_cache.json')
        self.approved_mappings = self._normalize_approved_cache(approved_data)
        logger.info(f"Loaded {len(self.approved_mappings)} approved mappings from R2 validation cache")
        
        # Load rejected mappings from R2 using new filename  
        rejected_data = self._fetch_json_from_r2('validation/rejected_mappings_cache.json')
        self.rejected_mappings = self._normalize_rejected_cache(rejected_data)

        logger.info(f"Loaded {len(self.rejected_mappings)} rejected mapping entries from R2 validation cache")

    def _generate_request_hash(self, exam_code: str = '', exam_name: str = '', data_source: str = '', clean_name: str = '') -> str:
        """
        Generate SHA-256 hash for request matching validation system.
        
        This must match the exact hash generation logic in validation/load_mappings.py
        to ensure proper lookup of approved/rejected mappings.
        
        Args:
            exam_code: Exam code from input
            exam_name: Original exam name
            data_source: Data source identifier  
            clean_name: Cleaned/standardized name
            
        Returns:
            SHA-256 hash string for validation cache lookup
        """
        # Use same key fields as validation system
        key_fields = [
            str(exam_code).strip().lower(),
            str(exam_name).strip().lower(), 
            str(data_source).strip().lower()
        ]
        
        # Create hash from concatenated fields (matching validation logic exactly)
        hash_input = '|'.join(key_fields)
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    
    def _generate_request_hash_from_mapping(self, mapping: Dict) -> str:
        """
        Generate SHA-256 hash from mapping dictionary (convenience method).
        
        Args:
            mapping: Dictionary containing exam_code, exam_name, data_source, clean_name
            
        Returns:
            SHA-256 hash string for validation cache lookup
        """
        return self._generate_request_hash(
            exam_code=mapping.get('exam_code', ''),
            exam_name=mapping.get('exam_name', ''), 
            data_source=mapping.get('data_source', '')
        )

    def reload_validation_caches(self) -> Dict[str, any]:
        """
        Public method to reload validation caches from R2 cloud storage.
        
        This allows external systems (API endpoints, admin tools) to refresh
        the validation caches without restarting the NHS lookup engine.
        
        Returns:
            Dict with detailed statistics of loaded approved and rejected mappings
        """
        logger.info("[VALIDATION-RELOAD] Reloading validation caches from R2...")
        
        try:
            # Clear existing caches
            old_approved_count = len(self.approved_mappings)
            old_rejected_count = len(self.rejected_mappings)
            
            self.approved_mappings.clear()
            self.rejected_mappings.clear()
            
            # Reload from R2 using existing logic
            self._load_validation_caches()
            
            result = {
                'approved_count': len(self.approved_mappings),
                'rejected_count': len(self.rejected_mappings),
                'previous_approved_count': old_approved_count,
                'previous_rejected_count': old_rejected_count,
                'approved_delta': len(self.approved_mappings) - old_approved_count,
                'rejected_delta': len(self.rejected_mappings) - old_rejected_count,
                'r2_available': self.r2_manager.is_available(),
                'status': 'success',
                'timestamp': time.time()
            }
            
            logger.info(f"[VALIDATION-RELOAD] Successfully reloaded validation caches: approved={result['approved_count']} (Δ{result['approved_delta']:+d}), rejected={result['rejected_count']} (Δ{result['rejected_delta']:+d})")
            return result
            
        except Exception as e:
            logger.error(f"[VALIDATION-RELOAD] Failed to reload validation caches: {e}")
            return {
                'approved_count': len(self.approved_mappings),
                'rejected_count': len(self.rejected_mappings),
                'previous_approved_count': old_approved_count if 'old_approved_count' in locals() else 0,
                'previous_rejected_count': old_rejected_count if 'old_rejected_count' in locals() else 0,
                'approved_delta': 0,
                'rejected_delta': 0,
                'r2_available': self.r2_manager.is_available() if hasattr(self, 'r2_manager') else False,
                'status': 'error',
                'error': str(e),
                'timestamp': time.time()
            }

    # =============================================================================
    # FAISS INDEX MANAGEMENT
    # =============================================================================
    
    def _find_local_cache_file(self) -> Optional[str]:
        """
        Find cached FAISS index file for the current retriever model.
        
        Searches in RENDER_DISK_PATH or 'embedding-caches' directory for files matching
        the pattern: {model_key}_*.cache
        
        Returns:
            Optional[str]: Path to cache file if found, None otherwise
        """
        cache_dir = os.environ.get('RENDER_DISK_PATH', 'embedding-caches')
        if not os.path.isdir(cache_dir): 
            return None
        
        for filename in os.listdir(cache_dir):
            if filename.startswith(f"{self.retriever_processor.model_key}_") and filename.endswith(".cache"):
                return os.path.join(cache_dir, filename)
        return None

    def _load_index_from_local_disk(self):
        """
        Load pre-built FAISS index and ID mappings from local disk cache.
        
        The cache contains:
        - index_data: Serialized FAISS index for vector search
        - id_mapping: List mapping FAISS indices to SNOMED IDs
        
        This avoids rebuilding the index on every startup (expensive operation).
        """
        local_cache_path = self._find_local_cache_file()
        if local_cache_path and os.path.exists(local_cache_path):
            try:
                with open(local_cache_path, 'rb') as f: 
                    cache_content = pickle.load(f)
                self.vector_index = faiss.deserialize_index(cache_content['index_data'])
                self.index_to_snomed_id = cache_content['id_mapping']
                logger.info(f"Successfully loaded FAISS index for model '{self.retriever_processor.model_key}' from: {local_cache_path}")
            except Exception as e:
                logger.critical(f"CRITICAL: Failed to load FAISS index from '{local_cache_path}': {e}.")
        else:
            logger.critical(f"CRITICAL: Cache not found on local disk for model '{self.retriever_processor.model_key}'.")

    # =============================================================================
    # MAIN STANDARDIZATION PIPELINE - ENTRY POINT
    # =============================================================================
    
    def standardize_exam(self, input_exam: str, extracted_input_components: Dict, custom_nlp_processor: Optional[NLPProcessor] = None, is_input_simple: bool = False, debug: bool = False, reranker_key: Optional[str] = None, data_source: Optional[str] = None, exam_code: Optional[str] = None) -> Dict:
        """
        V4 Two-Stage Pipeline: Retrieve candidates with BioLORD, then rerank with flexible rerankers + component scoring.
        
        Stage 1 (Retrieval): Use retriever_processor (BioLORD) to get top-k candidates via FAISS
        Stage 2 (Reranking): Use selected reranker (MedCPT/GPT/Claude/Gemini) + component scoring to find best match
        """
        if debug:
            logger.info(f"[DEBUG] Debug mode enabled for input: {input_exam}, is_input_simple: {is_input_simple}")
        
        # === REQUEST HASH LOGGING ===
        # Compute canonical hash for consistent logging across components
        # Extract modality from parsed components or fallback to parsed modality list
        input_modality = extracted_input_components.get('modality', [])
        modality_code_for_hash = input_modality[0] if input_modality else None
        
        request_hash, preimage = compute_request_hash_with_preimage(data_source, exam_code, input_exam, modality_code_for_hash)
        if debug:
            logger.info(f"[DEBUG-HASH] Request hash: {request_hash}")
            logger.info(f"[DEBUG-HASH] Preimage: {preimage}")
        
        # === EARLY APPROVAL CHECK ===
        # Check if this exact input has already been approved to skip expensive processing
        if data_source and exam_code and input_exam:
            validation_hash = self._generate_request_hash(
                exam_code=exam_code or '',
                exam_name=input_exam,
                data_source=data_source or ''
            )
            
            # Early return for approved mappings
            if validation_hash in self.approved_mappings:
                approved_mapping = self.approved_mappings[validation_hash]
                logger.info(f"[EARLY-APPROVAL] Skipping processing for pre-approved mapping: {input_exam} (hash: {validation_hash[:12]}...)")
                
                # Return approved mapping with validation metadata
                result = approved_mapping.copy()
                result.update({
                    'validation_status': 'approved_by_human',
                    'confidence': 1.0,  # Human approval = max confidence
                    'early_approval_skip': True,
                    'validation_hash': validation_hash
                })
                
                if debug:
                    result['debug_early_approval'] = True
                    result['debug_skipped_processing'] = 'Full pipeline skipped due to pre-approved mapping'
                
                return result
        
        # === VALIDATION ===
        if not self.retriever_processor or not self.retriever_processor.is_available():
            result = {'error': 'Retriever processor not available', 'confidence': 0.0}
            if debug: result['debug_early_exit'] = 'Early exit: Retriever not available'
            return result
        
        # Get the selected reranker (defaults to default if not specified)
        if not reranker_key:
            reranker_key = self.reranker_manager.get_default_reranker_key() if self.reranker_manager else 'medcpt'
        
        if not self.reranker_manager:
            result = {'error': 'Reranker manager not available', 'confidence': 0.0}
            if debug: result['debug_early_exit'] = 'Early exit: Reranker manager not available'
            return result

        # === STAGE 1: RETRIEVAL (using retriever_processor) ===
        logger.info(f"[V3-PIPELINE] Starting retrieval stage with {self.retriever_processor.model_key} ({self.retriever_processor.hf_model_name})")
        stage1_start = time.time()
        
        # Load FAISS index for retriever model if needed
        if not self._embeddings_loaded or self.nlp_processor.model_key != self.retriever_processor.model_key:
            logger.info(f"Loading index for retriever model '{self.retriever_processor.model_key}'...")
            self.nlp_processor = self.retriever_processor  # Update for backward compatibility
            self._load_index_from_local_disk()
            self._embeddings_loaded = True
        
        if not self.vector_index:
            result = {'error': 'Vector index not loaded.', 'confidence': 0.0}
            if debug: result['debug_early_exit'] = 'Early exit: Vector index not loaded'
            return result
        
        # Generate embedding for input using retriever
        input_embedding = self.retriever_processor.get_text_embedding(input_exam)
        if input_embedding is None:
            result = {'error': 'Failed to generate embedding for input.', 'confidence': 0.0}
            if debug: result['debug_early_exit'] = 'Early exit: Failed to generate embedding'
            return result
        
        # Prepare ensemble embedding and search FAISS index
        input_ensemble_embedding = np.concatenate([input_embedding, input_embedding]).astype('float32')
        faiss.normalize_L2(input_ensemble_embedding.reshape(1, -1))
        top_k = self.config['retriever_top_k']
        distances, indices = self.vector_index.search(input_ensemble_embedding.reshape(1, -1), top_k)
        
        # Get candidate entries
        candidate_snomed_ids = [self.index_to_snomed_id[i] for i in indices[0] if i < len(self.index_to_snomed_id)]
        candidate_entries = [self.snomed_lookup[str(sid)] for sid in candidate_snomed_ids if str(sid) in self.snomed_lookup]
        
        # HARD MODALITY FILTERING: Block candidates with mismatched modalities if input modality is provided
        input_modality = extracted_input_components.get('modality')
        if input_modality and len(input_modality) > 0:
            input_modality_upper = input_modality[0].upper()
            original_count = len(candidate_entries)
            
            filtered_candidates = []
            for entry in candidate_entries:
                entry_components = entry.get('_parsed_components', {})
                entry_modalities = entry_components.get('modality', [])
                
                if entry_modalities:
                    entry_modalities_upper = [m.upper() for m in entry_modalities]
                    if input_modality_upper in entry_modalities_upper:
                        filtered_candidates.append(entry)
                    else:
                        logger.debug(f"[MODALITY-FILTER] Blocked '{entry.get('primary_source_name', '')}' - modality mismatch: input '{input_modality_upper}' not in {entry_modalities_upper}")
                else:
                    # If NHS entry has no modality info, allow it through
                    filtered_candidates.append(entry)
            
            candidate_entries = filtered_candidates
            logger.info(f"[MODALITY-FILTER] Hard modality filtering: {original_count} → {len(candidate_entries)} candidates (input modality: {input_modality_upper})")
        
        if not candidate_entries:
            logger.warning("[V3-PIPELINE] Stage 1 failed - no candidates found after modality filtering")
            return {'error': 'No candidates found after modality filtering.', 'confidence': 0.0}
        
        stage1_time = time.time() - stage1_start
        logger.info(f"[V3-PIPELINE] Stage 1 completed in {stage1_time:.2f}s - retrieved {len(candidate_entries)} candidates")
        
        # Log top candidates for debugging
        if candidate_entries:
            logger.debug(f"[V3-PIPELINE] Top candidates: {', '.join([entry.get('primary_source_name', 'Unknown')[:30] for entry in candidate_entries[:3]])}")
        
        retrieval_scores = [float(distances[0][i]) for i in range(min(len(distances[0]), len(candidate_entries)))]
        logger.debug(f"[V3-PIPELINE] Retrieval scores - Min: {min(retrieval_scores):.3f}, Max: {max(retrieval_scores):.3f}, Avg: {sum(retrieval_scores)/len(retrieval_scores):.3f}")

        # === COMPLEXITY FILTERING (Between Stage 1 and 2) ===
        if is_input_simple and len(candidate_entries) > 1:
            logger.info(f"[COMPLEXITY-FILTER] Input is simple - applying complexity-based filtering to {len(candidate_entries)} candidates")
            
            # Separate candidates by complexity and semantic similarity
            prioritized_candidates = []
            simple_candidates = []
            complex_candidates = []
            
            for entry in candidate_entries:
                clean_name = entry.get('_clean_primary_name_for_embedding', '')
                is_complex_fsn = entry.get('_is_complex_fsn', False)
                
                # Check for high semantic similarity (>0.70) to preserve accurate matches
                semantic_similarity = self._calculate_semantic_similarity(input_exam, clean_name)
                
                if semantic_similarity > 0.70:
                    # High semantic match - preserve regardless of complexity
                    prioritized_candidates.append(entry)
                    logger.debug(f"[COMPLEXITY-FILTER] Preserving high-similarity match: '{clean_name[:30]}' (similarity={semantic_similarity:.3f})")
                elif not is_complex_fsn:
                    # Simple FSN for simple input - prefer these
                    simple_candidates.append(entry)
                    logger.debug(f"[COMPLEXITY-FILTER] Prioritizing simple FSN: '{clean_name[:30]}'")
                else:
                    # Complex FSN for simple input - deprioritize but keep available
                    complex_candidates.append(entry)
                    logger.debug(f"[COMPLEXITY-FILTER] Deprioritizing complex FSN: '{clean_name[:30]}'")
            
            # Reorder: high-similarity matches first, then simple FSNs, then complex FSNs
            candidate_entries = prioritized_candidates + simple_candidates + complex_candidates
            logger.info(f"[COMPLEXITY-FILTER] Reordered candidates: {len(prioritized_candidates)} high-similarity + {len(simple_candidates)} simple + {len(complex_candidates)} complex")

        # === STAGE 2: RERANKING & SCORING ===
        # Get reranker info for logging
        reranker_info = self.reranker_manager.get_available_rerankers().get(reranker_key, {})
        reranker_name = reranker_info.get('name', reranker_key)
        
        logger.info(f"[V4-PIPELINE] Starting reranking stage with {reranker_name} (key: {reranker_key})")
        stage2_start = time.time()
        
        # Prepare candidate texts for reranking
        candidate_texts = [entry.get('_clean_primary_name_for_embedding', '') for entry in candidate_entries]
        logger.debug(f"[V4-PIPELINE] Prepared {len(candidate_texts)} candidate texts for reranking")
        
        # Get reranker scores using selected reranker
        rerank_scores = self.reranker_manager.get_rerank_scores(input_exam, candidate_texts, reranker_key)
        
        # ### NEW LOGIC START ###
        # Check for the "clinically invalid" signal from the reranker (all scores are 0.0)
        is_clinically_invalid = rerank_scores and all(score == 0.0 for score in rerank_scores)

        if is_clinically_invalid:
            logger.warning(f"[V4-PIPELINE] Input exam '{input_exam}' was flagged as clinically invalid by the reranker. Aborting match.")
            # Return a specific error/status that app.py can handle
            return {
                'error': 'EXCLUDED_NON_CLINICAL',
                'message': f'Reranker identified input as non-clinical: {input_exam}',
                'confidence': 0.0,
                'all_candidates': [] # No candidates are relevant
            }
        # ### NEW LOGIC END ###

        if not rerank_scores or len(rerank_scores) != len(candidate_entries):
            logger.warning(f"[V4-PIPELINE] Reranker {reranker_name} failed (got {len(rerank_scores) if rerank_scores else 0} scores for {len(candidate_entries)} candidates) - using neutral fallback")
            rerank_scores = [0.5] * len(candidate_entries)  # Neutral fallback
        
        # Find best match by combining reranking + component scores
        best_match = None
        highest_confidence = -1.0
        
        wf = self.config['weights_final']
        
        # Check for reranker-specific weights
        reranker_specific_weights = wf.get('reranker_specific', {})
        if reranker_key in reranker_specific_weights:
            # Use reranker-specific weights
            specific_weights = reranker_specific_weights[reranker_key]
            reranker_weight = specific_weights.get('reranker', 0.45)
            component_weight = specific_weights.get('component', 0.55)
            logger.info(f"[V3-PIPELINE] Using {reranker_key}-specific weights: reranker={reranker_weight}, component={component_weight}")
        else:
            # Use default weights
            reranker_weight = wf.get('reranker', 0.45)
            component_weight = wf.get('component', 0.55)
            logger.debug(f"[V3-PIPELINE] Using default weights: reranker={reranker_weight}, component={component_weight}")
        
        component_scores = []
        final_scores = []
        position_bonuses = []
        
        logger.debug(f"[V3-PIPELINE] Processing {len(candidate_entries)} candidates with weights: reranker={reranker_weight}, component={component_weight}")
        
        for i, (entry, rerank_score) in enumerate(zip(candidate_entries, rerank_scores)):
            candidate_name = entry.get('primary_source_name', 'Unknown')
            
            # Calculate component score using extracted logic
            component_start = time.time()
            component_score = self._calculate_component_score(input_exam, extracted_input_components, entry)
            component_time = time.time() - component_start
            
            # CRITICAL SAFETY FIX: Check for explicit contrast mismatch
            # Calculate contrast score to detect dangerous explicit contradictions
            input_contrast = extracted_input_components.get('contrast', [])
            nhs_components = entry.get('_parsed_components', {})
            nhs_contrast = nhs_components.get('contrast', [])
            contrast_mismatch_score = self.config.get('contrast_mismatch_score', 0.05)
            
            # If both input and NHS have explicit contrast info and they conflict (score = contrast_mismatch_score)
            if (input_contrast and nhs_contrast and 
                not set(input_contrast).intersection(set(nhs_contrast)) and
                component_score == 0.0):  # Component score 0 indicates threshold violation
                
                logger.warning(f"[V3-PIPELINE] Rejecting '{candidate_name[:30]}' due to explicit contrast mismatch: input={input_contrast} vs NHS={nhs_contrast}")
                component_scores.append(0.0)
                final_scores.append(0.0) 
                position_bonuses.append(0.0)
                continue
            
            component_scores.append(component_score)
            
            # Combine reranker score and component score
            final_score = (reranker_weight * rerank_score) + (component_weight * component_score)
            
            # Apply position bonus if complexity filtering was used (respects reordering)
            # Only apply for non-prompt based models (HuggingFace), not for LLM rerankers
            position_bonus = 0.0
            reranker_info = self.reranker_manager.get_available_rerankers().get(reranker_key, {})
            is_openrouter_model = reranker_info.get('type') == 'openrouter'
            
            if is_input_simple and len(candidate_entries) > 1 and not is_openrouter_model:
                # Earlier positions get higher bonus (0.03 max, decays by 0.003 per position)
                # Skip for OpenRouter LLMs as they handle complexity in their own scoring
                position_bonus = max(0.0, 0.03 - (i * 0.003))
                final_score += position_bonus
                
            final_scores.append(final_score)
            position_bonuses.append(position_bonus)
            
            if final_score > highest_confidence:
                highest_confidence = final_score
                best_match = entry
                bonus_info = f" (pos_bonus={position_bonus:.3f})" if position_bonus > 0 else ""
                logger.info(f"[V3-PIPELINE] New best match: '{candidate_name[:40]}' (final_score={final_score:.3f}{bonus_info})")
            
            logger.debug(f"[V3-PIPELINE] Candidate {i+1}: '{candidate_name[:30]}' - rerank={rerank_score:.3f}, component={component_score:.3f}, final={final_score:.3f} (component_time={component_time:.3f}s)")
        
        stage2_time = time.time() - stage2_start
        
        # Log scoring statistics
        if final_scores:
            logger.info(f"[V3-PIPELINE] Stage 2 completed in {stage2_time:.2f}s")
            logger.info(f"[V3-PIPELINE] Score statistics:")
            logger.info(f"  Rerank scores - Min: {min(rerank_scores):.3f}, Max: {max(rerank_scores):.3f}, Avg: {sum(rerank_scores)/len(rerank_scores):.3f}")
            logger.info(f"  Component scores - Min: {min(component_scores):.3f}, Max: {max(component_scores):.3f}, Avg: {sum(component_scores)/len(component_scores):.3f}")
            logger.info(f"  Final scores - Min: {min(final_scores):.3f}, Max: {max(final_scores):.3f}, Avg: {sum(final_scores)/len(final_scores):.3f}")

        # === PREPARE ALL CANDIDATES FOR OUTPUT ===
        all_candidates_list = []
        if candidate_entries and final_scores:
            scored_candidates_with_details = list(zip(candidate_entries, final_scores))
            # Sort by final_score (descending)
            scored_candidates_with_details.sort(key=lambda x: x[1], reverse=True)
            
            # Format all candidates for the 'all_candidates' field
            for entry, final_score in scored_candidates_with_details:
                all_candidates_list.append({
                    'snomed_id': entry.get('snomed_concept_id', ''),
                    'primary_name': entry.get('primary_source_name', ''),
                    'snomed_fsn': entry.get('snomed_fsn', ''),
                    'confidence': round(final_score, 2)
                })

        # === RESULT FORMATTING ===
        total_time = time.time() - stage1_start
        
        if best_match:
            logger.info(f"[V3-PIPELINE] ✅ Match found in {total_time:.2f}s total")
            logger.info(f"[V3-PIPELINE] Best match: '{best_match.get('primary_source_name', '')}' (confidence={highest_confidence:.3f})")
            logger.info(f"[V3-PIPELINE] SNOMED: {best_match.get('snomed_concept_id', 'Unknown')}")
            
            # Handle laterality logic
            input_laterality = (extracted_input_components.get('laterality') or [None])[0]
            match_laterality = (best_match.get('_parsed_components', {}).get('laterality') or [None])[0]
            strip_laterality = (not input_laterality and match_laterality in ['left', 'right', 'bilateral'])
            laterally_ambiguous = (not input_laterality and match_laterality in ['left', 'right', 'bilateral'])
            
            if strip_laterality:
                if bilateral_peer := self.find_bilateral_peer_in_candidates(best_match, candidate_entries):
                    result = self._format_match_result(bilateral_peer, extracted_input_components, highest_confidence, self.retriever_processor, strip_laterality_from_name=True, input_exam_text=input_exam, force_ambiguous=laterally_ambiguous)
                    
                    # Add debug information for bilateral peer case (MUST be after _format_match_result)
                    if debug:
                        # Test debug parameter by modifying clean_name for bilateral peer
                        result['clean_name'] = result.get('clean_name', '') + ' [DEBUG MODE ACTIVE - BILATERAL]'
                        result['debug_simple'] = 'Debug parameter received successfully (bilateral peer)!'
                        logger.info("[DEBUG] Modified bilateral clean_name and added debug flag")
                        try:
                            def json_safe(value):
                                """Ensure value is JSON serializable."""
                                if value is None:
                                    return None
                                elif isinstance(value, (bool, int, str)):
                                    return value
                                elif isinstance(value, float):
                                    # Handle NaN, infinity
                                    if not (value == value):  # NaN check
                                        return 0.0
                                    elif value == float('inf'):
                                        return 999999.0
                                    elif value == float('-inf'):
                                        return -999999.0
                                    else:
                                        return float(value)
                                elif isinstance(value, (list, tuple)):
                                    return [json_safe(item) for item in value]
                                elif isinstance(value, dict):
                                    return {str(k): json_safe(v) for k, v in value.items()}
                                else:
                                    return str(value)
                            
                            debug_candidates = []
                            for i, entry in enumerate(candidate_entries[:25]):
                                candidate_data = {
                                    'rank': i + 1,
                                    'snomed_id': json_safe(entry.get('snomed_concept_id')),
                                    'primary_name': json_safe(entry.get('primary_source_name')),
                                    'fsn': json_safe(entry.get('snomed_fsn')),
                                    'is_complex_fsn': json_safe(entry.get('_is_complex_fsn', False)),
                                    'final_score': json_safe(final_scores[i] if i < len(final_scores) else 0.0),
                                    'rerank_score': json_safe(rerank_scores[i] if i < len(rerank_scores) else 0.0),
                                    'component_score': json_safe(component_scores[i] if i < len(component_scores) else 0.0),
                                    'position_bonus': json_safe(position_bonuses[i] if i < len(position_bonuses) else 0.0)
                                }
                                debug_candidates.append(candidate_data)
                            
                            result['debug'] = {
                                'input_simple': json_safe(is_input_simple),
                                'complexity_filtering_applied': json_safe(is_input_simple),
                                'total_candidates': json_safe(len(candidate_entries)),
                                'candidates': debug_candidates,
                                'note': 'Used bilateral peer for laterality adjustment'
                            }
                            logger.info(f"[DEBUG] Added JSON-safe bilateral peer debug info with {len(debug_candidates)} candidates")
                        except Exception as e:
                            logger.error(f"[DEBUG] Error creating bilateral peer debug info: {e}")
                            result['debug'] = {'error': f'Debug error: {str(e)}'}
                    
                    result['all_candidates'] = all_candidates_list
                    
                    # Apply semantic similarity safeguard to bilateral peer result
                    result = self._apply_semantic_similarity_safeguard(result, input_exam)
                    
                    # === HUMAN-IN-THE-LOOP VALIDATION CACHE CHECK ===
                    if data_source and exam_code and input_exam:
                        # Generate hash from the final result mapping
                        result_hash = self._generate_request_hash(
                            exam_code=exam_code or '',
                            exam_name=input_exam,
                            data_source=data_source or '',
                            clean_name=result.get('clean_name', '')
                        )
                        
                        # Check for approved mapping (override result with approved version)
                        if result_hash in self.approved_mappings:
                            approved_mapping = self.approved_mappings[result_hash]
                            logger.info(f"[VALIDATION-OVERRIDE] Using approved mapping for {input_exam} (hash: {result_hash[:12]}...)")
                            
                            # Override with approved mapping but preserve some original metadata
                            original_confidence = result.get('components', {}).get('confidence', 0.0)
                            result = approved_mapping.copy()
                            result.update({
                                'validation_status': 'approved_by_human',
                                'confidence': 1.0,  # Human approval = max confidence
                                'validation_hash': result_hash,
                                'original_ai_confidence': original_confidence
                            })
                            if debug:
                                result['debug_validation_override'] = True
                        
                        # Check for rejected mapping (mark as rejected but don't change result)
                        elif result_hash in self.rejected_mappings:
                            logger.info(f"[VALIDATION-REJECTED] Found rejected mapping for {input_exam} (hash: {result_hash[:12]}...)")
                            result.update({
                                'validation_status': 'rejected_by_human',
                                'validation_hash': result_hash
                            })
                            if debug:
                                result['debug_validation_rejected'] = True
                    
                    return result
            
            result = self._format_match_result(best_match, extracted_input_components, highest_confidence, self.retriever_processor, strip_laterality_from_name=strip_laterality, input_exam_text=input_exam, force_ambiguous=laterally_ambiguous)
            
            # Apply semantic similarity safeguard
            result = self._apply_semantic_similarity_safeguard(result, input_exam)
            
            # Add debug information if requested (MUST be after _format_match_result)
            if debug:
                result['debug_simple'] = 'Debug parameter received successfully!'
                logger.info("[DEBUG] Debug mode active - adding candidate analysis")
                try:
                    def json_safe(value):
                        """Ensure value is JSON serializable."""
                        if value is None:
                            return None
                        elif isinstance(value, (bool, int, str)):
                            return value
                        elif isinstance(value, float):
                            # Handle NaN, infinity
                            if not (value == value):  # NaN check
                                return 0.0
                            elif value == float('inf'):
                                return 999999.0
                            elif value == float('-inf'):
                                return -999999.0
                            else:
                                return float(value)
                        elif isinstance(value, (list, tuple)):
                            return [json_safe(item) for item in value]
                        elif isinstance(value, dict):
                            return {str(k): json_safe(v) for k, v in value.items()}
                        else:
                            return str(value)
                    
                    debug_candidates = []
                    for i, entry in enumerate(candidate_entries[:25]):  # Top 25 candidates
                        candidate_data = {
                            'rank': i + 1,
                            'snomed_id': json_safe(entry.get('snomed_concept_id')),
                            'primary_name': json_safe(entry.get('primary_source_name')),
                            'fsn': json_safe(entry.get('snomed_fsn')),
                            'is_complex_fsn': json_safe(entry.get('_is_complex_fsn', False)),
                            'final_score': json_safe(final_scores[i] if i < len(final_scores) else 0.0),
                            'rerank_score': json_safe(rerank_scores[i] if i < len(rerank_scores) else 0.0),
                            'component_score': json_safe(component_scores[i] if i < len(component_scores) else 0.0),
                            'position_bonus': json_safe(position_bonuses[i] if i < len(position_bonuses) else 0.0)
                        }
                        debug_candidates.append(candidate_data)
                    
                    result['debug'] = {
                        'input_simple': json_safe(is_input_simple),
                        'complexity_filtering_applied': json_safe(is_input_simple),
                        'total_candidates': json_safe(len(candidate_entries)),
                        'candidates': debug_candidates
                    }
                    logger.info(f"[DEBUG] Added JSON-safe debug info with {len(debug_candidates)} candidates")
                except Exception as e:
                    logger.error(f"[DEBUG] Error creating debug info: {e}")
                    result['debug'] = {'error': f'Debug error: {str(e)}'}
            
            result['all_candidates'] = all_candidates_list
            
            # === HUMAN-IN-THE-LOOP VALIDATION CACHE CHECK ===
            if data_source and exam_code and input_exam:
                # Generate hash from the final result mapping
                result_hash = self._generate_request_hash(
                    exam_code=exam_code or '',
                    exam_name=input_exam,
                    data_source=data_source or '',
                    clean_name=result.get('clean_name', '')
                )
                
                # Check for approved mapping (override result with approved version)
                if result_hash in self.approved_mappings:
                    approved_mapping = self.approved_mappings[result_hash]
                    logger.info(f"[VALIDATION-OVERRIDE] Using approved mapping for {input_exam} (hash: {result_hash[:12]}...)")
                    
                    # Override with approved mapping but preserve some original metadata
                    original_confidence = result.get('components', {}).get('confidence', 0.0)
                    result = approved_mapping.copy()
                    result.update({
                        'validation_status': 'approved_by_human',
                        'confidence': 1.0,  # Human approval = max confidence
                        'validation_hash': result_hash,
                        'original_ai_confidence': original_confidence
                    })
                    if debug:
                        result['debug_validation_override'] = True
                
                # Check for rejected mapping (mark as rejected but don't change result)
                elif result_hash in self.rejected_mappings:
                    logger.info(f"[VALIDATION-REJECTED] Found rejected mapping for {input_exam} (hash: {result_hash[:12]}...)")
                    result.update({
                        'validation_status': 'rejected_by_human',
                        'validation_hash': result_hash
                    })
                    if debug:
                        result['debug_validation_rejected'] = True
            
            return result
        
        logger.warning(f"[V3-PIPELINE] ❌ No suitable match found in {total_time:.2f}s total")
        return {'error': 'No suitable match found.', 'confidence': 0.0, 'all_candidates': all_candidates_list}

    # =============================================================================
    # COMPONENT-BASED SCORING SYSTEM
    # =============================================================================
    
    def _calculate_component_score(self, input_exam_text: str, input_components: Dict, nhs_entry: Dict) -> float:
        """
        CORE COMPONENT SCORING: Calculate rule-based match score for NHS candidate.
        
        This is the heart of the clinical matching logic that ensures safety and accuracy.
        
        SCORING PIPELINE:
        1. Check for blocking violations (diagnostic→interventional, anatomy incompatibility)
        2. Calculate individual component scores (anatomy, modality, laterality, contrast, technique)
        3. Apply component thresholds to prevent low-quality matches
        4. Combine component scores using configured weights
        5. Add interventional scoring bonuses/penalties
        6. Add context bonuses and specificity adjustments
        
        Args:
            input_exam_text: Original user input text
            input_components: Parsed semantic components from input
            nhs_entry: NHS database entry being scored
            
        Returns:
            float: Component score (0.0-1.0), or 0.0 if blocking violations detected
        """
        # 1. Check for any "blocking" level violations that should immediately reject the candidate
        diagnostic_penalty = self._check_diagnostic_protection(input_exam_text, nhs_entry)
        hybrid_modality_penalty = self._check_hybrid_modality_constraints(input_exam_text, nhs_entry)
        technique_specialization_penalty = self._check_technique_specialization_constraints(input_exam_text, nhs_entry)
        
        # Check for blocking penalties (< -1.0)
        if diagnostic_penalty < -1.0 or hybrid_modality_penalty < -1.0 or technique_specialization_penalty < -1.0:
            logger.debug(f"Blocking violation detected for '{nhs_entry.get('primary_source_name')}', returning 0.0 score.")
            return 0.0
        
        nhs_components = nhs_entry.get('_parsed_components', {})
        
        # 2. Calculate all component scores
        anatomy_score = self._calculate_anatomy_score_with_constraints(input_components, nhs_components)
        
        # Check for anatomy blocking penalty after the fact
        if anatomy_score < -1.0:
            logger.debug(f"Anatomical blocking violation for '{nhs_entry.get('primary_source_name')}', returning 0.0 score.")
            return 0.0
        
        modality_score = self._calculate_modality_score(
            input_components.get('modality', []),
            nhs_components.get('modality', [])
        )
        contrast_score = self._calculate_contrast_score(
            input_components.get('contrast', []),
            nhs_components.get('contrast', [])
        )
        technique_score = self._calculate_set_score(
            input_components.get('technique', []),
            nhs_components.get('technique', [])
        )
        
        input_lat = (input_components.get('laterality') or [None])[0]
        nhs_lat = (nhs_components.get('laterality') or [None])[0]
        laterality_score = self._calculate_laterality_score(input_lat, nhs_lat)
        
        # 3. Check component thresholds to gate low-quality matches
        if (violation := self._check_component_thresholds(anatomy_score, modality_score, laterality_score, contrast_score, technique_score)):
            logger.debug(f"Component threshold violation for '{nhs_entry.get('primary_source_name')}': {violation}")
            return 0.0
        
        # 4. Combine the component scores using weights from the config
        w = self.config['weights_component']
        component_score = (
            w.get('anatomy', 0.25) * anatomy_score +
            w.get('modality', 0.30) * modality_score +
            w.get('laterality', 0.15) * laterality_score +
            w.get('contrast', 0.20) * contrast_score +
            w.get('technique', 0.10) * technique_score
        )
        
        # 5. Add interventional scoring
        input_techniques = set(input_components.get('technique', []))
        is_input_interventional = any('Interventional' in t for t in input_techniques)
        nhs_techniques = set(nhs_components.get('technique', []))
        is_nhs_interventional = any('Interventional' in t for t in nhs_techniques)
        
        interventional_score = 0
        if is_input_interventional and is_nhs_interventional:
            interventional_score = self.config['interventional_bonus']
        elif is_input_interventional and not is_nhs_interventional:
            interventional_score = self.config['interventional_penalty']
        
        # 6. Add anatomical specificity score
        anatomical_specificity_score = self._calculate_anatomical_specificity_score(input_exam_text, nhs_entry)
        
        # 7. Add all bonuses and non-blocking penalties
        bonus_score = interventional_score + anatomical_specificity_score
        bonus_score += diagnostic_penalty + hybrid_modality_penalty + technique_specialization_penalty
        bonus_score += self._calculate_context_bonus(input_exam_text, nhs_entry, input_components.get('anatomy', []))
        bonus_score += self._calculate_synonym_bonus(input_exam_text, nhs_entry)
        bonus_score += self._calculate_biopsy_modality_preference(input_exam_text, nhs_entry)
        bonus_score += self._calculate_anatomy_specificity_preference(input_components, nhs_entry)
        
        # Exact match bonus
        if input_exam_text.strip().lower() == nhs_entry.get('primary_source_name', '').lower():
            bonus_score += self.config.get('exact_match_bonus', 0.25)
        
        final_component_score = component_score + bonus_score
        return max(0.0, min(1.0, final_component_score))

    def _calculate_set_score(self, list1: List[str], list2: List[str]) -> float:
        """
        Calculates a Jaccard similarity score between two lists of strings.
        (Intersection over Union)
        """
        set1, set2 = set(list1), set(list2)
        if not set1 and not set2:
                return 1.0  # Both empty is a perfect match.

        union = set1.union(set2)
        if not union:
                return 0.0  # Should be covered by the above, but for safety.

        intersection = set1.intersection(set2)
        return len(intersection) / len(union)
    
    def _calculate_modality_score(self, input_modality: List[str], nhs_modality: List[str]) -> float:
        # Handle empty lists
        if not input_modality or not nhs_modality: 
            return 0.5
        
        # For single modality lists, use direct comparison and similarity
        if len(input_modality) == 1 and len(nhs_modality) == 1:
            input_mod = input_modality[0]
            nhs_mod = nhs_modality[0]
            if input_mod == nhs_mod: 
                return 1.0
            return self.modality_similarity.get(input_mod, {}).get(nhs_mod, 0.0)
        
        # For multiple modalities, use set-based scoring
        return self._calculate_set_score(input_modality, nhs_modality)

    def _calculate_laterality_score(self, input_lat: Optional[str], nhs_lat: Optional[str]) -> float:
        """Calculates a more punitive score for laterality mismatches."""
        if input_lat == nhs_lat:
            return 1.0  # Perfect match
        if not input_lat or not nhs_lat:
            return 0.7  # Ambiguous match (e.g., input "Knee" vs NHS "Knee Rt")
        return 0.1  # Direct mismatch (e.g., input "Left" vs NHS "Right")

    def _calculate_contrast_score(self, input_contrast: List[str], nhs_contrast: List[str]) -> float:
        # Handle empty lists (no contrast specified)
        if not input_contrast and not nhs_contrast:
            # Both unspecified - perfect match with potential bonus
            if self.config.get('prefer_no_contrast_when_unspecified', False):
                return 1.0 + self.config.get('no_contrast_preference_bonus', 0.15)
            return 1.0
        
        # CRITICAL SAFETY: Handle unspecified input contrast
        if not input_contrast:
            # Input has no contrast specified
            if not nhs_contrast:
                # This case is already handled above
                return 1.0
            else:
                # NHS has contrast but input doesn't specify - this is dangerous!
                # Apply safety penalty to prevent adding contrast when not requested
                if self.config.get('prefer_no_contrast_when_unspecified', False):
                    return 0.1  # Heavy penalty for adding contrast when unspecified
                return self.config.get('contrast_null_score', 0.7)
        
        # Input has contrast specified but NHS doesn't
        if not nhs_contrast:
            return self.config.get('contrast_null_score', 0.7)
        
        # Both have contrast info - check for matches
        input_set = set(input_contrast)
        nhs_set = set(nhs_contrast)
        
        # Perfect match
        if input_set == nhs_set:
            return 1.0
        
        # Partial match (some overlap)
        if input_set.intersection(nhs_set):
            return 0.8
        
        # No match (e.g., 'with' vs 'without') - severe penalty
        return self.config.get('contrast_mismatch_score', 0.05)
    
    def _calculate_anatomy_score_with_constraints(self, input_components: dict, nhs_components: dict) -> float:
        """
        Calculate anatomy score with anatomical compatibility constraints.
        
        PIPELINE STEP: This method enforces anatomical compatibility constraints to prevent 
        impossible mappings like "Lower Limb" → "Head" that could cause patient safety issues.
        
        Args:
            input_components: Parsed components from user input exam name
            nhs_components: Parsed components from NHS database entry
            
        Returns:
            float: Anatomy score (0.0 to 1.0), or severe penalty (-10.0) for incompatible pairs
        """
        # Get anatomy sets from both input and NHS entry
        input_anatomy = set(str(a).lower() for a in input_components.get('anatomy', []))
        nhs_anatomy = set(str(a).lower() for a in nhs_components.get('anatomy', []))
        
        # Check if anatomical compatibility constraints are enabled
        constraint_config = self.config.get('anatomical_compatibility_constraints', {})
        if constraint_config.get('enable', False):
            # Get incompatible pairs from config
            incompatible_pairs = constraint_config.get('incompatible_pairs', [])
            blocking_penalty = constraint_config.get('blocking_penalty', -10.0)
            
            # Check each input anatomy term against each NHS anatomy term
            for input_term in input_anatomy:
                for nhs_term in nhs_anatomy:
                    # Check if this combination is in the incompatible pairs list
                    for pair in incompatible_pairs:
                        if len(pair) >= 2:
                            # Check both directions: [input, nhs] and [nhs, input]
                            if ((input_term in pair[0] or pair[0] in input_term) and 
                                (nhs_term in pair[1] or pair[1] in nhs_term)) or \
                               ((input_term in pair[1] or pair[1] in input_term) and 
                                (nhs_term in pair[0] or pair[0] in nhs_term)):
                                logger.warning(f"ANATOMICAL CONSTRAINT VIOLATION: Blocking impossible mapping "
                                             f"'{input_term}' → '{nhs_term}' (penalty: {blocking_penalty})")
                                return blocking_penalty
        
        # If no constraints violated, calculate normal set-based anatomy score
        if not input_anatomy and not nhs_anatomy: 
            return 1.0
        if not input_anatomy.union(nhs_anatomy): 
            return 0.0
        return len(input_anatomy.intersection(nhs_anatomy)) / len(input_anatomy.union(nhs_anatomy))

    # =============================================================================
    # SAFETY & CONSTRAINT CHECKS
    # =============================================================================

    def _check_component_thresholds(self, anatomy_score: float, modality_score: float, 
                                   laterality_score: float, contrast_score: float, technique_score: float) -> Optional[str]:
        """
        Check minimum component score thresholds to prevent semantic similarity override.
        
        PIPELINE STEP: This method ensures that fundamental component mismatches 
        cannot be overcome by high semantic similarity alone, maintaining clinical accuracy.
        
        Args:
            anatomy_score: Individual anatomy component score
            modality_score: Individual modality component score  
            laterality_score: Individual laterality component score
            contrast_score: Individual contrast component score
            technique_score: Individual technique component score
            
        Returns:
            Optional[str]: Violation description if threshold violated, None if passed
        """
        # Get threshold configuration
        threshold_config = self.config.get('minimum_component_thresholds', {})
        if not threshold_config.get('enable', False):
            return None
        
        # Get individual thresholds
        anatomy_min = threshold_config.get('anatomy_min', 0.1)
        modality_min = threshold_config.get('modality_min', 0.4)
        laterality_min = threshold_config.get('laterality_min', 0.0)
        contrast_min = threshold_config.get('contrast_min', 0.3)
        technique_min = threshold_config.get('technique_min', 0.0)
        
        # Check individual component thresholds
        if anatomy_score < anatomy_min:
            return f"Anatomy score {anatomy_score:.3f} below minimum {anatomy_min}"
        if modality_score < modality_min:
            return f"Modality score {modality_score:.3f} below minimum {modality_min}"
        if laterality_score < laterality_min:
            return f"Laterality score {laterality_score:.3f} below minimum {laterality_min}"
        if contrast_score < contrast_min:
            return f"Contrast score {contrast_score:.3f} below minimum {contrast_min}"
        if technique_score < technique_min:
            return f"Technique score {technique_score:.3f} below minimum {technique_min}"
        
        # Check combined component score threshold
        combined_min = threshold_config.get('combined_min', 0.25)
        w = self.config.get('weights_component', {})
        combined_score = (w.get('anatomy', 0.25) * anatomy_score + 
                         w.get('modality', 0.30) * modality_score + 
                         w.get('laterality', 0.15) * laterality_score + 
                         w.get('contrast', 0.20) * contrast_score + 
                         w.get('technique', 0.10) * technique_score)
        
        if combined_score < combined_min:
            return f"Combined component score {combined_score:.3f} below minimum {combined_min}"
        
        # All thresholds passed
        return None

    def _check_diagnostic_protection(self, input_exam_text: str, nhs_entry: dict) -> float:
        """
        Check diagnostic protection rules to prevent diagnostic exams mapping to interventional procedures.
        
        PIPELINE STEP: This method prevents diagnostic exams (marked as "Standard", "routine", etc.) 
        from being incorrectly mapped to interventional procedures (containing "excision", "biopsy", etc.).
        
        Args:
            input_exam_text: Original user input exam name
            nhs_entry: NHS database entry being considered for matching
            
        Returns:
            float: 0.0 for normal processing, or severe penalty for diagnostic→interventional violations
        """
        # Get diagnostic protection config
        protection_config = self.config.get('diagnostic_protection', {})
        if not protection_config.get('enable', False):
            return 0.0
        
        # Get keyword lists from config
        diagnostic_indicators = protection_config.get('diagnostic_indicators', [])
        interventional_indicators = protection_config.get('interventional_indicators', [])
        blocking_penalty = protection_config.get('blocking_penalty', -8.0)
        
        # Convert to lowercase for case-insensitive matching
        input_lower = input_exam_text.lower()
        nhs_name_lower = nhs_entry.get('primary_source_name', '').lower()
        
        # Check if input contains diagnostic indicators
        input_has_diagnostic = any(indicator.lower() in input_lower for indicator in diagnostic_indicators)
        
        # Check if NHS entry contains interventional indicators  
        nhs_has_interventional = any(indicator.lower() in nhs_name_lower for indicator in interventional_indicators)
        
        # If input is marked as diagnostic but NHS entry is interventional, block the mapping
        if input_has_diagnostic and nhs_has_interventional:
            # Find which specific indicators triggered the violation
            triggered_diagnostic = [ind for ind in diagnostic_indicators if ind.lower() in input_lower]
            triggered_interventional = [ind for ind in interventional_indicators if ind.lower() in nhs_name_lower]
            
            logger.warning(f"DIAGNOSTIC PROTECTION VIOLATION: Blocking diagnostic→interventional mapping. "
                          f"Input has diagnostic indicators {triggered_diagnostic}, "  
                          f"NHS entry has interventional indicators {triggered_interventional} "
                          f"(penalty: {blocking_penalty})")
            return blocking_penalty
        
        # No violation detected
        return 0.0
    
    def _check_hybrid_modality_constraints(self, input_exam_text: str, nhs_entry: dict) -> float:
        """
        Check hybrid modality constraints to prevent inappropriate hybrid modality confusion.
        
        PIPELINE STEP: This method prevents hybrid modality confusion like PET/CT → PET/MRI 
        that could affect clinical workflow and equipment availability.
        
        Args:
            input_exam_text: Original user input exam name
            nhs_entry: NHS database entry being considered for matching
            
        Returns:
            float: 0.0 for normal processing, or penalty for hybrid modality violations
        """
        # Get hybrid modality constraints config
        hybrid_config = self.config.get('hybrid_modality_constraints', {})
        if not hybrid_config.get('enable', False):
            return 0.0
        
        # Get constraint rules and penalty
        incompatibilities = hybrid_config.get('hybrid_incompatibilities', [])
        blocking_penalty = hybrid_config.get('blocking_penalty', -6.0)
        
        # Convert to lowercase for case-insensitive matching
        input_lower = input_exam_text.lower()
        nhs_name_lower = nhs_entry.get('primary_source_name', '').lower()
        
        # Check each hybrid incompatibility rule
        for rule in incompatibilities:
            input_pattern = rule.get('input_pattern', '')
            nhs_exclusions = rule.get('nhs_exclusions', [])
            reason = rule.get('reason', 'Hybrid modality constraint')
            
            # Check if input matches the pattern
            if input_pattern and re.search(input_pattern, input_lower):
                # Check if NHS entry matches any exclusion pattern
                for exclusion_pattern in nhs_exclusions:
                    if exclusion_pattern and re.search(exclusion_pattern, nhs_name_lower):
                        logger.warning(f"HYBRID MODALITY CONSTRAINT VIOLATION: {reason}. "
                                      f"Input '{input_exam_text}' matches pattern '{input_pattern}', "
                                      f"NHS entry '{nhs_entry.get('primary_source_name', '')}' "
                                      f"matches exclusion '{exclusion_pattern}' (penalty: {blocking_penalty})")
                        return blocking_penalty
        
        # No violation detected
        return 0.0
    
    def _check_technique_specialization_constraints(self, input_exam_text: str, nhs_entry: dict) -> float:
        """
        Check technique specialization constraints to prevent generic exams mapping to specialized techniques.
        
        PIPELINE STEP: This method ensures generic exam names (e.g., "MRI Brain") cannot be mapped 
        to highly specialized techniques (e.g., "Diffusion Tensor") without explicit indicators in the input.
        
        Args:
            input_exam_text: Original input exam name text
            nhs_entry: NHS database entry being evaluated
            
        Returns:
            float: 0.0 if no violation, negative penalty if specialized technique detected without indicators
        """
        # Get technique specialization configuration
        constraint_config = self.config.get('technique_specialization_constraints', {})
        if not constraint_config.get('enable', False):
            return 0.0
        
        # Get penalty for violations
        blocking_penalty = constraint_config.get('blocking_penalty', -5.0)
        specialization_rules = constraint_config.get('specialization_rules', {})
        
        # Get NHS entry text for analysis
        nhs_text = nhs_entry.get('primary_source_name', '').lower()
        input_text_lower = input_exam_text.lower()
        
        # Check each specialization rule
        for specialized_technique, rule in specialization_rules.items():
            specialized_technique_lower = specialized_technique.lower()
            required_indicators = rule.get('required_indicators', [])
            reason = rule.get('reason', 'Specialized technique requires explicit indicators')
            
            # Check if NHS entry contains this specialized technique
            if specialized_technique_lower in nhs_text:
                # Check if any required indicator is present in the input
                has_indicator = any(indicator.lower() in input_text_lower for indicator in required_indicators)
                
                if not has_indicator:
                    logger.debug(f"TECHNIQUE SPECIALIZATION VIOLATION: Input '{input_exam_text}' lacks indicators "
                               f"for specialized technique '{specialized_technique}'. Required indicators: "
                               f"{required_indicators}. Reason: {reason}")
                    return blocking_penalty
        
        # No violations detected
        return 0.0

    # =============================================================================
    # BONUS & PENALTY CALCULATIONS
    # =============================================================================

    def _calculate_context_bonus(self, input_exam: str, nhs_entry: dict, input_anatomy: List[str] = None) -> float:
        """
        Calculate context-based bonuses including gender, age, pregnancy, and clinical contexts.
        
        PIPELINE STEP: This method applies context bonuses that were previously calculated 
        post-scoring but are now integrated into the matching score calculation.
        
        Args:
            input_exam: Original user input exam name
            nhs_entry: NHS database entry being scored
            input_anatomy: Parsed anatomy from input (for context detection)
            
        Returns:
            float: Total context bonus to add to the final score
        """
        from context_detection import detect_gender_context, detect_age_context, detect_clinical_context
        
        total_bonus = 0.0
        input_lower = input_exam.lower()
        nhs_name_lower = nhs_entry.get('primary_source_name', '').lower()
        
        # PART 1: Calculate gender/age context bonuses (previously missing from scoring)
        # Detect gender context from input
        input_gender_context = detect_gender_context(input_exam, input_anatomy or [])
        if input_gender_context:
            # Check if NHS entry matches this gender context
            if input_gender_context == 'pregnancy' and any(term in nhs_name_lower for term in ['pregnancy', 'obstetric', 'prenatal', 'fetal']):
                pregnancy_bonus = self.config.get('pregnancy_context_bonus', 0.25)
                total_bonus += pregnancy_bonus
                logger.debug(f"Applied pregnancy context bonus: +{pregnancy_bonus}")
                
            elif input_gender_context == 'female' and any(term in nhs_name_lower for term in ['breast', 'mammography', 'female', 'gynae', 'uterus']):
                gender_bonus = self.config.get('gender_context_match_bonus', 0.20)
                total_bonus += gender_bonus
                logger.debug(f"Applied female gender context bonus: +{gender_bonus}")
                
            elif input_gender_context == 'male' and any(term in nhs_name_lower for term in ['prostate', 'scrotal', 'male', 'penis']):
                gender_bonus = self.config.get('gender_context_match_bonus', 0.20)
                total_bonus += gender_bonus
                logger.debug(f"Applied male gender context bonus: +{gender_bonus}")
        
        # Detect age context from input
        input_age_context = detect_age_context(input_exam)
        if input_age_context == 'paediatric' and any(term in nhs_name_lower for term in ['paediatric', 'pediatric', 'child', 'infant']):
            age_bonus = self.config.get('age_context_match_bonus', 0.15)
            total_bonus += age_bonus
            logger.debug(f"Applied paediatric age context bonus: +{age_bonus}")
        
        # PART 2: Calculate clinical context bonuses (from context_scoring config)
        if self.context_scoring:
            for context_type, details in self.context_scoring.items():
                if isinstance(details, dict) and 'keywords' in details:
                    keywords = details['keywords']
                    bonus = details.get('bonus', 0.10)
                    # Use a small, consistent penalty
                    penalty = -0.15 

                    # Check if the input contains any keyword for this context
                    input_has_context = any(k in input_lower for k in keywords)
                    # Check if the NHS candidate contains any keyword for this context
                    nhs_has_context = any(k in nhs_name_lower for k in keywords)

                    if input_has_context and nhs_has_context:
                        # Both have the context, apply bonus
                        total_bonus += bonus
                        logger.debug(f"Applied {context_type} context bonus: +{bonus}")
                    elif input_has_context and not nhs_has_context:
                        # Input has context but candidate is missing it, apply penalty
                        total_bonus += penalty
                        logger.debug(f"Applied {context_type} context penalty: {penalty} (Input had context, candidate did not)")
        
        return total_bonus
    
    def _calculate_synonym_bonus(self, input_exam: str, nhs_entry: dict) -> float:
        abbreviations = self.preprocessing_config.get('medical_abbreviations', {})
        if not abbreviations: return 0.0
        input_lower, nhs_name_lower = input_exam.lower(), nhs_entry.get('primary_source_name', '').lower()
        for abbrev, expansion in abbreviations.items():
            abbrev_l, expansion_l = abbrev.lower(), expansion.lower()
            if (abbrev_l in input_lower and expansion_l in nhs_name_lower) or \
               (expansion_l in input_lower and abbrev_l in nhs_name_lower):
                return self.config.get('synonym_match_bonus', 0.15)
        return 0.0
    
    def _calculate_biopsy_modality_preference(self, input_exam: str, nhs_entry: dict) -> float:
        """Calculate preference bonus/penalty for biopsy procedures based on modality."""
        if not self.config.get('biopsy_modality_preference', False):
                return 0.0

        input_lower = input_exam.lower()
        nhs_name_lower = nhs_entry.get('primary_source_name', '').lower()

        # Check if this is a biopsy procedure without explicit modality in input
        has_biopsy = 'biopsy' in input_lower or 'bx' in input_lower
        if not has_biopsy:
                return 0.0

        # Check if input already specifies a modality (if so, don't apply preference)
        explicit_modalities = ['ct', 'us', 'ultrasound', 'fluoroscop', 'mri', 'mr']
        if any(mod in input_lower for mod in explicit_modalities):
                return 0.0

        # Get organ-specific biopsy preferences from config
        organ_preferences = self.config.get('biopsy_organ_modality_preferences', {})
        default_preferences = self.config.get('biopsy_default_preferences', {})

        # Determine NHS entry modality
        nhs_components = nhs_entry.get('_parsed_components', {})
        nhs_modalities = [m.lower() for m in nhs_components.get('modality', [])]

        modality_key = ''
        if 'ct' in nhs_modalities:
                modality_key = 'ct'
        elif 'us' in nhs_modalities:
                modality_key = 'us'
        elif 'mri' in nhs_modalities:
                modality_key = 'mri'
        elif 'fluoroscopy' in nhs_modalities or 'ir' in nhs_modalities or 'interventional' in nhs_modalities:
                modality_key = 'fluoroscopy'
        else:
                return 0.0

        # Find matching organ in input and apply specific preferences
        for organ, preferences in organ_preferences.items():
                if organ in input_lower:
                        return preferences.get(modality_key, 0.0)

        # Fall back to default preferences if no organ match
        return default_preferences.get(modality_key, 0.0)
    
    def _calculate_anatomy_specificity_preference(self, input_components: dict, nhs_entry: dict) -> float:
        """Calculate preference bonus for generic NHS entries when input is generic."""
        if not self.config.get('anatomy_specificity_preference', False):
            return 0.0
            
        input_anatomy = input_components.get('anatomy', [])
        nhs_components = nhs_entry.get('_parsed_components', {})
        nhs_anatomy = nhs_components.get('anatomy', [])
        
        # Check if input is generic (no specific anatomy mentioned)
        if len(input_anatomy) == 0:
            # Input is generic - prefer NHS entries that are also generic
            if len(nhs_anatomy) == 0:
                return self.config.get('generic_anatomy_preference_bonus', 0.15)
            # If NHS entry has specific anatomy but input doesn't, slight penalty
            else:
                return -0.05
                
        # If input has specific anatomy, prefer NHS entries with matching anatomy
        # (this is handled by normal anatomy scoring, so no bonus needed)
        return 0.0
    
    def _calculate_anatomical_specificity_score(self, input_exam: str, nhs_entry: dict) -> float:
        """
        Calculate anatomical specificity score using separate weights for:
        - Anatomical detail (bonus for clinically relevant specificity)
        - Administrative detail (penalty for irrelevant specificity)
        - Technique specificity (small bonus for technique detail)
        """
        input_tokens = set(input_exam.lower().split())
        nhs_name = nhs_entry.get('primary_source_name', '')
        nhs_tokens = set(nhs_name.lower().split())
        
        # Find extra tokens in NHS entry not in input
        extra_tokens = nhs_tokens - input_tokens
        
        # Get word lists from config
        anatomical_words = set(self.config.get('anatomical_detail_words', []))
        administrative_words = set(self.config.get('administrative_detail_words', []))
        
        # Categorize extra tokens
        anatomical_extras = extra_tokens.intersection(anatomical_words)
        administrative_extras = extra_tokens.intersection(administrative_words)
        
        # Check for technique-related specificity
        technique_words = {'doppler', 'angiography', 'venography', 'arteriography', 
                          'perfusion', 'diffusion', 'spectroscopy', 'elastography'}
        technique_extras = extra_tokens.intersection(technique_words)
        
        # Calculate score components
        anatomical_bonus = len(anatomical_extras) * self.config.get('anatomical_specificity_bonus', 0.10)
        administrative_penalty = len(administrative_extras) * self.config.get('general_specificity_penalty', 0.20)
        technique_bonus = len(technique_extras) * self.config.get('technique_specificity_bonus', 0.05)
        
        # Penalty for completely unrecognized extra words (neither anatomical nor administrative)
        unrecognized_extras = extra_tokens - anatomical_words - administrative_words - technique_words
        # Filter out stop words from unrecognized
        unrecognized_extras = unrecognized_extras - self._specificity_stop_words
        unrecognized_penalty = len(unrecognized_extras) * 0.15
        
        total_score = anatomical_bonus + technique_bonus - administrative_penalty - unrecognized_penalty
        
        return total_score

    # =============================================================================
    # RESULT FORMATTING & UTILITIES
    # =============================================================================

    def _format_match_result(self, best_match: Dict, extracted_input_components: Dict, confidence: float, nlp_proc: NLPProcessor, strip_laterality_from_name: bool = False, input_exam_text: str = "", force_ambiguous: bool = False) -> Dict:
        """
        Formats the final result, ensuring it contains a fully populated 'components'
        dictionary for consistent processing by the calling function.
        """
        model_name = getattr(nlp_proc, 'model_key', 'default').split('/')[-1]
        source_name = f'UNIFIED_MATCH_V2_5_PRECISION_{model_name.upper()}'
        is_interventional = bool(best_match.get('_interventional_terms', []))
        
        clean_name = best_match.get('primary_source_name', '')

        if strip_laterality_from_name:
            clean_name = re.sub(r'\s+(lt|rt|left|right|both|bilateral)$', '', clean_name, flags=re.I).strip()

        input_contrast = (extracted_input_components.get('contrast') or [None])[0]
        if input_contrast == 'with' and 'with contrast' not in clean_name.lower():
            clean_name += " with contrast"

        # --- CRITICAL FIX IS HERE ---
        # Create the nested 'components' dictionary that app.py expects.
        # This dictionary includes all parsed components, confidence score, AND context information.
        
        # PIPELINE STEP: Detect context information that was previously calculated post-scoring
        # Now calculated here so it can influence the final result structure
        from context_detection import detect_gender_context, detect_age_context, detect_clinical_context
        
        input_anatomy = extracted_input_components.get('anatomy', [])
        gender_context = detect_gender_context(input_exam_text, input_anatomy)
        age_context = detect_age_context(input_exam_text) 
        clinical_context = detect_clinical_context(input_exam_text, input_anatomy)
        
        # Get components from the matched NHS entry (not input)
        matched_components = best_match.get('_parsed_components', {})
        
        final_components = {
            # Use components from the matched NHS entry
            'anatomy': matched_components.get('anatomy', []),
            'laterality': matched_components.get('laterality', []),
            'contrast': matched_components.get('contrast', []),
            'technique': matched_components.get('technique', []),
            'modality': matched_components.get('modality', []),
            'confidence': confidence,
            # Add context information from the input (these are input-specific)
            'gender_context': gender_context,
            'age_context': age_context, 
            'clinical_context': clinical_context
        }
        
        # Check for biopsy ambiguity
        biopsy_ambiguous = self._is_biopsy_ambiguous(input_exam_text, best_match)
        
        # Determine if this match is ambiguous (laterality, biopsy, or forced)
        is_ambiguous = force_ambiguous or strip_laterality_from_name or biopsy_ambiguous
        
        return {
            'clean_name': clean_name.strip(),
            'snomed_id': best_match.get('snomed_concept_id', ''),
            'snomed_fsn': best_match.get('snomed_fsn', ''),
            'snomed_laterality_concept_id': best_match.get('snomed_laterality_concept_id', ''),
            'snomed_laterality_fsn': best_match.get('snomed_laterality_fsn', ''),
            'is_diagnostic': not is_interventional,
            'is_interventional': is_interventional,
            'source': source_name,
            'ambiguous': is_ambiguous,  # Track laterality, biopsy, or forced ambiguity
            'components': final_components # Return the components nested under one key
        }

    def find_bilateral_peer(self, specific_entry: Dict) -> Optional[Dict]:
        specific_components = specific_entry.get('_parsed_components')
        if not specific_components:
                return None
        target_modalities = set(specific_components.get('modality', []))
        target_anatomy = set(specific_components.get('anatomy', []))
        target_contrasts = set(specific_components.get('contrast', []))
        target_techniques = set(specific_components.get('technique', []))

        for entry in self.nhs_data:
                entry_components = entry.get('_parsed_components')
                if not entry_components: 
                        continue
                entry_laterality = (entry_components.get('laterality') or [None])[0]
                if entry_laterality not in [None, 'bilateral']:
                        continue

                if (set(entry_components.get('modality', [])) == target_modalities and
                        set(entry_components.get('anatomy', [])) == target_anatomy and
                        set(entry_components.get('contrast', [])) == target_contrasts and
                        set(entry_components.get('technique', [])) == target_techniques):
                        return entry

        return None

    def find_bilateral_peer_in_candidates(self, specific_entry: Dict, candidate_entries: List[Dict]) -> Optional[Dict]:
        """Find bilateral peer within the filtered candidate entries (respects complexity filtering)."""
        specific_components = specific_entry.get('_parsed_components')
        if not specific_components:
            return None
        
        target_modalities = set(specific_components.get('modality', []))
        target_anatomy = set(specific_components.get('anatomy', []))
        target_contrasts = set(specific_components.get('contrast', []))
        target_techniques = set(specific_components.get('technique', []))

        # Search within our filtered candidates first (respects complexity filtering)
        for entry in candidate_entries:
            entry_components = entry.get('_parsed_components')
            if not entry_components:
                continue
            entry_laterality = (entry_components.get('laterality') or [None])[0]
            if entry_laterality not in [None, 'bilateral']:
                continue

            if (set(entry_components.get('modality', [])) == target_modalities and
                    set(entry_components.get('anatomy', [])) == target_anatomy and
                    set(entry_components.get('contrast', [])) == target_contrasts and
                    set(entry_components.get('technique', [])) == target_techniques):
                return entry

        # No fallback - only return results from candidate_entries to maintain consistency
        return None
    
    def _apply_semantic_similarity_safeguard(self, result: Dict, input_exam: str) -> Dict:
        """
        Apply semantic similarity safeguard to detect catastrophic mismatches.
        
        If similarity between input and output is catastrophically low, forces ambiguous=True
        and lowers confidence to trigger secondary pipeline correction.
        """
        final_clean_name = result.get('clean_name', '')
        if not final_clean_name or not input_exam:
            return result
            
        try:
            # Use the retriever processor to get embeddings for similarity check
            input_embedding = self.retriever_processor.get_text_embedding(input_exam.lower())
            output_embedding = self.retriever_processor.get_text_embedding(final_clean_name.lower())
            
            if input_embedding is not None and output_embedding is not None:
                # Calculate cosine similarity
                import numpy as np
                similarity = np.dot(input_embedding, output_embedding) / (
                    np.linalg.norm(input_embedding) * np.linalg.norm(output_embedding)
                )
                
                # If semantic similarity is catastrophically low, force ambiguous and lower confidence
                similarity_threshold = 0.3  # Very low threshold for catastrophic mismatches
                if similarity < similarity_threshold:
                    logger.warning(f"[SEMANTIC-SAFEGUARD] Catastrophic mismatch detected! Input: '{input_exam}' -> Output: '{final_clean_name}' (similarity: {similarity:.3f})")
                    
                    # Force ambiguous to trigger secondary pipeline
                    result['ambiguous'] = True
                    
                    # Lower confidence to ensure secondary pipeline activation
                    if 'components' in result and 'confidence' in result['components']:
                        original_confidence = result['components']['confidence']
                        result['components']['confidence'] = min(0.2, original_confidence)  # Cap at very low confidence
                        logger.warning(f"[SEMANTIC-SAFEGUARD] Lowered confidence: {original_confidence:.3f} -> {result['components']['confidence']:.3f}")
                    
                    # Add metadata for transparency
                    result['semantic_similarity_safeguard'] = {
                        'applied': True,
                        'similarity_score': float(similarity),
                        'threshold': similarity_threshold,
                        'reason': 'Catastrophic semantic mismatch detected'
                    }
                else:
                    logger.debug(f"[SEMANTIC-SAFEGUARD] Similarity check passed: {similarity:.3f} (threshold: {similarity_threshold})")
                
        except Exception as e:
            logger.error(f"[SEMANTIC-SAFEGUARD] Error in similarity check: {e}")
            # Don't fail the entire request, just log and continue
        
        return result
    
    def _is_biopsy_ambiguous(self, input_exam: str, nhs_entry: dict) -> bool:
        """Check if this is an ambiguous biopsy case where modality preference was applied."""
        if not self.config.get('biopsy_modality_preference', False):
            return False
            
        input_lower = input_exam.lower()
        
        # Check if this is a biopsy procedure without explicit modality in input
        has_biopsy = 'biopsy' in input_lower or 'bx' in input_lower
        if not has_biopsy:
            return False
            
        # Check if input already specifies a modality (if so, not ambiguous)
        explicit_modalities = ['ct', 'us', 'ultrasound', 'fluoroscop', 'mri', 'mr']
        if any(mod in input_lower for mod in explicit_modalities):
            return False
            
        # If we get here, it's a biopsy without explicit modality - this is ambiguous
        return True

    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two text strings using fuzzy matching.
        
        Used for complexity filtering to preserve high-similarity matches regardless
        of FSN complexity when input is simple.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            float: Similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts for comparison
        norm_text1 = text1.lower().strip()
        norm_text2 = text2.lower().strip()
        
        # Use fuzzy ratio for semantic similarity approximation
        similarity = fuzz.ratio(norm_text1, norm_text2) / 100.0
        return similarity

    def validate_consistency(self):
        snomed_to_names = defaultdict(set)
        for entry in self.nhs_data:
            if snomed_id := entry.get("snomed_concept_id"):
                if name := entry.get("primary_source_name"):
                    snomed_to_names[snomed_id].add(name)
        inconsistencies = {k: list(v) for k, v in snomed_to_names.items() if len(v) > 1}
        if inconsistencies:
            logger.warning(f"Found {len(inconsistencies)} SNOMED IDs with multiple primary names.")
        else:
            logger.info("NHS data consistency validation passed.")

# --- END OF FILE nhs_lookup_engine.py ---