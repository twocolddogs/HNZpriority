# --- START OF FILE preprocessing.py ---

# =============================================================================
# PREPROCESSING MODULE
# =============================================================================
# Cleans and normalizes radiology exam names before semantic analysis

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ExamPreprocessor:
    """
    Cleans and normalizes radiology exam names for consistent processing.
    
    Removes noise, expands abbreviations, and standardizes formatting to improve
    the accuracy of downstream semantic parsing and NHS lookup operations.
    """
    
    def __init__(self, abbreviation_expander=None, nhs_clean_names=None, config=None):
        """Initialize with optional abbreviation expander and configuration."""
        self.abbreviation_expander = abbreviation_expander
        # MODIFICATION: The nhs_clean_names protection is no longer needed due to the dual-lookup strategy.
        # This simplifies the preprocessor's responsibility to straightforward cleaning.
        self.nhs_clean_names = nhs_clean_names or set()
        
        # Load configuration for enhanced preprocessing
        self.config = config or {}
        self.medical_abbreviations = self.config.get('medical_abbreviations', {})
        self.anatomy_synonyms = self.config.get('anatomy_synonyms', {})
        
        self._init_patterns()
    
    def _init_patterns(self):
        """Set up regex patterns and string lists for text cleaning."""
        # Patterns for removing administrative qualifiers that add no clinical value
        self.admin_qualifier_patterns = [
            # Original patterns
            (r'\s*\(non-acute\)\s*', ' '),
            (r'\s*\(acute\)\s*', ' '),
            # --- RECOMMENDED ADDITION ---
            # Expanded to remove operational noise for better clinical grouping
            (r'\b(mobile|portable|ward|stat|opd|inpatient|outpatient)\b', ' '),
            (r'\s*\((mobile|portable|ward|stat)\)\s*', ' ')
        ]
        
        # NO REPORT suffixes to remove (ordered by specificity to avoid partial matches)
        self.no_report_patterns = [
            " - NO REPORT",    # Most specific pattern first
            "- NO REPORT", 
            "NO REPORT"        # Least specific pattern last
        ]
    
    def _remove_no_report_suffix(self, text: str) -> str:
        """Remove administrative 'NO REPORT' suffixes from exam names."""
        cleaned = text
        # Check each pattern in order of specificity to avoid partial matches
        for pattern in self.no_report_patterns:
            if cleaned.upper().endswith(pattern):
                cleaned = cleaned[:-len(pattern)].strip()
                break  # Stop after first match to prevent over-processing
        return cleaned
    
    def _remove_admin_qualifiers(self, text: str) -> str:
        """Remove administrative qualifiers like '(acute)' and '(non-acute)'."""
        cleaned = text
        # Apply each regex pattern to remove administrative noise
        for pattern, replacement in self.admin_qualifier_patterns:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        return cleaned
    
    def _expand_abbreviations(self, text: str) -> str:
        """
        Enhanced abbreviation expansion using configuration-based medical abbreviations.
        MODIFICATION: Now includes medical abbreviations from config alongside existing expander.
        """
        cleaned = text
        
        # Apply configuration-based medical abbreviations first
        for abbrev, expansion in self.medical_abbreviations.items():
            # Use word boundary regex to avoid partial matches
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            cleaned = re.sub(pattern, expansion, cleaned, flags=re.IGNORECASE)
        
        # Apply anatomy synonyms normalization
        for synonym, standard in self.anatomy_synonyms.items():
            pattern = r'\b' + re.escape(synonym) + r'\b'
            cleaned = re.sub(pattern, standard, cleaned, flags=re.IGNORECASE)
        
        # Apply legacy abbreviation expander if available
        if self.abbreviation_expander:
            cleaned = self.abbreviation_expander.expand(cleaned)
        
        return cleaned
    
    def _normalize_ordinals(self, text: str) -> str:
        """Convert ordinal numbers to standardized forms (1st -> First)."""
        if not self.abbreviation_expander:
            return text
        return self.abbreviation_expander.normalize_ordinals(text)
    
    def _handle_special_characters(self, text: str) -> str:
        """Clean up special characters that interfere with parsing."""
        cleaned = text
        
        # Remove caret notation - often indicates continuation from previous line
        if '^' in cleaned:
            # Take everything after the first caret (assumes format: "prefix^actual_content")
            cleaned = cleaned.split('^', 1)[1].strip()
        
        # --- FIX: Replace square brackets and parentheses with spaces ---
        cleaned = re.sub(r'[\[\]()]', ' ', cleaned)
        
        if '&' in cleaned:
            cleaned = cleaned.replace('&', ' and ')
        
        # Replace forward slashes with spaces for better word tokenization
        if '/' in cleaned:
            cleaned = cleaned.replace('/', ' ')
        
        # Remove commas that can interfere with parsing
        if ',' in cleaned:
            cleaned = cleaned.replace(',', ' ')
        
        return cleaned
    
    def _normalize_whitespace(self, text: str) -> str:
        """Collapse multiple spaces into single spaces and trim edges."""
        return ' '.join(text.split())
    
    def preprocess(self, exam_name: str) -> str:
        """
        Apply the complete preprocessing pipeline to clean and normalize exam names.
        
        Args:
            exam_name: Raw exam name from data source
            
        Returns:
            Cleaned and normalized exam name ready for semantic analysis
        """
        if not exam_name:
            return ""
        
        cleaned = exam_name
        
        # Apply preprocessing steps in dependency order
        cleaned = self._remove_no_report_suffix(cleaned)
        cleaned = self._remove_admin_qualifiers(cleaned)
        cleaned = self._expand_abbreviations(cleaned)
        cleaned = self._handle_special_characters(cleaned)
        cleaned = self._normalize_ordinals(cleaned)
        cleaned = self._normalize_whitespace(cleaned)
        
        return cleaned
    
    def preprocess_batch(self, exam_names: list) -> list:
        """Process multiple exam names in a single operation for efficiency."""
        return [self.preprocess(exam_name) for exam_name in exam_names]

# =============================================================================
# GLOBAL INSTANCE AND CONVENIENCE FUNCTIONS
# =============================================================================
_preprocessor: Optional[ExamPreprocessor] = None

def initialize_preprocessor(abbreviation_expander=None, config=None):
    """Set up the global preprocessor instance with the given abbreviation expander and config."""
    global _preprocessor
    _preprocessor = ExamPreprocessor(abbreviation_expander, config=config)

def preprocess_exam_name(exam_name: str) -> str:
    """Preprocess a single exam name using the global preprocessor instance."""
    if _preprocessor is None:
        raise RuntimeError("Preprocessor not initialized. Call initialize_preprocessor() first.")
    return _preprocessor.preprocess(exam_name)

def get_preprocessor() -> Optional[ExamPreprocessor]:
    """Access the global preprocessor instance for advanced operations."""
    return _preprocessor