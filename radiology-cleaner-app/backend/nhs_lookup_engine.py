# --- START OF FILE nhs_lookup_engine.py ---

# =============================================================================
# NHS LOOKUP ENGINE (V2.5 - REFACTORED WITH SCORING ENGINE)
# =============================================================================
# This version delegates all scoring logic to a dedicated ScoringEngine,
# improving modularity and maintainability. The lookup engine now focuses on
# data loading, candidate retrieval (FAISS), and final result formatting.

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
from typing import TYPE_CHECKING

# Core application components
from nlp_processor import NLPProcessor
from context_detection import detect_interventional_procedure_terms
from preprocessing import get_preprocessor
from scoring_engine import ScoringEngine  # <-- IMPORT THE NEW ENGINE

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
        self.reranker_processor = reranker_processor
        self.nlp_processor = retriever_processor
        self.semantic_parser = semantic_parser
        
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        self._load_config(config_path)
        
        # --- REFACTOR: INSTANTIATE SCORING ENGINE ---
        self.scoring_engine = ScoringEngine(
            config=self.config_data,  # Pass the entire config dict
            modality_similarity=self.modality_similarity,
            context_scoring=self.context_scoring,
            preprocessing_config=self.preprocessing_config
        )
        logger.info("Initialized ScoringEngine for all scoring logic.")
        
        self._load_nhs_data()
        self._build_lookup_tables()
        self._preprocess_and_parse_nhs_data()
        
        self._embeddings_loaded = False
        logger.info("NHSLookupEngine initialized with Scoring Engine architecture (v2.5).")

    def _load_config(self, config_path):
        """Loads configuration from a YAML file."""
        try:
            with open(config_path, 'r') as f:
                self.config_data = yaml.safe_load(f)
                self.config = self.config_data.get('scoring', {}) # for backward compatibility
                self.modality_similarity = self.config_data.get('modality_similarity', {})
                self.context_scoring = self.config_data.get('context_scoring', {})
                self.preprocessing_config = self.config_data.get('preprocessing', {})
                logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.critical(f"Could not load or parse {config_path}. Error: {e}", exc_info=True)
            raise

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
        """Preprocesses and parses all NHS data entries on initialization."""
        if not self.semantic_parser: raise RuntimeError("Semantic Parser required.")
        preprocessor = get_preprocessor()
        if not preprocessor: raise RuntimeError("Preprocessor not initialized.")
        
        for entry in self.nhs_data:
            snomed_fsn_raw = entry.get("snomed_fsn", "").strip()
            primary_name_raw = entry.get("primary_source_name", "").strip()
            snomed_fsn_clean = re.sub(r'\s*\((procedure|qualifier value|finding)\)$', '', snomed_fsn_raw, flags=re.I).strip()
            
            entry["_clean_fsn_for_embedding"] = preprocessor.preprocess(snomed_fsn_clean)
            entry["_clean_primary_name_for_embedding"] = preprocessor.preprocess(primary_name_raw)
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
        Two-Stage Pipeline: Retrieve candidates, then rerank with ScoringEngine.
        """
        if not self.retriever_processor.is_available() or not self.reranker_processor.is_available():
            return {'error': 'A required NLP processor is not available', 'confidence': 0.0}

        # === STAGE 1: RETRIEVAL (BioLORD) ===
        logger.info(f"Starting retrieval with {self.retriever_processor.model_key}")
        stage1_start = time.time()
        
        if not self._embeddings_loaded or self.nlp_processor.model_key != self.retriever_processor.model_key:
            self.nlp_processor = self.retriever_processor
            self._load_index_from_local_disk()
            self._embeddings_loaded = True
        
        if not self.vector_index: return {'error': 'Vector index not loaded.', 'confidence': 0.0}
        
        input_embedding = self.retriever_processor.get_text_embedding(input_exam)
        if input_embedding is None: return {'error': 'Failed to generate input embedding.', 'confidence': 0.0}
        
        input_ensemble = np.concatenate([input_embedding, input_embedding]).astype('float32')
        faiss.normalize_L2(input_ensemble.reshape(1, -1))
        top_k = self.config.get('retriever_top_k', 25)
        distances, indices = self.vector_index.search(input_ensemble.reshape(1, -1), top_k)
        
        candidate_snomed_ids = [self.index_to_snomed_id[i] for i in indices[0] if i < len(self.index_to_snomed_id)]
        candidate_entries = [self.snomed_lookup[str(sid)] for sid in candidate_snomed_ids if str(sid) in self.snomed_lookup]
        
        if not candidate_entries:
            logger.warning("Stage 1 failed - no candidates found.")
            return {'error': 'No candidates found during retrieval.', 'confidence': 0.0}
        
        logger.info(f"Stage 1 completed in {time.time() - stage1_start:.2f}s, retrieved {len(candidate_entries)} candidates.")

        # === STAGE 2: RERANKING & SCORING (MedCPT + ScoringEngine) ===
        logger.info(f"Starting reranking with {self.reranker_processor.model_key} and ScoringEngine.")
        stage2_start = time.time()
        
        candidate_texts = [entry.get('_clean_primary_name_for_embedding', '') for entry in candidate_entries]
        rerank_scores = self.reranker_processor.get_rerank_scores(input_exam, candidate_texts)
        if not rerank_scores or len(rerank_scores) != len(candidate_entries):
            rerank_scores = [0.5] * len(candidate_entries)

        best_match = None
        highest_confidence = -1.0
        
        # --- REFACTOR: SCORING LOOP ---
        # The complex scoring logic is now replaced by a single call to the ScoringEngine.
        for i, (entry, rerank_score) in enumerate(zip(candidate_entries, rerank_scores)):
            final_score, score_breakdown = self.scoring_engine.calculate_final_score(
                input_exam=input_exam,
                input_components=extracted_input_components,
                nhs_entry=entry,
                rerank_score=rerank_score
            )
            
            if final_score > highest_confidence:
                highest_confidence = final_score
                best_match = entry
            
            logger.debug(f"Candidate {i+1}: '{entry.get('primary_source_name', 'Unknown')[:30]}' "
                         f"- Rerank={score_breakdown['rerank_score']:.2f}, "
                         f"Comp={score_breakdown['component_score']:.2f}, "
                         f"Complex={score_breakdown['complexity_score']:.2f} -> Final={final_score:.3f}")

        logger.info(f"Stage 2 completed in {time.time() - stage2_start:.2f}s.")

        # === RESULT FORMATTING ===
        if best_match:
            logger.info(f"✅ Match found: '{best_match.get('primary_source_name')}' (confidence={highest_confidence:.3f})")
            return self.format_match_result(best_match, extracted_input_components, highest_confidence, input_exam)
        
        logger.warning("❌ No suitable match found after reranking.")
        return {'error': 'No suitable match found.', 'confidence': 0.0}

    # NOTE: All scoring methods like _calculate_component_score, _calculate_modality_score, etc., have been removed.

    def format_match_result(self, best_match: Dict, extracted_input_components: Dict, confidence: float, input_exam_text: str) -> Dict:
        """Formats the final result, including laterality and ambiguity logic."""
        source_name = f'UNIFIED_MATCH_V2_5_SCORING_ENGINE'
        is_interventional = bool(best_match.get('_interventional_terms', []))
        clean_name = best_match.get('primary_source_name', '')

        input_lat = (extracted_input_components.get('laterality') or [None])[0]
        match_lat = (best_match.get('_parsed_components', {}).get('laterality') or [None])[0]
        
        strip_laterality = (not input_lat and match_lat in ['left', 'right', 'bilateral'])
        force_ambiguous = (not input_lat and match_lat in ['left', 'right'])

        if strip_laterality:
            if bilateral_peer := self.find_bilateral_peer(best_match):
                best_match = bilateral_peer # Switch to the bilateral version
            else: # If no peer, just strip the name
                 clean_name = re.sub(r'\s+(lt|rt|left|right|both|bilateral)$', '', clean_name, flags=re.I).strip()

        # Add "with contrast" if needed
        input_contrast = (extracted_input_components.get('contrast') or [None])[0]
        if input_contrast == 'with' and 'with contrast' not in clean_name.lower():
            clean_name += " with contrast"

        from context_detection import detect_gender_context, detect_age_context, detect_clinical_context
        final_components = {
            **extracted_input_components,
            'confidence': confidence,
            'gender_context': detect_gender_context(input_exam_text, extracted_input_components.get('anatomy', [])),
            'age_context': detect_age_context(input_exam_text), 
            'clinical_context': detect_clinical_context(input_exam_text, extracted_input_components.get('anatomy', []))
        }
        
        biopsy_ambiguous = self._is_biopsy_ambiguous(input_exam_text)
        is_ambiguous = force_ambiguous or biopsy_ambiguous
        
        return {
            'clean_name': clean_name.strip(),
            'snomed_id': best_match.get('snomed_concept_id', ''),
            'snomed_fsn': best_match.get('snomed_fsn', ''),
            'snomed_laterality_concept_id': best_match.get('snomed_laterality_concept_id', ''),
            'snomed_laterality_fsn': best_match.get('snomed_laterality_fsn', ''),
            'is_diagnostic': not is_interventional,
            'is_interventional': is_interventional,
            'source': source_name,
            'ambiguous': is_ambiguous,
            'components': final_components
        }

    def find_bilateral_peer(self, specific_entry: Dict) -> Optional[Dict]:
        """Finds a non-lateralized or bilateral peer for a lateralized exam."""
        specific_components = specific_entry.get('_parsed_components')
        if not specific_components: return None

        target_modalities = set(specific_components.get('modality', []))
        target_anatomy = set(specific_components.get('anatomy', []))

        for entry in self.nhs_data:
            entry_components = entry.get('_parsed_components')
            if not entry_components: continue
            
            entry_laterality = (entry_components.get('laterality') or [None])[0]
            if entry_laterality not in [None, 'bilateral']: continue

            if (set(entry_components.get('modality', [])) == target_modalities and
                set(entry_components.get('anatomy', [])) == target_anatomy):
                    # A more robust check would compare contrast and technique too
                    return entry
        return None
    
    def _is_biopsy_ambiguous(self, input_exam: str) -> bool:
        """Checks if a biopsy is ambiguous (modality not specified)."""
        if not self.config.get('biopsy_modality_preference', False): return False
        input_lower = input_exam.lower()
        if not ('biopsy' in input_lower or 'bx' in input_lower): return False
        if any(mod in input_lower for mod in ['ct', 'us', 'ultrasound', 'mri', 'mr']): return False
        return True

    def validate_consistency(self):
        """Validates that SNOMED IDs map to unique primary names."""
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