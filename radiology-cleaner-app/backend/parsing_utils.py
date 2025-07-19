# --- START OF FILE parsing_utils.py ---

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class AbbreviationExpander:
    """Medical abbreviation expansion for radiology exam names"""

    def __init__(self):
        self.medical_abbreviations = {
            'abd': 'abdomen', 'abdo': 'abdomen', 'pelv': 'pelvis', 'ext': 'extremity',
            'br': 'breast', 'csp': 'cervical spine', 'tsp': 'thoracic spine', 'lsp': 'lumbar spine',
            'c-spine': 'cervical spine', 't-spine': 'thoracic spine', 'l-spine': 'lumbar spine',
            'iam': 'internal auditory meatus', 'tmj': 'temporomandibular joint',
            'cta': 'ct angiography', 'mra': 'mr angiography', 'ctpa': 'ct pulmonary angiography',
            'cxr': 'chest xray', 'axr': 'abdominal xray',
            'kub': 'kidneys ureters bladder',
            'mammo': 'mammogram', 'cap': 'chest abdomen pelvis',
            'w': 'with', 'wo': 'without', 'gad': 'gadolinium', 'iv': 'intravenous',
            'c+': 'with contrast', 'c-': 'without contrast',
            'bx': 'biopsy', 'fna': 'fine needle aspiration',
            'pc': 'percutaneous', 'st': 'soft tissue', 'f/u': 'follow up',
            'mrcp': 'magnetic resonance cholangiopancreatography',
            'psma': 'prostate specific membrane antigen',
            'rt': 'right', 'lt': 'left', 'bil': 'bilateral', 'bilat': 'bilateral',
            'r': 'right', 'l': 'left', 'both': 'bilateral'
        }
        # --- RECOMMENDED CHANGE: Use a single, powerful regex ---
        # Sort keys by length (desc) to match longer abbreviations first (e.g., 'c-spine' before 'c-')
        sorted_keys = sorted(self.medical_abbreviations.keys(), key=len, reverse=True)
        # Escape special characters (like '+') and join into a single pattern
        escaped_keys = [re.escape(key) for key in sorted_keys]
        # Compile the master regex for efficiency
        self.master_pattern = re.compile(r'\b(' + '|'.join(escaped_keys) + r')\b', re.IGNORECASE)

    def expand(self, text: str) -> str:
        # --- RECOMMENDED CHANGE: Use a robust regex replacement function ---
        # This function looks up the matched abbreviation in the dictionary
        def repl(match):
            return self.medical_abbreviations[match.group(0).lower()]
        
        # Use re.sub with the replacement function for a single-pass, robust expansion
        return self.master_pattern.sub(repl, text)
    
    def normalize_ordinals(self, text: str) -> str:
        ordinal_replacements = {
            r'\b1ST\b': 'First', r'\b2ND\b': 'Second', r'\b3RD\b': 'Third',
            r'\b1st\b': 'First', r'\b2nd\b': 'Second', r'\b3rd\b': 'Third',
        }
        result = text
        for pattern, replacement in ordinal_replacements.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

class AnatomyExtractor:
    """
    Extract anatomy using a single, hyper-optimized regular expression
    compiled once for maximum performance.
    """

    def __init__(self, nhs_authority: Dict):
        self.nhs_authority = nhs_authority
        self.anatomy_map = self._build_anatomy_vocabulary()
        
        # --- THE OPTIMIZED "MEGA-REGEX" ---
        # 1. Sort all anatomy terms from longest to shortest to prioritize matching longer phrases.
        sorted_keys = sorted(self.anatomy_map.keys(), key=len, reverse=True)
        
        # 2. Escape each term to ensure it's treated as a literal string in the regex.
        escaped_keys = [re.escape(key) for key in sorted_keys]
        
        # 3. Join all escaped keys with the OR pipe to create one massive pattern.
        pattern_str = '|'.join(escaped_keys)
        
        # 4. Compile the single, massive regex pattern once for hyper-efficiency.
        # The \b word boundaries ensure we match whole words/phrases.
        self.master_pattern = re.compile(r'\b(' + pattern_str + r')\b', re.IGNORECASE)

    def _build_anatomy_vocabulary(self) -> Dict[str, str]:
        anatomy_vocab = {
            'head': 'head', 'brain': 'brain', 'skull': 'head', 'cranium': 'head', 'sinus': 'sinuses',
            'sinuses': 'sinuses', 'orbit': 'orbit', 'orbits': 'orbit', 'face': 'face', 'neck': 'neck', 
            'chest': 'chest', 'thorax': 'chest', 'lung': 'chest', 'lungs': 'chest', 'heart': 'heart', 
            'cardiac': 'heart', 'mediastinum': 'mediastinum', 'pulmonary': 'chest', 'abdomen': 'abdomen', 
            'abdo': 'abdomen', 'belly': 'abdomen', 'tummy': 'abdomen', 'pelvis': 'pelvis', 'pelvic': 'pelvis', 
            'liver': 'liver', 'kidney': 'kidney', 'kidneys': 'kidney', 'renal': 'kidney', 'pancreas': 'pancreas', 
            'spleen': 'spleen', 'bladder': 'bladder', 'ureters': 'ureters', 'uterus': 'uterus', 'ovary': 'ovary', 
            'ovaries': 'ovary', 'prostate': 'prostate', 'spine': 'spine', 'spinal': 'spine', 'back': 'spine', 
            'cervical spine': 'cervical spine', 'thoracic spine': 'thoracic spine', 'lumbar spine': 'lumbar spine', 
            'sacrum': 'sacrum', 'coccyx': 'coccyx', 'shoulder': 'shoulder', 'shoulders': 'shoulder', 'arm': 'arm', 
            'arms': 'arm', 'elbow': 'elbow', 'elbows': 'elbow', 'wrist': 'wrist', 'wrists': 'wrist', 'hand': 'hand', 
            'hands': 'hand', 'finger': 'finger', 'fingers': 'finger', 'thumb': 'thumb', 'thumbs': 'thumb', 
            'hip': 'hip', 'hips': 'hip', 'thigh': 'thigh', 'thighs': 'thigh', 'knee': 'knee', 'knees': 'knee', 
            'leg': 'leg', 'legs': 'leg', 'ankle': 'ankle', 'ankles': 'ankle', 'foot': 'foot', 'feet': 'foot', 
            'toe': 'toe', 'toes': 'toe', 'breast': 'breast', 'breasts': 'breast', 'mammary': 'breast',
            'thyroid': 'thyroid', 'bone': 'bone', 'bones': 'bone', 'joint': 'joint', 'joints': 'joint', 
            'soft tissue': 'soft tissue', 'muscle': 'muscle', 'muscles': 'muscle', 'vessel': 'vessel', 
            'vessels': 'vessel', 'artery': 'artery', 'arteries': 'artery', 'vein': 'vein', 'veins': 'vein',
            'adrenal': 'adrenal', 'adrenals': 'adrenal', 'biliary': 'biliary', 'gallbladder': 'gallbladder', 
            'lymph node': 'lymph node', 'lymph nodes': 'lymph node', 'parotid': 'parotid', 'submandibular': 'submandibular', 
            'salivary gland': 'salivary gland', 'salivary glands': 'salivary gland', 'aortic arch': 'aortic arch', 
            'carotid': 'carotid', 'eye': 'eye', 'eyes': 'eye', 'ear': 'ear', 'ears': 'ear'
        }
        # The dynamic learning from NHS data can be simplified or removed if the base vocab is sufficient.
        # For now, a comprehensive base vocab is more stable.
        return anatomy_vocab

    def extract(self, text: str) -> List[str]:
        """
        Extracts anatomy by running the single master pattern and mapping the results.
        This is extremely fast and avoids catastrophic backtracking and worker timeouts.
        """
        # Find all non-overlapping matches of the master pattern in the text.
        found_terms = self.master_pattern.findall(text.lower())
        
        # Use a set to get unique standardized forms.
        # e.g., if "abdo" and "abdomen" are found, they both map to "abdomen", resulting in one entry.
        if not found_terms:
            return []
            
        unique_standard_forms = {self.anatomy_map[term] for term in found_terms}
        
        return sorted(list(unique_standard_forms))

class LateralityDetector:
    def __init__(self):
        self.patterns = {
            'bilateral': [
                # Slash-separated patterns (highest priority)
                r'\b(r/l|l/r|rt/lt|lt/rt|right/left|left/right)\b',
                # Post-preprocessing expanded patterns
                r'\bright\s+left\b|\bleft\s+right\b',
                # Ampersand and plus patterns
                r'\b(rt?\.?\s*[&+]\s*lt?\.?|lt?\.?\s*[&+]\s*rt?\.?)\b',
                r'\b(right\s*[&+]\s*left|left\s*[&+]\s*right)\b',
                # Parenthetical bilateral patterns (before preprocessing removes parens)
                r'\(\s*b\s*\)|\(\s*bil\s*\)|\(\s*bilat\s*\)',
                # Standalone B (after preprocessing removes parens)
                r'\bb\b(?!\w)',
                # Standard bilateral patterns
                r'\b(bilateral|bilat|both|b/l)\b',
                r'\b(rt?\.?\s*and\s*lt?\.?|lt?\.?\s*and\s*rt?\.?)\b',
                r'\b(left\s+and\s+right|right\s+and\s+left)\b'
            ],
            'left': [r'\b(left|lt?\.?|lft)\b(?!\s*(and|&|\+|/))', r'\(\s*l\s*\)'],
            'right': [r'\b(right|rt?\.?|rgt)\b(?!\s*(and|&|\+|/))', r'\(\s*r\s*\)']
        }
        self.compiled_patterns = {
            lat: [re.compile(p, re.IGNORECASE) for p in patterns]
            for lat, patterns in self.patterns.items()
        }

    def detect(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        if any(p.search(text_lower) for p in self.compiled_patterns['bilateral']):
            return 'bilateral'
        if any(p.search(text_lower) for p in self.compiled_patterns['left']):
            return 'left'
        if any(p.search(text_lower) for p in self.compiled_patterns['right']):
            return 'right'
        return None

class ContrastMapper:
    def __init__(self):
        self.patterns = {
            'with and without': [r'\bw\s*and\s*wo\b', r'\bw/wo\b', r'\bwith\s*and\s*without\b', r'\bpre\s*&\s*post\b', r'\bpre/post\b', r'\b(pre and post contrast)\b'],
            'with': [
                # SUPER-STRONG: Preprocessed standardized tokens (highest priority)
                r'\bWITH_CONTRAST\b',
                # Original patterns
                r'\bw\s+(contrast|iv|gad)\b', r'\bwith\s+contrast\b', r'\benhanced\b', r'\bpost\s*contrast\b', 
                r'\bc\+\b', r'\bC\+\b', r'\s+C\+$', r'\biv contrast\b', r'\bgadolinium\b', r'\bgad\b'
            ],
            'without': [
                # SUPER-STRONG: Preprocessed standardized tokens (highest priority)
                r'\bWITHOUT_CONTRAST\b',
                # Original patterns
                r'\bwo\s+(contrast|iv)\b', r'\bwithout\s+contrast\b', r'\bnon[\s\-]*contrast\b', 
                r'\bnon[\s\-]*enhanced\b', r'\bunenhanced\b', r'\bno\s+contrast\b', 
                r'\bcontrast\s+not\s+given\b', r'\bpre[\s\-]*contrast\b', r'\bc[\s\-]\b', 
                r'\bC[\s\-]\b', r'\s+C-$', r'\bplain\b', r'\bnative\b'
            ]
        }
        self.compiled_patterns = {
            ctype: [re.compile(p, re.IGNORECASE) for p in patterns]
            for ctype, patterns in self.patterns.items()
        }

    def detect_contrast(self, text: str) -> Optional[str]:
        for contrast_type in ['with and without', 'without', 'with']:
            if any(p.search(text) for p in self.compiled_patterns[contrast_type]):
                return contrast_type
        return None