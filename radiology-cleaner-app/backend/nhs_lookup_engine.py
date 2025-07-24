# --- START OF FILE nhs_lookup_engine.py ---

# =============================================================================
# NHS LOOKUP ENGINE (V2.4 - CORRECTED INITIALIZATION)
# =============================================================================
# This version corrects a KeyError during cache building by ensuring that
# the preprocessed NHS names are correctly created and stored during engine
# initialization. It retains the advanced, config-driven scoring model.

import json
import logging
import re
import os
import pickle
import time
import yaml
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

if TYPE_CHECKING:
    from parser import RadiologySemanticParser

logger = logging.getLogger(__name__)

class NHSLookupEngine:
    def __init__(self, nhs_json_path: str, retriever_processor: NLPProcessor, reranker_processor: NLPProcessor, semantic_parser: 'RadiologySemanticParser'):
        self.nhs_data = []
        self.snomed_lookup = {}
        self.index_to_snomed_id: List[str] = []
        self.vector_index: Optional[faiss.Index] = None
        
        self.nhs_json_path = nhs_json_path
        self.retriever_processor = retriever_processor
        self.reranker_processor = reranker_processor  # Can be None during cache building
        self.nlp_processor = retriever_processor  # Backward compatibility
        self.semantic_parser = semantic_parser
        self.complexity_scorer = ComplexityScorer()
        
        self._load_config_from_manager()
        
        self._load_nhs_data()
        self._build_lookup_tables()
        self._preprocess_and_parse_nhs_data() # This method will now function correctly
        
        self._embeddings_loaded = False

        self._specificity_stop_words = {
            'a', 'an', 'the', 'and', 'or', 'with', 'without', 'for', 'of', 'in', 'on', 'to',
            'ct', 'mr', 'mri', 'us', 'xr', 'x-ray', 'nm', 'pet', 'scan', 'imaging', 'procedure',
            'examination', 'study', 'left', 'right', 'bilateral', 'contrast', 'view'
        }
        logger.info("NHSLookupEngine initialized with Advanced Scoring architecture (v2.4).")

    def _load_config_from_manager(self):
        """Loads configuration from R2 via ConfigManager."""
        try:
            from config_manager import get_config
            config_manager = get_config()
            self.config = config_manager.get_section('scoring')
            self.modality_similarity = config_manager.get_section('modality_similarity')
            self.context_scoring = config_manager.get_section('context_scoring')
            self.preprocessing_config = config_manager.get_section('preprocessing')
            logger.info("Loaded enhanced scoring configuration from R2 via ConfigManager")
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
        try:
            with open(self.nhs_json_path, 'r', encoding='utf-8') as f:
                self.nhs_data = json.load(f)
            logger.info(f"Loaded {len(self.nhs_data)} NHS entries from {self.nhs_json_path}")
        except Exception as e:
            logger.critical(f"Failed to load NHS data: {e}", exc_info=True); raise

    def _build_lookup_tables(self):
        for entry in self.nhs_data:
            if snomed_id := entry.get("snomed_concept_id"):
                self.snomed_lookup[str(snomed_id)] = entry
        logger.info(f"Built SNOMED lookup table with {len(self.snomed_lookup)} entries")

    def _preprocess_and_parse_nhs_data(self):
        """
        CORRECTED METHOD: Ensures that preprocessed names are created and stored
        in each NHS data entry before they are needed for cache building or scoring.
        """
        if not self.semantic_parser: raise RuntimeError("Semantic Parser required.")
        preprocessor = get_preprocessor()
        if not preprocessor: raise RuntimeError("Preprocessor not initialized.")
        
        for entry in self.nhs_data:
            snomed_fsn_raw = entry.get("snomed_fsn", "").strip()
            primary_name_raw = entry.get("primary_source_name", "").strip()
            
            snomed_fsn_clean = re.sub(r'\s*\((procedure|qualifier value|finding)\)$', '', snomed_fsn_raw, flags=re.I).strip()

            # ** THE FIX IS HERE **
            # Preprocess and assign the cleaned names to the expected internal keys.
            entry["_clean_fsn_for_embedding"] = preprocessor.preprocess(snomed_fsn_clean)
            entry["_clean_primary_name_for_embedding"] = preprocessor.preprocess(primary_name_raw)
            
            # These subsequent calls now have the clean names they need to function correctly.
            entry["_interventional_terms"] = detect_interventional_procedure_terms(entry["_clean_primary_name_for_embedding"])
            entry['_parsed_components'] = self.semantic_parser.parse_exam_name(entry["_clean_primary_name_for_embedding"], 'Other')
            
            # Calculate binary complexity flag for FSNs at buildtime
            fsn_complexity_score = self.complexity_scorer.calculate_fsn_total_complexity(snomed_fsn_clean)
            entry["_is_complex_fsn"] = fsn_complexity_score > 0.4  # Binary threshold for complexity

    def _find_local_cache_file(self) -> Optional[str]:
        cache_dir = os.environ.get('RENDER_DISK_PATH', 'embedding-caches')
        if not os.path.isdir(cache_dir): return None
        for filename in os.listdir(cache_dir):
            if filename.startswith(f"{self.retriever_processor.model_key}_") and filename.endswith(".cache"):
                return os.path.join(cache_dir, filename)
        return None

    def _load_index_from_local_disk(self):
        local_cache_path = self._find_local_cache_file()
        if local_cache_path and os.path.exists(local_cache_path):
            try:
                with open(local_cache_path, 'rb') as f: cache_content = pickle.load(f)
                self.vector_index = faiss.deserialize_index(cache_content['index_data'])
                self.index_to_snomed_id = cache_content['id_mapping']
                logger.info(f"Successfully loaded FAISS index for model '{self.retriever_processor.model_key}' from: {local_cache_path}")
            except Exception as e:
                logger.critical(f"CRITICAL: Failed to load FAISS index from '{local_cache_path}': {e}.")
        else:
            logger.critical(f"CRITICAL: Cache not found on local disk for model '{self.retriever_processor.model_key}'.")

    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts using fuzzy string matching."""
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts for comparison
        norm_text1 = text1.lower().strip()
        norm_text2 = text2.lower().strip()
        
        # Use fuzzy ratio for semantic similarity approximation
        similarity = fuzz.ratio(norm_text1, norm_text2) / 100.0
        return similarity

    def _calculate_component_score(self, input_exam_text: str, input_components: Dict, nhs_entry: Dict) -> float:
        """
        Calculate component-based score for a candidate NHS entry.
        This is the core of the rule-based matching logic extracted from v2 architecture.
        
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

    def standardize_exam(self, input_exam: str, extracted_input_components: Dict, custom_nlp_processor: Optional[NLPProcessor] = None, is_input_simple: bool = False, debug: bool = False) -> Dict:
        """
        V3 Two-Stage Pipeline: Retrieve candidates with BioLORD, then rerank with MedCPT + component scoring.
        
        Stage 1 (Retrieval): Use retriever_processor (BioLORD) to get top-k candidates via FAISS
        Stage 2 (Reranking): Use reranker_processor (MedCPT) + component scoring to find best match
        """
        if debug:
            logger.info(f"[DEBUG] Debug mode enabled for input: {input_exam}, is_input_simple: {is_input_simple}")
        
        # === VALIDATION ===
        if not self.retriever_processor or not self.retriever_processor.is_available():
            result = {'error': 'Retriever processor not available', 'confidence': 0.0}
            if debug: result['debug_early_exit'] = 'Early exit: Retriever not available'
            return result
        if not self.reranker_processor or not self.reranker_processor.is_available():
            result = {'error': 'Reranker processor not available', 'confidence': 0.0}
            if debug: result['debug_early_exit'] = 'Early exit: Reranker not available'
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
        
        if not candidate_entries:
            logger.warning("[V3-PIPELINE] Stage 1 failed - no candidates found during retrieval")
            return {'error': 'No candidates found during retrieval stage.', 'confidence': 0.0}
        
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
            regular_candidates = []
            
            for entry in candidate_entries:
                clean_name = entry.get('_clean_primary_name_for_embedding', '')
                is_complex_fsn = entry.get('_is_complex_fsn', False)
                
                # Check for high semantic similarity (>0.85) to preserve accurate matches
                semantic_similarity = self._calculate_semantic_similarity(input_exam, clean_name)
                
                if semantic_similarity > 0.85:
                    # High semantic match - preserve regardless of complexity
                    prioritized_candidates.append(entry)
                    logger.debug(f"[COMPLEXITY-FILTER] Preserving high-similarity match: '{clean_name[:30]}' (similarity={semantic_similarity:.3f})")
                elif not is_complex_fsn:
                    # Simple FSN for simple input - prefer these
                    regular_candidates.append(entry)
                else:
                    # Complex FSN for simple input - deprioritize but keep available
                    regular_candidates.append(entry)
            
            # Reorder: high-similarity matches first, then simple FSNs, then complex FSNs
            candidate_entries = prioritized_candidates + regular_candidates
            logger.info(f"[COMPLEXITY-FILTER] Reordered candidates: {len(prioritized_candidates)} high-similarity + {len(regular_candidates)} others")

        # === STAGE 2: RERANKING & SCORING ===
        logger.info(f"[V3-PIPELINE] Starting reranking stage with {self.reranker_processor.model_key} ({self.reranker_processor.hf_model_name})")
        stage2_start = time.time()
        
        # Prepare candidate texts for cross-encoder reranking
        candidate_texts = [entry.get('_clean_primary_name_for_embedding', '') for entry in candidate_entries]
        logger.debug(f"[V3-PIPELINE] Prepared {len(candidate_texts)} candidate texts for reranking")
        
        # Get reranker scores using cross-encoder (MedCPT)
        rerank_scores = self.reranker_processor.get_rerank_scores(input_exam, candidate_texts)
        
        if not rerank_scores or len(rerank_scores) != len(candidate_entries):
            logger.warning(f"[V3-PIPELINE] Reranker failed (got {len(rerank_scores) if rerank_scores else 0} scores for {len(candidate_entries)} candidates) - using neutral fallback")
            rerank_scores = [0.5] * len(candidate_entries)  # Neutral fallback
        
        # Find best match by combining reranking + component scores
        best_match = None
        highest_confidence = -1.0
        
        wf = self.config['weights_final']
        reranker_weight = wf.get('reranker', 0.45)  # Read from config, default matches config.yaml
        component_weight = wf.get('component', 0.55)  # Read from config, default matches config.yaml
        
        component_scores = []
        final_scores = []
        
        logger.debug(f"[V3-PIPELINE] Processing {len(candidate_entries)} candidates with weights: reranker={reranker_weight}, component={component_weight}")
        
        for i, (entry, rerank_score) in enumerate(zip(candidate_entries, rerank_scores)):
            candidate_name = entry.get('primary_source_name', 'Unknown')
            
            # Calculate component score using extracted logic
            component_start = time.time()
            component_score = self._calculate_component_score(input_exam, extracted_input_components, entry)
            component_time = time.time() - component_start
            component_scores.append(component_score)
            
            # Combine reranker score and component score
            final_score = (reranker_weight * rerank_score) + (component_weight * component_score)
            final_scores.append(final_score)
            
            if final_score > highest_confidence:
                highest_confidence = final_score
                best_match = entry
                logger.info(f"[V3-PIPELINE] New best match: '{candidate_name[:40]}' (final_score={final_score:.3f})")
            
            logger.debug(f"[V3-PIPELINE] Candidate {i+1}: '{candidate_name[:30]}' - rerank={rerank_score:.3f}, component={component_score:.3f}, final={final_score:.3f} (component_time={component_time:.3f}s)")
        
        stage2_time = time.time() - stage2_start
        
        # Log scoring statistics
        if final_scores:
            logger.info(f"[V3-PIPELINE] Stage 2 completed in {stage2_time:.2f}s")
            logger.info(f"[V3-PIPELINE] Score statistics:")
            logger.info(f"  Rerank scores - Min: {min(rerank_scores):.3f}, Max: {max(rerank_scores):.3f}, Avg: {sum(rerank_scores)/len(rerank_scores):.3f}")
            logger.info(f"  Component scores - Min: {min(component_scores):.3f}, Max: {max(component_scores):.3f}, Avg: {sum(component_scores)/len(component_scores):.3f}")
            logger.info(f"  Final scores - Min: {min(final_scores):.3f}, Max: {max(final_scores):.3f}, Avg: {sum(final_scores)/len(final_scores):.3f}")

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
                if bilateral_peer := self.find_bilateral_peer(best_match):
                    result = self._format_match_result(bilateral_peer, extracted_input_components, highest_confidence, self.retriever_processor, strip_laterality_from_name=True, input_exam_text=input_exam, force_ambiguous=laterally_ambiguous)
                    
                    # Simple debug test for bilateral peer
                    if debug:
                        result['debug_simple'] = 'Debug parameter received successfully (bilateral peer)!'
                        logger.info("[DEBUG] Added simple debug flag to bilateral peer result")
                    
                    # Add debug information for bilateral peer case
                    if debug:
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
                                    'component_score': json_safe(component_scores[i] if i < len(component_scores) else 0.0)
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
                    
                    return result
            
            result = self._format_match_result(best_match, extracted_input_components, highest_confidence, self.retriever_processor, strip_laterality_from_name=strip_laterality, input_exam_text=input_exam, force_ambiguous=laterally_ambiguous)
            
            # Simple debug test
            if debug:
                result['debug_simple'] = 'Debug parameter received successfully!'
                logger.info("[DEBUG] Added simple debug flag to result")
            
            # Add debug information if requested
            if debug:
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
                            'component_score': json_safe(component_scores[i] if i < len(component_scores) else 0.0)
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
            
            return result
        
        logger.warning(f"[V3-PIPELINE] ❌ No suitable match found in {total_time:.2f}s total")
        return {'error': 'No suitable match found.', 'confidence': 0.0}

    def _calculate_laterality_score(self, input_lat: Optional[str], nhs_lat: Optional[str]) -> float:
        """Calculates a more punitive score for laterality mismatches."""
        if input_lat == nhs_lat:
            return 1.0  # Perfect match
        if not input_lat or not nhs_lat:
            return 0.7  # Ambiguous match (e.g., input "Knee" vs NHS "Knee Rt")
        return 0.1  # Direct mismatch (e.g., input "Left" vs NHS "Right")

    def _calculate_match_score(self, input_exam_text, input_components, nhs_entry, semantic_score, interventional_score, anatomical_specificity_score):
        # 1. Check for any "blocking" level violations that should immediately reject the candidate.
        diagnostic_penalty = self._check_diagnostic_protection(input_exam_text, nhs_entry)
        hybrid_modality_penalty = self._check_hybrid_modality_constraints(input_exam_text, nhs_entry)
        technique_specialization_penalty = self._check_technique_specialization_constraints(input_exam_text, nhs_entry)

        # Note: We check for values less than -1.0 to distinguish from fractional penalties.
        if diagnostic_penalty < -1.0 or hybrid_modality_penalty < -1.0 or technique_specialization_penalty < -1.0:
                logger.debug(f"Blocking violation detected for '{nhs_entry.get('primary_source_name')}', returning 0.0 score.")
                return 0.0

        nhs_components = nhs_entry.get('_parsed_components', {})

        # 2. Calculate all component scores using the new, correct list-based functions.
        anatomy_score = self._calculate_anatomy_score_with_constraints(
                input_components,
                nhs_components  # Pass the full dicts to the constraint checker
        )
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

        # 3. Check component thresholds to gate low-quality matches.
        if (violation := self._check_component_thresholds(anatomy_score, modality_score, laterality_score, contrast_score, technique_score)):
                logger.debug(f"Component threshold violation for '{nhs_entry.get('primary_source_name')}': {violation}")
                return 0.0

        # 4. Combine the component scores using weights from the config.
        w = self.config['weights_component']
        component_score = (
                w.get('anatomy', 0.25) * anatomy_score +
                w.get('modality', 0.30) * modality_score +
                w.get('laterality', 0.15) * laterality_score +
                w.get('contrast', 0.20) * contrast_score +
                w.get('technique', 0.10) * technique_score
        )

        # 5. Combine component score and semantic score into a final score, applying weight limiting.
        wf = self.config['weights_final']
        threshold_config = self.config.get('minimum_component_thresholds', {})
        if threshold_config.get('enable', False):
                max_semantic_weight = threshold_config.get('max_semantic_weight', 0.6)
                actual_semantic_weight = min(wf.get('semantic', 0.40), max_semantic_weight)
                actual_component_weight = 1.0 - actual_semantic_weight
                final_score = (actual_component_weight * component_score + actual_semantic_weight * semantic_score)
        else:
                final_score = (wf.get('component', 0.6) * component_score + wf.get('semantic', 0.4) * semantic_score)

        # 6. Add all bonuses and non-blocking penalties to the final score.
        final_score += interventional_score
        final_score += diagnostic_penalty
        final_score += hybrid_modality_penalty
        final_score += technique_specialization_penalty
        final_score += self._calculate_context_bonus(input_exam_text, nhs_entry, input_components.get('anatomy', []))
        final_score += self._calculate_synonym_bonus(input_exam_text, nhs_entry)
        final_score += self._calculate_biopsy_modality_preference(input_exam_text, nhs_entry)
        final_score += self._calculate_anatomy_specificity_preference(input_components, nhs_entry)
        final_score += anatomical_specificity_score

        if input_exam_text.strip().lower() == nhs_entry.get('primary_source_name', '').lower():
                final_score += self.config.get('exact_match_bonus', 0.25)

        return max(0.0, min(1.0, final_score))

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
        
        final_components = {
            **extracted_input_components,  # Unpack anatomy, laterality, contrast, technique
            'confidence': confidence,
            # Add context information that was previously calculated in app.py
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
        impossible mappings like "Lower Limb" → "Penis" that could cause patient safety issues.
        
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
                if isinstance(details, dict) and 'keywords' in details and 'bonus' in details:
                    keywords = details['keywords']
                    if any(k in input_lower for k in keywords) and any(k in nhs_name_lower for k in keywords):
                        clinical_bonus = details['bonus']
                        total_bonus += clinical_bonus
                        logger.debug(f"Applied {context_type} clinical context bonus: +{clinical_bonus}")
        
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
