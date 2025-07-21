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
            
            # Calculate anatomical specificity score (replacing old specificity penalty)
            anatomical_specificity_score = self._calculate_anatomical_specificity_score(input_exam, entry)
            
            current_score = self._calculate_match_score(input_exam, extracted_input_components, entry, semantic_score, interventional_score, anatomical_specificity_score)

            if current_score > highest_confidence:
                highest_confidence, best_match = current_score, entry

        if best_match:
            input_laterality = (extracted_input_components.get('laterality') or [None])[0]
            match_laterality = (best_match.get('_parsed_components', {}).get('laterality') or [None])[0]
            strip_laterality = (not input_laterality and match_laterality in ['left', 'right', 'bilateral'])
            
            # If input was laterally ambiguous, it should ALWAYS be marked as ambiguous
            laterally_ambiguous = (not input_laterality and match_laterality in ['left', 'right', 'bilateral'])

            if strip_laterality:
                if bilateral_peer := self.find_bilateral_peer(best_match):
                    return self._format_match_result(bilateral_peer, extracted_input_components, highest_confidence, nlp_proc, strip_laterality_from_name=True, input_exam_text=input_exam, force_ambiguous=laterally_ambiguous)

            return self._format_match_result(best_match, extracted_input_components, highest_confidence, nlp_proc, strip_laterality_from_name=strip_laterality, input_exam_text=input_exam, force_ambiguous=laterally_ambiguous)
        
        return {'clean_name': input_exam, 'snomed_id': '', 'confidence': 0.0, 'source': 'NO_MATCH'}

    def _calculate_laterality_score(self, input_lat: Optional[str], nhs_lat: Optional[str]) -> float:
        """Calculates a more punitive score for laterality mismatches."""
        if input_lat == nhs_lat:
            return 1.0  # Perfect match
        if not input_lat or not nhs_lat:
            return 0.7  # Ambiguous match (e.g., input "Knee" vs NHS "Knee Rt")
        return 0.1  # Direct mismatch (e.g., input "Left" vs NHS "Right")

    def _calculate_match_score(self, input_exam_text, input_components, nhs_entry, semantic_score, interventional_score, anatomical_specificity_score):
        nhs_components = nhs_entry.get('_parsed_components', {})
        w = self.config['weights_component']
        
        # --- MODIFICATION: Use more punitive laterality scoring ---
        input_lat = (input_components.get('laterality') or [None])[0]
        nhs_lat = (nhs_components.get('laterality') or [None])[0]
        laterality_score = self._calculate_laterality_score(input_lat, nhs_lat)
        
        # PIPELINE STEP: Calculate anatomy score with compatibility constraints
        # This prevents impossible mappings like "Lower Limb" → "Penis"
        anatomy_score = self._calculate_anatomy_score_with_constraints(input_components, nhs_components)
        
        # PIPELINE STEP: Check for anatomical compatibility violations
        # If anatomy score is severely negative, this indicates an impossible mapping
        if anatomy_score < -1.0:
            logger.debug(f"Anatomical constraint violation detected, returning 0.0 confidence")
            return 0.0
        
        # PIPELINE STEP: Check diagnostic protection rules
        # Prevent diagnostic exams from mapping to interventional procedures
        diagnostic_protection_penalty = self._check_diagnostic_protection(input_exam_text, nhs_entry)
        if diagnostic_protection_penalty < -1.0:
            logger.debug(f"Diagnostic protection violation detected, returning 0.0 confidence")
            return 0.0
        
        # PIPELINE STEP: Check hybrid modality constraints  
        # Prevent inappropriate hybrid modality confusion (e.g., PET/CT → PET/MRI)
        hybrid_modality_penalty = self._check_hybrid_modality_constraints(input_exam_text, nhs_entry)
        if hybrid_modality_penalty < -1.0:
            logger.debug(f"Hybrid modality constraint violation detected, returning 0.0 confidence")
            return 0.0
        
        modality_score = self._calculate_modality_score(input_components.get('modality'), nhs_components.get('modality'))
        contrast_score = self._calculate_contrast_score((input_components.get('contrast') or [None])[0], (nhs_components.get('contrast') or [None])[0])
        technique_score = self._calculate_set_score(input_components, nhs_components, 'technique')
        
        # PIPELINE STEP: Check for modality mismatch
        # If modalities are completely different (e.g., CT vs US), block the mapping
        if modality_score == 0.0:
            logger.debug(f"Modality mismatch detected, returning 0.0 confidence")
            return 0.0

        # PIPELINE STEP: Check minimum component score thresholds
        # Prevent semantic similarity from overriding fundamental component mismatches
        threshold_violation = self._check_component_thresholds(
            anatomy_score, modality_score, laterality_score, contrast_score, technique_score
        )
        if threshold_violation:
            logger.debug(f"Component threshold violation detected: {threshold_violation}")
            return 0.0

        component_score = (w['anatomy'] * anatomy_score + w['modality'] * modality_score + w['laterality'] * laterality_score + w['contrast'] * contrast_score + w['technique'] * technique_score)
        
        # PIPELINE STEP: Apply semantic weight limiting to prevent override of component logic
        wf = self.config['weights_final']
        threshold_config = self.config.get('minimum_component_thresholds', {})
        if threshold_config.get('enable', False):
            max_semantic_weight = threshold_config.get('max_semantic_weight', 0.6)
            # Limit semantic weight and rebalance with component weight
            actual_semantic_weight = min(wf.get('semantic', 0.40), max_semantic_weight)
            actual_component_weight = 1.0 - actual_semantic_weight
            final_score = (actual_component_weight * component_score + actual_semantic_weight * semantic_score)
            
            if actual_semantic_weight < wf.get('semantic', 0.40):
                logger.debug(f"Limited semantic weight from {wf.get('semantic', 0.40):.3f} to {actual_semantic_weight:.3f} "
                           f"to prevent component override")
        else:
            # Use original weights if threshold checking disabled
            final_score = (wf['component'] * component_score + wf['semantic'] * semantic_score)
        
        final_score += interventional_score
        # PIPELINE STEP: Apply context bonuses (now includes gender/age bonuses previously missing)
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
        nhs_modality = nhs_components.get('modality', '').lower()
        
        # Map NHS modality to config key
        if nhs_modality == 'ct' or 'ct' in nhs_name_lower:
            modality_key = 'ct'
        elif nhs_modality == 'us' or any(term in nhs_name_lower for term in ['us', 'ultrasound', 'sonograph']):
            modality_key = 'us'
        elif nhs_modality == 'mri' or any(term in nhs_name_lower for term in ['mri', 'mr ']):
            modality_key = 'mri'
        elif nhs_modality in ['fluoroscopy', 'fl'] or any(term in nhs_name_lower for term in ['fluoroscop', 'fluoro']):
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