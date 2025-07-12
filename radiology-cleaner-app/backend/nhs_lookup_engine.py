# nhs_lookup_engine.py

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import re
from fuzzywuzzy import fuzz # Import fuzzywuzzy for string matching
from nlp_processor import NLPProcessor # Import the NLPProcessor

logger = logging.getLogger(__name__)

class NHSLookupEngine:
    """
    NHS-first lookup engine that treats NHS.json as the single source of truth.
    Extracts components from input and matches against NHS entries for standardization.
    """
    
    def __init__(self, nhs_json_path: str, nlp_processor: NLPProcessor):
        self.nhs_data = []
        self.component_lookup = {}
        self.snomed_lookup = {}
        self.nhs_json_path = nhs_json_path
        self.nlp_processor = nlp_processor # Store NLPProcessor instance
        self._load_nhs_data()
        self._build_lookup_tables()
        self._precompute_embeddings() # New pre-computation step
    
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
        
        # Build SNOMED lookup for exact matches
        for entry in self.nhs_data:
            snomed_id = entry.get("SNOMED CT \nConcept-ID")
            if snomed_id:
                self.snomed_lookup[str(snomed_id)] = entry
        
        # Build component-based lookup
        for entry in self.nhs_data:
            components = self._extract_components_from_nhs_entry(entry)
            if components:
                # Create lookup keys from components
                lookup_key = self._create_lookup_key(components)
                if lookup_key not in self.component_lookup:
                    self.component_lookup[lookup_key] = []
                self.component_lookup[lookup_key].append(entry)
        
        logger.info(f"Built lookup tables: {len(self.snomed_lookup)} SNOMED entries, {len(self.component_lookup)} component keys")
    
    def _precompute_embeddings(self):
        """Pre-computes and stores embeddings for all NHS clean names."""
        if not self.nlp_processor or not self.nlp_processor.word_vectors:
            logger.warning("NLPProcessor or word embeddings not available. Skipping embedding pre-computation.")
            return

        for entry in self.nhs_data:
            clean_name = entry.get("Clean Name")
            if clean_name:
                entry["_embedding"] = self.nlp_processor.get_text_embedding(clean_name)
            else:
                entry["_embedding"] = None
        logger.info("Pre-computed embeddings for NHS data.")

    def _extract_components_from_nhs_entry(self, entry: Dict) -> Dict:
        """Extract components from an NHS entry for lookup purposes."""
        fsn = entry.get("SNOMED CT FSN", "").lower()
        clean_name = entry.get("Clean Name", "").lower()
        
        components = {
            'modality': [],
            'anatomy': [],
            'laterality': [],
            'contrast': [],
            'procedure_type': []
        }
        
        # Extract modality
        if 'computed tomography' in fsn or 'ct' in clean_name:
            components['modality'].append('ct')
        if 'magnetic resonance' in fsn or 'mr' in clean_name or 'mri' in clean_name:
            components['modality'].append('mr')
        if 'radiography' in fsn or 'xr' in clean_name or 'x-ray' in fsn:
            components['modality'].append('xr')
        if 'ultrasonography' in fsn or 'ultrasound' in fsn or 'us' in clean_name:
            components['modality'].append('us')
        if 'nuclear medicine' in fsn or 'nm' in clean_name:
            components['modality'].append('nm')
        if 'mammography' in fsn or 'mamm' in clean_name:
            components['modality'].append('mamm')
        
        # Extract anatomy - comprehensive list
        anatomy_terms = [
            'head', 'brain', 'skull', 'cranium', 'cerebral',
            'chest', 'thorax', 'lung', 'pulmonary',
            'abdomen', 'abdominal', 'pelvis', 'pelvic',
            'spine', 'spinal', 'vertebral', 'cervical', 'thoracic', 'lumbar', 'sacral',
            'knee', 'shoulder', 'elbow', 'wrist', 'hand', 'ankle', 'foot',
            'femur', 'tibia', 'fibula', 'radius', 'ulna', 'humerus',
            'heart', 'cardiac', 'coronary', 'aortic', 'vascular',
            'liver', 'kidney', 'renal', 'adrenal', 'thyroid',
            'breast', 'mammary', 'prostate', 'uterine', 'ovarian'
        ]
        
        for term in anatomy_terms:
            if term in fsn or term in clean_name:
                components['anatomy'].append(term)
        
        # Extract laterality
        laterality_entry = entry.get("SNOMED FSN of Laterality", "").lower()
        if 'left' in laterality_entry or 'left' in clean_name:
            components['laterality'].append('left')
        if 'right' in laterality_entry or 'right' in clean_name:
            components['laterality'].append('right')
        if 'bilateral' in laterality_entry or 'both' in clean_name:
            components['laterality'].append('bilateral')
        
        # Extract contrast
        if 'with contrast' in fsn or 'contrast' in fsn:
            components['contrast'].append('with')
        if 'without contrast' in fsn or 'non-contrast' in fsn:
            components['contrast'].append('without')
        
        # Extract procedure type
        if 'angiography' in fsn or 'angiogram' in clean_name:
            components['procedure_type'].append('angiography')
        if 'venography' in fsn or 'venogram' in clean_name:
            components['procedure_type'].append('venography')
        if 'biopsy' in fsn or 'biopsy' in clean_name:
            components['procedure_type'].append('biopsy')
        if 'drainage' in fsn or 'drainage' in clean_name:
            components['procedure_type'].append('drainage')
        
        return components
    
    def _create_lookup_key(self, components: Dict) -> str:
        """Create a lookup key from components."""
        # Sort components for consistent keys
        key_parts = []
        for comp_type in ['modality', 'anatomy', 'procedure_type', 'laterality', 'contrast']:
            if components.get(comp_type):
                sorted_comps = sorted(components[comp_type])
                key_parts.append(f"{comp_type}:{','.join(sorted_comps)}")
        
        return '|'.join(key_parts)
    
    def lookup_by_components(self, extracted_components: Dict) -> List[Tuple[Dict, float]]:
        """
        Find NHS entries that match the extracted components.
        Returns list of (nhs_entry, confidence_score) tuples.
        """
        matches = []
        
        for entry in self.nhs_data:
            nhs_components = self._extract_components_from_nhs_entry(entry)
            confidence = self._calculate_component_match_confidence(extracted_components, nhs_components)
            
            if confidence > 0.5:  # Only consider matches above 50%
                matches.append((entry, confidence))
        
        # Sort by confidence (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def _calculate_component_match_confidence(self, input_components: Dict, nhs_components: Dict) -> float:
        """Calculate confidence score between input and NHS components."""
        # --- START: STRICT MODALITY MATCHING ---
        input_modality = set(input_components.get('modality', []))
        nhs_modality = set(nhs_components.get('modality', []))

        # If the input specifies a modality, it MUST match at least one modality in the NHS entry.
        # This prevents matching, e.g., a CT scan to an XR entry.
        if input_modality and not input_modality.intersection(nhs_modality):
            logger.debug(f"Modality mismatch: Input modality {input_modality} has no overlap with NHS modality {nhs_modality}. Returning 0.0 confidence.")
            return 0.0
        # --- END: STRICT MODALITY MATCHING ---

        # --- START: STRICT ANATOMY MATCHING ---
        input_anatomy = set(input_components.get('anatomy', []))
        nhs_anatomy = set(nhs_components.get('anatomy', []))

        # If the input specifies anatomy, it MUST have some overlap with the NHS entry's anatomy.
        # This prevents matching completely different body parts, e.g., "head" vs "foot".
        if input_anatomy and not input_anatomy.intersection(nhs_anatomy):
            logger.debug(f"Anatomy mismatch: Input anatomy {input_anatomy} has no overlap with NHS anatomy {nhs_anatomy}.")
            return 0.0
        # --- END: STRICT ANATOMY MATCHING ---
        
        total_score = 0
        total_weight = 0
        
        # Component weights (more important components get higher weight)
        weights = {
            'modality': 3.0,
            'anatomy': 2.0,
            'procedure_type': 2.0,
            'laterality': 1.0,
            'contrast': 1.0
        }
        
        for comp_type, weight in weights.items():
            input_comps = set(input_components.get(comp_type, []))
            nhs_comps = set(nhs_components.get(comp_type, []))
            
            if input_comps or nhs_comps:
                # Calculate Jaccard similarity
                intersection = len(input_comps & nhs_comps)
                union = len(input_comps | nhs_comps)
                similarity = intersection / union if union > 0 else 0

                # Special handling for anatomy to penalize extra terms in NHS entry
                if comp_type == 'anatomy':
                    nhs_only_terms = nhs_comps - input_comps
                    input_only_terms = input_comps - nhs_comps

                    # Penalize NHS-only terms (broader NHS entry than input)
                    if nhs_only_terms:
                        if len(nhs_comps) > 0:
                            penalty_ratio = len(nhs_only_terms) / len(nhs_comps)
                            similarity *= (1 - penalty_ratio * 0.5) # Less severe penalty
                            logger.debug(f"Anatomy penalty (NHS-only): {nhs_only_terms}, new similarity: {similarity:.2f}")
                    
                    # Heavily penalize input-only terms (NHS entry missing key input anatomy)
                    if input_only_terms:
                        if len(input_comps) > 0:
                            penalty_ratio = len(input_only_terms) / len(input_comps)
                            similarity *= (1 - penalty_ratio * 0.8) # More severe penalty
                            logger.debug(f"Anatomy penalty (Input-only): {input_only_terms}, new similarity: {similarity:.2f}")
                
                total_score += similarity * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0
    
    def lookup_by_snomed(self, snomed_id: str) -> Optional[Dict]:
        """Direct lookup by SNOMED ID."""
        return self.snomed_lookup.get(str(snomed_id))
    
    def standardize_exam(self, input_exam: str, extracted_components: Dict) -> Dict:
        """
        Main method to standardize an exam using NHS data as source of truth,
        incorporating semantic similarity.
        
        Args:
            input_exam: Original exam name
            extracted_components: Components extracted by NLP/parsing
            
        Returns:
            Standardized result with NHS clean name and SNOMED
        """
        best_match = None
        highest_confidence = 0.0

        # Construct a cleaned input string for fuzzy/semantic matching based on extracted components
        # This ensures that the text used for matching aligns with the parsed modality and anatomy.
        cleaned_input_for_matching = ""
        if extracted_components.get('modality'):
            cleaned_input_for_matching += " ".join(extracted_components['modality'])
        if extracted_components.get('anatomy'):
            cleaned_input_for_matching += " ".join(extracted_components['anatomy'])
        cleaned_input_for_matching = cleaned_input_for_matching.strip()

        if not cleaned_input_for_matching:
            cleaned_input_for_matching = input_exam.lower() # Fallback if no components extracted

        # Tier 1: Find high-confidence component matches first
        high_confidence_component_threshold = 0.8 # Define a threshold for strong component match
        potential_matches = []

        for entry in self.nhs_data:
            nhs_components = self._extract_components_from_nhs_entry(entry)
            component_confidence = self._calculate_component_match_confidence(extracted_components, nhs_components)

            if component_confidence >= high_confidence_component_threshold:
                potential_matches.append((entry, component_confidence))

        # If high-confidence component matches are found, refine with fuzzy/semantic
        if potential_matches:
            logger.debug(f"Found {len(potential_matches)} high-confidence component matches. Refining...")
            for entry, component_confidence in potential_matches:
                nhs_clean_name = entry.get("Clean Name")
                if not nhs_clean_name:
                    continue

                fuzzy_score = fuzz.ratio(cleaned_input_for_matching, nhs_clean_name.lower()) / 100.0

                semantic_score = 0.0
                if self.nlp_processor and self.nlp_processor.word_vectors:
                    input_embedding = self.nlp_processor.get_text_embedding(cleaned_input_for_matching)
                    if input_embedding and entry.get("_embedding"):
                        semantic_score = self.nlp_processor.calculate_semantic_similarity(
                            input_embedding, entry["_embedding"]
                        )

                combined_score = (0.15 * fuzzy_score) + (0.15 * semantic_score) + (0.7 * component_confidence)

                if combined_score > highest_confidence:
                    highest_confidence = combined_score
                    best_match = entry
        else:
            # Tier 2: If no high-confidence component matches, consider all entries with a lower component threshold
            logger.debug("No high-confidence component matches found. Broadening search...")
            for entry in self.nhs_data:
                nhs_clean_name = entry.get("Clean Name")
                if not nhs_clean_name:
                    continue

                nhs_components = self._extract_components_from_nhs_entry(entry)
                component_confidence = self._calculate_component_match_confidence(extracted_components, nhs_components)

                # Only consider if component confidence is above 0 (i.e., not a complete mismatch)
                if component_confidence == 0.0:
                    continue

                fuzzy_score = fuzz.ratio(cleaned_input_for_matching, nhs_clean_name.lower()) / 100.0

                semantic_score = 0.0
                if self.nlp_processor and self.nlp_processor.word_vectors:
                    input_embedding = self.nlp_processor.get_text_embedding(cleaned_input_for_matching)
                    if input_embedding and entry.get("_embedding"):
                        semantic_score = self.nlp_processor.calculate_semantic_similarity(
                            input_embedding, entry["_embedding"]
                        )

                combined_score = (0.15 * fuzzy_score) + (0.15 * semantic_score) + (0.7 * component_confidence)

                if combined_score > highest_confidence:
                    highest_confidence = combined_score
                    best_match = entry

        if best_match and highest_confidence > 0.0: # Only consider if a match was found and confidence is above zero
            result = {
                'input_exam': input_exam,
                'clean_name': best_match.get('Clean Name', ''),
                'snomed_id': best_match.get('SNOMED CT \nConcept-ID', ''),
                'snomed_fsn': best_match.get('SNOMED CT FSN', ''),
                'laterality_snomed': best_match.get('SNOMED CT Concept-ID of Laterality', ''),
                'laterality_fsn': best_match.get('SNOMED FSN of Laterality', ''),
                'confidence': highest_confidence,
                'source': 'NHS_LOOKUP_SEMANTIC',
                'extracted_components': extracted_components
            }
            logger.info(f"NHS match found for '{input_exam}': '{result['clean_name']}' (confidence: {highest_confidence:.2f})")
            return result
        
        # No match found or confidence too low
        logger.warning(f"No strong NHS match found for '{input_exam}' with components: {extracted_components}")
        return {
            'input_exam': input_exam,
            'clean_name': input_exam,  # Fallback to original
            'snomed_id': '',
            'snomed_fsn': '',
            'laterality_snomed': '',
            'laterality_fsn': '',
            'confidence': 0.0,
            'source': 'NO_MATCH',
            'extracted_components': extracted_components
        }
    
    def validate_consistency(self) -> Dict:
        """Validate that each SNOMED ID has only one clean name."""
        snomed_to_clean_names = defaultdict(set)
        
        for entry in self.nhs_data:
            snomed_id = entry.get("SNOMED CT \nConcept-ID")
            clean_name = entry.get("Clean Name")
            
            if snomed_id and clean_name:
                snomed_to_clean_names[snomed_id].add(clean_name)
        
        # Find inconsistencies
        inconsistencies = {
            snomed_id: list(clean_names) 
            for snomed_id, clean_names in snomed_to_clean_names.items() 
            if len(clean_names) > 1
        }
        
        if inconsistencies:
            logger.warning(f"Found {len(inconsistencies)} SNOMED IDs with multiple clean names: {inconsistencies}")
        else:
            logger.info("NHS data is consistent - each SNOMED ID has exactly one clean name")
        
        return {
            'total_entries': len(self.nhs_data),
            'unique_snomed_ids': len(snomed_to_clean_names),
            'inconsistencies': inconsistencies
        }