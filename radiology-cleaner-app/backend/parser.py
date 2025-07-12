import re
from typing import Dict, List, Optional, Set
# UPDATED: Importing from our new utility file
from parsing_utils import AnatomyExtractor, LateralityDetector, USAContrastMapper

class RadiologySemanticParser:
    """
    A Python parser that standardizes radiology exam names by extracting key
    components. It uses a robust, rule-based system for high accuracy,
    supported by injected utility classes.
    """
    def __init__(self, nlp_processor=None, anatomy_extractor=None, laterality_detector=None, contrast_mapper=None):
        self.nlp_processor = nlp_processor
        self.anatomy_extractor = anatomy_extractor
        self.laterality_detector = laterality_detector
        self.contrast_mapper = contrast_mapper

        self.modality_map = {'CT': 'CT', 'MR': 'MRI', 'MRI': 'MRI', 'XR': 'XR', 'US': 'US', 'NM': 'NM', 'PET': 'PET', 'MG': 'Mammography', 'Mammo':'Mammography', 'DEXA': 'DEXA', 'FL': 'Fluoroscopy', 'IR': 'IR', 'Other': 'Other', 'BR': 'Mammography'}

        self.technique_patterns = {
            'Angiography': [re.compile(p, re.I) for p in [r'angiogram', r'angiography', r'\bcta\b', r'\bmra\b', r'venogram', r'angio']],
            'HRCT': [re.compile(p, re.I) for p in [r'hrct', r'high resolution']],
            'Colonography': [re.compile(p, re.I) for p in [r'colonography', r'virtual colonoscopy']],
            'Doppler': [re.compile(p, re.I) for p in [r'doppler', r'duplex']],
            'Intervention': [re.compile(p, re.I) for p in [r'biopsy', r'drainage', 'aspir', r'injection', r'guided', r'procedure', 'ablation', 'placement', 'loc', 'bx']],
        }

        self.anatomy_lookup = {}
        if self.anatomy_extractor:
            self.anatomy_lookup = self.anatomy_extractor.anatomy_terms
        self.sorted_anatomy_terms = sorted(self.anatomy_lookup.keys(), key=len, reverse=True)

    def parse_exam_name(self, exam_name: str, modality_code: str) -> Dict:
        """
        Parses a radiology exam name using rule-based matching.
        """
        lower_name = exam_name.lower()
        
        # --- REFACTORED: Anatomy Parsing ---
        # The NLP entity extraction was not being used, so it has been removed.
        found_anatomy_keys = self._parse_anatomy_hybrid(lower_name)
        
        parsed = {
            'modality': self._parse_modality(lower_name, modality_code),
            'anatomy': sorted(list(found_anatomy_keys)),
            'laterality': self._parse_laterality(lower_name),
            'contrast': self._parse_contrast(lower_name),
            'technique': self._parse_technique(lower_name),
        }
        
        result = {
            'cleanName': self._build_clean_name(parsed),
            'confidence': self._calculate_confidence(parsed, exam_name),
            **parsed
        }
        return result

    def _parse_anatomy_hybrid(self, lower_name: str) -> Set[str]:
        """
        Uses precise longest-match-first rule-based anatomy extraction.
        REFACTORED: Removed the unused nlp_terms argument.
        """
        found_keys: Set[str] = set()
        for term_key in self.sorted_anatomy_terms:
            if term_key in lower_name:
                found_keys.add(self.anatomy_lookup[term_key])
        return found_keys

    def _parse_modality(self, lower_name: str, modality_code: str) -> str:
        """Parse modality from exam name first, fall back to modality_code."""
        modality_patterns = {
            'CT': re.compile(r'\b(ct|computed tomography)\b', re.I),
            'MRI': re.compile(r'\b(mr|mri|magnetic resonance)\b', re.I),
            'XR': re.compile(r'\b(xr|x-ray|radiograph|plain film)\b', re.I),
            'US': re.compile(r'\b(us|ultrasound|sonogram)\b', re.I),
            'NM': re.compile(r'\b(nm|nuclear medicine|spect|scintigraphy)\b', re.I),
            'PET': re.compile(r'\b(pet|positron emission)\b', re.I),
            'Mammography': re.compile(r'\b(mg|mammo|mammography)\b', re.I),
            'Fluoroscopy': re.compile(r'\b(fl|fluoroscopy|screening)\b', re.I),
        }
        for modality, pattern in modality_patterns.items():
            if pattern.search(lower_name):
                return modality
        if modality_code and modality_code.upper() in self.modality_map:
            return self.modality_map[modality_code.upper()]
        return modality_code or 'Other'

    def _parse_laterality(self, lower_name: str) -> Optional[str]:
        """Parse laterality using the dedicated LateralityDetector."""
        return self.laterality_detector.detect(lower_name) if self.laterality_detector else None

    def _parse_contrast(self, lower_name: str) -> Optional[str]:
        """Parse contrast status using the dedicated USAContrastMapper."""
        return self.contrast_mapper.detect_contrast(lower_name) if self.contrast_mapper else None

    def _parse_technique(self, lower_name: str) -> List[str]:
        """Parse techniques using regex patterns."""
        techniques = []
        for tech, patterns in self.technique_patterns.items():
            if any(p.search(lower_name) for p in patterns):
                techniques.append(tech)
        return sorted(list(set(techniques)))

    def _build_clean_name(self, parsed: Dict) -> str:
        """Constructs a standardized, human-readable clean name."""
        parts = [parsed['modality']]
        if parsed['anatomy']: parts.append(" ".join(parsed['anatomy']))
        else: parts.append("Unknown Anatomy")
        if 'Angiography' in parsed['technique']: parts.append("Angiography")
        if parsed['laterality']: parts.append(parsed['laterality'])
        clean_name = " ".join(parts)
        if parsed['contrast'] == 'with and without': clean_name += " with/without Contrast"
        elif parsed['contrast'] == 'with': clean_name += " with Contrast"
        elif parsed['contrast'] == 'without': clean_name += " without Contrast"
        return clean_name.strip()

    def _calculate_confidence(self, result: Dict, original_exam_name: str) -> float:
        """Calculates a confidence score based on the completeness of the parse."""
        score = 0.5
        if result.get('anatomy'): score += 0.25
        if result.get('modality') != 'Unknown': score += 0.1
        if result.get('contrast'): score += 0.1
        if result.get('laterality'): score += 0.05
        if len(original_exam_name.split()) < 3: score -= 0.1
        return max(0.1, min(1.0, round(score, 2)))