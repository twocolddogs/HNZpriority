# --- START OF FILE parsing_utils.py ---

# =============================================================================
# PARSING UTILITIES (V2 - OPTIMIZED AND ROBUST)
# =============================================================================
# This module provides highly optimized utility classes for extracting specific
# components from radiology exam names. This version refactors the core logic
# to use single, pre-compiled "mega-regex" patterns for maximum performance
# and maintainability, avoiding common regex pitfalls like catastrophic backtracking.

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
    expression compiled from a comprehensive vocabulary.
    """
    def __init__(self, nhs_authority: Dict):
        """
        Initializes the extractor by building a vocabulary and compiling a master regex.
        
        Args:
            nhs_authority: The loaded NHS.json data (used to potentially seed the vocabulary).
        """
        self.nhs_authority = nhs_authority
        self.anatomy_map = self._build_anatomy_vocabulary()
        
        # --- THE OPTIMIZED "MEGA-REGEX" ---
        # 1. Sort all anatomy terms from longest to shortest to prioritize matching
        #    longer, more specific phrases first (e.g., "cervical spine" before "spine").
        sorted_keys = sorted(self.anatomy_map.keys(), key=len, reverse=True)
        
        # 2. Escape each term to ensure characters like '.' or '+' are treated literally.
        escaped_keys = [re.escape(key) for key in sorted_keys]
        
        # 3. Join all keys into a single pattern using the OR pipe '|'.
        #    The \b word boundaries are crucial to ensure we match whole words/phrases.
        pattern_str = r'\b(' + '|'.join(escaped_keys) + r')\b'
        
        # 4. Compile this single, massive regex once for extreme efficiency.
        self.master_pattern = re.compile(pattern_str, re.IGNORECASE)

    def _build_anatomy_vocabulary(self) -> Dict[str, str]:
        """Creates a mapping from various anatomy terms to their standardized form."""
        # This vocabulary should be comprehensive and is the primary source of truth.
        anatomy_vocab = {
            'head': 'head', 'brain': 'brain', 'skull': 'head', 'cranium': 'head', 'sinus': 'sinuses',
            'sinuses': 'sinuses', 'orbit': 'orbit', 'orbits': 'orbit', 'face': 'face', 'neck': 'neck', 
            'chest': 'chest', 'thorax': 'chest', 'lung': 'chest', 'lungs': 'chest', 'heart': 'heart', 
            'cardiac': 'heart', 'mediastinum': 'mediastinum', 'pulmonary': 'chest', 'abdomen': 'abdomen', 
            'abdo': 'abdomen', 'tummy': 'abdomen', 'pelvis': 'pelvis', 'pelvic': 'pelvis', 
            'liver': 'liver', 'kidney': 'kidney', 'kidneys': 'kidney', 'renal': 'kidney', 'pancreas': 'pancreas', 
            'spleen': 'spleen', 'bladder': 'bladder', 'ureter': 'ureters', 'ureters': 'ureters', 'uterus': 'uterus',
            'ovary': 'ovary', 'ovaries': 'ovary', 'prostate': 'prostate', 'spine': 'spine', 'spinal': 'spine', 
            'cervical spine': 'cervical spine', 'thoracic spine': 'thoracic spine', 'lumbar spine': 'lumbar spine', 
            'sacrum': 'sacrum', 'coccyx': 'coccyx', 'shoulder': 'shoulder', 'shoulders': 'shoulder', 'arm': 'arm', 
            'arms': 'arm', 'elbow': 'elbow', 'elbows': 'elbow', 'wrist': 'wrist', 'wrists': 'wrist', 'hand': 'hand', 
            'hands': 'hand', 'finger': 'finger', 'fingers': 'finger', 'thumb': 'thumb', 'thumbs': 'thumb', 
            'hip': 'hip', 'hips': 'hip', 'thigh': 'thigh', 'thighs': 'thigh', 'knee': 'knee', 'knees': 'knee', 
            'leg': 'leg', 'legs': 'leg', 'ankle': 'ankle', 'ankles': 'ankle', 'foot': 'foot', 'feet': 'foot', 
            'toe': 'toe', 'toes': 'toe', 'breast': 'breast', 'breasts': 'breast', 'mammary': 'breast',
            'thyroid': 'thyroid', 'bone': 'bone', 'bones': 'bone', 'joint': 'joint', 'joints': 'joint', 
            'soft tissue': 'soft tissue', 'muscle': 'muscle', 'muscles': 'muscle', 
            'adrenal': 'adrenal', 'adrenals': 'adrenal', 'biliary': 'biliary', 'gallbladder': 'gallbladder', 
            'lymph node': 'lymph node', 'lymph nodes': 'lymph node', 'parotid': 'parotid', 'submandibular': 'submandibular', 
            'salivary gland': 'salivary gland', 'salivary glands': 'salivary gland', 'aortic arch': 'aortic arch', 
            'carotid': 'carotid', 'carotid arteries': 'carotid', 'eye': 'eye', 'eyes': 'eye', 'ear': 'ear', 'ears': 'ear',
            'scrotum': 'scrotum', 'testes': 'testes', 'testis': 'testes'
        }
        # Dynamically adding terms from NHS.json can be an advanced feature, but a strong
        # base vocabulary like this provides more stability.
        return anatomy_vocab

    def extract(self, text: str) -> List[str]:
        """
        Extracts anatomy by running the single master pattern and mapping the results.
        This is extremely fast and avoids performance issues.
        """
        if not text:
            return []
            
        # findall() returns a list of all matched strings.
        found_terms = self.master_pattern.findall(text.lower())
        
        # Use a set to map found terms to their standard form and ensure uniqueness.
        # e.g., if "abdo" and "abdomen" are found, they both map to "abdomen", resulting in one entry.
        if not found_terms:
            return []
            
        unique_standard_forms = {self.anatomy_map[term] for term in found_terms}
        
        return sorted(list(unique_standard_forms))

class LateralityDetector:
    """Detects laterality with a prioritized, pre-compiled set of regex patterns."""
    def __init__(self):
        # Patterns are ordered by priority: bilateral checks run first.
        self.patterns = {
            'bilateral': [
                r'\b(r/l|l/r|rt/lt|lt/rt)\b',                # Slashed abbreviations
                r'\bright\s*&\s*left\b|\bleft\s*&\s*right\b', # Ampersand
                r'\b(bilateral|bilat|both)\b',               # Full words
            ],
            'left': [r'\b(left|lt|lft)\b'],
            'right': [r'\b(right|rt|rgt)\b']
        }
        self.compiled_patterns = {
            lat: [re.compile(p, re.IGNORECASE) for p in patterns]
            for lat, patterns in self.patterns.items()
        }

    def detect(self, text: str) -> Optional[str]:
        """Detects the most likely laterality, prioritizing 'bilateral'."""
        text_lower = text.lower()
        # The order of checking here is crucial.
        if any(p.search(text_lower) for p in self.compiled_patterns['bilateral']):
            return 'bilateral'
        if any(p.search(text_lower) for p in self.compiled_patterns['left']):
            return 'left'
        if any(p.search(text_lower) for p in self.compiled_patterns['right']):
            return 'right'
        return None

class ContrastMapper:
    """Maps contrast terms, designed to work on pre-normalized preprocessed text."""
    def __init__(self):
        # These patterns now primarily look for the standardized tokens
        # produced by the config-driven preprocessor.
        self.patterns = {
            'with': [
                r'\bWITH_CONTRAST\b',  # Standard token from preprocessing
                r'\bw\s*c\b',          # Handle cases like "w c"
                r'\bpost\s*contrast\b'
            ],
            'without': [
                r'\bWITHOUT_CONTRAST\b',# Standard token from preprocessing
                r'\bnon-?contrast\b',
                r'\bplain\b'
            ]
        }
        self.compiled_patterns = {
            ctype: [re.compile(p, re.IGNORECASE) for p in patterns]
            for ctype, patterns in self.patterns.items()
        }

    def detect_contrast(self, text: str) -> Optional[str]:
        """Detects contrast, checking for 'without' before 'with'."""
        # Check for 'without' first because some inputs might contain both
        # (e.g., "CT Chest without, with contrast on request").
        if any(p.search(text) for p in self.compiled_patterns['without']):
            return 'without'
        if any(p.search(text) for p in self.compiled_patterns['with']):
            return 'with'
        return None

# --- END OF FILE parsing_utils.py ---
