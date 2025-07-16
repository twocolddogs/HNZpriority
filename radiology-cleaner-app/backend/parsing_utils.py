# --- START OF FILE parsing_utils.py ---

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class AbbreviationExpander:
    """Medical abbreviation expansion for radiology exam names"""

    def __init__(self):
        self.medical_abbreviations = {
            # Anatomy
            'abd': 'abdomen', 'abdo': 'abdomen', 'pelv': 'pelvis', 'ext': 'extremity',
            'br': 'breast', 'csp': 'cervical spine', 'tsp': 'thoracic spine', 'lsp': 'lumbar spine',
            'c-spine': 'cervical spine', 't-spine': 'thoracic spine', 'l-spine': 'lumbar spine',
            'iam': 'internal auditory meatus', 'tmj': 'temporomandibular joint',
            # Modality & Combined Anatomy
            'cta': 'ct angiography', 'mra': 'mr angiography', 'ctpa': 'ct pulmonary angiography',
            'cxr': 'chest xray', 'axr': 'abdominal xray',
            'kub': 'kidneys ureters bladder',
            'mammo': 'mammogram', 'cap': 'chest abdomen pelvis',
            # Contrast
            'w': 'with', 'wo': 'without', 'gad': 'gadolinium', 'iv': 'intravenous',
            'c+': 'with contrast', 'c-': 'without contrast',
            # Interventional & Clinical
            'bx': 'biopsy', 'fna': 'fine needle aspiration',
            'pc': 'percutaneous', 'st': 'soft tissue', 'f/u': 'follow up',
            # Other common terms
            'mrcp': 'magnetic resonance cholangiopancreatography',
            'psma': 'prostate specific membrane antigen',
            # Laterality (comprehensive list)
            'rt': 'right', 'lt': 'left', 'bil': 'bilateral', 'bilat': 'bilateral',
            'r': 'right', 'l': 'left', 'both': 'bilateral'
        }

    def expand(self, text: str) -> str:
        words = text.split()
        expanded_words = []
        for word in words:
            clean_word = word.lower().strip('.,()[]/-+').strip()
            if clean_word in self.medical_abbreviations:
                 expanded_words.append(self.medical_abbreviations[clean_word])
            else:
                 expanded_words.append(word)
        return ' '.join(expanded_words)
    
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
    """Extract anatomy using NHS authority data"""

    def __init__(self, nhs_authority: Dict):
        self.nhs_authority = nhs_authority
        self.anatomy_terms = self._build_anatomy_vocabulary()

    def _build_anatomy_vocabulary(self) -> Dict[str, str]:
        anatomy_vocab = {
            'head': 'head', 'brain': 'brain', 'skull': 'head', 'cranium': 'head', 'sinus': 'sinuses',
            'sinuses': 'sinuses', 'orbit': 'orbit', 'face': 'face', 'neck': 'neck', 'chest': 'chest',
            'thorax': 'chest', 'lung': 'chest', 'lungs': 'chest', 'heart': 'heart', 'cardiac': 'heart',
            'mediastinum': 'mediastinum', 'pulmonary': 'chest', 'abdomen': 'abdomen', 'abdo': 'abdomen',
            'belly': 'abdomen', 'tummy': 'abdomen', 'pelvis': 'pelvis', 'pelvic': 'pelvis', 'liver': 'liver',
            'kidney': 'kidney', 'kidneys': 'kidney', 'renal': 'kidney', 'pancreas': 'pancreas', 'spleen': 'spleen',
            'bladder': 'bladder', 'ureters': 'ureters', 'uterus': 'uterus', 'ovary': 'ovary', 'ovaries': 'ovary',
            'prostate': 'prostate', 'spine': 'spine', 'spinal': 'spine', 'back': 'spine', 'cervical': 'cervical spine',
            'thoracic': 'thoracic spine', 'lumbar': 'lumbar spine', 'sacrum': 'sacrum', 'coccyx': 'coccyx',
            'shoulder': 'shoulder', 'arm': 'arm', 'elbow': 'elbow', 'wrist': 'wrist', 'hand': 'hand',
            'finger': 'finger', 'thumb': 'thumb', 'hip': 'hip', 'thigh': 'thigh', 'knee': 'knee', 'leg': 'leg',
            'ankle': 'ankle', 'foot': 'foot', 'toe': 'toe', 'breast': 'breast', 'mammary': 'breast',
            'thyroid': 'thyroid', 'bone': 'bone', 'joint': 'joint', 'soft tissue': 'soft tissue',
            'muscle': 'muscle', 'vessel': 'vessel', 'artery': 'artery', 'vein': 'vein',
            'adrenal': 'adrenal', 'biliary': 'biliary', 'gallbladder': 'gallbladder', 'lymph': 'lymph node',
            'parotid': 'parotid', 'submandibular': 'submandibular', 'salivary': 'salivary gland',
            'aortic arch': 'aortic arch', 'carotid': 'carotid'
        }
        anatomy_stop_words = {
            'projection', 'projections', 'view', 'views', 'single', 'multiple', 'scan', 'scans', 'imaging', 'image',
            'mobile', 'portable', 'procedure', 'examination', 'study', 'protocol', 'technique', 'method',
            'series', 'guidance', 'guided', 'localization', 'mapping','and', 'or', 'with', 'without', 'plus', 'including',
            'via', 'through', 'during', 'for', 'of', 'in', 'on','18f', 'fdg', 'psma', 'gallium', 'technetium', 'iodine',
            'contrast','non-contrast', 'pre-contrast', 'post-contrast', 'unenhanced', 'plain', 'enhanced', 'dynamic', 'static',
            'delayed', 'early', 'late', 'pre', 'post', 'follow', 'up','routine', 'standard', 'complete', 'limited', 'focused',
            'targeted', 'selective','whole', 'body', 'full', 'partial', 'complete', 'limited', 'focused', 'targeted', 'selective',
            'doppler', 'duplex', 'flow', 'perfusion', 'diffusion', 'spectroscopy', 'angiography', 'venography',
            'arteriography', 'lymphangiography', 'cholangiography', 'pyelography', 'urography',
            'screening', 'surveillance', 'monitoring', 'assessment', 'evaluation', 'diagnosis', 'therapeutic'
        }
        for clean_name in self.nhs_authority.keys():
            parts = clean_name.lower().split()
            if len(parts) > 1:
                modality_words = {'ct', 'mri', 'mr', 'us', 'xr', 'nm', 'pet', 'dexa', 'mammography', 'mammo', 'mamm', 'mg', 'fluoroscopy'}
                anatomy_parts = [p for p in parts if p not in modality_words and p not in anatomy_stop_words]
                if anatomy_parts:
                    anatomy_phrase = ' '.join(anatomy_parts)
                    if anatomy_phrase and anatomy_phrase not in anatomy_vocab:
                        if any(known_anatomy in anatomy_phrase for known_anatomy in anatomy_vocab.keys()):
                            anatomy_vocab[anatomy_phrase] = anatomy_phrase
                    for word in anatomy_parts:
                        if word and len(word) > 2 and word not in modality_words and word not in anatomy_stop_words:
                            if word not in anatomy_vocab:
                                anatomy_vocab[word] = word
        return anatomy_vocab

    def extract(self, text: str) -> List[str]:
        text_lower = text.lower()
        found_anatomy = set()
        # Sort terms by length, longest first, to match phrases like "cervical spine" before "spine".
        sorted_terms = sorted(self.anatomy_terms.items(), key=lambda item: len(item[0]), reverse=True)
        
        for term, standard_form in sorted_terms:
            try:
                # This unified pattern correctly handles all cases without crashing.
                # It asserts that the match is not immediately preceded or followed by a word character.
                if re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text_lower, re.IGNORECASE):
                    # To avoid adding sub-parts of an already found phrase, check against found standardized forms.
                    # e.g., if we've already found "cervical spine", don't also add "spine".
                    is_sub_part = False
                    for found_item in found_anatomy:
                        if standard_form in found_item:
                           is_sub_part = True
                           break
                    if not is_sub_part:
                       found_anatomy.add(standard_form)

            except re.error:
                logger.warning(f"Skipping invalid anatomy term for regex: '{term}'")
                continue
        return sorted(list(found_anatomy))

class LateralityDetector:
    """Detect laterality (left, right, bilateral) from exam names"""

    def __init__(self):
        self.patterns = {
            'bilateral': [r'\b(bilateral|bilat|both|b/l)\b', r'\b(rt?\.?\s*(and|&|\+)\s*lt?\.?)\b', r'\b(left\s+and\s+right)\b'],
            'left': [r'\b(left|lt?\.?|lft)\b(?!\s*(and|&|\+))'],
            'right': [r'\b(right|rt?\.?|rgt)\b(?!\s*(and|&|\+))']
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
    """Contrast detection for radiology exam names"""

    def __init__(self):
        self.patterns = {
            'with and without': [r'\bw\s*and\s*wo\b', r'\bw/wo\b', r'\bwith\s*and\s*without\b', r'\bpre\s*&\s*post\b', r'\bpre/post\b', r'\b(pre and post contrast)\b'],
            'with': [r'\bw\s+(contrast|iv|gad)\b', r'\bwith\s+contrast\b', r'\benhanced\b', r'\bpost\s*contrast\b', r'\bc\+\b', r'\bC\+\b', r'\s+C\+$', r'\biv contrast\b'],
            'without': [r'\bwo\s+(contrast|iv)\b', r'\bwithout\s+contrast\b', r'\bnon[\s\-]*contrast\b', r'\bnon[\s\-]*enhanced\b', r'\bunenhanced\b', r'\bno\s+contrast\b', r'\bcontrast\s+not\s+given\b', r'\bpre[\s\-]*contrast\b', r'\bc[\s\-]\b', r'\bC[\s\-]\b', r'\s+C-$', r'\bplain\b', r'\bnative\b']
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
