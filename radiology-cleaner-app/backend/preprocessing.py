# --- START OF FILE preprocessing.py ---

# =============================================================================
# PREPROCESSING MODULE (V2.1 - CORRECTED)
# =============================================================================
# Cleans and normalizes radiology exam names before semantic analysis.
# This version is driven by config.yaml and corrects the AttributeError by
# removing the call to the now-deprecated .expand() method.

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
    - Remove administrative and operational noise (e.g., 'ward', 'mobile').
    - Standardize special characters and whitespace.
    
    The goal is to produce a canonical, clinically-focused string ready for
    downstream semantic parsing and NHS lookup operations.
    """
    
    def __init__(self, abbreviation_expander=None, nhs_clean_names=None, config=None):
        """Initialize with optional abbreviation expander and configuration."""
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
        """Set up regex patterns and string lists for text cleaning."""
        self.admin_qualifier_patterns = [
            (r'\s*\((non-acute|acute|mobile|portable|ward|stat|standard)\)\s*', ' '),
            (r'\b(mobile|portable|ward|stat|opd|inpatient|outpatient|standard)\b', ' ')
        ]
        
        self.no_report_patterns = [
            " - NO REPORT", " -NO REPORT", "- NO REPORT", "NO REPORT"
        ]
    
    def _remove_no_report_suffix(self, text: str) -> str:
        """Remove administrative 'NO REPORT' suffixes from exam names."""
        cleaned = text
        for pattern in self.no_report_patterns:
            if cleaned.upper().endswith(pattern):
                return cleaned[:-len(pattern)].strip()
        return cleaned
    
    def _remove_admin_qualifiers(self, text: str) -> str:
        """Remove administrative qualifiers like '(acute)' and 'ward'."""
        cleaned = text
        for pattern, replacement in self.admin_qualifier_patterns:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        return cleaned
    
    def _expand_abbreviations(self, text: str) -> str:
        """
        Unified and enhanced abbreviation expansion using config.yaml.
        This is now the core normalization engine.
        """
        cleaned = text
        
        # Apply all medical abbreviations from config.
        # Special handling for patterns with special characters like C+ and C-
        for abbrev, expansion in self.medical_abbreviations.items():
            if any(char in abbrev for char in ['+', '-']):
                # For abbreviations with + or -, use a more flexible pattern that doesn't require word boundaries after the symbol
                escaped_abbrev = re.escape(abbrev)
                # Match the abbreviation at word boundaries but allow symbols at the end
                pattern = r'\b' + escaped_abbrev + r'(?=\s|$)'
                cleaned = re.sub(pattern, expansion, cleaned, flags=re.IGNORECASE)
            elif any(char in abbrev for char in ['/', '(', ')']):
                # For other special characters, use standard escaping
                pattern = r'\b' + re.escape(abbrev) + r'\b'
                cleaned = re.sub(pattern, expansion, cleaned, flags=re.IGNORECASE)
            else:
                # Standard word boundary approach for normal abbreviations
                pattern = r'\b' + re.escape(abbrev) + r'\b'
                cleaned = re.sub(pattern, expansion, cleaned, flags=re.IGNORECASE)
        
        # Apply anatomy synonyms normalization from config.
        for synonym, standard in self.anatomy_synonyms.items():
            pattern = r'\b' + re.escape(synonym) + r'\b'
            cleaned = re.sub(pattern, standard, cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def _normalize_ordinals(self, text: str) -> str:
        """Convert ordinal numbers (e.g., 3rd -> Third)."""
        if not self.abbreviation_expander:
            return text
        return self.abbreviation_expander.normalize_ordinals(text)
    
    def _handle_special_characters(self, text: str) -> str:
        """Clean up special characters that interfere with parsing."""
        cleaned = text
        cleaned = re.sub(r'[\[\]()/]', ' ', cleaned)
        cleaned = cleaned.replace('&', ' and ')
        cleaned = cleaned.replace(',', ' ')
        # Clean up leftover hyphens and dashes
        cleaned = re.sub(r'\s*-\s*$', '', cleaned)  # Remove trailing dash
        cleaned = re.sub(r'^\s*-\s*', '', cleaned)  # Remove leading dash
        cleaned = re.sub(r'\s+-\s+', ' ', cleaned)  # Replace spaced dashes with space
        return cleaned
    
    def _normalize_whitespace(self, text: str) -> str:
        """Collapse multiple spaces into single spaces and trim edges."""
        return ' '.join(text.split())
    
    def preprocess(self, exam_name: str) -> str:
        """
        Apply the complete, prioritized preprocessing pipeline.
        """
        if not exam_name:
            return ""
        
        cleaned = exam_name
        
        cleaned = self._remove_no_report_suffix(cleaned)
        cleaned = self._remove_admin_qualifiers(cleaned)
        cleaned = self._expand_abbreviations(cleaned)
        cleaned = self._handle_special_characters(cleaned)
        cleaned = self._normalize_ordinals(cleaned)
        cleaned = self._normalize_whitespace(cleaned)
        
        return cleaned
    
    def preprocess_batch(self, exam_names: list) -> list:
        """Process multiple exam names in a single operation."""
        return [self.preprocess(exam_name) for exam_name in exam_names]

# =============================================================================
# GLOBAL INSTANCE AND CONVENIENCE FUNCTIONS
# =============================================================================
_preprocessor: Optional[ExamPreprocessor] = None

def initialize_preprocessor(abbreviation_expander=None, config=None):
    """
    Set up the global preprocessor instance.
    """
    global _preprocessor
    _preprocessor = ExamPreprocessor(abbreviation_expander, config=config)

def preprocess_exam_name(exam_name: str) -> str:
    """Preprocess a single exam name using the global preprocessor instance."""
    if _preprocessor is None:
        raise RuntimeError("Preprocessor not initialized. Call initialize_preprocessor() first.")
    return _preprocessor.preprocess(exam_name)

def get_preprocessor() -> Optional[ExamPreprocessor]:
    """Access the global preprocessor instance."""
    return _preprocessor

# --- END OF FILE preprocessing.py ---