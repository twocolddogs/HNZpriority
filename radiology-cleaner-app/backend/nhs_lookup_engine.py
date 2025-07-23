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
from scoring_engine import ScoringEngine
from preprocessing import get_preprocessor

if TYPE_CHECKING:
    from parser import RadiologySemanticParser

logger = logging.getLogger(__name__)

class NHSLookupEngine:
    def __init__(self, nhs_json_path: str, retriever_processor: NLPProcessor, reranker_processor: NLPProcessor, semantic_parser: 'RadiologySemanticParser', config_path: str = None):
        self.nhs_data = []
        self.snomed_lookup = {}
        self.index_to_snomed_id: List[str] = []
        self.vector_index: Optional[faiss.Index] = None
        
        self.nhs_json_path = nhs_json_path
        self.retriever_processor = retriever_processor
        self.reranker_processor = reranker_processor  # Can be None during cache building
        self.nlp_processor = retriever_processor  # Backward compatibility
        self.semantic_parser = semantic_parser
        
        # Set default config path if not provided
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        self._load_config(config_path)
        
        # Initialize scoring engine with loaded config
        self.scoring_engine = ScoringEngine(
            config=self.config,
            modality_similarity=self.modality_similarity,
            context_scoring=self.context_scoring,
            preprocessing_config=self.preprocessing_config
        )
        
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

    def _load_config(self, config_path):
        """Loads scoring weights and parameters from a YAML config file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.config = config['scoring']
                self.modality_similarity = config.get('modality_similarity', {})
                self.context_scoring = config.get('context_scoring', {})
                self.preprocessing_config = config.get('preprocessing', {})
                logger.info(f"Loaded enhanced scoring configuration from {config_path}")
        except Exception as e:
            logger.error(f"Could not load or parse {config_path}. Using default weights. Error: {e}")
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

    def standardize_exam(self, input_exam: str, extracted_input_components: Dict, custom_nlp_processor: Optional[NLPProcessor] = None) -> Dict:
        """
        V3 Two-Stage Pipeline: Retrieve candidates with BioLORD, then rerank with MedCPT + component scoring.
        
        Stage 1 (Retrieval): Use retriever_processor (BioLORD) to get top-k candidates via FAISS
        Stage 2 (Reranking): Use reranker_processor (MedCPT) + component scoring to find best match
        """
        # === VALIDATION ===
        if not self.retriever_processor or not self.retriever_processor.is_available():
            return {'error': 'Retriever processor not available', 'confidence': 0.0}
        if not self.reranker_processor or not self.reranker_processor.is_available():
            return {'error': 'Reranker processor not available', 'confidence': 0.0}

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
            return {'error': 'Vector index not loaded.', 'confidence': 0.0}
        
        # Generate embedding for input using retriever
        input_embedding = self.retriever_processor.get_text_embedding(input_exam)
        if input_embedding is None:
            return {'error': 'Failed to generate embedding for input.', 'confidence': 0.0}
        
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
        
        # Find best match by combining reranking + component + complexity scores
        best_match = None
        highest_confidence = -1.0
        
        wf = self.config['weights_final']
        logger.debug(f"[V3-PIPELINE] Processing {len(candidate_entries)} candidates with weights: {wf}")
        
        component_scores = []
        final_scores = []
        score_breakdowns = []
        
        for i, (entry, rerank_score) in enumerate(zip(candidate_entries, rerank_scores)):
            candidate_name = entry.get('primary_source_name', 'Unknown')
            
            # Calculate final score using the new ScoringEngine (includes complexity scoring)
            scoring_start = time.time()
            final_score, score_breakdown = self.scoring_engine.calculate_final_score(
                input_exam, extracted_input_components, entry, rerank_score
            )
            scoring_time = time.time() - scoring_start
            
            component_scores.append(score_breakdown['component_score'])
            final_scores.append(final_score)
            score_breakdowns.append(score_breakdown)
            
            if final_score > highest_confidence:
                highest_confidence = final_score
                best_match = entry
                logger.info(f"[V3-PIPELINE] New best match: '{candidate_name[:40]}' (final_score={final_score:.3f})")
            
            logger.debug(f"[V3-PIPELINE] Candidate {i+1}: '{candidate_name[:30]}' - rerank={rerank_score:.3f}, component={score_breakdown['component_score']:.3f}, complexity={score_breakdown['complexity_score']:.3f}, final={final_score:.3f} (scoring_time={scoring_time:.3f}s)")
        
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
                    return self._format_match_result(bilateral_peer, extracted_input_components, highest_confidence, self.retriever_processor, strip_laterality_from_name=True, input_exam_text=input_exam, force_ambiguous=laterally_ambiguous)
            
            return self._format_match_result(best_match, extracted_input_components, highest_confidence, self.retriever_processor, strip_laterality_from_name=strip_laterality, input_exam_text=input_exam, force_ambiguous=laterally_ambiguous)
        
        logger.warning(f"[V3-PIPELINE] ❌ No suitable match found in {total_time:.2f}s total")
        return {'error': 'No suitable match found.', 'confidence': 0.0}

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
            clean_name = re.sub(r'\s+(lt|rt|left|right|both|bilateral)

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
, '', clean_name, flags=re.I).strip()

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
