import json
import logging
from typing import Dict, List, Optional
from collections import defaultdict
from fuzzywuzzy import fuzz
# This will now be your API-based processor class
from nlp_processor import NLPProcessor

logger = logging.getLogger(__name__)

class NHSLookupEngine:
    """
    NHS lookup engine, updated to work with the lightweight, API-based NLP Processor.
    """
    def __init__(self, nhs_json_path: str, nlp_processor: NLPProcessor):
        self.nhs_data = []
        self.snomed_lookup = {}
        self.nhs_json_path = nhs_json_path
        self.nlp_processor = nlp_processor
        self._load_nhs_data()
        self._build_lookup_tables()
        # This will now pre-compute embeddings via a batch API call.
        self._precompute_embeddings()
        logger.info("NHSLookupEngine initialized successfully with API-based embeddings.")

    def _load_nhs_data(self):
        """Load NHS data from JSON file."""
        try:
            with open(self.nhs_json_path, 'r', encoding='utf-8') as f:
                self.nhs_data = json.load(f)
            logger.info(f"Loaded {len(self.nhs_data)} NHS entries.")
        except Exception as e:
            logger.error(f"Failed to load NHS data: {e}", exc_info=True)

    def _build_lookup_tables(self):
        """Build optimized SNOMED lookup table."""
        for entry in self.nhs_data:
            if snomed_id := entry.get("SNOMED CT \nConcept-ID"):
                self.snomed_lookup[str(snomed_id)] = entry

    def _precompute_embeddings(self):
        """
        Pre-computes embeddings for all NHS clean names using a single BATCH API call.
        Now includes preprocessing of NHS clean names to expand abbreviations.
        """
        # CORRECTED CHECK: Use the is_available() method instead of checking for .model
        if not self.nlp_processor or not self.nlp_processor.is_available():
            logger.warning("NLP Processor is not available. Skipping embedding pre-computation.")
            return

        logger.info("Pre-computing embeddings for all NHS clean names via batch API call...")
        all_clean_names = [e.get("Clean Name") for e in self.nhs_data if e.get("Clean Name")]
        
        # ENHANCEMENT: Preprocess NHS clean names to expand abbreviations  
        from parsing_utils import AbbreviationExpander
        abbreviation_expander = AbbreviationExpander()  # Use default medical abbreviations
        preprocessed_clean_names = [abbreviation_expander.expand(name) for name in all_clean_names]
        
        # Use the batch method for efficiency with preprocessed names
        embeddings = self.nlp_processor.batch_get_embeddings(preprocessed_clean_names)
        
        name_to_embedding = dict(zip(all_clean_names, embeddings))
        
        for entry in self.nhs_data:
            if clean_name := entry.get("Clean Name"):
                entry["_embedding"] = name_to_embedding.get(clean_name)
                entry["_preprocessed_name"] = abbreviation_expander.expand(clean_name)  # Store for debugging
        
        successful_count = sum(1 for e in embeddings if e is not None)
        logger.info(f"Successfully pre-computed {successful_count}/{len(all_clean_names)} embeddings with preprocessing.")

    def _extract_modality_from_nhs_entry(self, entry: Dict) -> set:
        """Extract modality from NHS entry clean name."""
        clean_name = entry.get("Clean Name", "").lower()
        modalities = set()
        
        # Map NHS clean name patterns to modalities
        modality_patterns = {
            'ct': ['ct ', 'computed tomography', 'dect'],
            'mr': ['mr ', 'mri', 'magnetic resonance', 'mrcp', 'mra'],
            'us': ['us ', 'ultrasound', 'echo', 'doppler'],
            'xr': ['xr ', 'x-ray', 'plain film', 'radiograph'],
            'nm': ['nm ', 'nuclear medicine', 'scintigraphy', 'spect', 'pet'],
            'fluoro': ['fluoroscopy', 'screening', 'barium'],
            'mammo': ['mammography', 'tomosynthesis'],
            'dexa': ['dexa', 'bone density']
        }
        
        for modality, patterns in modality_patterns.items():
            if any(pattern in clean_name for pattern in patterns):
                modalities.add(modality)
        
        return modalities

    def _nhs_entry_has_contrast(self, entry: Dict) -> bool:
        """Check if NHS entry indicates contrast use."""
        clean_name = entry.get("Clean Name", "").lower()
        snomed_fsn = entry.get("SNOMED CT FSN", "").lower()
        
        # Check for explicit contrast indicators
        contrast_indicators = [
            'with contrast', 'contrast', 'enhanced', 'gadolinium', 'intravenous',
            'iv contrast', 'oral contrast', 'contrast medium', 'contrast agent'
        ]
        
        full_text = f"{clean_name} {snomed_fsn}"
        return any(indicator in full_text for indicator in contrast_indicators)

    def _extract_components_from_nhs_entry(self, entry: Dict) -> Dict:
        """Extract components from an NHS entry for lookup purposes."""
        clean_name = entry.get("Clean Name", "").lower()
        components = {'modality': list(self._extract_modality_from_nhs_entry(entry)), 'anatomy': []}
        # ... (add other rules as needed)
        return components

    def _calculate_component_match_confidence(self, input_components: Dict, nhs_components: Dict) -> float:
        input_modality = set(input_components.get('modality', []))
        nhs_modality = set(nhs_components.get('modality', []))
        if input_modality and not input_modality.intersection(nhs_modality): return 0.0
        return 0.7 # Simplified for brevity

    def validate_consistency(self) -> Dict:
        """Validate that each SNOMED ID has only one clean name."""
        snomed_to_clean_names = defaultdict(set)
        for entry in self.nhs_data:
            if snomed_id := entry.get("SNOMED CT \nConcept-ID"):
                if clean_name := entry.get("Clean Name"):
                    snomed_to_clean_names[snomed_id].add(clean_name)
        
        inconsistencies = {k: list(v) for k, v in snomed_to_clean_names.items() if len(v) > 1}
        if inconsistencies:
            logger.warning(f"Found {len(inconsistencies)} SNOMED IDs with multiple clean names.")
        else:
            logger.info("NHS data is consistent.")
        return {'inconsistencies_found': len(inconsistencies)}

    def standardize_exam(self, input_exam: str, extracted_components: Dict) -> Dict:
        """Main method to standardize an exam using pre-computed API embeddings."""
        best_match, highest_confidence = None, 0.0
        
        # CORRECTED CHECK: Use is_available()
        if not self.nlp_processor or not self.nlp_processor.is_available():
            logger.warning("Semantic search disabled; NLP processor not available.")
            return {'clean_name': input_exam, 'snomed_id': '', 'snomed_fsn': '', 'confidence': 0.0, 'source': 'NO_SEMANTIC_SEARCH'}

        input_embedding = self.nlp_processor.get_text_embedding(input_exam)
        if input_embedding is None:
            logger.warning(f"Could not generate input embedding for '{input_exam}'.")
            return {'clean_name': input_exam, 'snomed_id': '', 'snomed_fsn': '', 'confidence': 0.0, 'source': 'NO_INPUT_EMBEDDING'}

        for entry in self.nhs_data:
            nhs_clean_name = entry.get("Clean Name")
            # SIMPLIFIED: We assume embeddings were pre-computed.
            nhs_embedding = entry.get("_embedding")

            if not nhs_clean_name or nhs_embedding is None:
                continue

            # MODALITY VALIDATION: Check if modalities are compatible
            input_modalities = set(extracted_components.get('modality', []))
            nhs_modalities = self._extract_modality_from_nhs_entry(entry)
            
            # If input has modality info, enforce modality matching
            if input_modalities and nhs_modalities:
                modality_match = bool(input_modalities.intersection(nhs_modalities))
                if not modality_match:
                    # Skip entries with incompatible modalities
                    continue

            semantic_score = self.nlp_processor.calculate_semantic_similarity(input_embedding, nhs_embedding)
            fuzzy_score = fuzz.ratio(input_exam, nhs_clean_name.lower()) / 100.0
            
            # Enhanced combined score with modality bonus
            combined_score = (0.8 * semantic_score) + (0.2 * fuzzy_score)
            
            # Give bonus for exact modality match
            if input_modalities and nhs_modalities and input_modalities.intersection(nhs_modalities):
                combined_score += 0.1  # Small bonus for modality match
            
            # CONTRAST MATCHING: Give strong bonus for contrast alignment
            input_contrast = extracted_components.get('contrast', [])
            nhs_has_contrast = self._nhs_entry_has_contrast(entry)
            
            if input_contrast:
                contrast_type = input_contrast[0] if input_contrast else None
                if contrast_type == 'with' and nhs_has_contrast:
                    combined_score += 0.15  # Strong bonus for with contrast match
                elif contrast_type == 'without' and not nhs_has_contrast:
                    combined_score += 0.15  # Strong bonus for without contrast match
                elif contrast_type in ['with', 'without'] and ((contrast_type == 'with') != nhs_has_contrast):
                    combined_score -= 0.2  # Penalty for contrast mismatch
            
            if combined_score > highest_confidence:
                highest_confidence, best_match = combined_score, entry

        if best_match:
            return {
                'clean_name': best_match.get('Clean Name', ''),
                'snomed_id': best_match.get('SNOMED CT \nConcept-ID', ''),
                'snomed_fsn': best_match.get('SNOMED CT FSN', ''),
                'confidence': min(highest_confidence, 1.0),
                'source': 'API_EMBEDDING_MATCH_V2'
            }
        
        return {'clean_name': input_exam, 'snomed_id': '', 'snomed_fsn': '', 'confidence': 0.0, 'source': 'NO_MATCH'}