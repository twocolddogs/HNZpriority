import re
from collections import defaultdict
from typing import Dict, List, Optional, Set

class RadiologySemanticParser:
    """
    A Python parser that standardizes radiology exam names by extracting key
    components using a hybrid approach. It combines NLP-extracted entities
    with a robust, regex-based rule system for high accuracy.
    """
    def __init__(self, db_manager=None, standardization_engine=None):
        self.db_manager = db_manager
        self.standardization_engine = standardization_engine
        
        # --- Mappings and Patterns ---
        self.anatomy_mappings = {
            'head': {'terms': ['head', 'brain', 'skull', 'cranial', 'cerebral', 'cranium'], 'standardName': 'Head', 'category': 'neurological'},
            'neck': {'terms': ['neck', 'cervical soft tissue', 'pharynx', 'larynx'], 'standardName': 'Neck', 'category': 'head_neck'},
            'sinuses': {'terms': ['sinus', 'sinuses', 'paranasal'], 'standardName': 'Sinuses', 'category': 'head_neck'},
            'temporal_bones': {'terms': ['temporal bone', 'petrous', 'iam', 'internal auditory'], 'standardName': 'Temporal Bones', 'category': 'head_neck'},
            'orbit': {'terms': ['orbit', 'orbital', 'eye'], 'standardName': 'Orbits', 'category': 'head_neck'},
            'facial_bones': {'terms': ['facial bone', 'face', 'maxilla', 'mandible', 'tmj', 'opg'], 'standardName': 'Facial Bones', 'category': 'head_neck'},
            'pituitary': {'terms': ['pituitary', 'sella', 'pituitary fossa'], 'standardName': 'Pituitary', 'category': 'neurological'},
            'c_spine': {'terms': ['cervical spine', 'c spine', 'cspine', 'c-spine'], 'standardName': 'Cervical Spine', 'category': 'spine'},
            't_spine': {'terms': ['thoracic spine', 't spine', 'tspine', 'dorsal spine'], 'standardName': 'Thoracic Spine', 'category': 'spine'},
            'l_spine': {'terms': ['lumbar spine', 'l spine', 'lspine', 'lumbosacral'], 'standardName': 'Lumbar Spine', 'category': 'spine'},
            'sacrum': {'terms': ['sacrum', 'sacral', 'sacrococcygeal', 'coccyx', 'sacroiliac', 'si joint'], 'standardName': 'Sacrum/Coccyx', 'category': 'spine'},
            'whole_spine': {'terms': ['whole spine', 'full spine', 'entire spine', 'spine'], 'standardName': 'Whole Spine', 'category': 'spine'},
            'chest': {'terms': ['chest', 'thorax', 'thoracic', 'lung', 'lungs'], 'standardName': 'Chest', 'category': 'chest'},
            'ribs': {'terms': ['rib', 'ribs', 'thoracic cage'], 'standardName': 'Ribs', 'category': 'chest'},
            'sternum': {'terms': ['sternum', 'sternal'], 'standardName': 'Sternum', 'category': 'chest'},
            'clavicle': {'terms': ['clavicle', 'clavicular', 'acromioclavicular', 'ac joint'], 'standardName': 'Clavicle', 'category': 'chest'},
            'abdomen': {'terms': ['abdomen', 'abdominal', 'abdo'], 'standardName': 'Abdomen', 'category': 'abdomen'},
            'pelvis': {'terms': ['pelvis', 'pelvic'], 'standardName': 'Pelvis', 'category': 'pelvis'},
            'liver': {'terms': ['liver', 'hepatic'], 'standardName': 'Liver', 'category': 'abdomen'},
            'pancreas': {'terms': ['pancreas', 'pancreatic'], 'standardName': 'Pancreas', 'category': 'abdomen'},
            'kidneys': {'terms': ['kidney', 'renal', 'nephro', 'kub'], 'standardName': 'Kidneys', 'category': 'abdomen'},
            'urinary_tract': {'terms': ['bladder', 'ureter', 'urethra', 'urinary', 'urography', 'ctu', 'ivu', 'cystogram'], 'standardName': 'Urinary Tract', 'category': 'genitourinary'},
            'small_bowel': {'terms': ['bowel', 'intestine', 'small bowel', 'enterography', 'enteroclysis'], 'standardName': 'Small Bowel', 'category': 'abdomen'},
            'colon': {'terms': ['colon', 'colonography', 'large bowel'], 'standardName': 'Colon', 'category': 'abdomen'},
            'prostate': {'terms': ['prostate', 'prostatic'], 'standardName': 'Prostate', 'category': 'pelvis'},
            'female_pelvis': {'terms': ['uterus', 'ovary', 'ovarian', 'endometrial', 'female pelvis', 'gynaecology'], 'standardName': 'Female Pelvis', 'category': 'pelvis'},
            'shoulder': {'terms': ['shoulder'], 'standardName': 'Shoulder', 'category': 'musculoskeletal'},
            'humerus': {'terms': ['humerus', 'humeral', 'upper arm', 'arm'], 'standardName': 'Humerus', 'category': 'musculoskeletal'},
            'elbow': {'terms': ['elbow'], 'standardName': 'Elbow', 'category': 'musculoskeletal'},
            'forearm': {'terms': ['forearm', 'radius', 'ulna', 'radial', 'ulnar'], 'standardName': 'Forearm', 'category': 'musculoskeletal'},
            'wrist': {'terms': ['wrist', 'carpal', 'scaphoid'], 'standardName': 'Wrist', 'category': 'musculoskeletal'},
            'hand': {'terms': ['hand', 'metacarpal'], 'standardName': 'Hand', 'category': 'musculoskeletal'},
            'finger': {'terms': ['finger', 'thumb', 'phalanx', 'phalangeal'], 'standardName': 'Finger', 'category': 'musculoskeletal'},
            'hip': {'terms': ['hip', 'acetabulum'], 'standardName': 'Hip', 'category': 'musculoskeletal'},
            'femur': {'terms': ['femur', 'femoral', 'thigh'], 'standardName': 'Femur', 'category': 'musculoskeletal'},
            'knee': {'terms': ['knee', 'patella', 'patellar'], 'standardName': 'Knee', 'category': 'musculoskeletal'},
            'tibia_fibula': {'terms': ['tibia', 'fibula', 'tibial', 'fibular', 'tib fib', 'leg', 'lower extremity'], 'standardName': 'Tibia/Fibula', 'category': 'musculoskeletal'},
            'ankle': {'terms': ['ankle', 'talar', 'talus'], 'standardName': 'Ankle', 'category': 'musculoskeletal'},
            'foot': {'terms': ['foot', 'feet', 'metatarsal', 'tarsal'], 'standardName': 'Foot', 'category': 'musculoskeletal'},
            'toe': {'terms': ['toe', 'toes', 'phalanges'], 'standardName': 'Toe', 'category': 'musculoskeletal'},
            'calcaneus': {'terms': ['calcaneus', 'calcaneum', 'os calcis', 'heel'], 'standardName': 'Calcaneus', 'category': 'musculoskeletal'},
            'aorta': {'terms': ['aorta', 'aortic'], 'standardName': 'Aorta', 'category': 'vascular'},
            'carotid': {'terms': ['carotid'], 'standardName': 'Carotid', 'category': 'vascular'},
            'cerebral_vessels': {'terms': ['circle of willis', 'cow', 'intracranial', 'cerebral vessel'], 'standardName': 'Cerebral Vessels', 'category': 'vascular'},
            'coronary': {'terms': ['coronary', 'cardiac vessel', 'heart vessel'], 'standardName': 'Coronary', 'category': 'vascular'},
            'pulmonary_vessels': {'terms': ['pulmonary artery', 'pulmonary angiogram', 'ctpa', 'pe protocol', 'pulmonary embolus'], 'standardName': 'Pulmonary Vessels', 'category': 'vascular'},
        }
        
        self.modality_map = {'CT': 'CT', 'MR': 'MRI', 'MRI': 'MRI', 'XR': 'XR', 'US': 'US', 'NM': 'NM', 'PET': 'PET', 'MG': 'Mammography', 'Mammo':'Mammography', 'DEXA': 'DEXA', 'FL': 'Fluoroscopy', 'IR': 'IR', 'Other': 'Other', 'BR': 'Mammography'}
        
        self.technique_patterns = {
            'Angiography': [re.compile(p, re.I) for p in [r'angiogram', r'angiography', r'\bcta\b', r'\bmra\b', r'venogram', r'angio']],
            'HRCT': [re.compile(p, re.I) for p in [r'hrct', r'high resolution']],
            'Colonography': [re.compile(p, re.I) for p in [r'colonography', r'virtual colonoscopy']],
            'Doppler': [re.compile(p, re.I) for p in [r'doppler', r'duplex']],
            'Intervention': [re.compile(p, re.I) for p in [r'biopsy', r'drainage', 'aspir', r'injection', r'guided', r'procedure', 'ablation']],
        }
        
        self.contrast_patterns = {
            'with and without': [re.compile(p, re.I) for p in [r'w/wo', r'c\+\/?-', r'\+\/?-', r'with and without', r'pre and post', r'pre & post', r'w and wo']],
            'with': [re.compile(p, re.I) for p in [r'\b(w|c|with)\s*\+', r'\b(w|with)\b(?!o|out)', r'post contrast', r'\bce\b', r'iv contrast', r'(?<!un)enhanced', r'post gad']],
            'without': [re.compile(p, re.I) for p in [r'\b(w|c|wo)\s*-', r'without contrast', r'no contrast', r'non-?contrast', r'unenhanced', r'\bwo\b']],
        }
        
        self.laterality_patterns = {
            'Bilateral': re.compile(r'\b(bilateral|bilat|both|b/l)\b', re.I),
            'Left': re.compile(r'\b(left|lt)\b', re.I),
            'Right': re.compile(r'\b(right|rt)\b', re.I),
        }
        
        # Build a reverse lookup for fast searching
        self.anatomy_lookup = {}
        for key, config in self.anatomy_mappings.items():
            for term in config['terms']:
                self.anatomy_lookup[term.lower()] = {'key': key, **config}
        
        # Sort terms by length (desc) to match longer phrases first
        self.sorted_anatomy_terms = sorted(self.anatomy_lookup.keys(), key=len, reverse=True)

    def parse_exam_name(self, exam_name: str, modality_code: str, scispacy_entities: Optional[Dict] = None) -> Dict:
        """
        Parses a radiology exam name using a hybrid approach.
        """
        if scispacy_entities is None:
            scispacy_entities = {}
            
        lower_name = exam_name.lower()
        
        # Step 1: Hybrid Anatomy Parsing
        nlp_anatomy_terms = [term.lower() for term in scispacy_entities.get('ANATOMY', [])]
        found_anatomy_keys = self._parse_anatomy_hybrid(lower_name, nlp_anatomy_terms)
        
        # Step 2: Parse Other Components
        parsed = {
            'modality': self.modality_map.get(modality_code, modality_code),
            'anatomy': sorted([self.anatomy_mappings[key]['standardName'] for key in found_anatomy_keys]),
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
        """Combines NLP and rule-based anatomy extraction for higher accuracy."""
        found_keys: Set[str] = set()
        
        # 1. Process NLP-extracted terms first to get a baseline
        for term in nlp_terms:
            for registered_term, info in self.anatomy_lookup.items():
                if term in registered_term or registered_term in term:
                    found_keys.add(info['key'])
        
        # 2. Apply rule-based matching to catch specifics and confirm
        # This is crucial for compound terms like 'cervical spine'.
        for term_key in self.sorted_anatomy_terms:
            if term_key in lower_name:
                found_keys.add(self.anatomy_lookup[term_key]['key'])
                
        return found_keys

    def _parse_laterality(self, lower_name: str, scispacy_entities: Dict) -> Optional[str]:
        """Parse laterality using NLP first, then regex fallback."""
        nlp_directions = [d.lower() for d in scispacy_entities.get('DIRECTION', [])]
        if 'left' in nlp_directions:
            return 'Left'
        if 'right' in nlp_directions:
            return 'Right'
        if 'bilateral' in nlp_directions:
             return 'Bilateral'

        for lat, pattern in self.laterality_patterns.items():
            if pattern.search(lower_name):
                return lat
        return None

    def _parse_contrast(self, lower_name: str) -> Optional[str]:
        """Parse contrast status, prioritizing more specific terms."""
        if any(p.search(lower_name) for p in self.contrast_patterns['with and without']):
            return 'with and without'
        if any(p.search(lower_name) for p in self.contrast_patterns['with']):
            return 'with'
        if any(p.search(lower_name) for p in self.contrast_patterns['without']):
            return 'without'
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
            score += 0.30
        if result.get('modality') != 'Unknown':
            score += 0.1
        if result.get('contrast'):
            score += 0.1
        
        # Small penalty for very short names
        if len(original_exam_name.split()) < 3:
            score -= 0.1
            
        return max(0.1, min(1.0, round(score, 2)))
