import re

class RadiologySemanticParser:
    """
    A Python port of the radiology semantic parser, designed to standardize
    radiology exam names by extracting key components. This version uses a
    hybrid approach, combining NLP entities with rule-based matching for
    maximum accuracy.
    """
    def __init__(self):
        # (The entire __init__ section with all the mappings and patterns remains unchanged)
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
            'whole_spine': {'terms': ['whole spine', 'full spine', 'entire spine'], 'standardName': 'Whole Spine', 'category': 'spine'},
            'chest': {'terms': ['chest', 'thorax', 'thoracic', 'lung'], 'standardName': 'Chest', 'category': 'chest'},
            'ribs': {'terms': ['rib', 'ribs', 'thoracic cage'], 'standardName': 'Ribs', 'category': 'chest'},
            'sternum': {'terms': ['sternum', 'sternal'], 'standardName': 'Sternum', 'category': 'chest'},
            'clavicle': {'terms': ['clavicle', 'clavicular', 'acromioclavicular', 'ac joint'], 'standardName': 'Clavicle', 'category': 'chest'},
            'abdomen': {'terms': ['abdomen', 'abdominal', 'abdo'], 'standardName': 'Abdomen', 'category': 'abdomen'},
            'pelvis': {'terms': ['pelvis', 'pelvic'], 'standardName': 'Pelvis', 'category': 'pelvis'},
            'liver': {'terms': ['liver', 'hepatic'], 'standardName': 'Liver', 'category': 'abdomen'},
            'pancreas': {'terms': ['pancreas', 'pancreatic'], 'standardName': 'Pancreas', 'category': 'abdomen'},
            'kidneys': {'terms': ['kidney', 'renal', 'nephro', 'kub'], 'standardName': 'Kidneys', 'category': 'abdomen'},
            'urinary_tract': {'terms': ['bladder', 'ureter', 'urethra', 'urinary', 'urography', 'ctu', 'ivu'], 'standardName': 'Urinary Tract', 'category': 'genitourinary'},
            'small_bowel': {'terms': ['bowel', 'intestine', 'small bowel', 'enterography', 'enteroclysis'], 'standardName': 'Small Bowel', 'category': 'abdomen'},
            'colon': {'terms': ['colon', 'colonography', 'large bowel'], 'standardName': 'Colon', 'category': 'abdomen'},
            'prostate': {'terms': ['prostate', 'prostatic'], 'standardName': 'Prostate', 'category': 'pelvis'},
            'female_pelvis': {'terms': ['uterus', 'ovary', 'ovarian', 'endometrial', 'female pelvis', 'gynaecology'], 'standardName': 'Female Pelvis', 'category': 'pelvis'},
            'shoulder': {'terms': ['shoulder'], 'standardName': 'Shoulder', 'category': 'musculoskeletal'},
            'humerus': {'terms': ['humerus', 'humeral'], 'standardName': 'Humerus', 'category': 'musculoskeletal'},
            'elbow': {'terms': ['elbow'], 'standardName': 'Elbow', 'category': 'musculoskeletal'},
            'forearm': {'terms': ['forearm', 'radius', 'ulna', 'radial', 'ulnar'], 'standardName': 'Forearm', 'category': 'musculoskeletal'},
            'wrist': {'terms': ['wrist', 'carpal', 'scaphoid'], 'standardName': 'Wrist', 'category': 'musculoskeletal'},
            'hand': {'terms': ['hand', 'metacarpal'], 'standardName': 'Hand', 'category': 'musculoskeletal'},
            'finger': {'terms': ['finger', 'thumb', 'phalanx', 'phalangeal'], 'standardName': 'Finger', 'category': 'musculoskeletal'},
            'hip': {'terms': ['hip', 'acetabulum'], 'standardName': 'Hip', 'category': 'musculoskeletal'},
            'femur': {'terms': ['femur', 'femoral', 'thigh'], 'standardName': 'Femur', 'category': 'musculoskeletal'},
            'knee': {'terms': ['knee', 'patella', 'patellar'], 'standardName': 'Knee', 'category': 'musculoskeletal'},
            'tibia_fibula': {'terms': ['tibia', 'fibula', 'tibial', 'fibular', 'tib fib', 'leg'], 'standardName': 'Tibia/Fibula', 'category': 'musculoskeletal'},
            'ankle': {'terms': ['ankle', 'talar', 'talus'], 'standardName': 'Ankle', 'category': 'musculoskeletal'},
            'foot': {'terms': ['foot', 'feet', 'metatarsal', 'tarsal'], 'standardName': 'Foot', 'category': 'musculoskeletal'},
            'toe': {'terms': ['toe', 'phalanges'], 'standardName': 'Toe', 'category': 'musculoskeletal'},
            'calcaneus': {'terms': ['calcaneus', 'calcaneum', 'os calcis', 'heel'], 'standardName': 'Calcaneus', 'category': 'musculoskeletal'},
            'aorta': {'terms': ['aorta', 'aortic'], 'standardName': 'Aorta', 'category': 'vascular'},
            'carotid': {'terms': ['carotid'], 'standardName': 'Carotid', 'category': 'vascular'},
            'cerebral_vessels': {'terms': ['circle of willis', 'cow', 'intracranial'], 'standardName': 'Cerebral Vessels', 'category': 'vascular'},
            'coronary': {'terms': ['coronary', 'cardiac vessel'], 'standardName': 'Coronary', 'category': 'vascular'},
            'pulmonary_vessels': {'terms': ['pulmonary artery', 'pulmonary angiogram', 'ctpa', 'pe protocol'], 'standardName': 'Pulmonary Vessels', 'category': 'vascular'},
        }
        self.modality_map = {'CT': 'CT', 'MR': 'MRI', 'MRI': 'MRI', 'XR': 'XR', 'US': 'US', 'NM': 'NM', 'PET': 'PET', 'Mamm': 'Mammography', 'DEXA': 'DEXA', 'FL': 'Fluoroscopy', 'IR': 'IR', 'Other': 'Other', 'BR': 'Mammography'}
        self.technique_patterns = {
            'Angiography': [re.compile(p, re.I) for p in [r'angiogram', r'angiography', r'cta', r'mra', r'venogram']],
            'HRCT': [re.compile(p, re.I) for p in [r'hrct', r'high resolution']],
            'Colonography': [re.compile(p, re.I) for p in [r'colonography', r'virtual colonoscopy']],
            'Doppler': [re.compile(p, re.I) for p in [r'doppler', r'duplex']],
            'Intervention': [re.compile(p, re.I) for p in [r'biopsy', r'drainage', r'injection']],
        }
        self.contrast_patterns = {
            'with': [re.compile(p, re.I) for p in [r'\bC\+', r'with contrast', r'post contrast', r'enhanced', r'post gad']],
            'without': [re.compile(p, re.I) for p in [r'\bC-', r'without contrast', r'no contrast', r'non-?contrast', r'unenhanced']],
            'with and without': [re.compile(p, re.I) for p in [r'C\+\/?-', r'\+\/?-', r'with and without', r'pre and post', r'pre & post']],
        }
        self.laterality_patterns = {
            'Bilateral': re.compile(r'\b(bilateral|bilat|both|b/l)\b', re.I),
            'Left': re.compile(r'\b(left|lt)\b', re.I),
            'Right': re.compile(r'\b(right|rt)\b', re.I),
        }
        self.anatomy_lookup = {term.lower(): {'key': key, **config} for key, config in self.anatomy_mappings.items() for term in config['terms']}
        self.sorted_anatomy_terms = sorted(self.anatomy_lookup.keys(), key=len, reverse=True)


    def parse_exam_name(self, exam_name, modality_code, scispacy_entities=None):
        if scispacy_entities is None:
            scispacy_entities = {}

        result = {
            'modality': self.modality_map.get(modality_code, modality_code),
            'anatomy': [],
            'laterality': None,
            'contrast': None,
            'technique': []
        }
        
        lower_name = exam_name.lower()

        # --- HYBRID ANATOMY PARSING ---
        found_anatomy = set()
        nlp_anatomy = scispacy_entities.get('ANATOMY', [])
        for item in nlp_anatomy:
            term_key = item.lower()
            if term_key in self.anatomy_lookup:
                found_anatomy.add(self.anatomy_lookup[term_key]['standardName'])
            else:
                found_anatomy.add(item.capitalize())
        
        for term in self.sorted_anatomy_terms:
            if term in lower_name:
                info = self.anatomy_lookup[term]
                found_anatomy.add(info['standardName'])

        result['anatomy'] = sorted(list(found_anatomy))

        # --- COMPONENT PARSING ---
        # Get laterality from NLP first, then fall back to rules
        
        # --- THIS IS THE FIX ---
        # Safely get the first element from the DIRECTION list, or None if it's empty.
        directions = scispacy_entities.get('DIRECTION', [])
        result['laterality'] = directions[0] if directions else None
        # --- END OF FIX ---

        if not result['laterality']:
            for lat, pattern in self.laterality_patterns.items():
                if pattern.search(lower_name):
                    result['laterality'] = lat
                    break
        
        for con, patterns in self.contrast_patterns.items():
            if any(p.search(lower_name) for p in patterns):
                result['contrast'] = con
                break

        for tech, patterns in self.technique_patterns.items():
            if any(p.search(lower_name) for p in patterns) and tech not in result['technique']:
                result['technique'].append(tech)

        # --- POST-PROCESSING AND CLEANUP ---
        if 'Cerebral Vessels' in result['anatomy'] and 'Head' in result['anatomy']: result['anatomy'].remove('Head')
        if 'Pulmonary Vessels' in result['anatomy'] and 'Chest' in result['anatomy']: result['anatomy'].remove('Chest')
        if 'Coronary' in result['anatomy'] and 'Heart' in result['anatomy']: result['anatomy'].remove('Heart')

        if all(x in lower_name for x in ['chest', 'abdomen', 'pelvis']):
            result['anatomy'] = ['Abdomen', 'Chest', 'Pelvis']
        
        result['cleanName'] = self._build_clean_name(result)
        return result

    def _build_clean_name(self, parsed):
        parts = [parsed['modality']]
        
        if parsed['anatomy']:
            parts.append(" ".join(sorted(parsed['anatomy'])))
        else:
            parts.append("Unknown Anatomy")
        
        if 'Angiography' in parsed['technique']: parts.append('Angiography')
        elif 'HRCT' in parsed['technique']: parts.append('HRCT')
        
        relevant_anatomy_for_laterality = {'Shoulder', 'Knee', 'Hip', 'Elbow', 'Wrist', 'Hand', 'Ankle', 'Foot', 'Femur', 'Humerus', 'Clavicle'}
        if parsed['laterality'] and any(a in relevant_anatomy_for_laterality for a in parsed['anatomy']):
            parts.append(parsed['laterality'])
        
        clean_name = " ".join(parts)
        
        if parsed['contrast']:
            clean_name += f" ({parsed['contrast']} contrast)"
            
        return clean_name.strip()
