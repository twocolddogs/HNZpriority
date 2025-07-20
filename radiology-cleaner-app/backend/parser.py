# --- START OF FILE parser.py ---

# =============================================================================
# RADIOLOGY SEMANTIC PARSER (V2 - ENHANCED TECHNIQUE DETECTION)
# =============================================================================
# This module is responsible for breaking down a cleaned radiology exam name
# into its constituent semantic components: modality, anatomy, laterality,
# contrast, and specific techniques. This version features more granular
# technique detection, especially for interventional procedures.

import re
from typing import Dict, List, Optional
from parsing_utils import AnatomyExtractor, LateralityDetector, ContrastMapper

class RadiologySemanticParser:
    """
    Parses a cleaned radiology exam name into a structured dictionary of components.
    
    It leverages utility classes to extract specific features and uses regex patterns
    to identify modality and specialized techniques. The output of this parser is a
    key input for the NHSLookupEngine's scoring algorithm.
    """
    def __init__(self, nlp_processor=None, anatomy_extractor=None, laterality_detector=None, contrast_mapper=None):
        """
        Initializes the parser with necessary utility components.
        
        Args:
            nlp_processor: An NLP model processor (optional, currently not used directly in parsing).
            anatomy_extractor: Utility to extract anatomical parts.
            laterality_detector: Utility to detect left, right, or bilateral.
            contrast_mapper: Utility to map contrast terms.
        """
        self.nlp_processor = nlp_processor
        self.anatomy_extractor = anatomy_extractor
        self.laterality_detector = laterality_detector
        self.contrast_mapper = contrast_mapper

        # A map to normalize modality codes and terms found in exam names.
        self.modality_map = {
            'CT': 'CT', 'MR': 'MRI', 'MRI': 'MRI', 'XR': 'XR', 'US': 'US', 'NM': 'NM',
            'PET': 'PET', 'MG': 'MG', 'MAMM': 'MG', 'MAMMO': 'MG', 'DEXA': 'DEXA', 
            'FL': 'Fluoroscopy', 
            'IR': 'IR',
            'XA': 'IR',
            'Other': 'Other', 'BR': 'MG'
        }
        
        # MODIFICATION: Expanded and split interventional patterns for better granularity.
        # This allows the scoring engine to differentiate between vascular and non-vascular procedures.
        self.technique_patterns = {
            'HRCT': [re.compile(p, re.I) for p in [r'\b(hrct|high resolution)\b']],
            'Colonography': [re.compile(p, re.I) for p in [r'\b(colonography|virtual colonoscopy)\b']],
            'Doppler': [re.compile(p, re.I) for p in [r'\b(doppler|duplex)\b']],
            'Tomosynthesis': [re.compile(p, re.I) for p in [r'\b(tomosynthesis|tomo)\b']],
            'Barium Study': [re.compile(p, re.I) for p in [r'\b(barium|upper gi|lower gi)\b']],
            'Vascular Interventional': [re.compile(p, re.I) for p in [
                r'\b(angiogram|angiography|cta|mra|venography|angio|dsa)\b',
                r'\b(stent|angioplasty|emboli[sz]ation|thrombolysis|thrombectomy|atherectomy|picc|line|catheter)\b'
            ]],
            'Non-Vascular Interventional': [re.compile(p, re.I) for p in [
                r'\b(biopsy|bx|fna|drainage|aspirat|injection|vertebroplasty|ablation|guided|guidance|placement|locali[sz]ation|insertion|insert)\b'
            ]]
        }

    def parse_exam_name(self, exam_name: str, modality_code: str) -> Dict:
        """
        Executes the full parsing pipeline on a single cleaned exam name.
        
        Args:
            exam_name: The preprocessed exam name string.
            modality_code: The original modality code from the source data.
            
        Returns:
            A dictionary containing the parsed components and a generated clean name.
        """
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
        """Determines modality from text, falling back to the provided code."""
        explicit_modality_patterns = {
            'CT': re.compile(r'\b(ct|computed tomography)\b', re.I),
            'MRI': re.compile(r'\b(mr|mri|mra|magnetic resonance)\b', re.I),
            'MG': re.compile(r'\b(mg|mammo|mamm|mammography|mammogram|tomosynthesis|tomo|br)\b', re.I),
            'US': re.compile(r'\b(us|ultrasound|sonogram|doppler|duplex)\b', re.I),
            'NM': re.compile(r'\b(nm|nuclear medicine|spect|scintigraphy)\b', re.I),
            'PET': re.compile(r'\b(pet|positron emission)\b', re.I),
            'DEXA': re.compile(r'\b(dexa|dxa|bone densitometry)\b', re.I),
            'Fluoroscopy': re.compile(r'\b(fl|fluoroscopy|barium|swallow|meal|enema)\b', re.I),
            'XR': re.compile(r'\b(xr|x-ray|xray|radiograph|plain film|projection)\b', re.I),
        }
        
        for modality, pattern in explicit_modality_patterns.items():
            if pattern.search(lower_name):
                return modality # Return immediately if an explicit modality is found

        # Fallback to check for interventional/technique-based modalities
        inferred_modality_patterns = {
        'IR': re.compile(r'\b(ir|interventional|xa|angiography|angiogram|dsa|picc|biopsy|drainage|stent)\b', re.I),
        # Add other inferred modalities here if needed
        }

        for modality, pattern in inferred_modality_patterns.items():
            if pattern.search(lower_name):
                return modality
    
        # Final fallback to the provided modality code
        return self.modality_map.get(str(modality_code).upper(), 'Other') if modality_code else 'Other'

    def _parse_laterality(self, lower_name: str) -> List[str]:
        """Extracts laterality information using the LateralityDetector."""
        detected = self.laterality_detector.detect(lower_name) if self.laterality_detector else None
        return [detected] if detected else []

    def _parse_contrast(self, lower_name: str) -> List[str]:
        """Extracts contrast information using the ContrastMapper."""
        # This now expects pre-normalized tokens like 'WITH_CONTRAST'
        detected = self.contrast_mapper.detect_contrast(lower_name) if self.contrast_mapper else None
        return [detected] if detected else []

    def _parse_technique(self, lower_name: str) -> List[str]:
        """Identifies specific techniques based on predefined regex patterns."""
        techniques = {
            tech for tech, patterns in self.technique_patterns.items()
            if any(p.search(lower_name) for p in patterns)
        }
        return sorted(list(techniques))

    def _build_clean_name(self, parsed: Dict) -> str:
        """Constructs a simple, standardized name from the parsed components."""
        parts = [parsed.get('modality', 'Unknown')]
        
        techniques = parsed.get('technique', [])
        # Add "Angiogram" to the clean name if it's a vascular procedure for clarity
        if 'Vascular Interventional' in techniques:
            parts.append("Angiogram")
        
        if parsed.get('anatomy'):
            parts.append(" ".join(sorted(list(set(parsed['anatomy'])))))
        
        if parsed.get('laterality'):
            # Abbreviate laterality for a cleaner name
            lat_map = {'left': 'Lt', 'right': 'Rt', 'bilateral': 'Both'}
            parts.append(lat_map.get(parsed['laterality'][0], parsed['laterality'][0].capitalize()))

        return " ".join(part for part in parts if part).strip()

    

# --- END OF FILE parser.py ---
