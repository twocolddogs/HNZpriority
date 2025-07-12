import re
from collections import defaultdict
from typing import Dict, List, Optional, Set
from comprehensive_preprocessor import AnatomyExtractor, LateralityDetector, USAContrastMapper

class RadiologySemanticParser:
    """
    A Python parser that standardizes radiology exam names by extracting key
    components using a hybrid approach. It combines NLP-extracted entities
    with a robust, regex-based rule system for high accuracy.
    """
    def __init__(self, nlp_processor=None, anatomy_extractor=None, laterality_detector=None, contrast_mapper=None):
        self.nlp_processor = nlp_processor
        self.anatomy_extractor = anatomy_extractor
        self.laterality_detector = laterality_detector
        self.contrast_mapper = contrast_mapper

        # --- Mappings and Patterns ---
        # Modality map remains as it's a direct mapping of codes
        self.modality_map = {'CT': 'CT', 'MR': 'MRI', 'MRI': 'MRI', 'XR': 'XR', 'US': 'US', 'NM': 'NM', 'PET': 'PET', 'MG': 'Mammography', 'Mammo':'Mammography', 'DEXA': 'DEXA', 'FL': 'Fluoroscopy', 'IR': 'IR', 'Other': 'Other', 'BR': 'Mammography'}
        
        self.technique_patterns = {
            'Angiography': [re.compile(p, re.I) for p in [r'angiogram', r'angiography', r'\bcta\b', r'\bmra\b', r'venogram', r'angio']],
            'HRCT': [re.compile(p, re.I) for p in [r'hrct', r'high resolution']],
            'Colonography': [re.compile(p, re.I) for p in [r'colonography', r'virtual colonoscopy']],
            'Doppler': [re.compile(p, re.I) for p in [r'doppler', r'duplex']],
            'Intervention': [re.compile(p, re.I) for p in [r'biopsy', r'drainage', 'aspir', r'injection', r'guided', r'procedure', 'ablation', 'placement', 'loc', 'bx']],
        }
        
        # Build anatomy lookup from AnatomyExtractor
        self.anatomy_lookup = {}
        self.anatomy_standard_names = {}
        if self.anatomy_extractor:
            for term, standard_name in self.anatomy_extractor.anatomy_terms.items():
                self.anatomy_lookup[term] = standard_name
                self.anatomy_standard_names[standard_name] = standard_name # Store unique standard names
        
        # Sort terms by length (desc) to match longer phrases first
        self.sorted_anatomy_terms = sorted(self.anatomy_lookup.keys(), key=len, reverse=True)

    def parse_exam_name(self, exam_name: str, modality_code: str) -> Dict:
        """
        Parses a radiology exam name using a hybrid approach combining NLP entities 
        with rule-based matching for maximum accuracy.

        Args:
            exam_name: The raw exam name string.
            modality_code: The modality code (e.g., 'CT', 'MR').

        Returns:
            A dictionary containing the parsed components.
        """
        lower_name = exam_name.lower()
        
        # --- Step 1: Hybrid Anatomy Parsing --- 
        nlp_anatomy_terms = []
        scispacy_entities = {}
        if self.nlp_processor:
            scispacy_entities = self.nlp_processor.extract_entities(exam_name)
            nlp_anatomy_terms = [term.lower() for term in scispacy_entities.get('ANATOMY', [])]

        found_anatomy_keys = self._parse_anatomy_hybrid(lower_name, nlp_anatomy_terms)
        
        # --- Step 2: Parse Other Components ---
        parsed = {
            'modality': self._parse_modality(lower_name, modality_code),
            'anatomy': sorted(list(found_anatomy_keys)),
            'laterality': self._parse_laterality(lower_name, scispacy_entities),
            'contrast': self._parse_contrast(lower_name),
            'technique': self._parse_technique(lower_name),
        }
        
        # Step 3: Post-processing and Confidence Calculation
        result = {
            'cleanName': self._build_clean_name(parsed),
            'confidence': self._calculate_confidence(parsed, exam_name),
            **parsed
        }
        
        return result

    def _parse_anatomy_hybrid(self, lower_name: str, nlp_terms: List[str]) -> Set[str]:
        """Uses precise longest-match-first rule-based anatomy extraction for maximum accuracy."""
        found_keys: Set[str] = set()
        
        # Use rule-based matching with longest-match-first logic
        # This is crucial for compound terms like 'cervical spine' vs 'spine'
        for term_key in self.sorted_anatomy_terms:
            if term_key in lower_name:
                found_keys.add(self.anatomy_lookup[term_key])
                
        return found_keys

    def _parse_modality(self, lower_name: str, modality_code: str) -> str:
        """Parse modality from exam name first, fall back to modality_code."""
        # Priority 1: Parse from exam name for clear modality indicators
        modality_patterns = {
            'CT': re.compile(r'\b(ct|computed tomography)\b', re.I),
            'MRI': re.compile(r'\b(mr|mri|magnetic resonance)\b', re.I),
            'XR': re.compile(r'\b(xr|x-ray|radiograph|plain film)\b', re.I),
            'US': re.compile(r'\b(us|ultrasound|sonogram)\b', re.I),
            'NM': re.compile(r'\b(nm|nuclear medicine|spect|scintigraphy)\b', re.I),
            'PET': re.compile(r'\b(pet|positron emission)\b', re.I),
            'Mammography': re.compile(r'\b(mg|mammo|mammography|breast)\b', re.I),
            'Fluoroscopy': re.compile(r'\b(fl|fluoroscopy|screening)\b', re.I),
            'DEXA': re.compile(r'\b(dexa|bone density)\b', re.I)
        }
        
        # Check exam name for modality indicators
        for modality, pattern in modality_patterns.items():
            if pattern.search(lower_name):
                return modality
        
        # Priority 2: Use provided modality_code if no clear indication in name
        if modality_code and modality_code.upper() in self.modality_map:
            return self.modality_map[modality_code.upper()]
        
        # Priority 3: Default fallback
        return modality_code or 'Other'

    def _parse_laterality(self, lower_name: str, scispacy_entities: Dict) -> Optional[str]:
        """Parse laterality using the dedicated LateralityDetector."""
        if self.laterality_detector:
            return self.laterality_detector.detect(lower_name)
        return None

    def _parse_contrast(self, lower_name: str) -> Optional[str]:
        """Parse contrast status using the dedicated USAContrastMapper."""
        if self.contrast_mapper:
            return self.contrast_mapper.detect_contrast(lower_name)
        return None

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
        
        if parsed['anatomy']:
            # A simple join is effective. More complex ordering could be added.
            parts.append(" ".join(parsed['anatomy']))
        else:
            parts.append("Unknown Anatomy")

        if 'Angiography' in parsed['technique']:
            parts.append("Angiography")

        if parsed['laterality']:
            parts.append(parsed['laterality'])
            
        clean_name = " ".join(parts)

        if parsed['contrast']:
            if parsed['contrast'] == 'with and without':
                clean_name += " with/without Contrast"
            elif parsed['contrast'] == 'with':
                 clean_name += " with Contrast"
            elif parsed['contrast'] == 'without':
                 clean_name += " without Contrast"
                 
        return clean_name.strip()

    def _calculate_confidence(self, result: Dict, original_exam_name: str) -> float:
        """Calculates a confidence score based on the completeness of the parse."""
        score = 0.5  # Base confidence

        if result.get('anatomy'):
            score += 0.25
        if result.get('modality') != 'Unknown':
            score += 0.1
        if result.get('contrast'):
            score += 0.1
        if result.get('laterality'):
            score += 0.05
        
        # Penalty for very short names which are often ambiguous
        if len(original_exam_name.split()) < 3:
            score -= 0.1
            
        return max(0.1, min(1.0, round(score, 2)))
