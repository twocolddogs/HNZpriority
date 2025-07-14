import json
import logging
from typing import Dict, List, Optional
from collections import defaultdict
from fuzzywuzzy import fuzz
# Use TYPE_CHECKING to avoid a circular import issue with parser.py
from typing import TYPE_CHECKING 

from nlp_processor import NLPProcessor

# This allows us to use 'RadiologySemanticParser' as a type hint
if TYPE_CHECKING:
    from parser import RadiologySemanticParser

logger = logging.getLogger(__name__)

class NHSLookupEngine:
    """
    NHS lookup engine, refactored to use a unified semantic parser for both
    input and its internal NHS data, ensuring consistency and performance.
    """
    def __init__(self, nhs_json_path: str, nlp_processor: NLPProcessor, semantic_parser: 'RadiologySemanticParser'):
        self.nhs_data = []
        self.snomed_lookup = {}
        self.nhs_json_path = nhs_json_path
        self.nlp_processor = nlp_processor
        # REFACTOR: The engine now holds an instance of the main parser.
        self.semantic_parser = semantic_parser 
        
        self._load_nhs_data()
        self._build_lookup_tables()
        
        # REFACTOR: The core improvement. All NHS data is pre-parsed ONCE at startup.
        self._pre_parse_nhs_data_with_semantic_parser()
        
        self._precompute_embeddings()
        logger.info("NHSLookupEngine initialized with fully pre-parsed and embedded NHS data.")

    def _load_nhs_data(self):
        """Load NHS data from JSON file."""
        try:
            with open(self.nhs_json_path, 'r', encoding='utf-8') as f:
                self.nhs_data = json.load(f)
            logger.info(f"Loaded {len(self.nhs_data)} NHS entries.")
        except Exception as e:
            logger.error(f"Failed to load NHS data: {e}", exc_info=True)
            raise

    def _build_lookup_tables(self):
        """Build optimized SNOMED lookup table."""
        for entry in self.nhs_data:
            if snomed_id := entry.get("SNOMED CT \nConcept-ID"):
                self.snomed_lookup[str(snomed_id)] = entry

    def _pre_parse_nhs_data_with_semantic_parser(self):
        """
        Pre-parses all NHS entries using the main RadiologySemanticParser.
        This ensures the rules applied to the reference data are identical to the
        rules applied to user input, and moves all parsing to startup time.
        """
        if not self.semantic_parser:
            logger.error("CRITICAL: Semantic Parser not provided to NHSLookupEngine. Cannot pre-parse NHS data.")
            raise RuntimeError("Semantic Parser required for NHS data preprocessing")

        logger.info("Pre-parsing all NHS entries using the unified RadiologySemanticParser...")
        count = 0
        failed_count = 0
        
        for entry in self.nhs_data:
            clean_name = entry.get("Clean Name")
            if clean_name:
                try:
                    # Use the exact same pipeline that processes user input.
                    # Provide a placeholder modality as it's often parsed from the name itself.
                    parsed_components = self.semantic_parser.parse_exam_name(clean_name, 'Other')
                    
                    # Validate that we got meaningful results
                    if not parsed_components or not isinstance(parsed_components, dict):
                        logger.warning(f"Parser returned invalid result for NHS entry: '{clean_name}'")
                        failed_count += 1
                        continue
                        
                    # Cache the structured result directly on the entry.
                    entry['_parsed_components'] = parsed_components
                    count += 1
                    
                    # Log first few successful parses for verification
                    if count <= 3:
                        logger.info(f"Sample parse result for '{clean_name}': {parsed_components}")
                        
                except Exception as e:
                    logger.error(f"Failed to parse NHS entry '{clean_name}': {e}")
                    failed_count += 1
                    
        logger.info(f"Finished pre-parsing: {count} successful, {failed_count} failed out of {len(self.nhs_data)} NHS entries.")
        
        if count == 0:
            raise RuntimeError("CRITICAL: No NHS entries were successfully pre-parsed. System will not function.")
        elif failed_count > count * 0.5:  # More than 50% failures
            logger.warning(f"High failure rate in NHS preprocessing: {failed_count}/{count + failed_count} failed")

    def _precompute_embeddings(self):
        """Pre-computes embeddings for all NHS clean names using the NLP processor."""
        if not self.nlp_processor or not self.nlp_processor.is_available():
            logger.warning("NLP Processor not available. Skipping embedding pre-computation.")
            return

        logger.info("Pre-computing embeddings for all NHS clean names...")
        all_clean_names = [e.get("Clean Name") for e in self.nhs_data if e.get("Clean Name")]
        embeddings = self.nlp_processor.batch_get_embeddings(all_clean_names)
        
        name_to_embedding = dict(zip(all_clean_names, embeddings))
        
        for entry in self.nhs_data:
            if clean_name := entry.get("Clean Name"):
                entry["_embedding"] = name_to_embedding.get(clean_name)
        
        successful_count = sum(1 for e in embeddings if e is not None)
        logger.info(f"Successfully pre-computed {successful_count}/{len(all_clean_names)} embeddings.")

    def standardize_exam(self, input_exam: str, extracted_input_components: Dict) -> Dict:
        """
        Main method to standardize an exam. Compares pre-parsed input components
        against pre-parsed NHS components for maximum consistency and speed.
        """
        best_match, highest_confidence = None, 0.0
        
        if not self.nlp_processor or not self.nlp_processor.is_available():
            logger.warning("Semantic search disabled; NLP processor not available.")
            return {'clean_name': input_exam, 'snomed_id': '', 'snomed_fsn': '', 'confidence': 0.0, 'source': 'NO_SEMANTIC_SEARCH'}

        input_embedding = self.nlp_processor.get_text_embedding(input_exam)
        if input_embedding is None:
            logger.warning(f"Could not generate input embedding for '{input_exam}'.")
            return {'clean_name': input_exam, 'snomed_id': '', 'snomed_fsn': '', 'confidence': 0.0, 'source': 'NO_INPUT_EMBEDDING'}

        for entry in self.nhs_data:
            nhs_embedding = entry.get("_embedding")
            # REFACTOR: Retrieve the fully pre-parsed NHS components.
            nhs_components = entry.get("_parsed_components")

            if not nhs_components or nhs_embedding is None:
                continue

            # --- Component Matching (Now Apples-to-Apples) ---
            # Fix: Handle both string and list formats for modality/laterality
            input_modality = extracted_input_components.get('modality')
            if isinstance(input_modality, list):
                input_modality = input_modality[0] if input_modality else None
            
            nhs_modality = nhs_components.get('modality')
            
            # Log component comparison for debugging
            logger.debug(f"Comparing input_modality='{input_modality}' vs nhs_modality='{nhs_modality}'")
            
            # Relaxed modality matching - only skip if clearly incompatible
            if input_modality and nhs_modality:
                input_mod_lower = input_modality.lower() if input_modality else ''
                nhs_mod_lower = nhs_modality.lower() if nhs_modality else ''
                if input_mod_lower and nhs_mod_lower and input_mod_lower != nhs_mod_lower:
                    # Allow some common modality aliases
                    modality_aliases = {
                        'ct': ['computed tomography', 'dect'],
                        'mr': ['mri', 'magnetic resonance'],
                        'us': ['ultrasound', 'echo'],
                        'xr': ['x-ray', 'radiograph']
                    }
                    
                    compatible = False
                    for canonical, aliases in modality_aliases.items():
                        if (input_mod_lower == canonical and nhs_mod_lower in aliases) or \
                           (nhs_mod_lower == canonical and input_mod_lower in aliases):
                            compatible = True
                            break
                    
                    if not compatible:
                        logger.debug(f"Skipping due to modality mismatch: {input_mod_lower} vs {nhs_mod_lower}")
                        continue

            input_lat = extracted_input_components.get('laterality')
            if isinstance(input_lat, list):
                input_lat = input_lat[0] if input_lat else None
                
            nhs_lat = nhs_components.get('laterality')
            
            # Relaxed laterality matching - only enforce if both are specified
            if input_lat and nhs_lat:
                if input_lat.lower() != nhs_lat.lower():
                    logger.debug(f"Skipping due to laterality mismatch: {input_lat} vs {nhs_lat}")
                    continue

            # --- Scoring ---
            semantic_score = self.nlp_processor.calculate_semantic_similarity(input_embedding, nhs_embedding)
            # Fix: Use 'cleanName' (camelCase) as returned by semantic parser
            nhs_clean_name = nhs_components.get('cleanName', entry.get('Clean Name', ''))
            fuzzy_score = fuzz.ratio(input_exam.lower(), nhs_clean_name.lower()) / 100.0
            combined_score = (0.7 * semantic_score) + (0.3 * fuzzy_score)

            # Bonus/Penalty for component alignment
            if input_modality and input_modality.lower() == nhs_modality.lower():
                combined_score += 0.1

            input_contrast = extracted_input_components.get('contrast')
            if isinstance(input_contrast, list):
                input_contrast = input_contrast[0] if input_contrast else None
                
            nhs_contrast = nhs_components.get('contrast')
            
            if input_contrast and nhs_contrast:
                if input_contrast.lower() == nhs_contrast.lower():
                    combined_score += 0.15  # Strong bonus for alignment
                else:
                    combined_score -= 0.1   # Reduced penalty for mismatch
            
            if combined_score > highest_confidence:
                highest_confidence, best_match = combined_score, entry

        if best_match:
            # The final result uses the pre-parsed data from the best match
            final_components = best_match.get('_parsed_components', {})
            
            # Use INPUT components to represent what was found in the user's exam name
            # Ensure components are in list format for consistency
            anatomy = extracted_input_components.get('anatomy', [])
            if not isinstance(anatomy, list):
                anatomy = [anatomy] if anatomy else []
                
            laterality = extracted_input_components.get('laterality')
            if laterality and not isinstance(laterality, list):
                laterality = [laterality]
            elif not laterality:
                laterality = []
                
            contrast = extracted_input_components.get('contrast')
            if contrast and not isinstance(contrast, list):
                contrast = [contrast]
            elif not contrast:
                contrast = []
                
            modality = extracted_input_components.get('modality')
            if modality and not isinstance(modality, list):
                modality = [modality]
            elif not modality:
                modality = []
                
            technique = extracted_input_components.get('technique', [])
            if not isinstance(technique, list):
                technique = [technique] if technique else []
            
            # Use the canonical NHS "Clean Name" as the primary source
            canonical_clean_name = best_match.get('Clean Name', final_components.get('cleanName', ''))
            
            logger.info(f"Best match found: '{canonical_clean_name}' with confidence {highest_confidence:.3f}")
            
            return {
                'clean_name': canonical_clean_name,
                'snomed_id': best_match.get('SNOMED CT \nConcept-ID', ''),
                'snomed_fsn': best_match.get('SNOMED CT FSN', ''),
                # Return the components from the INPUT exam name to show what was detected
                'anatomy': anatomy,
                'laterality': laterality,
                'contrast': contrast,
                'modality': modality,
                'technique': technique,
                'confidence': min(highest_confidence, 1.0),
                'source': 'UNIFIED_PARSER_MATCH_V4'
            }
        
        logger.warning(f"No match found for input: '{input_exam}' after checking {len(self.nhs_data)} NHS entries")
        return {'clean_name': input_exam, 'snomed_id': '', 'snomed_fsn': '', 'confidence': 0.0, 'source': 'NO_MATCH'}

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