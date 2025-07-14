# =============================================================================
# NHS LOOKUP ENGINE
# =============================================================================
# This module provides the core NHS reference data lookup functionality for
# standardizing radiology exam names. It uses semantic matching combined with
# fuzzy string matching to find the best matches in the NHS reference data.
#
# KEY FEATURES:
# - Pre-parsed NHS reference data using unified semantic parser
# - Pre-computed embeddings for all NHS entries at startup
# - Semantic similarity scoring using NLP models
# - Support for multiple NLP models (default, PubMed, etc.)
# - Component-based matching (anatomy, modality, contrast, etc.)
# - SNOMED CT integration for medical coding standards
# =============================================================================

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
    NHS lookup engine that standardizes radiology exam names using the NHS reference data.
    
    This engine provides unified semantic parsing for both input and NHS reference data,
    ensuring consistency in component extraction and matching. It supports multiple NLP
    models for semantic similarity and includes comprehensive caching and optimization.
    
    INITIALIZATION PIPELINE:
    1. Load NHS reference data from JSON file
    2. Build SNOMED lookup tables for medical coding
    3. Pre-parse ALL NHS entries using unified semantic parser
    4. Pre-compute embeddings for all NHS entries using selected NLP model
    5. Validate data consistency and prepare for matching
    
    MATCHING PIPELINE:
    1. Generate embedding for input exam using selected NLP model
    2. Compare input components against pre-parsed NHS components
    3. Calculate semantic similarity scores using embeddings
    4. Apply fuzzy string matching for additional scoring
    5. Select best match based on combined confidence scores
    """
    def __init__(self, nhs_json_path: str, nlp_processor: NLPProcessor, semantic_parser: 'RadiologySemanticParser'):
        # Core components
        self.nhs_data = []
        self.snomed_lookup = {}
        self.nhs_json_path = nhs_json_path
        self.nlp_processor = nlp_processor  # Default NLP processor
        self.semantic_parser = semantic_parser  # Unified semantic parser
        
        # INITIALIZATION PIPELINE
        # Step 1: Load NHS reference data
        self._load_nhs_data()
        
        # Step 2: Build lookup tables for fast SNOMED access
        self._build_lookup_tables()
        
        # Step 3: Pre-parse all NHS entries using unified semantic parser
        self._pre_parse_nhs_data_with_semantic_parser()
        
        # Step 4: Pre-compute embeddings for all NHS entries
        self._precompute_embeddings()
        
        logger.info("NHSLookupEngine initialized with fully pre-parsed and embedded NHS data.")

    def _load_nhs_data(self):
        """
        Load NHS reference data from JSON file.
        
        The NHS.json file contains the authoritative radiology exam names with
        associated SNOMED CT codes and other metadata. This serves as the single
        source of truth for standardization.
        """
        try:
            with open(self.nhs_json_path, 'r', encoding='utf-8') as f:
                self.nhs_data = json.load(f)
            logger.info(f"Loaded {len(self.nhs_data)} NHS entries from {self.nhs_json_path}")
        except Exception as e:
            logger.error(f"Failed to load NHS data: {e}", exc_info=True)
            raise

    def _build_lookup_tables(self):
        """
        Build optimized SNOMED lookup table for fast medical code retrieval.
        
        Creates a hash map from SNOMED CT concept IDs to NHS entries,
        enabling O(1) lookup time for medical code validation and retrieval.
        """
        for entry in self.nhs_data:
            if snomed_id := entry.get("SNOMED CT \nConcept-ID"):
                self.snomed_lookup[str(snomed_id)] = entry
        
        logger.info(f"Built SNOMED lookup table with {len(self.snomed_lookup)} entries")

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

    def _precompute_embeddings(self, custom_nlp_processor: Optional[NLPProcessor] = None):
        """
        Pre-compute embeddings for all NHS clean names using the specified NLP processor.
        
        This method generates vector embeddings for all NHS reference entries, enabling
        semantic similarity calculations during matching. Uses the default NLP processor
        unless a custom one is provided (e.g., PubMed model).
        
        Args:
            custom_nlp_processor: Optional custom NLP processor to use for embeddings
                                 (e.g., PubMed model for enhanced medical terminology)
        
        EMBEDDING PROCESS:
        1. Select appropriate NLP processor (custom or default)
        2. Extract all NHS clean names for batch processing
        3. Generate embeddings using batch API calls for efficiency
        4. Cache embeddings directly on NHS entries for fast access
        5. Log success/failure statistics
        """
        # Select NLP processor - use custom if provided, otherwise use default
        nlp_proc = custom_nlp_processor if custom_nlp_processor else self.nlp_processor
        
        if not nlp_proc or not nlp_proc.is_available():
            logger.warning("NLP Processor not available. Skipping embedding pre-computation.")
            return

        model_name = getattr(nlp_proc, 'model_name', 'unknown')
        logger.info(f"Pre-computing embeddings for all NHS clean names using model: {model_name}")
        
        # Extract all clean names for batch processing
        all_clean_names = [e.get("Clean Name") for e in self.nhs_data if e.get("Clean Name")]
        
        # Generate embeddings using batch processing for efficiency
        embeddings = nlp_proc.batch_get_embeddings(all_clean_names)
        
        # Create mapping from clean names to embeddings
        name_to_embedding = dict(zip(all_clean_names, embeddings))
        
        # Cache embeddings directly on NHS entries for fast access during matching
        for entry in self.nhs_data:
            if clean_name := entry.get("Clean Name"):
                entry["_embedding"] = name_to_embedding.get(clean_name)
        
        successful_count = sum(1 for e in embeddings if e is not None)
        logger.info(f"Successfully pre-computed {successful_count}/{len(all_clean_names)} embeddings using {model_name}.")

    def standardize_exam(self, input_exam: str, extracted_input_components: Dict, custom_nlp_processor: Optional[NLPProcessor] = None) -> Dict:
        """
        Main method to standardize an exam using NHS reference data.
        
        This method compares pre-parsed input components against pre-parsed NHS components
        for maximum consistency and speed. It supports custom NLP processors for enhanced
        medical terminology processing (e.g., PubMed-trained models).
        
        Args:
            input_exam: Cleaned/preprocessed exam name string (not raw input)
            extracted_input_components: Pre-parsed components from input exam
            custom_nlp_processor: Optional custom NLP processor for embedding generation
        
        Returns:
            Dictionary containing standardized exam information with SNOMED codes
            
        MATCHING PROCESS:
        1. Generate input embedding using selected NLP processor
        2. Compare input components against pre-parsed NHS components
        3. Calculate semantic similarity scores using embeddings
        4. Apply fuzzy string matching for additional scoring
        5. Select best match based on combined confidence scores
        """
        best_match, highest_confidence = None, 0.0
        
        # Select NLP processor - use custom if provided, otherwise use default
        nlp_proc = custom_nlp_processor if custom_nlp_processor else self.nlp_processor
        
        if not nlp_proc or not nlp_proc.is_available():
            logger.warning("Semantic search disabled; NLP processor not available.")
            return {'clean_name': input_exam, 'snomed_id': '', 'snomed_fsn': '', 'confidence': 0.0, 'source': 'NO_SEMANTIC_SEARCH'}

        # Generate embedding for input exam using selected NLP processor
        # IMPORTANT: The input_exam parameter is already the cleaned/preprocessed exam name
        # This ensures consistency with NHS embeddings which are also from cleaned names
        input_embedding = nlp_proc.get_text_embedding(input_exam)
        if input_embedding is None:
            logger.warning(f"Could not generate input embedding for cleaned exam '{input_exam}'.")
            return {'clean_name': input_exam, 'snomed_id': '', 'snomed_fsn': '', 'confidence': 0.0, 'source': 'NO_INPUT_EMBEDDING'}
        
        # If using custom NLP processor, need to recompute NHS embeddings with same model
        if custom_nlp_processor and custom_nlp_processor != self.nlp_processor:
            logger.info(f"Custom NLP processor detected, recomputing NHS embeddings for consistency")
            self._precompute_embeddings(custom_nlp_processor)

        # MAIN MATCHING LOOP: Compare input against all NHS entries
        for entry in self.nhs_data:
            nhs_embedding = entry.get("_embedding")
            nhs_components = entry.get("_parsed_components")

            # Skip entries without embeddings or parsed components
            if not nhs_components or nhs_embedding is None:
                continue

            # COMPONENT MATCHING: Compare input components against NHS components
            # Handle both string and list formats for flexibility
            input_modality = extracted_input_components.get('modality')
            if isinstance(input_modality, list):
                input_modality = input_modality[0] if input_modality else None
            
            nhs_modality = nhs_components.get('modality')
            
            # Relaxed modality matching - only skip if clearly incompatible
            if input_modality and nhs_modality:
                input_mod_lower = input_modality.lower() if input_modality else ''
                nhs_mod_lower = nhs_modality.lower() if nhs_modality else ''
                if input_mod_lower and nhs_mod_lower and input_mod_lower != nhs_mod_lower:
                    # Allow common modality aliases for flexibility
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

            # Laterality matching - only enforce if both are specified
            input_lat = extracted_input_components.get('laterality')
            if isinstance(input_lat, list):
                input_lat = input_lat[0] if input_lat else None
                
            nhs_lat = nhs_components.get('laterality')
            
            if input_lat and nhs_lat:
                if input_lat.lower() != nhs_lat.lower():
                    logger.debug(f"Skipping due to laterality mismatch: {input_lat} vs {nhs_lat}")
                    continue

            # SCORING: Calculate combined confidence score
            # Use selected NLP processor for semantic similarity
            semantic_score = nlp_proc.calculate_semantic_similarity(input_embedding, nhs_embedding)
            
            # Use NHS Clean Name for fuzzy matching
            nhs_clean_name = nhs_components.get('cleanName', entry.get('Clean Name', ''))
            fuzzy_score = fuzz.ratio(input_exam.lower(), nhs_clean_name.lower()) / 100.0
            
            # Combined score: weighted average of semantic and fuzzy scores
            combined_score = (0.7 * semantic_score) + (0.3 * fuzzy_score)

            # BONUS SCORING: Component alignment bonuses
            if input_modality and input_modality.lower() == nhs_modality.lower():
                combined_score += 0.1  # Modality alignment bonus

            # Contrast alignment scoring
            input_contrast = extracted_input_components.get('contrast')
            if isinstance(input_contrast, list):
                input_contrast = input_contrast[0] if input_contrast else None
                
            nhs_contrast = nhs_components.get('contrast')
            
            if input_contrast and nhs_contrast:
                if input_contrast.lower() == nhs_contrast.lower():
                    combined_score += 0.15  # Strong bonus for contrast alignment
                else:
                    combined_score -= 0.1   # Reduced penalty for mismatch
            
            # Track best match
            if combined_score > highest_confidence:
                highest_confidence, best_match = combined_score, entry

        # RESULT FORMATTING: Process best match if found
        if best_match:
            final_components = best_match.get('_parsed_components', {})
            
            # Normalize input components to list format for consistency
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
            
            # Use the canonical NHS "Clean Name" as the standardized result
            canonical_clean_name = best_match.get('Clean Name', final_components.get('cleanName', ''))
            
            model_name = getattr(nlp_proc, 'model_name', 'default')
            logger.info(f"Best match found: '{canonical_clean_name}' with confidence {highest_confidence:.3f} using model {model_name}")
            
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
                'source': f'UNIFIED_PARSER_MATCH_V5_{model_name.upper()}'
            }
        
        # No match found
        logger.warning(f"No match found for input: '{input_exam}' after checking {len(self.nhs_data)} NHS entries")
        return {'clean_name': input_exam, 'snomed_id': '', 'snomed_fsn': '', 'confidence': 0.0, 'source': 'NO_MATCH'}

    def validate_consistency(self) -> Dict:
        """
        Validate NHS data consistency and integrity.
        
        Checks that each SNOMED CT concept ID maps to only one clean name,
        ensuring data integrity for medical coding standards. This validation
        is critical for maintaining consistent standardization results.
        
        Returns:
            Dictionary with validation results and inconsistency count
        """
        snomed_to_clean_names = defaultdict(set)
        
        # Build mapping from SNOMED IDs to clean names
        for entry in self.nhs_data:
            if snomed_id := entry.get("SNOMED CT \nConcept-ID"):
                if clean_name := entry.get("Clean Name"):
                    snomed_to_clean_names[snomed_id].add(clean_name)
        
        # Identify inconsistencies (SNOMED IDs with multiple clean names)
        inconsistencies = {k: list(v) for k, v in snomed_to_clean_names.items() if len(v) > 1}
        
        if inconsistencies:
            logger.warning(f"Found {len(inconsistencies)} SNOMED IDs with multiple clean names.")
            # Log first few inconsistencies for debugging
            for i, (snomed_id, clean_names) in enumerate(list(inconsistencies.items())[:3]):
                logger.warning(f"  SNOMED {snomed_id}: {clean_names}")
        else:
            logger.info("NHS data consistency validation passed.")
        
        return {
            'inconsistencies_found': len(inconsistencies),
            'total_snomed_ids': len(snomed_to_clean_names),
            'validation_passed': len(inconsistencies) == 0
        }