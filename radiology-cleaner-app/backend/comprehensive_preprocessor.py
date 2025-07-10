import re
import json
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher


class ModalityExtractor:
    """Extract modality from exam names with high accuracy"""
    
    def __init__(self):
        # Comprehensive modality patterns with aliases and variations
        self.modality_patterns = {
            'CT': [
                r'\bCT\b',
                r'\bComputed Tomography\b',
                r'\bCAT\b',
                r'\bCTA\b',  # CT Angiography
                r'\bCTPA\b',  # CT Pulmonary Angiogram
                r'\bCCTA\b',  # Cardiac CT Angiography
            ],
            'MRI': [
                r'\bMRI\b',
                r'\bMR\b(?!\s*[A-Z])',  # MR but not MRI-related abbreviations
                r'\bMagnetic Resonance\b',
                r'\bMRA\b',  # MR Angiography
                r'\bMRV\b',  # MR Venography
                r'\bfMRI\b',  # Functional MRI
                r'\bDWI\b',  # Diffusion Weighted Imaging
            ],
            'US': [
                r'\bUS\b',
                r'\bUltrasound\b',
                r'\bUltra-sound\b',
                r'\bSonogram\b',
                r'\bEcho\b',
                r'\bDoppler\b',
                r'\bCDUS\b',  # Color Doppler US
            ],
            'XR': [
                r'\bXR\b',
                r'\bX-Ray\b',
                r'\bXray\b',
                r'\bRadiograph\b',
                r'\bPlain Film\b',
                r'\bCXR\b',  # Chest X-ray
                r'\bAXR\b',  # Abdominal X-ray
                r'\bKUB\b',  # Kidneys, Ureters, Bladder
                r'\bsingle projection\b',  # Common XR term
                r'\btwo views?\b',  # Two view X-ray
                r'\bAP and lateral\b',  # Standard X-ray views
                r'\bplain radiograph\b',
                r'\bbone film\b',
            ],
            'NM': [
                r'\bNM\b',
                r'\bNuclear Medicine\b',
                r'\bScintigraphy\b',
                r'\bSPECT\b',
                r'\bGamma Camera\b',
                r'\bBone Scan\b',
                r'\bThyroid Scan\b',
            ],
            'PET': [
                r'\bPET\b',
                r'\bPositron Emission\b',
                r'\bPET-CT\b',
                r'\bPET/CT\b',
                r'\bFDG-PET\b',
            ],
            'Mammography': [
                r'\bMamm\b',
                r'\bMammography\b',
                r'\bMammogram\b',
                r'\bBreast\b(?=.*(?:imaging|screen|exam))',
                r'\bTomosynthesis\b',
                r'\bDBT\b',  # Digital Breast Tomosynthesis
            ],
            'DEXA': [
                r'\bDEXA\b',
                r'\bDXA\b',
                r'\bBone Density\b',
                r'\bDensitometry\b',
                r'\bOsteoporosis\b(?=.*scan)',
            ],
            'Fluoroscopy': [
                r'\bFluoro\b',
                r'\bFluoroscopy\b',
                r'\bBarium\b',
                r'\bSwallow\b(?=.*study)',
                r'\bUGI\b',  # Upper GI
                r'\bSBFT\b',  # Small Bowel Follow Through
            ],
            'IR': [
                r'\bIR\b',
                r'\bInterventional\b',
                r'\bAngioplasty\b',
                r'\bEmbolization\b',
                r'\bStent\b',
                r'\bBiopsy\b(?=.*guided)',
            ]
        }
        
        # Compile patterns for efficiency
        self.compiled_patterns = {}
        for modality, patterns in self.modality_patterns.items():
            self.compiled_patterns[modality] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def extract(self, text: str) -> Optional[str]:
        """Extract modality from text with confidence scoring"""
        text = text.strip()
        modality_scores = {}
        
        for modality, patterns in self.compiled_patterns.items():
            score = 0
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    # Higher score for exact matches at word boundaries
                    if pattern.search(text.split()[0] if text.split() else ''):
                        score += 10  # First word gets highest priority
                    else:
                        score += len(matches) * 5
            
            if score > 0:
                modality_scores[modality] = score
        
        # Return modality with highest score
        if modality_scores:
            return max(modality_scores.items(), key=lambda x: x[1])[0]
        
        return None


class LateralityDetector:
    """Detect laterality (left, right, bilateral) from exam names"""
    
    def __init__(self):
        self.patterns = {
            'Bilateral': [
                r'\b(?:bilateral|bilat|both|b/l)\b',
                r'\b(?:rt?\.?\s*(?:and|&|\+)\s*lt?\.?)\b',
                r'\b(?:right\s*(?:and|&|\+)\s*left)\b',
                r'\b(?:left\s*(?:and|&|\+)\s*right)\b',
            ],
            'Left': [
                r'\b(?:left|lt?\.?)\b(?!\s*(?:and|&|\+))',
                r'\b(?:l)\b(?=\s+(?:shoulder|knee|hip|elbow|hand|foot|ankle|wrist))',
            ],
            'Right': [
                r'\b(?:right|rt?\.?)\b(?!\s*(?:and|&|\+))',
                r'\b(?:r)\b(?=\s+(?:shoulder|knee|hip|elbow|hand|foot|ankle|wrist))',
            ]
        }
        
        # Compile patterns
        self.compiled_patterns = {}
        for laterality, patterns in self.patterns.items():
            self.compiled_patterns[laterality] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def detect(self, text: str) -> Optional[str]:
        """Detect laterality from text"""
        text_lower = text.lower()
        
        # Check bilateral first (more specific)
        for pattern in self.compiled_patterns['Bilateral']:
            if pattern.search(text_lower):
                return 'Bilateral'
        
        # Then check left/right
        for laterality in ['Left', 'Right']:
            for pattern in self.compiled_patterns[laterality]:
                if pattern.search(text_lower):
                    return laterality
        
        return None


class GenderContextDetector:
    """Detect gender context from exam names"""
    
    def __init__(self):
        self.patterns = {
            'male': [
                r'\b(?:male|man|men)\b',
                r'\b(?:prostate|prostatic)\b',
                r'\b(?:male\s+pelvis)\b',
                r'\b(?:testicular|scrotal)\b',
            ],
            'female': [
                r'\b(?:female|woman|women)\b',
                r'\b(?:gynaecolog|gynecolog)\b',
                r'\b(?:mammograph|breast)\b',
                r'\b(?:ovarian|uterine|cervical)\b',
                r'\b(?:female\s+pelvis)\b',
                r'\b(?:pelvic)\b(?=.*(?:female|gyn))',
            ],
            'pregnancy': [
                r'\b(?:pregnant|pregnancy)\b',
                r'\b(?:obstetric|maternal)\b',
                r'\b(?:fetal|foetal)\b',
                r'\b(?:antenatal|prenatal)\b',
                r'\b(?:gravid)\b',
            ]
        }
        
        # Compile patterns
        self.compiled_patterns = {}
        for gender, patterns in self.patterns.items():
            self.compiled_patterns[gender] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def detect(self, text: str) -> Optional[str]:
        """Detect gender context from text"""
        for gender, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    return gender
        return None


class PaediatricDetector:
    """Detect paediatric studies from exam names"""
    
    def __init__(self):
        self.patterns = [
            r'\b(?:paed|ped|pediatric|paediatric)\b',
            r'\b(?:child|children|infant|baby)\b',
            r'\b(?:neonat|newborn)\b',
            r'\b(?:juvenile|adolescent)\b',
            r'\b(?:yr?s?\s*old|year\s*old)\b',  # Age indicators
            r'\b(?:[0-9]+\s*(?:month|week|day)\s*old)\b',
        ]
        
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.patterns]
    
    def detect(self, text: str) -> bool:
        """Detect if exam is paediatric"""
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                return True
        return False


class USAContrastMapper:
    """Enhanced contrast detection with USA conventions"""
    
    def __init__(self):
        self.patterns = {
            'with and without': [
                r'\bw\s*and\s*wo\b',
                r'\bw/wo\b',
                r'\bw\+/-\b',
                r'\bwith\s*and\s*without\b',
                r'\bpre\s*and\s*post\b',
                r'\bpre\s*&\s*post\b',
            ],
            'with': [
                r'\bw\s+(?:contrast|iv|gad)\b',
                r'\bw\b(?!\s*(?:and|wo|/wo))',  # w but not w and wo
                r'\bwith\s+contrast\b',
                r'\benhanced\b',
                r'\bpost\s*contrast\b',
                r'\bpost\s*gad\b',
                r'\bc\+\b',
            ],
            'without': [
                r'\bwo\s+(?:contrast|iv)\b',
                r'\bwo\b(?!\s*and)',  # wo but not wo and
                r'\bwithout\s+contrast\b',
                r'\bnon\s*contrast\b',
                r'\bunenhanced\b',
                r'\bplain\b',
                r'\bc-\b',
            ]
        }
        
        # Compile patterns in order of specificity
        self.compiled_patterns = {}
        for contrast_type, patterns in self.patterns.items():
            self.compiled_patterns[contrast_type] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def detect_contrast(self, text: str) -> Optional[str]:
        """Detect contrast type with USA conventions"""
        # Check in order of specificity (most specific first)
        for contrast_type in ['with and without', 'with', 'without']:
            for pattern in self.compiled_patterns[contrast_type]:
                if pattern.search(text):
                    return contrast_type
        return None


class AbbreviationExpander:
    """Comprehensive abbreviation expansion"""
    
    def __init__(self, usa_patterns: Dict = None):
        self.usa_abbreviations = usa_patterns.get('common_abbreviations', {}) if usa_patterns else {}
        
        # Medical abbreviations from radiology
        self.medical_abbreviations = {
            # Anatomy
            'abd': 'abdomen',
            'abdo': 'abdomen',
            'pelv': 'pelvis',
            'ext': 'extremity',
            'ue': 'upper extremity',
            'le': 'lower extremity',
            'lle': 'left lower extremity',
            'rle': 'right lower extremity',
            'rue': 'right upper extremity',
            'lue': 'left upper extremity',
            
            # Modality
            'cta': 'ct angiography',
            'mra': 'mr angiography',
            'ctpa': 'ct pulmonary angiography',
            'cxr': 'chest xray',
            'axr': 'abdominal xray',
            'kub': 'kidneys ureters bladder',
            
            # Contrast
            'w': 'with',
            'wo': 'without',
            'gad': 'gadolinium',
            'iv': 'intravenous',
            
            # Gender/Age
            'm': 'male',
            'f': 'female',
            'paed': 'paediatric',
            'ped': 'pediatric',
            
            # Laterality
            'rt': 'right',
            'lt': 'left',
            'bil': 'bilateral',
            'bilat': 'bilateral',
            'r': 'right',
            'l': 'left',
            
            # Common terms
            'angio': 'angiography',
            'venous': 'venography',
            'arterial': 'arteriography',
            'fx': 'fracture',
            'eval': 'evaluation',
            'f/u': 'follow up',
            'post-op': 'post operative',
            'pre-op': 'pre operative',
        }
        
        # Combine all abbreviations
        self.all_abbreviations = {**self.medical_abbreviations, **self.usa_abbreviations}
    
    def expand(self, text: str) -> str:
        """Expand abbreviations in text"""
        words = text.split()
        expanded = []
        
        for word in words:
            # Clean word (remove punctuation for lookup)
            clean_word = word.lower().rstrip('.,()[]')
            
            if clean_word in self.all_abbreviations:
                expanded.append(self.all_abbreviations[clean_word])
            else:
                expanded.append(word)
        
        return ' '.join(expanded)


class AnatomyExtractor:
    """Extract anatomy using NHS authority and USA patterns"""
    
    def __init__(self, nhs_authority: Dict, usa_patterns: Dict = None):
        self.nhs_authority = nhs_authority
        self.usa_patterns = usa_patterns or {}
        
        # Build anatomy vocabulary from NHS data
        self.anatomy_terms = self._build_anatomy_vocabulary()
    
    def _build_anatomy_vocabulary(self) -> Dict[str, str]:
        """Build comprehensive anatomy vocabulary from NHS clean names"""
        anatomy_vocab = {}
        
        # Extract anatomy from NHS clean names
        for clean_name in self.nhs_authority.keys():
            parts = clean_name.split()
            if len(parts) > 1:
                # Everything after modality is anatomy
                anatomy = ' '.join(parts[1:]).lower()
                anatomy_vocab[anatomy] = anatomy
                
                # Add individual words
                for word in parts[1:]:
                    if len(word) > 2:  # Skip short words
                        anatomy_vocab[word.lower()] = word.lower()
        
        # Add common variations
        anatomy_vocab.update({
            'head': 'head',
            'brain': 'head',
            'skull': 'head',
            'chest': 'chest',
            'thorax': 'chest',
            'lung': 'chest',
            'abdomen': 'abdomen',
            'belly': 'abdomen',
            'tummy': 'abdomen',
            'pelvis': 'pelvis',
            'hip': 'hip',
            'spine': 'spine',
            'back': 'spine',
        })
        
        return anatomy_vocab
    
    def extract(self, text: str) -> List[str]:
        """Extract anatomy terms from text"""
        text_lower = text.lower()
        found_anatomy = set()
        
        # Look for anatomy terms
        for term, standard_form in self.anatomy_terms.items():
            if term in text_lower:
                found_anatomy.add(standard_form)
        
        return sorted(list(found_anatomy))


class ComprehensivePreprocessor:
    """Complete preprocessing pipeline for radiology exam names"""
    
    def __init__(self, nhs_json_path: str, usa_json_path: str = None):
        # Load data
        with open(nhs_json_path) as f:
            nhs_data = json.load(f)
        
        usa_patterns = {}
        if usa_json_path:
            with open(usa_json_path) as f:
                usa_data = json.load(f)
            usa_patterns = self._extract_usa_patterns(usa_data)
        
        # Build NHS authority
        self.nhs_authority = {}
        for item in nhs_data:
            clean_name = item['Clean Name']
            self.nhs_authority[clean_name] = {
                'snomed_concept_id': item.get('SNOMED CT \nConcept-ID', ''),
                'snomed_fsn': item.get('SNOMED CT FSN', ''),
                'snomed_laterality_id': item.get('SNOMED CT Concept-ID of Laterality', ''),
                'snomed_laterality_fsn': item.get('SNOMED FSN of Laterality', ''),
                'is_diagnostic': item.get('Diagnostic procedure', '') == 'Y',
                'is_interventional': item.get('Interventional Procedure', '') == 'Y'
            }
        
        # Initialize all extractors
        self.abbreviation_expander = AbbreviationExpander(usa_patterns)
        self.modality_extractor = ModalityExtractor()
        self.anatomy_extractor = AnatomyExtractor(self.nhs_authority, usa_patterns)
        self.laterality_detector = LateralityDetector()
        self.contrast_mapper = USAContrastMapper()
        self.gender_detector = GenderContextDetector()
        self.paediatric_detector = PaediatricDetector()
    
    def _extract_usa_patterns(self, usa_data: List[Dict]) -> Dict:
        """Extract patterns from USA JSON data"""
        patterns = {
            'common_abbreviations': {},
            'anatomy_variants': defaultdict(set),
            'contrast_patterns': {}
        }
        
        for item in usa_data:
            short_name = item.get('SHORT_NAME', '')
            long_name = item.get('LONG_NAME', '')
            
            # Extract abbreviations
            if short_name and long_name:
                short_words = short_name.split()
                long_words = long_name.split()
                
                for short_word in short_words:
                    if len(short_word) <= 4:  # Likely abbreviation
                        for long_word in long_words:
                            if long_word.lower().startswith(short_word.lower()):
                                patterns['common_abbreviations'][short_word.lower()] = long_word.lower()
        
        return patterns
    
    def preprocess_exam_name(self, exam_name: str, provided_modality: str = None) -> Dict:
        """Complete preprocessing pipeline"""
        original = exam_name.strip()
        
        # Step 1: Expand abbreviations
        expanded = self.abbreviation_expander.expand(original)
        
        # Step 2: Extract all components
        # Use provided modality first, fall back to extraction
        detected_modality = self.modality_extractor.extract(expanded)
        final_modality = provided_modality or detected_modality
        
        components = {
            'original': original,
            'expanded': expanded,
            'modality': final_modality,
            'detected_modality': detected_modality,  # Keep for debugging
            'provided_modality': provided_modality,  # Keep for debugging
            'anatomy': self.anatomy_extractor.extract(expanded),
            'laterality': self.laterality_detector.detect(expanded),
            'contrast': self.contrast_mapper.detect_contrast(expanded),
            'gender_context': self.gender_detector.detect(expanded),
            'is_paediatric': self.paediatric_detector.detect(expanded)
        }
        
        # Step 3: Try to map to NHS clean names
        nhs_candidates = self._map_to_nhs_clean_names(components)
        
        # Step 4: Calculate confidence
        confidence = self._calculate_confidence(components, nhs_candidates)
        
        return {
            'components': components,
            'nhs_candidates': nhs_candidates,
            'confidence': confidence,
            'best_match': nhs_candidates[0] if nhs_candidates else None
        }
    
    def _map_to_nhs_clean_names(self, components: Dict) -> List[Dict]:
        """Map extracted components to NHS clean names"""
        candidates = []
        
        if not components['modality']:
            return candidates
        
        # Build search patterns
        base_pattern = components['modality']
        if components['anatomy']:
            base_pattern += ' ' + ' '.join(components['anatomy'])
        
        # Add laterality for relevant anatomy
        if components['laterality'] and self._is_laterality_relevant(components['anatomy']):
            base_pattern += ' ' + components['laterality']
        
        # Search NHS authority
        for nhs_clean_name, nhs_data in self.nhs_authority.items():
            similarity = self._calculate_similarity(base_pattern.lower(), nhs_clean_name.lower())
            
            if similarity > 0.6:  # Threshold for candidates
                candidates.append({
                    'clean_name': nhs_clean_name,
                    'similarity': similarity,
                    'snomed_data': nhs_data,
                    'match_pattern': base_pattern
                })
        
        # Sort by similarity
        return sorted(candidates, key=lambda x: x['similarity'], reverse=True)
    
    def _is_laterality_relevant(self, anatomy_list: List[str]) -> bool:
        """Check if laterality is relevant for given anatomy"""
        lateral_anatomy = {
            'shoulder', 'knee', 'hip', 'elbow', 'hand', 'foot', 
            'ankle', 'wrist', 'arm', 'leg', 'thigh', 'calf'
        }
        
        anatomy_str = ' '.join(anatomy_list).lower()
        return any(anat in anatomy_str for anat in lateral_anatomy)
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _calculate_confidence(self, components: Dict, nhs_candidates: List[Dict]) -> float:
        """Calculate overall confidence score"""
        confidence = 0.5  # Base confidence
        
        # Component detection confidence
        if components['modality']:
            confidence += 0.2
        if components['anatomy']:
            confidence += 0.2
        if components['contrast']:
            confidence += 0.1
        
        # NHS match confidence
        if nhs_candidates:
            best_similarity = nhs_candidates[0]['similarity']
            confidence += best_similarity * 0.3
        
        return min(1.0, confidence)


# Usage example
if __name__ == "__main__":
    # Initialize preprocessor
    preprocessor = ComprehensivePreprocessor(
        nhs_json_path="/path/to/NHS.json",
        usa_json_path="/path/to/USA.json"
    )
    
    # Test preprocessing
    test_cases = [
        "CT Abd w contrast",
        "MRI Head wo contrast rt",
        "CXR chest bilateral",
        "US pelvis female",
        "CT chest abdomen pelvis w/wo contrast"
    ]
    
    for test_case in test_cases:
        result = preprocessor.preprocess_exam_name(test_case)
        print(f"\nInput: {test_case}")
        print(f"Components: {result['components']}")
        print(f"Best Match: {result['best_match']['clean_name'] if result['best_match'] else 'None'}")
        print(f"Confidence: {result['confidence']:.2f}")