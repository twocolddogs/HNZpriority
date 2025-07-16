# --- START OF FILE nhs_lookup_engine.py ---

# =============================================================================
# NHS LOOKUP ENGINE (FINAL CORRECTED VERSION)
# =============================================================================
# This version includes all architectural improvements:
# 1. FSN-First Pre-computation.
# 2. Text-Driven Interventional Scoring.
# 3. Intelligent Laterality Fallback.
# 4. Specificity Penalty.
# 5. RESTORED: A robust Modality Matching Gatekeeper to prevent incorrect
#    modality assignments.
# 6. RESTORED: A balanced component-based scoring system.
# =============================================================================

import json
import logging
import re
from typing import Dict, List, Optional
from collections import defaultdict
from fuzzywuzzy import fuzz
from typing import TYPE_CHECKING 

from nlp_processor import NLPProcessor
from context_detection import detect_interventional_procedure_terms

if TYPE_CHECKING:
    from parser import RadiologySemanticParser

logger = logging.getLogger(__name__)

class NHSLookupEngine:
    def __init__(self, nhs_json_path: str, nlp_processor: NLPProcessor, semantic_parser: 'RadiologySemanticParser'):
        self.nhs_data = []
        self.snomed_lookup = {}
        self.nhs_json_path = nhs_json_path
        self.nlp_processor = nlp_processor
        self.semantic_parser = semantic_parser
        self._embeddings_cache = {}
        
        self._load_nhs_data()
        self._build_lookup_tables()
        self._preprocess_and_parse_nhs_data()
        self._precompute_embeddings()

        self._specificity_penalty_weight = 0.08
        self._specificity_stop_words = {
            'a', 'an', 'the', 'and', 'or', 'with', 'without', 'for', 'of', 'in', 'on', 'to', 'is', 'from',
            'ct', 'mr', 'mri', 'us', 'xr', 'x-ray', 'nm', 'pet', 'dexa', 'dect', 'computed', 'tomography',
            'magnetic', 'resonance', 'ultrasound', 'radiograph', 'scan', 'scans', 'imaging', 'image', 'mammo', 'mammogram',
            'left', 'right', 'bilateral', 'lt', 'rt', 'bilat', 'both', 'contrast', 'iv', 'gadolinium', 'gad', 'c+', 'c-',
            'procedure', 'examination', 'study', 'protocol', 'view', 'views', 'projection',
            'series', 'ap', 'pa', 'lat', 'oblique', 'guidance', 'guided', 'body', 'whole',
            'artery', 'vein', 'joint', 'spine', 'tract', 'system', 'time', 'delayed', 'immediate', 'phase', 'early', 'late'
        }
        logger.info("NHSLookupEngine initialized with clean data model and robust matching logic.")

    def _load_nhs_data(self):
        try:
            with open(self.nhs_json_path, 'r', encoding='utf-8') as f:
                # Assuming the file has been cleaned as per prior instructions
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
            snomed_fsn = entry.get("snomed_fsn", "").strip()
            primary_name = entry.get("primary_source_name", "").strip()
            
            text_to_process = snomed_fsn if snomed_fsn else primary_name
            if not text_to_process: continue

            text_to_process = re.sub(r'\s*\((procedure|qualifier value)\)$', '', text_to_process, flags=re.I).strip()
            preprocessed_text = preprocessor.preprocess(text_to_process)
            entry["_source_text_for_embedding"] = preprocessed_text
            entry["_interventional_terms"] = detect_interventional_procedure_terms(preprocessed_text)
            entry['_parsed_components'] = self.semantic_parser.parse_exam_name(preprocessed_text, 'Other')

    def _precompute_embeddings(self, custom_nlp_processor: Optional[NLPProcessor] = None):
        nlp_proc = custom_nlp_processor or self.nlp_processor
        if not nlp_proc or not nlp_proc.is_available(): return
        model_name = getattr(nlp_proc, 'model_name', 'unknown')
        if model_name in self._embeddings_cache: return
        texts_to_embed = [e["_source_text_for_embedding"] for e in self.nhs_data if e.get("_source_text_for_embedding")]
        embeddings = nlp_proc.batch_get_embeddings(texts_to_embed)
        text_to_embedding = dict(zip(texts_to_embed, embeddings))
        for entry in self.nhs_data:
            source_text = entry.get("_source_text_for_embedding")
            entry["_embedding"] = text_to_embedding.get(source_text)

    def find_bilateral_peer(self, specific_entry: Dict) -> Optional[Dict]:
        specific_clean_name = specific_entry.get("clean_name")
        if not specific_clean_name: return None
        base_name_pattern = re.compile(r'\s+(lt|rt|left|right)$', re.IGNORECASE)
        base_name = base_name_pattern.sub('', specific_clean_name).strip()
        bilateral_pattern = re.compile(r'\s+(both|bilateral)$', re.IGNORECASE)
        for entry in self.nhs_data:
            entry_clean_name = entry.get("clean_name", "")
            if not bilateral_pattern.search(entry_clean_name): continue
            entry_base_name = bilateral_pattern.sub('', entry_clean_name).strip()
            if base_name.lower() == entry_base_name.lower():
                return entry
        return None

    def _format_match_result(self, best_match: Dict, extracted_input_components: Dict, confidence: float, nlp_proc: NLPProcessor, strip_laterality_from_name: bool = False) -> Dict:
        model_name = getattr(nlp_proc, 'model_name', 'default').split('/')[-1]
        source_name = f'UNIFIED_MATCH_V12_{model_name.upper()}'
        
        detected_interventional_terms = best_match.get('_interventional_terms', [])
        is_interventional = bool(detected_interventional_terms)
        is_diagnostic = not is_interventional

        clean_name = best_match.get('primary_source_name', '')
        if strip_laterality_from_name:
            clean_name = re.sub(r'\s+(lt|rt|left|right|both|bilateral)$', '', clean_name, flags=re.I).strip()
        
        return {
            'clean_name': clean_name,
            'snomed_id': best_match.get('snomed_concept_id', ''),
            'snomed_fsn': best_match.get('snomed_fsn', ''),
            'snomed_laterality_concept_id': best_match.get('snomed_laterality_concept_id', ''),
            'snomed_laterality_fsn': best_match.get('snomed_laterality_fsn', ''),
            'is_diagnostic': is_diagnostic,
            'is_interventional': is_interventional,
            'detected_interventional_terms': detected_interventional_terms,
            'confidence': min(confidence, 1.0),
            'source': source_name,
            'anatomy': extracted_input_components.get('anatomy', []),
            'laterality': extracted_input_components.get('laterality', []),
            'contrast': extracted_input_components.get('contrast', []),
            'modality': extracted_input_components.get('modality', []),
            'technique': extracted_input_components.get('technique', []),
        }

    def standardize_exam(self, input_exam: str, extracted_input_components: Dict, custom_nlp_processor: Optional[NLPProcessor] = None) -> Dict:
        best_match, highest_confidence = None, 0.0
        nlp_proc = custom_nlp_processor or self.nlp_processor

        if not nlp_proc or not nlp_proc.is_available():
            return {'error': 'NLP Processor not available', 'confidence': 0.0}

        model_name = getattr(nlp_proc, 'model_name', 'unknown')
        if model_name not in self._embeddings_cache:
            logger.info(f"Embeddings for model '{model_name}' not found in cache. Pre-computing now...")
            self._precompute_embeddings(custom_nlp_processor=nlp_proc)
            self._embeddings_cache[model_name] = True # Mark as cached
        
        input_embedding = nlp_proc.get_text_embedding(input_exam)
        if input_embedding is None:
            return {'error': 'Could not generate input embedding', 'confidence': 0.0}

        # --- Get parsed components from input for matching ---
        input_modality = extracted_input_components.get('modality')
        input_laterality = extracted_input_components.get('laterality')
        input_contrast = extracted_input_components.get('contrast')
        input_techniques = set(extracted_input_components.get('technique', []))
        input_interventional_terms = set(detect_interventional_procedure_terms(input_exam))
        is_interventional_input = bool(input_interventional_terms)

        # --- Main Matching Loop ---
        for entry in self.nhs_data:
            nhs_embedding = entry.get("_embedding")
            nhs_components = entry.get("_parsed_components")
            if not nhs_components or nhs_embedding is None: continue

            # ================================================================
            # MODALITY MATCHING GATEKEEPER (RESTORED)
            # ================================================================
            nhs_modality = nhs_components.get('modality')
            if input_modality and input_modality.lower() != 'other' and nhs_modality and input_modality.lower() != nhs_modality.lower():
                continue # Hard filter: skip if modalities are different and known.
            
            # ================================================================
            # LATERALITY MATCHING GATEKEEPER (RESTORED)
            # ================================================================
            nhs_laterality = nhs_components.get('laterality')
            if input_laterality and nhs_laterality and input_laterality[0].lower() != nhs_laterality[0].lower():
                continue # Hard filter: if both specify different lateralities, skip.
                
            # ================================================================
            # SCORING LOGIC
            # ================================================================
            semantic_score = nlp_proc.calculate_semantic_similarity(input_embedding, nhs_embedding)
            fuzzy_score = fuzz.token_sort_ratio(input_exam.lower(), entry.get("_source_text_for_embedding", "").lower()) / 100.0
            combined_score = (0.7 * semantic_score) + (0.3 * fuzzy_score)

            # Component Alignment Bonuses
            if input_modality and nhs_modality and input_modality.lower() == nhs_modality.lower():
                combined_score += 0.1
            
            common_techniques = input_techniques.intersection(set(nhs_components.get('technique', [])))
            if common_techniques:
                combined_score += len(common_techniques) * 0.20

            if input_contrast and nhs_components.get('contrast') and input_contrast[0] == nhs_components['contrast'][0]:
                combined_score += 0.15
            elif input_contrast and not nhs_components.get('contrast'):
                combined_score -= 0.1
            elif not input_contrast and nhs_components.get('contrast'):
                combined_score -= 0.05

            # Text-Driven Interventional Scoring
            nhs_interventional_terms = set(entry.get('_interventional_terms', []))
            is_interventional_nhs = bool(nhs_interventional_terms)
            if is_interventional_input and is_interventional_nhs:
                combined_score += 0.25 + (0.1 * len(input_interventional_terms.intersection(nhs_interventional_terms)))
            elif is_interventional_input and not is_interventional_nhs:
                combined_score -= 0.30
            elif not is_interventional_input and is_interventional_nhs:
                combined_score -= 0.20
            else: # Both are diagnostic
                combined_score += 0.10

            # Specificity Penalty
            input_tokens = {w for w in input_exam.lower().split() if w not in self._specificity_stop_words}
            nhs_tokens = {w for w in entry.get("_source_text_for_embedding", "").lower().split() if w not in self._specificity_stop_words}
            extra_words = nhs_tokens - input_tokens
            if extra_words:
                combined_score -= len(extra_words) * self._specificity_penalty_weight
            
            if combined_score > highest_confidence:
                highest_confidence, best_match = combined_score, entry

        if best_match:
            # Post-Matching Laterality Fallback Logic
            best_match_parsed = best_match.get('_parsed_components', {})
            match_laterality = best_match_parsed.get('laterality', []) if best_match_parsed else []
            if not input_laterality and match_laterality and match_laterality[0] != 'bilateral':
                bilateral_peer = self.find_bilateral_peer(best_match)
                if bilateral_peer:
                    return self._format_match_result(bilateral_peer, extracted_input_components, highest_confidence, nlp_proc)
                else:
                    return self._format_match_result(best_match, extracted_input_components, highest_confidence, nlp_proc, strip_laterality_from_name=True)
            return self._format_match_result(best_match, extracted_input_components, highest_confidence, nlp_proc)
        
        return {'clean_name': input_exam, 'snomed_id': '', 'confidence': 0.0, 'source': 'NO_MATCH'}
        
    def validate_consistency(self):
        """Validates the consistency of the NHS data."""
        # This function can be expanded with more checks
        snomed_to_clean_names = defaultdict(set)
        for entry in self.nhs_data:
            if snomed_id := entry.get("snomed_concept_id"):
                if clean_name := entry.get("clean_name"):
                    snomed_to_clean_names[snomed_id].add(clean_name)
        inconsistencies = {k: list(v) for k, v in snomed_to_clean_names.items() if len(v) > 1}
        if inconsistencies:
            logger.warning(f"Found {len(inconsistencies)} SNOMED IDs with multiple clean names.")
        else:
            logger.info("NHS data consistency validation passed.")