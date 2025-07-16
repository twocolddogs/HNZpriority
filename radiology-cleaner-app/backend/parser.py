# --- START OF FILE parser.py ---

import re
from typing import Dict, List, Optional, Set
from parsing_utils import AnatomyExtractor, LateralityDetector, ContrastMapper

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

        # MODIFICATION: Expanded and standardized modality map.
        self.modality_map = {
            'CT': 'CT', 'MR': 'MRI', 'MRI': 'MRI', 'XR': 'XR', 'US': 'US', 'NM': 'NM',
            'PET': 'PET', 'MG': 'MG', 'MAMM': 'MG', 'MAMMO': 'MG', 'MAMMOGRAM': 'MG',
            'DEXA': 'DEXA', 'FL': 'Fluoroscopy', 'IR': 'IR', 'XA': 'XA', 'Other': 'Other',
            'BR': 'MG'
        }
        
        # MODIFICATION: Re-organized and expanded technique patterns.
        self.technique_patterns = {
            'HRCT': [re.compile(p, re.I) for p in [r'\b(hrct|high resolution)\b']],
            'Colonography': [re.compile(p, re.I) for p in [r'\b(colonography|virtual colonoscopy)\b']],
            'Doppler': [re.compile(p, re.I) for p in [r'\b(doppler|duplex)\b']],
            'Tomosynthesis': [re.compile(p, re.I) for p in [r'\b(tomosynthesis|tomo)\b']],
            'Barium Study': [re.compile(p, re.I) for p in [r'barium', r'\bupper gi\b', r'\blower gi\b']],
            'Vascular Interventional': [re.compile(p, re.I) for p in [
                r'\b(angiogram|angiography|cta|mra|venogram|angio|dsa)\b',
                r'\b(stent|angioplasty|emboli[sz]ation|thrombolysis|thrombectomy|atherectomy|picc|line|catheter)\b'
            ]],
            'Non-Vascular Interventional': [re.compile(p, re.I) for p in [
                r'\b(biopsy|bx|fna|drainage|aspirat|injection|vertebroplasty|ablation|guided|guidance|placement|locali[sz]ation|insertion|insert)\b'
            ]]
        }

    def parse_exam_name(self, exam_name: str, modality_code: str) -> Dict:
        """Parses a radiology exam name using rule-based matching."""
        lower_name = exam_name.lower()
        anatomy = self.anatomy_extractor.extract(lower_name) if self.anatomy_extractor else []
        
        parsed = {
            'modality': self._parse_modality(lower_name, modality_code),
            'anatomy': anatomy,
            'laterality': self._parse_laterality(lower_name),
            'contrast': self._parse_contrast(lower_name),
            'technique': self._parse_technique(lower_name),
        }
        
        return {
            'clean_name': self._build_clean_name(parsed),
            'confidence': self._calculate_confidence(parsed, exam_name),
            **parsed
        }

    def _parse_modality(self, lower_name: str, modality_code: str) -> str:
        """MODIFICATION: Improved regex to better capture modality from text."""
        modality_patterns = {
            'CT': re.compile(r'\b(ct|computed tomography)\b', re.I),
            'MRI': re.compile(r'\b(mr|mri|magnetic resonance)\b', re.I),
            'MG': re.compile(r'\b(mg|mammo|mamm|mammography|mammogram|tomosynthesis|tomo|br)\b', re.I),
            'XR': re.compile(r'\b(xr|x-ray|xray|radiograph|plain film)\b', re.I),
            'US': re.compile(r'\b(us|ultrasound|sonogram|doppler|duplex)\b', re.I),
            'NM': re.compile(r'\b(nm|nuclear medicine|spect|scintigraphy)\b', re.I),
            'PET': re.compile(r'\b(pet|positron emission)\b', re.I),
            'DEXA': re.compile(r'\b(dexa|dxa|bone densitometry)\b', re.I),
            'Fluoroscopy': re.compile(r'\b(fl|fluoroscopy|barium|swallow|meal|enema)\b', re.I),
            'XA': re.compile(r'\b(xa|angiography|angiogram|dsa)\b', re.I),
        }
        for modality, pattern in modality_patterns.items():
            if pattern.search(lower_name):
                return modality
        return self.modality_map.get(modality_code.upper(), 'Other') if modality_code else 'Other'

    def _parse_laterality(self, lower_name: str) -> List[str]:
        """Parse laterality using the dedicated LateralityDetector, return as list."""
        detected = self.laterality_detector.detect(lower_name) if self.laterality_detector else None
        return [detected] if detected else []

    def _parse_contrast(self, lower_name: str) -> List[str]:
        """Parse contrast status using the dedicated ContrastMapper, return as list."""
        detected = self.contrast_mapper.detect_contrast(lower_name) if self.contrast_mapper else None
        return [detected] if detected else []

    def _parse_technique(self, lower_name: str) -> List[str]:
        """Parse techniques using regex patterns."""
        techniques = {tech for tech, patterns in self.technique_patterns.items() if any(p.search(lower_name) for p in patterns)}
        return sorted(list(techniques))

    def _build_clean_name(self, parsed: Dict) -> str:
        """Constructs a standardized, human-readable clean name."""
        parts = [parsed['modality']]
        if parsed.get('technique'):
            # Prioritize key techniques in the name
            if 'Angiography' in parsed['technique']: parts.append("Angiogram")
        if parsed['anatomy']:
            parts.append(" ".join(sorted(list(set(parsed['anatomy'])))))
        if parsed['laterality']:
            lat_map = {'left': 'Lt', 'right': 'Rt', 'bilateral': 'Both'}
            parts.append(lat_map.get(parsed['laterality'][0], parsed['laterality'][0]))
        return " ".join(parts).strip()

    def _calculate_confidence(self, result: Dict, original_exam_name: str) -> float:
        """Calculates a confidence score based on the completeness of the parse."""
        score = 0.5
        if result.get('anatomy'): score += 0.3
        if result.get('modality') != 'Other': score += 0.1
        if result.get('contrast'): score += 0.05
        if result.get('laterality'): score += 0.05
        return max(0.1, min(1.0, round(score, 4)))