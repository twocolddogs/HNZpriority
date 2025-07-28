# --- START OF FILE parser.py ---

# =============================================================================
# RADIOLOGY SEMANTIC PARSER (V2.9 - HYBRID & GRANULAR DETECTION)
# =============================================================================
# This module is responsible for breaking down a cleaned radiology exam name
# into its constituent semantic components. This enhanced version features:
# - Detection of multiple modalities for hybrid imaging (e.g., PET/CT).
# - More granular technique detection to differentiate diagnostic from
#   interventional procedures and identify specific NM/Fluoro studies.

import re
from typing import Dict, List, Optional
from parsing_utils import AnatomyExtractor, LateralityDetector, ContrastMapper

class RadiologySemanticParser:
    """
    Parses a cleaned radiology exam name into a structured dictionary of components.
    
    It leverages utility classes to extract specific features and uses regex patterns
    to identify modality and specialized techniques. The output of this parser is a
    key input for the NHSLookupEngine's scoring algorithm, providing a rich,
    structured representation of the exam's clinical intent.
    """
    def __init__(self, nlp_processor=None, anatomy_extractor=None, laterality_detector=None, contrast_mapper=None):
        """
        Initializes the parser with necessary utility components and pre-compiled regex patterns.

        Why: Pre-compiling regex patterns in the constructor is a performance optimization.
             This method sets up all the rules and definitions the parser will use for its analysis.

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
            'PET': 'NM', 'MG': 'MG', 'MAMM': 'MG', 'MAMMO': 'MG', 'DEXA': 'DEXA', 
            'FL': 'Fluoroscopy', 
            'IR': 'IR',
            'XA': 'IR',
            'Other': 'Other', 'BR': 'MG'
        }
        
        # MODIFICATION: Expanded and split patterns for better granularity. This allows
        # the scoring engine to differentiate between various procedure types with
        # much higher precision.
        self.technique_patterns = {
            # Core Modality-Specific Techniques
            'MRCP': [re.compile(p, re.I) for p in [r'\b(mrcp|magnetic resonance cholangiopancreatography|cholangiopancreatography)\b']],
            'HRCT': [re.compile(p, re.I) for p in [r'\b(hrct|high resolution)\b']],
            'Colonography': [re.compile(p, re.I) for p in [r'\b(colonography|virtual colonoscopy)\b']],
            'Doppler': [re.compile(p, re.I) for p in [r'\b(doppler|duplex)\b']],
            'Tomosynthesis': [re.compile(p, re.I) for p in [r'\b(tomosynthesis|tomo)\b']],
            
            # ENHANCED: Fluoroscopy and GI studies are now more inclusive.
            'Fluoroscopic GI/Swallow Study': [re.compile(p, re.I) for p in [
                r'\b(barium|upper gi|lower gi|swallow|meal|enema|videofluoroscopy)\b'
            ]],
            
            # NEW: Specific Nuclear Medicine techniques for better differentiation.
            'SPECT': [re.compile(p, re.I) for p in [r'\b(spect|single photon)\b']],
            'V/Q Scan': [re.compile(p, re.I) for p in [r'\b(v/q|ventilation perfusion)\b']],
            
            # NEW: Differentiating diagnostic vascular from therapeutic interventional.
            'Diagnostic Angiography': [re.compile(p, re.I) for p in [
                r'\b(angiogram|angiography|arteriogram|arteriography|angio|dsa)\b'
            ]],
            
            # Interventional Categories (now more focused on therapeutic/procedural actions).
            'Arterial Interventional': [re.compile(p, re.I) for p in [
                r'\b(stent|angioplasty|emboli[sz]ation|thrombolysis|thrombectomy|atherectomy)\b',
                r'\b(arterial|artery|aortic|aorta|carotid|femoral artery|renal artery)\b'
            ]],
            'Venous Interventional': [re.compile(p, re.I) for p in [
                r'\b(venography|venogram|phlebography)\b',
                r'\b(picc|line|catheter|port|hickman|tunneled)\b',
                r'\b(venous|vein|vena cava|jugular|subclavian|femoral vein)\b',
                r'\b(ivc filter|vena cava filter|thrombolysis venous)\b'
            ]],
            'Non-Vascular Interventional': [re.compile(p, re.I) for p in [
                r'\b(biopsy|bx|fna|drainage|aspirat|injection|vertebroplasty|ablation|guided|guidance|placement|locali[sz]ation)\b',
                r'\b(?!.*\b(?:picc|line|catheter)\b)(insertion|insert)\b'
            ]],

            # Specific PET Tracers (for advanced NM classification).
            '18F-FDG PET': [re.compile(p, re.I) for p in [
                r'\b(fdg|18f.?fdg|f.?18.?fdg|fluorodeoxyglucose|18f.?fluorodeoxyglucose|fludeoxyglucose)\b'
            ]],
            '18F-PSMA PET': [re.compile(p, re.I) for p in [
                r'\b(psma|18f.?psma|f.?18.?psma|prostate.?specific.?membrane.?antigen)\b',
                r'\b(18f.?dcfpyl|dcfpyl|18f.?pyl|pyl)\b'
            ]],
            'Gallium-68 PET': [re.compile(p, re.I) for p in [
                r'\b(ga.?68|gallium.?68|68.?ga|68.?gallium)\b',
                r'\b(ga.?68.?dotatate|dotatate|ga.?68.?dotanoc|dotanoc|ga.?68.?dotatoc|dotatoc)\b',
                r'\b(ga.?68.?psma|68.?ga.?psma)\b'
            ]]
        }

    def parse_exam_name(self, exam_name: str, modality_code: str) -> Dict:
        """
        Executes the full parsing pipeline on a single cleaned exam name.

        Why: This is the main entry point for the parser. It orchestrates the calls to
             the various private parsing methods in the correct sequence and assembles
             the final structured output.

        Args:
            exam_name: The preprocessed exam name string.
            modality_code: The original modality code from the source data (used as a fallback).
            
        Returns:
            A dictionary containing the parsed components and a generated clean name.
        """
        lower_name = exam_name.lower()
        anatomy = self.anatomy_extractor.extract(lower_name) if self.anatomy_extractor else []
        
        # The parsed dictionary holds the structured output of each component.
        parsed = {
            'modality': self._parse_modality(lower_name, modality_code),
            'anatomy': anatomy,
            'laterality': self._parse_laterality(lower_name),
            'contrast': self._parse_contrast(lower_name),
            'technique': self._parse_technique(lower_name),
        }
        
        # The final output includes both the parsed components and a constructed
        # standardized name for display or logging purposes.
        return {
            'clean_name': self._build_clean_name(parsed),
            **parsed
        }

    def _parse_modality(self, lower_name: str, modality_code: str) -> List[str]:
        """
        Determines modalities, prioritizing input modality_code over text parsing.

        Why: The input modality_code is the authoritative source from the data system,
             and should take priority over text parsing which may be ambiguous.
             Text parsing is used as fallback for missing or 'OTHER' modality codes.

        Args:
            lower_name: The lowercased, cleaned exam name.
            modality_code: The original modality code from source data (priority source).

        Returns:
            A list of identified modality strings (e.g., ['XR']).
        """
        # A single, prioritized list of patterns to detect modalities.
        # Hybrid patterns are first to ensure both components are captured.
        MODALITY_PATTERNS = [
            # Hybrid Imaging (Highest Priority) - These patterns match both modalities.
            ('NM', re.compile(r'\b(pet[/\- ]?ct|spect[/\- ]?ct)\b', re.I)),
            ('CT', re.compile(r'\b(pet[/\- ]?ct|spect[/\- ]?ct)\b', re.I)),
            ('NM', re.compile(r'\b(pet[/\- ]?mr|spect[/\- ]?mr)\b', re.I)),
            ('MRI', re.compile(r'\b(pet[/\- ]?mr|spect[/\- ]?mr)\b', re.I)),
            
            # Interventional/Fluoroscopy
            ('IR', re.compile(r'\b(x-ray angiography|biopsy|drainage|stent|intervention|picc|insert)\b', re.I)),
            ('Fluoroscopy', re.compile(r'\b(fl|fluoroscopy|barium|swallow|meal|enema|videofluoroscopy|image intensifier)\b', re.I)),

            # Primary Modalities (Ordered from more to less specific to avoid conflicts)
            ('DEXA', re.compile(r'\b(dexa|dxa|bone densitometry)\b', re.I)),
            ('MRI', re.compile(r'\b(mr|mri|mra|magnetic resonance)\b', re.I)),
            ('MG', re.compile(r'\b(mg|mammo|mamm|mammography|tomosynthesis)\b', re.I)),
            ('US', re.compile(r'\b(us|ultrasound|sonogram|doppler|duplex)\b', re.I)),
            ('NM', re.compile(r'\b(nm|nuclear medicine|spect|scintigraphy|pet|v/q|mag3|renogram)\b', re.I)),
            ('CT', re.compile(r'\b(ct|computed tomography)\b', re.I)),
            ('XR', re.compile(r'\b(xr|x-ray|xray|radiograph|plain film)\b', re.I)),
        ]

        # FIRST: Check input modality_code (highest priority)
        if modality_code and modality_code.upper() != 'OTHER':
            input_modality = self.modality_map.get(str(modality_code).upper())
            if input_modality:
                return [input_modality]

        # SECOND: Parse from exam name text if input modality unavailable
        found_modalities = []
        for modality, pattern in MODALITY_PATTERNS:
            if pattern.search(lower_name):
                if modality not in found_modalities:  # Avoid adding duplicates
                    found_modalities.append(modality)

        # If text parsing found any modalities, return them.
        if found_modalities:
            return sorted(list(set(found_modalities)))

        # Final fallback if both input modality and text parsing failed
        return []


    def _parse_laterality(self, lower_name: str) -> List[str]:
        """
        Extracts laterality information using the LateralityDetector utility.

        Why: Laterality (left, right, bilateral) is a critical component for patient safety
             and accurate procedure mapping. This delegates the task to a specialized class.

        Args:
            lower_name: The lowercased, cleaned exam name.

        Returns:
            A list containing the detected laterality string, or an empty list if none found.
        """
        detected = self.laterality_detector.detect(lower_name) if self.laterality_detector else None
        return [detected] if detected else []

    def _parse_contrast(self, lower_name: str) -> List[str]:
        """
        Extracts contrast information using the ContrastMapper utility.

        Why: Contrast usage is a key differentiator between exam types and has significant
             clinical and billing implications. This delegates the task to a specialized class.

        Args:
            lower_name: The lowercased, cleaned exam name.

        Returns:
            A list containing the detected contrast status, or an empty list if none found.
        """
        if self.contrast_mapper:
            return self.contrast_mapper.detect_contrast(lower_name)
        return []

    def _parse_technique(self, lower_name: str) -> List[str]:
        """
        Identifies specific techniques based on predefined regex patterns.

        Why: This provides a deeper level of clinical specificity beyond just modality and
             anatomy (e.g., differentiating a standard 'MRI Brain' from an 'MRCP'). This
             granularity is vital for accurate matching of complex procedures.

        Args:
            lower_name: The lowercased, cleaned exam name.

        Returns:
            A sorted list of unique technique names found in the text.
        """
        techniques = {
            tech for tech, patterns in self.technique_patterns.items()
            if any(p.search(lower_name) for p in patterns)
        }
        return sorted(list(techniques))

    def _build_clean_name(self, parsed: Dict) -> str:
        """
        Constructs a simple, standardized name from the parsed components.

        Why: This creates a consistent, human-readable representation of the parsed exam,
             which is useful for logging, debugging, and final output.

        Args:
            parsed: The dictionary of parsed components.

        Returns:
            A standardized, space-separated string.
        """
        # Join multiple modalities with a '+' for clarity in hybrid scans (e.g., "NM+CT").
        modality_str = "+".join(sorted(list(set(parsed.get('modality', []))))) or 'Unknown'
        parts = [modality_str]
        
        techniques = parsed.get('technique', [])
        # Add "Angiogram" to the clean name if it's a vascular procedure for clarity
        if 'Diagnostic Angiography' in techniques:
            parts.append("Angiogram")
        
        if parsed.get('anatomy'):
            parts.append(" ".join(sorted(list(set(parsed['anatomy'])))))
        
        if parsed.get('laterality'):
            # Abbreviate laterality for a cleaner name
            lat_map = {'left': 'Lt', 'right': 'Rt', 'bilateral': 'Both'}
            lat = parsed['laterality'][0]
            parts.append(lat_map.get(lat, lat.capitalize()))

        return " ".join(part for part in parts if part).strip()

# --- END OF FILE parser.py ---
