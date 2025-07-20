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
    expression compiled from a comprehensive vocabulary.
    """
    def __init__(self, nhs_authority: Dict):
        self.nhs_authority = nhs_authority
        self.anatomy_map = self._build_anatomy_vocabulary()
        
        sorted_keys = sorted(self.anatomy_map.keys(), key=len, reverse=True)
        escaped_keys = [re.escape(key) for key in sorted_keys]
        pattern_str = r'\b(' + '|'.join(escaped_keys) + r')\b'
        self.master_pattern = re.compile(pattern_str, re.IGNORECASE)

    def _build_anatomy_vocabulary(self) -> Dict[str, str]:
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
        return anatomy_vocab

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
        """Detects the standardized laterality term, prioritizing 'bilateral'."""
        text_lower = text.lower()
        # The order of checking is crucial to correctly handle strings that might
        # contain multiple terms post-processing (e.g., from a complex original string).
        if any(p.search(text_lower) for p in self.compiled_patterns['bilateral']):
            return 'bilateral'
        if any(p.search(text_lower) for p in self.compiled_patterns['left']):
            return 'left'
        if any(p.search(text_lower) for p in self.compiled_patterns['right']):
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

    def detect_contrast(self, text: str) -> Optional[str]:
        """Detects the final, standardized contrast term."""
        if any(p.search(text) for p in self.compiled_patterns['without']):
            return 'without'
        if any(p.search(text) for p in self.compiled_patterns['with']):
            return 'with'
        return None

# --- END OF FILE parsing_utils.py ---