import re

class RadiologySemanticParser:
    """
    A Python port of the radiology semantic parser, designed to standardize
    radiology exam names by extracting key components like modality, anatomy,
    laterality, contrast, and technique.
    It can be enhanced by providing pre-extracted entities from an NLP model like ScispaCy.
    """
    def __init__(self):
        # (All of your anatomy_mappings and other dictionaries remain here, unchanged)
        # ...
        self.anatomy_mappings = {
            'head': {'terms': ['head', 'brain', 'skull', 'cranial', 'cerebral', 'cranium'], 'standardName': 'Head', 'category': 'neurological'},
            # ... all the other anatomy mappings ...
            'peripheral_vessels': {'terms': ['peripheral', 'extremity vessel', 'runoff'], 'standardName': 'Peripheral Vessels', 'category': 'vascular'},
        }

        self.modality_map = {'CT': 'CT', 'MR': 'MRI', 'MRI': 'MRI', 'XR': 'XR', 'US': 'US', 'NM': 'NM', 'PET': 'PET', 'Mamm': 'Mammography', 'DEXA': 'DEXA', 'FL': 'Fluoroscopy', 'IR': 'IR', 'Other': 'Other'}
        
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

        self.anatomy_lookup = {}
        for key, config in self.anatomy_mappings.items():
            for term in config['terms']:
                self.anatomy_lookup[term.lower()] = {'key': key, **config}
        
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

        # 1. Use NLP entities
        result['anatomy'] = sorted(list(set(scispacy_entities.get('ANATOMY', []))))
        
        # --- THE FIX IS HERE ---
        # Safely get the laterality. If the DIRECTION list exists but is empty, this will not crash.
        direction_list = scispacy_entities.get('DIRECTION', [])
        result['laterality'] = direction_list[0] if direction_list else None
        
        # 2. Fallback to regex/keyword rules
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

        if not result['anatomy']:
            found_anatomy_keys = set()
            for term in self.sorted_anatomy_terms:
                if term in lower_name:
                    info = self.anatomy_lookup[term]
                    if info['key'] not in found_anatomy_keys:
                        result['anatomy'].append(info['standardName'])
                        found_anatomy_keys.add(info['key'])
            result['anatomy'] = sorted(list(set(result['anatomy'])))

        # 3. Post-processing and refinement
        if 'Cerebral Vessels' in result['anatomy'] and 'Head' in result['anatomy']:
            result['anatomy'].remove('Head')
        if 'Pulmonary Vessels' in result['anatomy'] and 'Chest' in result['anatomy']:
            result['anatomy'].remove('Chest')
        if 'Pituitary' in result['anatomy'] and 'Head' in result['anatomy']:
            result['anatomy'].remove('Head')
            
        if 'chest' in lower_name and 'abdomen' in lower_name and 'pelvis' in lower_name:
            result['anatomy'] = ['Abdomen', 'Chest', 'Pelvis']
        elif 'head' in lower_name and 'neck' in lower_name:
            result['anatomy'] = ['Head', 'Neck']

        result['cleanName'] = self._build_clean_name(result)
        return result

    def _build_clean_name(self, parsed):
        # ... (This function remains unchanged) ...
        parts = [parsed['modality']]
        if parsed['anatomy']:
            parts.append(" ".join(sorted(parsed['anatomy'])))
        if 'Angiography' in parsed['technique']:
            parts.append('Angiography')
        relevant_anatomy_for_laterality = {'Shoulder', 'Knee', 'Hip', 'Elbow', 'Wrist', 'Hand', 'Ankle', 'Foot'}
        if parsed['laterality'] and any(a in relevant_anatomy_for_laterality for a in parsed['anatomy']):
            parts.append(parsed['laterality'])
        clean_name = " ".join(parts)
        if parsed['contrast']:
            clean_name += f" ({parsed['contrast']} contrast)"
        return clean_name.strip()
