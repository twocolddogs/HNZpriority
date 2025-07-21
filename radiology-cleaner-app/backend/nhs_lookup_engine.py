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
            if filename.startswith(f"{self.nlp_processor.model_key}_") and filename.endswith(".cache"):
                return os.path.join(cache_dir, filename)
        return None

    def _load_index_from_local_disk(self):
        local_cache_path = self._find_local_cache_file()
        if local_cache_path and os.path.exists(local_cache_path):
            try:
                with open(local_cache_path, 'rb') as f: cache_content = pickle.load(f)
                self.vector_index = faiss.deserialize_index(cache_content['index_data'])
                self.index_to_snomed_id = cache_content['id_mapping']
                logger.info(f"Successfully loaded FAISS index for model '{self.nlp_processor.model_key}' from: {local_cache_path}")
            except Exception as e:
                logger.critical(f"CRITICAL: Failed to load FAISS index from '{local_cache_path}': {e}.")
        else:
            logger.critical(f"CRITICAL: Cache not found on local disk for model '{self.nlp_processor.model_key}'.")

    def standardize_exam(self, input_exam: str, extracted_input_components: Dict, custom_nlp_processor: Optional[NLPProcessor] = None) -> Dict:
        nlp_proc = custom_nlp_processor or self.nlp_processor
        if not nlp_proc or not nlp_proc.is_available(): return {'error': 'NLP Processor not available', 'confidence': 0.0}

        if not self._embeddings_loaded or self.nlp_processor.model_key != nlp_proc.model_key:
            logger.info(f"Loading index for model '{nlp_proc.model_key}'...")
            self.nlp_processor = nlp_proc
            self._load_index_from_local_disk()
            self._embeddings_loaded = True
        
        if not self.vector_index: return {'error': 'Vector index not loaded.', 'confidence': 0.0}
            
        input_embedding = nlp_proc.get_text_embedding(input_exam)
        if input_embedding is None: return {'error': 'Failed to generate embedding for input.', 'confidence': 0.0}
        
        input_ensemble_embedding = np.concatenate([input_embedding, input_embedding]).astype('float32')
        faiss.normalize_L2(input_ensemble_embedding.reshape(1, -1))

        top_k = self.config['retriever_top_k']
        distances, indices = self.vector_index.search(input_ensemble_embedding.reshape(1, -1), top_k)
        
        candidate_snomed_ids = [self.index_to_snomed_id[i] for i in indices[0] if i < len(self.index_to_snomed_id)]
        candidate_entries = [self.snomed_lookup[str(sid)] for sid in candidate_snomed_ids if str(sid) in self.snomed_lookup]

        best_match, highest_confidence = None, 0.0
        
        for i, entry in enumerate(candidate_entries):
            semantic_sim = float(distances[0][i])
            fuzzy_score = fuzz.token_sort_ratio(input_exam.lower(), entry.get("_clean_primary_name_for_embedding", "").lower()) / 100.0
            semantic_score = (0.7 * semantic_sim) + (0.3 * fuzzy_score)

            input_interventional_terms = set(detect_interventional_procedure_terms(input_exam))
            nhs_interventional_terms = set(entry.get('_interventional_terms', []))
            interventional_score = self.config['interventional_bonus'] if input_interventional_terms and nhs_interventional_terms else (self.config['interventional_penalty'] if input_interventional_terms and not nhs_interventional_terms else 0)
            
            input_tokens = {w for w in input_exam.lower().split() if w not in self._specificity_stop_words}
            nhs_tokens = {w for w in entry.get("_clean_primary_name_for_embedding", "").lower().split() if w not in self._specificity_stop_words}
            specificity_penalty = len(nhs_tokens - input_tokens) * self.config['specificity_penalty_weight']
            
            current_score = self._calculate_match_score(input_exam, extracted_input_components, entry, semantic_score, interventional_score, specificity_penalty)

            if current_score > highest_confidence:
                highest_confidence, best_match = current_score, entry

        if best_match:
            input_laterality = (extracted_input_components.get('laterality') or [None])[0]
            match_laterality = (best_match.get('_parsed_components', {}).get('laterality') or [None])[0]
            strip_laterality = (not input_laterality and match_laterality in ['left', 'right', 'bilateral'])

            if strip_laterality:
                if bilateral_peer := self.find_bilateral_peer(best_match):
                    return self._format_match_result(bilateral_peer, extracted_input_components, highest_confidence, nlp_proc, strip_laterality_from_name=False)

            return self._format_match_result(best_match, extracted_input_components, highest_confidence, nlp_proc, strip_laterality_from_name=strip_laterality)
        
        return {'clean_name': input_exam, 'snomed_id': '', 'confidence': 0.0, 'source': 'NO_MATCH'}

    def _calculate_laterality_score(self, input_lat: Optional[str], nhs_lat: Optional[str]) -> float:
        """Calculates a more punitive score for laterality mismatches."""
        if input_lat == nhs_lat:
            return 1.0  # Perfect match
        if not input_lat or not nhs_lat:
            return 0.7  # Ambiguous match (e.g., input "Knee" vs NHS "Knee Rt")
        return 0.1  # Direct mismatch (e.g., input "Left" vs NHS "Right")

    def _calculate_match_score(self, input_exam_text, input_components, nhs_entry, semantic_score, interventional_score, specificity_penalty):
        nhs_components = nhs_entry.get('_parsed_components', {})
        w = self.config['weights_component']
        
        # --- MODIFICATION: Use more punitive laterality scoring ---
        input_lat = (input_components.get('laterality') or [None])[0]
        nhs_lat = (nhs_components.get('laterality') or [None])[0]
        laterality_score = self._calculate_laterality_score(input_lat, nhs_lat)
        
        anatomy_score = self._calculate_set_score(input_components, nhs_components, 'anatomy')
        modality_score = self._calculate_modality_score(input_components.get('modality'), nhs_components.get('modality'))
        contrast_score = self._calculate_contrast_score((input_components.get('contrast') or [None])[0], (nhs_components.get('contrast') or [None])[0])
        technique_score = self._calculate_set_score(input_components, nhs_components, 'technique')
        
        # --- MODIFICATION: Add heavy penalty for modality mismatch ---
        if modality_score == 0.0:
             # If modalities are completely different (e.g., CT vs US), slash the confidence.
            return 0.0

        component_score = (w['anatomy'] * anatomy_score + w['modality'] * modality_score + w['laterality'] * laterality_score + w['contrast'] * contrast_score + w['technique'] * technique_score)
        
        wf = self.config['weights_final']
        final_score = (wf['component'] * component_score + wf['semantic'] * semantic_score)
        
        final_score += interventional_score
        final_score += self._calculate_context_bonus(input_exam_text, nhs_entry)
        final_score += self._calculate_synonym_bonus(input_exam_text, nhs_entry)
        final_score += self._calculate_biopsy_modality_preference(input_exam_text, nhs_entry)
        final_score -= specificity_penalty
        
        if input_exam_text.strip().lower() == nhs_entry.get('primary_source_name', '').lower():
            final_score += self.config.get('exact_match_bonus', 0.25)
            
        return max(0.0, min(1.0, final_score))

    def _format_match_result(self, best_match: Dict, extracted_input_components: Dict, confidence: float, nlp_proc: NLPProcessor, strip_laterality_from_name: bool = False) -> Dict:
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
        # This dictionary includes all parsed components AND the final confidence score.
        final_components = {
            **extracted_input_components,  # Unpack anatomy, laterality, contrast, technique
            'confidence': confidence
        }
        
        return {
            'clean_name': clean_name.strip(),
            'snomed_id': best_match.get('snomed_concept_id', ''),
            'snomed_fsn': best_match.get('snomed_fsn', ''),
            'snomed_laterality_concept_id': best_match.get('snomed_laterality_concept_id', ''),
            'snomed_laterality_fsn': best_match.get('snomed_laterality_fsn', ''),
            'is_diagnostic': not is_interventional,
            'is_interventional': is_interventional,
            'source': source_name,
            'ambiguous': strip_laterality_from_name,  # Track when laterality was stripped due to ambiguous input
            'components': final_components # Return the components nested under one key
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
            entry_laterality = (entry_components.get('laterality') or [None])[0]
            if entry_laterality not in [None, 'bilateral']: continue
            
            if (entry_components.get('modality') == target_modality and set(entry_components.get('anatomy', [])) == target_anatomy and
                (entry_components.get('contrast') or [None])[0] == target_contrast and set(entry_components.get('technique', [])) == target_techniques):
                return entry
        return None
    
    def _calculate_set_score(self, comp1, comp2, key):
        set1, set2 = set(comp1.get(key, [])), set(comp2.get(key, []))
        if not set1 and not set2: return 1.0
        if not set1.union(set2): return 0.0
        return len(set1.intersection(set2)) / len(set1.union(set2))
    
    def _calculate_modality_score(self, input_modality: Optional[str], nhs_modality: Optional[str]) -> float:
        if input_modality == nhs_modality: return 1.0
        if not input_modality or not nhs_modality: return 0.5
        return self.modality_similarity.get(input_modality, {}).get(nhs_modality, 0.0)
    
    def _calculate_contrast_score(self, input_contrast: Optional[str], nhs_contrast: Optional[str]) -> float:
        # Perfect match (both same, including both None)
        if input_contrast == nhs_contrast: 
            # Bonus for both being None when preference is enabled
            if (not input_contrast and not nhs_contrast and 
                self.config.get('prefer_no_contrast_when_unspecified', False)):
                return 1.0 + self.config.get('no_contrast_preference_bonus', 0.15)
            return 1.0
        
        # One has contrast, one doesn't
        if not input_contrast or not nhs_contrast: 
            return self.config.get('contrast_null_score', 0.7)
        
        # Both have contrast but different types (with vs without)    
        return self.config.get('contrast_mismatch_score', 0.3)
    
    def _calculate_context_bonus(self, input_exam: str, nhs_entry: dict) -> float:
        if not self.context_scoring: return 0.0
        input_lower, nhs_name_lower = input_exam.lower(), nhs_entry.get('primary_source_name', '').lower()
        bonus = 0.0
        for context_type, details in self.context_scoring.items():
            if isinstance(details, dict) and 'keywords' in details and 'bonus' in details:
                keywords = details['keywords']
                if any(k in input_lower for k in keywords) and any(k in nhs_name_lower for k in keywords):
                    bonus += details['bonus']
        return bonus
    
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
            
        # Apply modality preference based on NHS entry modality/name
        nhs_components = nhs_entry.get('_parsed_components', {})
        nhs_modality = nhs_components.get('modality', '').lower()
        
        # Check both modality and name content for guidance type
        if nhs_modality == 'ct' or 'ct' in nhs_name_lower:
            return self.config.get('biopsy_ct_preference_bonus', 0.25)
        elif nhs_modality == 'us' or any(term in nhs_name_lower for term in ['us', 'ultrasound', 'sonograph']):
            return self.config.get('biopsy_us_preference_bonus', 0.20)
        elif nhs_modality in ['fluoroscopy', 'fl'] or any(term in nhs_name_lower for term in ['fluoroscop', 'fluoro']):
            return self.config.get('biopsy_fl_preference_penalty', -0.15)
            
        return 0.0

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