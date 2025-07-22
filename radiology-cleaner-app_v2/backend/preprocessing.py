# --- START OF FILE preprocessing.py ---

# =============================================================================
# PREPROCESSING MODULE (V2.2 - ENHANCED & DEDUPLICATED)
# =============================================================================
# Cleans and normalizes radiology exam names before semantic analysis.
# This enhanced version is driven by config.yaml and features:
# - More aggressive removal of administrative noise.
# - Intelligent deduplication of redundant modality keywords (e.g., "MR MRI").
# - Full integration with the config-driven abbreviation expansion engine.

import re
import logging
import yaml
import os
from typing import Optional

logger = logging.getLogger(__name__)

class ExamPreprocessor:
    """
    Cleans and normalizes radiology exam names for consistent processing.
    
    This preprocessor is driven by a configuration file (config.yaml) to:
    - Expand a comprehensive list of medical, anatomical, and contrast abbreviations.
    - Remove administrative and operational noise (e.g., 'ward', 'mobile', '(single projection)').
    - Deduplicate redundant modality mentions (e.g., "MR MRCP" -> "MRCP").
    - Standardize special characters and whitespace.
    
    The goal is to produce a canonical, clinically-focused string ready for
    downstream semantic parsing and NHS lookup operations.
    """
    
    def __init__(self, abbreviation_expander=None, nhs_clean_names=None, config=None):
        """
        Initializes the preprocessor with necessary components and configuration.

        Args:
            abbreviation_expander: An instance used for ordinal normalization (e.g., 1st -> First).
            nhs_clean_names: (Not currently used) Intended for vocabulary-based cleaning.
            config (dict, optional): A dictionary containing preprocessing rules, typically
                                     loaded from config.yaml. If not provided, it will
                                     attempt to load the config file itself.
        """
        # The abbreviation_expander is now only used for ordinal normalization.
        self.abbreviation_expander = abbreviation_expander
        
        # Load configuration for enhanced preprocessing from config.yaml
        if config is None:
            try:
                config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
                with open(config_path, 'r') as f:
                    full_config = yaml.safe_load(f)
                    config = full_config.get('preprocessing', {})
            except Exception as e:
                logger.warning(f"Could not load config.yaml for preprocessing: {e}. Falling back to empty config.")
                config = {}
        
        self.config = config or {}
        self.medical_abbreviations = self.config.get('medical_abbreviations', {})
        self.anatomy_synonyms = self.config.get('anatomy_synonyms', {})
        
        self._init_patterns()
    
    def _init_patterns(self):
        """
        Initializes and compiles regular expression patterns and string lists for text cleaning.
        This function centralizes all static patterns for efficiency.
        """
        # ENHANCED: These patterns more aggressively remove common administrative or
        # non-clinical text found within parentheses or as standalone keywords.
        self.admin_qualifier_patterns = [
            # Removes parenthesized text like "(mobile)", "(single projection)", "(procedure)", etc.
            (r'\s*\((non-acute|acute|mobile|portable|ward|stat|standard|single projection|gr|procedure|finding|qualifier value)\)\s*', ' '),
            # Removes standalone keywords like "ward", "portable", "imaging", "scan".
            (r'\b(mobile|portable|ward|stat|opd|inpatient|outpatient|standard|imaging|scan)\b', ' ')
        ]
        
        # These patterns target common suffixes indicating an un-reported exam,
        # which should be stripped before processing.
        self.no_report_patterns = [
            " - NO REPORT", " -NO REPORT", "- NO REPORT", "NO REPORT"
        ]
    
    def _remove_no_report_suffix(self, text: str) -> str:
        """
        Removes administrative 'NO REPORT' suffixes from exam names.

        Why: Exam names are sometimes appended with this status, which is not part of the
             clinical description and must be removed for accurate matching.

        Args:
            text (str): The input exam name.

        Returns:
            str: The exam name with the suffix removed, if present.
        """
        cleaned = text
        for pattern in self.no_report_patterns:
            if cleaned.upper().endswith(pattern):
                return cleaned[:-len(pattern)].strip()
        return cleaned
    
    def _remove_admin_qualifiers(self, text: str) -> str:
        """
        Removes administrative qualifiers using the pre-compiled regex patterns.

        Why: Terms like 'ward' or '(portable)' describe the logistical context, not the
             clinical nature of the exam, and can interfere with semantic matching.

        Args:
            text (str): The input exam name.

        Returns:
            str: The exam name with administrative qualifiers removed.
        """
        cleaned = text
        for pattern, replacement in self.admin_qualifier_patterns:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        return cleaned
    
    def _expand_abbreviations(self, text: str) -> str:
        """
        Expands abbreviations and normalizes synonyms using the config-driven dictionaries.

        Why: This is the core normalization step. It converts concise, ambiguous abbreviations
             (e.g., 'C+', 'LSP', 'KUB') into their full, standardized forms, creating a
             consistent language for the downstream parser to analyze.

        Args:
            text (str): The input exam name.

        Returns:
            str: The exam name with abbreviations expanded.
        """
        cleaned = text
        
        # Apply all medical abbreviations from config.
        # It includes special handling for patterns with symbols like '+' or '/'.
        for abbrev, expansion in self.medical_abbreviations.items():
            if any(char in abbrev for char in ['+', '-']):
                # For abbreviations with + or -, use a flexible pattern that doesn't require word boundaries after the symbol
                escaped_abbrev = re.escape(abbrev)
                pattern = r'\b' + escaped_abbrev + r'(?=\s|$)'
                cleaned = re.sub(pattern, expansion, cleaned, flags=re.IGNORECASE)
            elif any(char in abbrev for char in ['/', '(', ')']):
                # For other special characters, use standard escaping with word boundaries
                pattern = r'\b' + re.escape(abbrev) + r'\b'
                cleaned = re.sub(pattern, expansion, cleaned, flags=re.IGNORECASE)
            else:
                # Standard word boundary approach for normal alphanumeric abbreviations
                pattern = r'\b' + re.escape(abbrev) + r'\b'
                cleaned = re.sub(pattern, expansion, cleaned, flags=re.IGNORECASE)
        
        # Apply anatomy synonyms normalization from config.
        for synonym, standard in self.anatomy_synonyms.items():
            pattern = r'\b' + re.escape(synonym) + r'\b'
            cleaned = re.sub(pattern, standard, cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def _deduplicate_modalities(self, text: str) -> str:
        """
        Removes redundant modality keywords from the exam name (e.g., "MR MRI" -> "MRI").

        Why: Input exam names can sometimes be redundant (e.g., from concatenating fields).
             Redundancy like "MR MRCP" can confuse the parser and NLP model. This step
             ensures each modality is mentioned only once in its most complete form.

        Args:
            text (str): The exam name, ideally after abbreviation expansion.

        Returns:
            str: The exam name with redundant modality mentions removed.
        """
        modality_groups = {
            'MRI': [r'mr\b', r'mri\b', r'magnetic resonance\b'],
            'CT': [r'ct\b', r'computed tomography\b'],
            'US': [r'us\b', r'ultrasound\b', r'sonogram\b'],
            'XR': [r'xr\b', r'x-ray\b', r'xray\b', r'radiograph\b'],
            'NM': [r'nm\b', r'nuclear medicine\b', r'spect\b'],
            'FL': [r'fl\b', r'fluoroscopy\b', r'fluoro\b'],
            'MG': [r'mg\b', r'mamm\b', r'mammography\b', r'mammogram\b']
        }
    
        # Use a copy to modify while iterating
        cleaned_text = text
        for primary_modality, patterns in modality_groups.items():
            # Find all occurrences of variants for the current modality group
            found_variants = []
            for pattern in patterns:
                if re.search(pattern, cleaned_text, re.IGNORECASE):
                    found_variants.append(pattern)
            
            # If more than one variant is found (e.g., both 'mr' and 'mri' are present)
            if len(found_variants) > 1:
                # Keep the longest (most explicit) variant and remove the others
                found_variants.sort(key=len, reverse=True)
                variant_to_keep = found_variants[0]
                variants_to_remove = found_variants[1:]
                
                for pattern_to_remove in variants_to_remove:
                    # Remove the shorter, redundant variants
                    cleaned_text = re.sub(pattern_to_remove, '', cleaned_text, flags=re.IGNORECASE)
        
        # Use the whitespace normalization to clean up any double spaces left behind
        return self._normalize_whitespace(cleaned_text)

    def _normalize_ordinals(self, text: str) -> str:
        """
        Converts ordinal number strings to their full word form (e.g., "3rd" -> "Third").

        Why: Standardizing ordinals ensures consistent parsing and matching, especially
             for exams like "3rd trimester ultrasound".

        Args:
            text (str): The input text.

        Returns:
            str: Text with ordinals normalized.
        """
        if not self.abbreviation_expander:
            return text
        return self.abbreviation_expander.normalize_ordinals(text)
    
    def _handle_special_characters(self, text: str) -> str:
        """
        Cleans up special characters that can interfere with parsing.

        Why: Characters like `[]()/,&-` are often used inconsistently. This function
             replaces them with spaces or standardizes them to prevent parsing errors.

        Args:
            text (str): The input text.

        Returns:
            str: Text with problematic special characters handled.
        """
        cleaned = text
        # Replace common separators with a space
        cleaned = re.sub(r'[\[\]()/]', ' ', cleaned)
        cleaned = cleaned.replace('&', ' and ')
        cleaned = cleaned.replace(',', ' ')
        
        # Clean up leftover hyphens and dashes more robustly
        cleaned = re.sub(r'\s*-\s*$', '', cleaned)  # Remove trailing dash and whitespace
        cleaned = re.sub(r'^\s*-\s*', '', cleaned)  # Remove leading dash and whitespace
        cleaned = re.sub(r'\s+-\s+', ' ', cleaned)  # Replace space-padded dashes with a single space
        return cleaned
    
    def _normalize_whitespace(self, text: str) -> str:
        """
        Collapses multiple spaces into single spaces and trims leading/trailing whitespace.

        Why: A crucial final cleanup step to ensure the string is in a canonical format
             with consistent spacing, which is important for regex and string matching.

        Args:
            text (str): The input text.

        Returns:
            str: The text with normalized whitespace.
        """
        return ' '.join(text.split())
    
    def should_exclude_exam(self, exam_name: str) -> bool:
        """
        Checks if an exam should be excluded from analysis based on keywords.

        Why: Source data often contains non-clinical entries (e.g., 'Radiology Conferences',
             'test case'). This function acts as a filter to prevent these from being
             processed, saving resources and preventing erroneous matches.

        Args:
            exam_name (str): The original exam name.

        Returns:
            bool: True if the exam should be excluded, False otherwise.
        """
        if not exam_name:
            return True
            
        exam_lower = exam_name.lower()
        
        # List of regex patterns that indicate a non-clinical or administrative entry.
        exclusion_patterns = [
            r'\b(conference|conferences)\b',
            r'\b(mdm|multidisciplinary.?meeting)\b', 
            r'\b(meeting|meetings)\b',
            r'\b(discussion|discussions)\b',
            r'\b(presentation|presentations)\b',
            r'\b(teaching|education|educational)\b',
            r'\b(review.?meeting|case.?review)\b',
            r'\b(journal.?club)\b',
            r'\b(admin|administrative)\b',
            r'\b(cancelled|canceled|no.?show)\b',
            r'\b(test.?patient|test.?case)\b'
        ]
        
        for pattern in exclusion_patterns:
            if re.search(pattern, exam_lower):
                logger.debug(f"Excluding non-clinical entry: {exam_name}")
                return True
                
        return False

    def preprocess(self, exam_name: str) -> str:
        """
        Applies the complete, prioritized preprocessing pipeline to a single exam name.

        Why: This is the main public method that orchestrates all cleaning and normalization
             steps in the correct order to produce a final, canonical string for analysis.
             The order of operations is important (e.g., expand abbreviations before deduplicating).

        Args:
            exam_name (str): The raw exam name from the source system.

        Returns:
            str: The fully cleaned and normalized exam name.
        """
        if not exam_name:
            return ""
        
        cleaned = exam_name
        
        # The order of these operations is deliberate and important.
        cleaned = self._remove_no_report_suffix(cleaned)
        cleaned = self._remove_admin_qualifiers(cleaned)
        cleaned = self._expand_abbreviations(cleaned)
        cleaned = self._deduplicate_modalities(cleaned) # NEW: Deduplicate after expansion
        cleaned = self._handle_special_characters(cleaned)
        cleaned = self._normalize_ordinals(cleaned)
        cleaned = self._normalize_whitespace(cleaned) # Final cleanup
        
        return cleaned
    
    def preprocess_batch(self, exam_names: list) -> list:
        """
        Applies the full preprocessing pipeline to a list of exam names.

        Why: Provides an efficient way to process multiple exams at once, for example,
             during batch processing or initial data loading.

        Args:
            exam_names (list): A list of raw exam name strings.

        Returns:
            list: A list of fully cleaned and normalized exam names.
        """
        return [self.preprocess(exam_name) for exam_name in exam_names]

# =============================================================================
# GLOBAL INSTANCE AND CONVENIENCE FUNCTIONS
# =============================================================================
# This pattern creates a single, shared instance of the preprocessor to avoid
# the overhead of re-initializing it on every call.

_preprocessor: Optional[ExamPreprocessor] = None

def initialize_preprocessor(abbreviation_expander=None, config=None):
    """
    Initializes the global singleton instance of the ExamPreprocessor.

    Why: This must be called once at application startup to ensure the global
         preprocessor is available for use by other modules.

    Args:
        abbreviation_expander: The ordinal expander instance.
        config (dict): The preprocessing configuration dictionary.
    """
    global _preprocessor
    if _preprocessor is None:
        logger.info("Initializing global ExamPreprocessor instance...")
        _preprocessor = ExamPreprocessor(abbreviation_expander, config=config)

def preprocess_exam_name(exam_name: str) -> str:
    """
    A convenience function to preprocess a single exam name using the global instance.

    Why: Provides a simple, direct way for other parts of the application to access
         the preprocessing functionality without needing to manage an instance.

    Args:
        exam_name (str): The raw exam name.

    Returns:
        str: The cleaned exam name.
    """
    if _preprocessor is None:
        raise RuntimeError("Preprocessor not initialized. Call initialize_preprocessor() first.")
    return _preprocessor.preprocess(exam_name)

def get_preprocessor() -> Optional[ExamPreprocessor]:
    """
    Returns the global singleton preprocessor instance.

    Why: Allows other modules to get a direct reference to the shared preprocessor if needed.

    Returns:
        ExamPreprocessor: The global preprocessor instance.
    """
    return _preprocessor

# --- END OF FILE preprocessing.py ---
