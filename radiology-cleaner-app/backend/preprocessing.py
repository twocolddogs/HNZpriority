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
    
    def __init__(self, abbreviation_expander=None):
        """Initialize with optional abbreviation expander for text expansion."""
        self.abbreviation_expander = abbreviation_expander
        self._init_patterns()
    
    def _init_patterns(self):
        """Set up regex patterns and string lists for text cleaning."""
        # Patterns for removing administrative qualifiers that add no clinical value
        self.admin_qualifier_patterns = [
            (r'\s*\(non-acute\)\s*', ' '),  # "(non-acute)" -> " "
            (r'\s*\(acute\)\s*', ' ')       # "(acute)" -> " "
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
    
    def _expand_abbreviations(self, text: str, original_exam: str) -> str:
        """Expand medical abbreviations to their full forms."""
        if not self.abbreviation_expander:
            return text  # Skip if no expander configured
        
        pre_expansion = text
        expanded = self.abbreviation_expander.expand(text)
        
        # Log gender-related expansions for debugging gender detection issues
        if ('female' in original_exam.lower() or 'male' in original_exam.lower()) and pre_expansion != expanded:
            logger.info(f"DEBUG: Abbreviation expansion: '{pre_expansion}' -> '{expanded}'")
        
        return expanded
    
    def _normalize_ordinals(self, text: str) -> str:
        """Convert ordinal numbers to standardized forms (1st -> First)."""
        if not self.abbreviation_expander:
            return text  # Skip if no expander configured
        # Delegate to the abbreviation expander's ordinal normalization
        return self.abbreviation_expander.normalize_ordinals(text)
    
    def _handle_special_characters(self, text: str) -> str:
        """Clean up special characters that interfere with parsing."""
        cleaned = text
        
        # Remove caret notation - often indicates continuation from previous line
        if '^' in cleaned:
            # Take everything after the first caret (assumes format: "prefix^actual_content")
            cleaned = cleaned.split('^', 1)[1].strip()
        
        # Replace forward slashes with spaces for better word tokenization
        if '/' in cleaned:
            cleaned = cleaned.replace('/', ' ')
        
        return cleaned
    
    def _normalize_whitespace(self, text: str) -> str:
        """Collapse multiple spaces into single spaces and trim edges."""
        # Split on any whitespace and rejoin with single spaces
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
            return exam_name
        
        # Enable debug logging for gender-related exam names to track processing
        if 'female' in exam_name.lower() or 'male' in exam_name.lower():
            logger.info(f"DEBUG: Preprocessing input: '{exam_name}'")
        
        cleaned = exam_name
        
        # Apply preprocessing steps in dependency order
        cleaned = self._remove_no_report_suffix(cleaned)        # Remove administrative suffixes
        cleaned = self._remove_admin_qualifiers(cleaned)        # Remove clinical qualifiers  
        cleaned = self._expand_abbreviations(cleaned, exam_name)  # Expand medical abbreviations
        cleaned = self._handle_special_characters(cleaned)      # Clean problematic characters
        cleaned = self._normalize_ordinals(cleaned)             # Standardize ordinal numbers
        cleaned = self._normalize_whitespace(cleaned)           # Final whitespace cleanup
        
        # Log final result for gender-related exams to verify processing
        if 'female' in exam_name.lower() or 'male' in exam_name.lower():
            logger.info(f"DEBUG: Preprocessing output: '{cleaned}'")
        
        return cleaned
    
    def preprocess_batch(self, exam_names: list) -> list:
        """
        Process multiple exam names in a single operation for efficiency.
        
        Args:
            exam_names: List of raw exam names to preprocess
            
        Returns:
            List of cleaned exam names in the same order
        """
        return [self.preprocess(exam_name) for exam_name in exam_names]


# =============================================================================
# GLOBAL INSTANCE AND CONVENIENCE FUNCTIONS
# =============================================================================

# Module-level preprocessor instance for easy access across the application
_preprocessor: Optional[ExamPreprocessor] = None

def initialize_preprocessor(abbreviation_expander=None):
    """
    Set up the global preprocessor instance with the given abbreviation expander.
    
    This must be called during application initialization before using preprocess_exam_name().
    """
    global _preprocessor
    _preprocessor = ExamPreprocessor(abbreviation_expander)

def preprocess_exam_name(exam_name: str) -> str:
    """
    Preprocess a single exam name using the global preprocessor instance.
    
    Raises:
        RuntimeError: If initialize_preprocessor() hasn't been called yet
    """
    if _preprocessor is None:
        raise RuntimeError("Preprocessor not initialized. Call initialize_preprocessor() first.")
    return _preprocessor.preprocess(exam_name)

def get_preprocessor() -> Optional[ExamPreprocessor]:
    """Access the global preprocessor instance for advanced operations."""
    return _preprocessor