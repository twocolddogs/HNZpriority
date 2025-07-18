# --- START OF FILE parser.py ---

import re
from typing import Dict, List, Optional, Set
from parsing_utils import AnatomyExtractor, LateralityDetector, ContrastMapper

class RadiologySemanticParser:
    def __init__(self, nlp_processor=None, anatomy_extractor=None, laterality_detector=None, contrast_mapper=None):
        self.nlp_processor = nlp_processor
        self.anatomy_extractor = anatomy_extractor
        self.laterality_detector = laterality_detector
        self.contrast_mapper = contrast_mapper

        self.modality_map = {
            'CT': 'CT', 'MR': 'MRI', 'MRI': 'MRI', 'XR': 'XR', 'US': 'US', 'NM': 'NM',
            'PET': 'PET', 'MG': 'MG', 'MAMM': 'MG', 'MAMMO': 'MG', 'DEXA': 'DEXA', 
            'FL': 'Fluoroscopy', 
            'IR': 'IR',  # ADDITION: Recognize 'IR' as a valid modality code.
            'XA': 'IR',  # MODIFICATION: Map incoming 'XA' codes directly to 'IR'.
            'Other': 'Other', 'BR': 'MG'
        }
        
        self.technique_patterns = {
            'HRCT': [re.compile(p, re.I) for p in [r'\b(hrct|high resolution)\b']],
            'Colonography': [re.compile(p, re.I) for p in [r'\b(colonography|virtual colonoscopy)\b']],
            'Doppler': [re.compile(p, re.I) for p in [r'\b(doppler|duplex)\b']],
            'Tomosynthesis': [re.compile(p, re.I) for p in [r'\b(tomosynthesis|tomo)\b']],
            'Barium Study': [re.compile(p, re.I) for p in [r'barium', r'\bupper gi\b', r'\blower gi\b']],
            'Vascular Interventional': [re.compile(p, re.I) for p in [
                r'\b(angiogram|angiography|cta|mra|venography|angio|dsa)\b',
                r'\b(stent|angioplasty|emboli[sz]ation|thrombolysis|thrombectomy|atherectomy|picc|line|catheter)\b'
            ]],
            'Non-Vascular Interventional': [re.compile(p, re.I) for p in [
                r'\b(biopsy|bx|fna|drainage|aspirat|injection|vertebroplasty|ablation|guided|guidance|placement|locali[sz]ation|insertion|insert)\b'
            ]]
        }

    def parse_exam_name(self, exam_name: str, modality_code: str) -> Dict:
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
        # MODIFICATION: Added a comprehensive 'IR' pattern and removed 'XA'.
        # This gives 'IR' high priority in text-based detection.
        modality_patterns = {
            'IR': re.compile(r'\b(ir|interventional|xa|angiography|angiogram|dsa|picc|biopsy|drainage|stent|ablation|emboli[sz]ation)\b', re.I),
            'CT': re.compile(r'\b(ct|computed tomography)\b', re.I),
            'MRI': re.compile(r'\b(mr|mri|mra|magnetic resonance)\b', re.I),
            'MG': re.compile(r'\b(mg|mammo|mamm|mammography|mammogram|tomosynthesis|tomo|br)\b', re.I),
            'US': re.compile(r'\b(us|ultrasound|sonogram|doppler|duplex)\b', re.I),
            'NM': re.compile(r'\b(nm|nuclear medicine|spect|scintigraphy)\b', re.I),
            'PET': re.compile(r'\b(pet|positron emission)\b', re.I),
            'DEXA': re.compile(r'\b(dexa|dxa|bone densitometry)\b', re.I),
            'Fluoroscopy': re.compile(r'\b(fl|fluoroscopy|barium|swallow|meal|enema)\b', re.I),
            'XR': re.compile(r'\b(xr|x-ray|xray|radiograph|plain film|projection)\b', re.I), # XR is last as a fallback
        }
        for modality, pattern in modality_patterns.items():
            if pattern.search(lower_name):
                return modality
        # Fallback to the modality map if no text pattern matches
        return self.modality_map.get(str(modality_code).upper(), 'Other') if modality_code else 'Other'

    def _parse_laterality(self, lower_name: str) -> List[str]:
        detected = self.laterality_detector.detect(lower_name) if self.laterality_detector else None
        return [detected] if detected else []

    def _parse_contrast(self, lower_name: str) -> List[str]:
        detected = self.contrast_mapper.detect_contrast(lower_name) if self.contrast_mapper else None
        return [detected] if detected else []

    def _parse_technique(self, lower_name: str) -> List[str]:
        techniques = {tech for tech, patterns in self.technique_patterns.items() if any(p.search(lower_name) for p in patterns)}
        return sorted(list(techniques))

    def _build_clean_name(self, parsed: Dict) -> str:
        """Constructs a standardized, human-readable clean name."""
        parts = [parsed.get('modality', 'Unknown')]
        
        # Consolidate techniques for cleaner naming
        techniques = parsed.get('technique', [])
        if 'Vascular Interventional' in techniques: parts.append("Angiogram")
        
        if parsed.get('anatomy'):
            parts.append(" ".join(sorted(list(set(parsed['anatomy'])))))
        
        if parsed.get('laterality'):
            lat_map = {'left': 'Lt', 'right': 'Rt', 'bilateral': 'Both'}
            parts.append(lat_map.get(parsed['laterality'][0], parsed['laterality'][0].capitalize()))

        return " ".join(part for part in parts if part).strip()

    def _calculate_confidence(self, result: Dict, original_exam_name: str) -> float:
        score = 0.5
        if result.get('anatomy'): score += 0.3
        if result.get('modality') not in ['Other', 'Unknown']: score += 0.1
        if result.get('contrast'): score += 0.05
        if result.get('laterality'): score += 0.05
        return max(0.1, min(1.0, round(score, 4)))