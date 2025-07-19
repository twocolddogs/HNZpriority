# --- START OF FILE nhs_lookup_engine.py ---

# =============================================================================
# NHS LOOKUP ENGINE (V2.2 - FINAL RUNTIME VERSION)
# =============================================================================
# This is the definitive runtime engine with a strict separation of concerns.
# - It ONLY loads the pre-built FAISS index from the local persistent disk.
# - It trusts that `sync_cache.py` has already downloaded the latest version.
# - It does NOT communicate with R2 or compute the index on the fly.
# - It fixes the `AttributeError` by including the `validate_consistency` method.
# =============================================================================

import json
import logging
import re
import os
import pickle
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

if TYPE_CHECKING:
    from parser import RadiologySemanticParser

logger = logging.getLogger(__name__)

class NHSLookupEngine:
    def __init__(self, nhs_json_path: str, nlp_processor: NLPProcessor, semantic_parser: 'RadiologySemanticParser', config_path: str = 'config.yaml'):
        self.nhs_data = []
        self.snomed_lookup = {}
        self.index_to_snomed_id: List[str] = []
        self.vector_index: Optional[faiss.Index] = None
        
        self.nhs_json_path = nhs_json_path
        self.nlp_processor = nlp_processor
        self.semantic_parser = semantic_parser
        
        self._load_config(config_path)
        
        self._load_nhs_data()
        self._build_lookup_tables()
        self._preprocess_and_parse_nhs_data()
        
        self._embeddings_loaded = False

        self._specificity_stop_words = {
            'a', 'an', 'the', 'and', 'or', 'with', 'without', 'for', 'of', 'in', 'on', 'to', 'is', 'from',
            'ct', 'mr', 'mri', 'us', 'xr', 'x-ray', 'nm', 'pet', 'dexa', 'dect', 'computed', 'tomography',
            'magnetic', 'resonance', 'ultrasound', 'radiograph', 'scan', 'scans', 'imaging', 'image', 'mammo', 'mammogram',
            'left', 'right', 'bilateral', 'lt', 'rt', 'bilat', 'both', 'contrast', 'iv', 'gadolinium', 'gad', 'c+', 'c-',
            'procedure', 'examination', 'study', 'protocol', 'view', 'views', 'projection',
            'series', 'ap', 'pa', 'lat', 'oblique', 'guidance', 'guided', 'body', 'whole',
            'artery', 'vein', 'joint', 'spine', 'tract', 'system', 'time', 'delayed', 'immediate', 'phase', 'early', 'late'
        }
        logger.info("NHSLookupEngine initialized with V2.2 Final Runtime architecture.")

    def _load_config(self, config_path):
        """Loads scoring weights and parameters from a YAML config file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.config = config['scoring']
                # Load additional configuration sections
                self.modality_similarity = config.get('modality_similarity', {})
                self.context_scoring = config.get('context_scoring', {})
                self.preprocessing_config = config.get('preprocessing', {})
                logger.info(f"Loaded enhanced scoring configuration from {config_path}")
        except Exception as e:
            logger.error(f"Could not load or parse {config_path}. Using default weights. Error: {e}")
            self.config = {
                'retriever_top_k': 25,
                'weights_component': {'anatomy': 0.35, 'modality': 0.25, 'laterality': 0.15, 'contrast': 0.15, 'technique': 0.10},
                'weights_final': {'component': 0.55, 'semantic': 0.35, 'frequency': 0.10},
                'interventional_bonus': 0.15,
                'interventional_penalty': -0.20,
                'specificity_penalty_weight': 0.05,
                'exact_match_bonus': 0.25,
                'synonym_match_bonus': 0.15,
                'context_match_bonus': 0.10,
                'contrast_mismatch_score': 0.3,
                'contrast_null_score': 0.7
            }
            self.modality_similarity = {}
            self.context_scoring = {}
            self.preprocessing_config = {}

    def _load_nhs_data(self):
        try:
            with open(self.nhs_json_path, 'r', encoding='utf-8') as f:
                self.nhs_data = json.load(f)
            logger.info(f"Loaded {len(self.nhs_data)} NHS entries from {self.nhs_json_path}")
        except Exception as e:
            logger.error(f"Failed to load NHS data: {e}", exc_info=True)
            raise

    def _build_lookup_tables(self):
        for entry in self.nhs_data:
            if snomed_id := entry.get("snomed_concept_id"):
                self.snomed_lookup[str(snomed_id)] = entry
        logger.info(f"Built SNOMED lookup table with {len(self.snomed_lookup)} entries")

    def _preprocess_and_parse_nhs_data(self):
        if not self.semantic_parser:
            raise RuntimeError("Semantic Parser required for NHS data preprocessing")
        from preprocessing import get_preprocessor
        preprocessor = get_preprocessor()
        if not preprocessor:
            raise RuntimeError("Preprocessor not initialized before NHS engine.")
        
        for entry in self.nhs_data:
            snomed_fsn_raw = entry.get("snomed_fsn", "").strip()
            primary_name_raw = entry.get("primary_source_name", "").strip()
            snomed_fsn_clean = re.sub(r'\s*\((procedure|qualifier value|finding)\)$', '', snomed_fsn_raw, flags=re.I).strip()

            entry["_clean_fsn_for_embedding"] = preprocessor.preprocess(snomed_fsn_clean)
            entry["_clean_primary_name_for_embedding"] = preprocessor.preprocess(primary_name_raw)
            entry["_interventional_terms"] = detect_interventional_procedure_terms(entry["_clean_primary_name_for_embedding"])
            entry['_parsed_components'] = self.semantic_parser.parse_exam_name(entry["_clean_primary_name_for_embedding"], 'Other')

    def _find_local_cache_file(self) -> Optional[str]:
        """Finds the single expected cache file on the local disk for the current model."""
        cache_dir = os.environ.get('RENDER_DISK_PATH', 'embedding-caches')
        if not os.path.isdir(cache_dir):
            return None
            
        # Since sync_cache.py cleans up, there should only be one file per model.
        for filename in os.listdir(cache_dir):
            if filename.startswith(f"{self.nlp_processor.model_key}_") and filename.endswith(".cache"):
                return os.path.join(cache_dir, filename)
        return None

    def _load_index_from_local_disk(self):
        """
        Loads the FAISS index from the single cache file on the local disk.
        Trusts that sync_cache.py has already provided the latest version.
        """
        local_cache_path = self._find_local_cache_file()

        if local_cache_path:
            try:
                with open(local_cache_path, 'rb') as f:
                    cache_content = pickle.load(f)
                self.vector_index = faiss.deserialize_index(cache_content['index_data'])
                self.index_to_snomed_id = cache_content['id_mapping']
                logger.info(f"Successfully loaded FAISS index for model '{self.nlp_processor.model_key}' from local path: {local_cache_path}")
            except Exception as e:
                logger.critical(f"CRITICAL: Failed to load FAISS index from '{local_cache_path}': {e}.")
        else:
             logger.critical(f"CRITICAL: Cache not found on local disk for model '{self.nlp_processor.model_key}'. Ensure sync_cache.py ran successfully.")

    def standardize_exam(self, input_exam: str, extracted_input_components: Dict, custom_nlp_processor: Optional[NLPProcessor] = None) -> Dict:
        nlp_proc = custom_nlp_processor or self.nlp_processor
        if not nlp_proc or not nlp_proc.is_available():
            return {'error': 'NLP Processor not available', 'confidence': 0.0}

        if not self._embeddings_loaded or self.nlp_processor.model_key != nlp_proc.model_key:
            logger.info(f"Loading index for model '{nlp_proc.model_key}'...")
            self.nlp_processor = nlp_proc
            self._load_index_from_local_disk()
            self._embeddings_loaded = True
        
        if not self.vector_index:
            return {'error': 'Vector index is not loaded. Cannot perform search.', 'confidence': 0.0}
            
        # 1. RETRIEVAL STAGE
        primary_input_embedding = nlp_proc.get_text_embedding(input_exam)
        input_ensemble_embedding = np.concatenate([primary_input_embedding, primary_input_embedding]).astype('float32')
        faiss.normalize_L2(input_ensemble_embedding.reshape(1, -1))

        top_k = self.config['retriever_top_k']
        distances, indices = self.vector_index.search(input_ensemble_embedding.reshape(1, -1), top_k)
        
        candidate_snomed_ids = [self.index_to_snomed_id[i] for i in indices[0] if i < len(self.index_to_snomed_id)]
        candidate_entries = [self.snomed_lookup[str(sid)] for sid in candidate_snomed_ids if str(sid) in self.snomed_lookup]

        # 2. RANKING STAGE
        best_match, highest_confidence = None, 0.0
        
        for i, entry in enumerate(candidate_entries):
            semantic_sim = float(distances[0][i])
            fuzzy_score = fuzz.token_sort_ratio(input_exam.lower(), entry.get("_clean_primary_name_for_embedding", "").lower()) / 100.0
            semantic_score = (0.7 * semantic_sim) + (0.3 * fuzzy_score)

            input_interventional_terms = set(detect_interventional_procedure_terms(input_exam))
            nhs_interventional_terms = set(entry.get('_interventional_terms', []))
            interventional_score = 0
            if input_interventional_terms and nhs_interventional_terms: 
                interventional_score = self.config['interventional_bonus']
            elif input_interventional_terms and not nhs_interventional_terms: 
                interventional_score = self.config['interventional_penalty']
            
            input_tokens = {w for w in input_exam.lower().split() if w not in self._specificity_stop_words}
            nhs_tokens = {w for w in entry.get("_clean_primary_name_for_embedding", "").lower().split() if w not in self._specificity_stop_words}
            specificity_penalty = len(nhs_tokens - input_tokens) * self.config['specificity_penalty_weight']
            
            current_score = self._calculate_match_score(input_exam, extracted_input_components, entry, semantic_score, interventional_score, specificity_penalty)

            if current_score > highest_confidence:
                highest_confidence, best_match = current_score, entry

        if best_match:
            best_match_parsed = best_match.get('_parsed_components', {})
            match_laterality = (best_match_parsed.get('laterality') or [None])[0]
            input_laterality = (extracted_input_components.get('laterality') or [None])[0]
            strip_laterality = (not input_laterality and match_laterality and match_laterality != 'bilateral')
            
            if strip_laterality:
                bilateral_peer = self.find_bilateral_peer(best_match)
                if bilateral_peer:
                    logger.info(f"Found bilateral peer for ambiguous input. Swapping '{best_match.get('primary_source_name')}' for '{bilateral_peer.get('primary_source_name')}'.")
                    return self._format_match_result(bilateral_peer, extracted_input_components, highest_confidence, nlp_proc)

            return self._format_match_result(best_match, extracted_input_components, highest_confidence, nlp_proc, strip_laterality_from_name=strip_laterality)
        
        return {'clean_name': input_exam, 'snomed_id': '', 'confidence': 0.0, 'source': 'NO_MATCH'}

    def _calculate_match_score(self, input_exam_text, input_components, nhs_entry, semantic_score, interventional_score, specificity_penalty):
        nhs_components = nhs_entry.get('_parsed_components', {})
        input_anatomy = set(input_components.get('anatomy', []))
        nhs_anatomy = set(nhs_components.get('anatomy', []))
        anatomy_score = len(input_anatomy.intersection(nhs_anatomy)) / len(input_anatomy.union(nhs_anatomy)) if input_anatomy.union(nhs_anatomy) else 1.0
        
        # Enhanced modality scoring with similarity matrix
        modality_score = self._calculate_modality_score(
            input_components.get('modality'), 
            nhs_components.get('modality')
        )
        
        input_lat = (input_components.get('laterality') or [None])[0]
        nhs_lat = (nhs_components.get('laterality') or [None])[0]
        laterality_score = 1.0 if input_lat == nhs_lat else 0.5
        
        # Enhanced contrast scoring with configurable penalties
        input_con = (input_components.get('contrast') or [None])[0]
        nhs_con = (nhs_components.get('contrast') or [None])[0]
        contrast_score = self._calculate_contrast_score(input_con, nhs_con)
        
        input_tech = set(input_components.get('technique', []))
        nhs_tech = set(nhs_components.get('technique', []))
        technique_score = len(input_tech.intersection(nhs_tech)) / len(input_tech.union(nhs_tech)) if input_tech.union(nhs_tech) else 1.0
        
        cfg_comp = self.config['weights_component']
        component_score = (
            cfg_comp['anatomy'] * anatomy_score + 
            cfg_comp['modality'] * modality_score + 
            cfg_comp['laterality'] * laterality_score + 
            cfg_comp['contrast'] * contrast_score + 
            cfg_comp['technique'] * technique_score
        )
        
        # Enhanced final score calculation with context bonuses
        cfg_final = self.config['weights_final']
        final_score = (
            cfg_final['component'] * component_score + 
            cfg_final['semantic'] * semantic_score
        )
        
        # Add frequency scoring if available (placeholder for future implementation)
        if 'frequency' in cfg_final:
            frequency_score = self._calculate_frequency_score(nhs_entry)
            final_score += cfg_final['frequency'] * frequency_score
        
        # Add interventional scoring
        final_score += interventional_score
        
        # Add context-aware bonuses
        context_bonus = self._calculate_context_bonus(input_exam_text, nhs_entry)
        final_score += context_bonus
        
        # Apply specificity penalty
        final_score *= (1 - specificity_penalty)
        
        # Add exact match bonus
        if input_exam_text.strip().lower() == nhs_entry.get('primary_source_name', '').lower():
            final_score += self.config['exact_match_bonus']
        
        # Add synonym match bonus
        synonym_bonus = self._calculate_synonym_bonus(input_exam_text, nhs_entry)
        final_score += synonym_bonus
            
        return max(0, final_score)

    def _format_match_result(self, best_match: Dict, extracted_input_components: Dict, confidence: float, nlp_proc: NLPProcessor, strip_laterality_from_name: bool = False) -> Dict:
        model_name = getattr(nlp_proc, 'model_key', 'default').split('/')[-1]
        source_name = f'UNIFIED_MATCH_V2_2_RETRIEVER_{model_name.upper()}'
        is_interventional = bool(best_match.get('_interventional_terms', []))
        clean_name = best_match.get('primary_source_name', '')
        
        if strip_laterality_from_name:
            clean_name = re.sub(r'\s+(lt|rt|left|right|both|bilateral)$', '', clean_name, flags=re.I).strip()

        return {
            'clean_name': clean_name, 
            'snomed_id': best_match.get('snomed_concept_id', ''), 
            'snomed_fsn': best_match.get('snomed_fsn', ''), 
            'snomed_laterality_concept_id': best_match.get('snomed_laterality_concept_id', ''), 
            'snomed_laterality_fsn': best_match.get('snomed_laterality_fsn', ''), 
            'is_diagnostic': not is_interventional, 
            'is_interventional': is_interventional, 
            'confidence': min(confidence, 1.0), 
            'source': source_name, 
            'anatomy': extracted_input_components.get('anatomy', []), 
            'laterality': extracted_input_components.get('laterality', []), 
            'contrast': extracted_input_components.get('contrast', []), 
            'modality': extracted_input_components.get('modality', []), 
            'technique': extracted_input_components.get('technique', [])
        }

    def find_bilateral_peer(self, specific_entry: Dict) -> Optional[Dict]:
        specific_components = specific_entry.get('_parsed_components')
        if not specific_components: return None
        target_modality = specific_components.get('modality')
        target_anatomy = set(specific_components.get('anatomy', []))
        target_contrast = (specific_components.get('contrast') or [None])[0]
        target_techniques = set(specific_components.get('technique', []))
        
        for entry in self.nhs_data:
            entry_components = entry.get('_parsed_components')
            if not entry_components: continue
            if (entry_components.get('laterality') or [None])[0] != 'bilateral': continue
            if (
                entry_components.get('modality') == target_modality and 
                set(entry_components.get('anatomy', [])) == target_anatomy and 
                (entry_components.get('contrast') or [None])[0] == target_contrast and 
                set(entry_components.get('technique', [])) == target_techniques
            ):
                return entry
        return None
    
    def _calculate_modality_score(self, input_modality: str, nhs_modality: str) -> float:
        """Calculate modality score using similarity matrix for partial credit."""
        if not input_modality or not nhs_modality:
            return 1.0 if input_modality == nhs_modality else 0.0
        
        # Exact match
        if input_modality == nhs_modality:
            return 1.0
        
        # Check similarity matrix
        if input_modality in self.modality_similarity:
            similarity_map = self.modality_similarity[input_modality]
            if nhs_modality in similarity_map:
                return similarity_map[nhs_modality]
        
        # Reverse check (NHS -> input)
        if nhs_modality in self.modality_similarity:
            similarity_map = self.modality_similarity[nhs_modality]
            if input_modality in similarity_map:
                return similarity_map[input_modality]
        
        # No match
        return 0.0
    
    def _calculate_contrast_score(self, input_contrast: str, nhs_contrast: str) -> float:
        """Calculate contrast score with configurable penalties."""
        # Exact match
        if input_contrast == nhs_contrast:
            return 1.0
        
        # One or both are None/null
        if not input_contrast or not nhs_contrast:
            return self.config.get('contrast_null_score', 0.7)
        
        # Mismatch
        return self.config.get('contrast_mismatch_score', 0.3)
    
    def _calculate_context_bonus(self, input_exam: str, nhs_entry: dict) -> float:
        """Calculate context-aware bonuses based on clinical scenarios."""
        if not self.context_scoring:
            return 0.0
        
        input_lower = input_exam.lower()
        nhs_name_lower = nhs_entry.get('primary_source_name', '').lower()
        bonus = 0.0
        
        # Check each context type
        for context_type in ['emergency', 'screening', 'intervention', 'pregnancy', 'paediatric']:
            keywords_key = f'{context_type}_keywords'
            bonus_key = f'{context_type}_bonus'
            
            if keywords_key in self.context_scoring and bonus_key in self.context_scoring:
                keywords = self.context_scoring[keywords_key]
                
                # Check if both input and NHS entry contain keywords from this context
                input_has_context = any(keyword in input_lower for keyword in keywords)
                nhs_has_context = any(keyword in nhs_name_lower for keyword in keywords)
                
                if input_has_context and nhs_has_context:
                    bonus += self.context_scoring[bonus_key]
        
        return bonus
    
    def _calculate_synonym_bonus(self, input_exam: str, nhs_entry: dict) -> float:
        """Calculate bonus for medical abbreviation/synonym matches."""
        if not self.preprocessing_config.get('medical_abbreviations'):
            return 0.0
        
        input_lower = input_exam.lower()
        nhs_name_lower = nhs_entry.get('primary_source_name', '').lower()
        abbreviations = self.preprocessing_config['medical_abbreviations']
        
        # Check for abbreviation expansions
        for abbrev, expansion in abbreviations.items():
            abbrev_lower = abbrev.lower()
            expansion_lower = expansion.lower()
            
            # Check if input has abbreviation and NHS has expansion (or vice versa)
            if ((abbrev_lower in input_lower and expansion_lower in nhs_name_lower) or
                (expansion_lower in input_lower and abbrev_lower in nhs_name_lower)):
                return self.config.get('synonym_match_bonus', 0.15)
        
        return 0.0
    
    def _calculate_frequency_score(self, nhs_entry: dict) -> float:
        """Calculate frequency-based score (placeholder for future implementation)."""
        # Future implementation: could use exam frequency data
        # For now, return neutral score
        return 0.5
        
    def validate_consistency(self):
        """Checks for any SNOMED IDs mapped to multiple different primary names."""
        snomed_to_primary_names = defaultdict(set)
        for entry in self.nhs_data:
            if snomed_id := entry.get("snomed_concept_id"):
                if primary_name := entry.get("primary_source_name"):
                    snomed_to_primary_names[snomed_id].add(primary_name)
        inconsistencies = {k: list(v) for k, v in snomed_to_primary_names.items() if len(v) > 1}
        
        if inconsistencies:
            logger.warning(f"Found {len(inconsistencies)} SNOMED IDs with multiple primary source names.")
        else:
            logger.info("NHS data consistency validation passed.")