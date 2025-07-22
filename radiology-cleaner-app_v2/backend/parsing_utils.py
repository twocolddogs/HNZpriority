# --- START OF FILE parsing_utils.py ---

# =============================================================================
# PARSING UTILITIES (V2.2 - FULLY NORMALIZED)
# =============================================================================
# This version simplifies BOTH the ContrastMapper and LateralityDetector to
# work exclusively with pre-normalized tokens from the config-driven preprocessor.
# This creates a single source of truth for all abbreviation logic.

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class AbbreviationExpander:
    """
    DEPRECATED: This class's functionality has been superseded by the more powerful,
    config-driven approach in `preprocessing.py`. It is kept here for reference
    but should no longer be actively used in the main pipeline. The logic for
    ordinal normalization is retained as it's a distinct task.
    """
    def normalize_ordinals(self, text: str) -> str:
        """Converts ordinal numbers to standardized forms (e.g., 3rd -> Third)."""
        ordinal_replacements = {
            r'\b1ST\b': 'First', r'\b2ND\b': 'Second', r'\b3RD\b': 'Third',
        }
        result = text
        for pattern, replacement in ordinal_replacements.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

class AnatomyExtractor:
    """
    Extracts and standardizes anatomy terms using a single, hyper-optimized regular
    expression compiled from a comprehensive, config-driven vocabulary.
    """
    def __init__(self, anatomy_vocabulary: Dict[str, str]):
        """
        Initializes with an anatomy vocabulary, typically loaded from config.
        Args:
            anatomy_vocabulary (Dict[str, str]): A dictionary mapping synonyms to standard forms.
        """
        if not anatomy_vocabulary:
            logger.error("AnatomyExtractor initialized with an empty vocabulary!")
            self.anatomy_map = {}
        else:
            self.anatomy_map = {k.lower(): v.lower() for k, v in anatomy_vocabulary.items()}
        
        # The rest of the __init__ method remains the same
        sorted_keys = sorted(self.anatomy_map.keys(), key=len, reverse=True)
        escaped_keys = [re.escape(key) for key in sorted_keys]
        pattern_str = r'\b(' + '|'.join(escaped_keys) + r')\b'
        self.master_pattern = re.compile(pattern_str, re.IGNORECASE)

    def extract(self, text: str) -> List[str]:
        if not text:
            return []
        found_terms = self.master_pattern.findall(text.lower())
        if not found_terms:
            return []
        unique_standard_forms = {self.anatomy_map[term] for term in found_terms}
        return sorted(list(unique_standard_forms))

class LateralityDetector:
    """
    Detects laterality from a pre-normalized string. Assumes abbreviations like
    'RT' or 'BILAT' have already been expanded to 'right' or 'bilateral'.
    """
    def __init__(self):
        # --- CRITICAL FIX IS HERE ---
        # The patterns are now extremely simple and only look for the final,
        # standardized words. The logic for "rt", "l/r", etc., now lives
        # exclusively in config.yaml.
        self.patterns = {
            'bilateral': [r'\bbilateral\b'],
            'left': [r'\bleft\b'],
            'right': [r'\bright\b']
        }
        self.compiled_patterns = {
            lat: [re.compile(p, re.IGNORECASE) for p in patterns]
            for lat, patterns in self.patterns.items()
        }

    def detect(self, text: str) -> Optional[str]:
        """
        Detects the standardized laterality term, correctly resolving cases where both left and right are mentioned to 'bilateral'.
        """
        text_lower = text.lower()
        # Check for the most specific term first.
        if any(p.search(text_lower) for p in self.compiled_patterns['bilateral']):
            return 'bilateral'
        
        # Check for the presence of left and right individually 
        found_left = any(p.search(text_lower) for p in self.compiled_patterns['left'])
        found_right = any(p.search(text_lower) for p in self.compiled_patterns['right'])
        
        # If both are found, it's bilateral.
        if found_left and found_right:
            return 'bilateral'
            
        # Otherwise, return the specific one that was found.
        if found_left:
            return 'left'
        if found_right:
            return 'right'
        
        return None

class ContrastMapper:
    """
    Maps contrast terms from a pre-normalized string. Assumes abbreviations
    have already been standardized by the config-driven preprocessor.
    """
    def __init__(self):
        # The patterns now ONLY look for the final standardized terms.
        self.patterns = {
            'with': [r'\bwith contrast\b'],
            'without': [r'\bwithout contrast\b']
        }
        self.compiled_patterns = {
            ctype: [re.compile(p, re.IGNORECASE) for p in patterns]
            for ctype, patterns in self.patterns.items()
        }

    def detect_contrast(self, text: str) -> List[str]:
        """
        Detects all specified contrast states in the text.
        Returns a list to handle multiphase studies (e.g., with AND without).
        """
        found_states = []
        text_lower = text.lower() # Standardize to lower for searching
        
        # Use the lowercased text for all searches
        if any(p.search(text_lower) for p in self.compiled_patterns['with']):
            found_states.append('with')
        
        if any(p.search(text_lower) for p in self.compiled_patterns['without']):
            found_states.append('without')
        
        # Return a sorted, unique list of states found
        return sorted(list(set(found_states)))

# --- END OF FILE parsing_utils.py ---
