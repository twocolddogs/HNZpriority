import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import re
from fuzzywuzzy import fuzz
from nlp_processor import NLPProcessor

logger = logging.getLogger(__name__)

class NHSLookupEngine:
    """
    NHS-first lookup engine that treats NHS.json as the single source of truth.
    Extracts components from input and matches against NHS entries for standardization.
    """

    def __init__(self, nhs_json_path: str, nlp_processor: NLPProcessor):
        self.nhs_data = []
        self.snomed_lookup = {}
        self.nhs_json_path = nhs_json_path
        self.nlp_processor = nlp_processor
        self._load_nhs_data()
        self._build_lookup_tables()
        self._precompute_embeddings()

    def _load_nhs_data(self):
        """Load NHS data from JSON file."""
        try:
            with open(self.nhs_json_path, 'r', encoding='utf-8') as f:
                self.nhs_data = json.load(f)
            logger.info(f"Loaded {len(self.nhs_data)} NHS entries from {self.nhs_json_path}")
        except Exception as e:
            logger.error(f"Failed to load NHS data: {e}")
            self.nhs_data = []

    def _build_lookup_tables(self):
        """Build optimized lookup tables from NHS data."""
        logger.info("Building NHS lookup tables...")
        for entry in self.nhs_data:
            snomed_id = entry.get("SNOMED CT \nConcept-ID")
            if snomed_id: self.snomed_lookup[str(snomed_id)] = entry
        logger.info(f"Built SNOMED lookup table with {len(self.snomed_lookup)} entries.")

    def _precompute_embeddings(self):
        """Pre-computes and stores embeddings for all NHS clean names."""
        # UPDATED: Check for the new model attribute
        if not self.nlp_processor or not self.nlp_processor.model:
            logger.warning("NLPProcessor model not available. Skipping embedding pre-computation.")
            return

        logger.info("Pre-computing embeddings for all NHS clean names...")
        all_clean_names = [e.get("Clean Name") for e in self.nhs_data if e.get("Clean Name")]
        embeddings = self.nlp_processor.model.encode(all_clean_names, show_progress_bar=True)
        
        # Assign embeddings back to the entries
        name_to_embedding = dict(zip(all_clean_names, embeddings))
        for entry in self.nhs_data:
            clean_name = entry.get("Clean Name")
            entry["_embedding"] = name_to_embedding.get(clean_name)
        logger.info(f"Pre-computed {len(name_to_embedding)} embeddings for NHS data.")

    def _extract_components_from_nhs_entry(self, entry: Dict) -> Dict:
        """Extract components from an NHS entry for lookup purposes."""
        fsn = entry.get("SNOMED CT FSN", "").lower()
        clean_name = entry.get("Clean Name", "").lower()
        components = {'modality': [], 'anatomy': [], 'laterality': [], 'contrast': [], 'procedure_type': []}
        if 'ct' in clean_name: components['modality'].append('ct')
        if 'mr' in clean_name or 'mri' in clean_name: components['modality'].append('mr')
        if 'xr' in clean_name or 'x-ray' in clean_name: components['modality'].append('xr')
        if 'us' in clean_name: components['modality'].append('us')
        anatomy_terms = ['head', 'brain', 'chest', 'abdomen', 'pelvis', 'spine', 'knee', 'shoulder', 'liver', 'kidney', 'breast']
        for term in anatomy_terms:
            if term in fsn or term in clean_name: components['anatomy'].append(term)
        return components

    def _calculate_component_match_confidence(self, input_components: Dict, nhs_components: Dict) -> float:
        """Calculate confidence score between input and NHS components."""
        input_modality = set(input_components.get('modality', []))
        nhs_modality = set(nhs_components.get('modality', []))
        if input_modality and not input_modality.intersection(nhs_modality): return 0.0

        input_anatomy = set(input_components.get('anatomy', []))
        nhs_anatomy = set(nhs_components.get('anatomy', []))
        if input_anatomy and not input_anatomy.intersection(nhs_anatomy): return 0.0

        total_score, total_weight = 0, 0
        weights = {'modality': 3.0, 'anatomy': 2.0, 'laterality': 1.0, 'contrast': 1.0}
        for comp_type, weight in weights.items():
            input_comps, nhs_comps = set(input_components.get(comp_type, [])), set(nhs_components.get(comp_type, []))
            if input_comps or nhs_comps:
                intersection, union = len(input_comps & nhs_comps), len(input_comps | nhs_comps)
                similarity = intersection / union if union > 0 else 0
                if comp_type == 'anatomy' and nhs_comps - input_comps:
                    similarity *= (1 - len(nhs_comps - input_comps) / len(nhs_comps) * 0.5)
                total_score += similarity * weight
                total_weight += weight
        return total_score / total_weight if total_weight > 0 else 0

    def standardize_exam(self, input_exam: str, extracted_components: Dict) -> Dict:
        """Main method to standardize an exam using NHS data as source of truth."""
        best_match, highest_confidence = None, 0.0
        cleaned_input_for_matching = " ".join(extracted_components.get('modality', []) + extracted_components.get('anatomy', []))
        if not cleaned_input_for_matching: cleaned_input_for_matching = input_exam.lower()

        input_embedding = None
        # UPDATED: Check for the new model attribute
        if self.nlp_processor and self.nlp_processor.model:
            input_embedding = self.nlp_processor.get_text_embedding(cleaned_input_for_matching)

        for entry in self.nhs_data:
            component_confidence = self._calculate_component_match_confidence(extracted_components, self._extract_components_from_nhs_entry(entry))
            if component_confidence == 0.0: continue

            nhs_clean_name = entry.get("Clean Name")
            if not nhs_clean_name: continue

            fuzzy_score = fuzz.ratio(cleaned_input_for_matching, nhs_clean_name.lower()) / 100.0
            
            semantic_score = 0.0
            if input_embedding is not None and entry.get("_embedding") is not None:
                semantic_score = self.nlp_processor.calculate_semantic_similarity(input_embedding, entry["_embedding"])
            
            combined_score = (0.7 * component_confidence) + (0.15 * fuzzy_score) + (0.15 * semantic_score)
            if combined_score > highest_confidence:
                highest_confidence, best_match = combined_score, entry

        if best_match:
            return {
                'clean_name': best_match.get('Clean Name', ''), 'snomed_id': best_match.get('SNOMED CT \nConcept-ID', ''),
                'snomed_fsn': best_match.get('SNOMED CT FSN', ''), 'confidence': min(highest_confidence, 1.0), 'source': 'NHS_LOOKUP_SEMANTIC_V3'
            }
        
        logger.warning(f"No strong NHS match found for '{input_exam}'")
        return {'clean_name': input_exam, 'snomed_id': '', 'snomed_fsn': '', 'confidence': 0.0, 'source': 'NO_MATCH'}
    
    def validate_consistency(self) -> Dict:
        """Validate that each SNOMED ID has only one clean name."""
        snomed_to_clean_names = defaultdict(set)
        for entry in self.nhs_data:
            snomed_id, clean_name = entry.get("SNOMED CT \nConcept-ID"), entry.get("Clean Name")
            if snomed_id and clean_name: snomed_to_clean_names[snomed_id].add(clean_name)
        inconsistencies = {sid: list(names) for sid, names in snomed_to_clean_names.items() if len(names) > 1}
        if inconsistencies: logger.warning(f"Found {len(inconsistencies)} SNOMED IDs with multiple clean names.")
        else: logger.info("NHS data is consistent.")
        return {'inconsistencies_found': len(inconsistencies)}