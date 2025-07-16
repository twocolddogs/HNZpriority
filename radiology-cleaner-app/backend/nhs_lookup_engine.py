# --- START OF FILE nhs_lookup_engine.py ---

# =============================================================================
# NHS LOOKUP ENGINE (FINAL VERSION - CLEAN DATA MODEL)
# =============================================================================
# This version assumes the source NHS.json has been cleaned to use standard,
# newline-free keys (e.g., "snomed_concept_id" instead of "SNOMED CT \nConcept-ID").
# This is the most robust and maintainable architecture.

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
        logger.info("NHSLookupEngine initialized with clean data model and FSN-first pre-computation.")

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
            # MODIFICATION: Using the new, clean key
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
            # MODIFICATION: Using new, clean keys
            snomed_fsn = entry.get("snomed_fsn", "").strip()
            primary_source_name = entry.get("primary_source_name", "").strip()
            
            text_to_process = snomed_fsn if snomed_fsn else primary_source_name
            
            if not text_to_process:
                logger.warning(f"Skipping NHS entry with no usable FSN or Clean Name: {entry.get('snomed_concept_id')}")
                continue

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
        specific_primary_source_name = specific_entry.get("primary_source_name")
        if not specific_primary_source_name: return None
        base_name_pattern = re.compile(r'\s+(lt|rt|left|right)$', re.IGNORECASE)
        base_name = base_name_pattern.sub('', specific_primary_source_name).strip()
        bilateral_pattern = re.compile(r'\s+(both|bilateral)$', re.IGNORECASE)
        for entry in self.nhs_data:
            entry_primary_source_name = entry.get("primary_source_name", "")
            if not bilateral_pattern.search(entry_primary_source_name): continue
            entry_base_name = bilateral_pattern.sub('', entry_primary_source_name).strip()
            if base_name.lower() == entry_base_name.lower():
                logger.info(f"Laterality Fallback: Found bilateral peer '{entry_primary_source_name}' for specific match '{specific_primary_source_name}'")
                return entry
        return None

    def _format_match_result(self, best_match: Dict, extracted_input_components: Dict, confidence: float, nlp_proc: NLPProcessor, strip_laterality_from_name: bool = False) -> Dict:
        """Helper to format the final result dictionary, now with clean keys."""
        model_name = getattr(nlp_proc, 'model_name', 'default').split('/')[-1]
        source_name = f'FSN_PRIMARY_MATCH_V12_{model_name.upper()}'
        
        detected_interventional_terms = best_match.get('_interventional_terms', [])
        is_interventional = bool(detected_interventional_terms)
        is_diagnostic = not is_interventional

        clean_name = best_match.get('primary_source_name', '')
        if strip_laterality_from_name:
            clean_name = re.sub(r'\s+(lt|rt|left|right|both|bilateral)$', '', clean_name, flags=re.I).strip()
        
        return {
            'clean_name': clean_name,
            # MODIFICATION: Using new, clean keys
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
        """Main method to standardize an exam."""
        best_match, highest_confidence = None, 0.0
        nlp_proc = custom_nlp_processor or self.nlp_processor

        if not nlp_proc or not nlp_proc.is_available():
            return {'error': 'NLP Processor not available', 'confidence': 0.0}

        input_embedding = nlp_proc.get_text_embedding(input_exam)
        if input_embedding is None:
            return {'error': 'Could not generate input embedding', 'confidence': 0.0}

        input_interventional_terms = set(detect_interventional_procedure_terms(input_exam))
        is_interventional_input = bool(input_interventional_terms)

        for entry in self.nhs_data:
            nhs_embedding = entry.get("_embedding")
            nhs_components = entry.get("_parsed_components")
            if not nhs_components or nhs_embedding is None: continue

            semantic_score = nlp_proc.calculate_semantic_similarity(input_embedding, nhs_embedding)
            fuzzy_score = fuzz.token_sort_ratio(input_exam.lower(), entry.get("_source_text_for_embedding", "").lower()) / 100.0
            combined_score = (0.7 * semantic_score) + (0.3 * fuzzy_score)

            nhs_interventional_terms = set(entry.get('_interventional_terms', []))
            is_interventional_nhs = bool(nhs_interventional_terms)

            if is_interventional_input and is_interventional_nhs:
                overlap_bonus = 0.25 + (0.1 * len(input_interventional_terms.intersection(nhs_interventional_terms)))
                combined_score += overlap_bonus
            elif is_interventional_input and not is_interventional_nhs: combined_score -= 0.30
            elif not is_interventional_input and is_interventional_nhs: combined_score -= 0.20
            else: combined_score += 0.10

            input_tokens = {word for word in input_exam.lower().split() if word not in self._specificity_stop_words}
            nhs_source_tokens = {word for word in entry.get("_source_text_for_embedding", "").lower().split() if word not in self._specificity_stop_words}
            extra_words = nhs_source_tokens - input_tokens
            if extra_words:
                combined_score -= len(extra_words) * self._specificity_penalty_weight
            
            if combined_score > highest_confidence:
                highest_confidence, best_match = combined_score, entry

        if best_match:
            input_laterality = extracted_input_components.get('laterality', [])
            best_match_parsed = best_match.get('_parsed_components', {})
            match_laterality = best_match_parsed.get('laterality', []) if best_match_parsed else []

            if not input_laterality and match_laterality and match_laterality[0] != 'bilateral':
                bilateral_peer = self.find_bilateral_peer(best_match)
                if bilateral_peer:
                    return self._format_match_result(bilateral_peer, extracted_input_components, highest_confidence, nlp_proc)
                else:
                    return self._format_match_result(best_match, extracted_input_components, highest_confidence, nlp_proc, strip_laterality_from_name=True)

            return self._format_match_result(best_match, extracted_input_components, highest_confidence, nlp_proc)
        
        logger.warning(f"No suitable match found for input: '{input_exam}'")
        return {'clean_name': input_exam, 'snomed_id': '', 'confidence': 0.0, 'source': 'NO_MATCH'}

    def validate_consistency(self):
        """Validate the consistency of the NHS data and initialization state."""
        validation_errors = []
        
        # Check if NHS data was loaded
        if not self.nhs_data:
            validation_errors.append("No NHS data loaded")
        
        # Check if SNOMED lookup table was built
        if not self.snomed_lookup:
            validation_errors.append("SNOMED lookup table is empty")
        
        # Check if semantic parser is available
        if not self.semantic_parser:
            validation_errors.append("Semantic parser not initialized")
        
        # Check if NLP processor is available
        if not self.nlp_processor or not self.nlp_processor.is_available():
            validation_errors.append("NLP processor not available")
        
        # Validate sample of entries have required preprocessing
        sample_entries = self.nhs_data[:min(10, len(self.nhs_data))]
        missing_preprocessing = 0
        for entry in sample_entries:
            if not entry.get("_source_text_for_embedding") or not entry.get("_parsed_components"):
                missing_preprocessing += 1
        
        if missing_preprocessing > 0:
            validation_errors.append(f"{missing_preprocessing}/{len(sample_entries)} sample entries missing preprocessing")
        
        # Log validation results
        if validation_errors:
            for error in validation_errors:
                logger.error(f"NHS Lookup Engine validation error: {error}")
            raise RuntimeError(f"NHS Lookup Engine validation failed: {'; '.join(validation_errors)}")
        else:
            logger.info("NHS Lookup Engine validation passed successfully")
            logger.info(f"Loaded {len(self.nhs_data)} NHS entries with {len(self.snomed_lookup)} SNOMED mappings")