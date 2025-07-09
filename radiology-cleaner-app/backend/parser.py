import re
import numpy as np
from collections import defaultdict
from datetime import datetime

class RadiologySemanticParser:
    """
    A Python port of the radiology semantic parser, designed to standardize
    radiology exam names by extracting key components. This version uses a
    hybrid approach, combining NLP entities with rule-based matching for
    maximum accuracy.
    """
    def __init__(self, db_manager=None, standardization_engine=None):
        self.db_manager = db_manager
        self.standardization_engine = standardization_engine
        self.db_manager = db_manager
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

        # Gender detection patterns
        self.gender_patterns = {
            'male': [re.compile(p, re.I) for p in [r'\bmale\b', r'\bm\b(?=\s|$)', r'\bmen\b', r'\bprostate\b', r'\bmale pelvis\b']],
            'female': [re.compile(p, re.I) for p in [r'\bfemale\b', r'\bf\b(?=\s|$)', r'\bwomen\b', r'\bpelvic\b(?=.*female)', 
                       r'\bgynaecology\b', r'\bmammography\b', r'\bbreast\b', r'\bfemale pelvis\b', r'\bovarian\b', r'\buterine\b']],
            'pregnancy': [re.compile(p, re.I) for p in [r'\bpregnant\b', r'\bpregnancy\b', r'\bobstetric\b', r'\bfetal\b', r'\bmaternal\b']]
        }
        
        # Clinical context patterns
        self.clinical_context = {
            'emergency': [re.compile(p, re.I) for p in [r'\btrauma\b', r'\bstat\b', r'\bemergency\b', r'\bpe protocol\b', r'\bctpa\b', r'\bacute\b']],
            'screening': [re.compile(p, re.I) for p in [r'\bscreening\b', r'\broutine\b', r'\bpreventive\b', r'\bwellness\b']],
            'follow_up': [re.compile(p, re.I) for p in [r'\bfollow.?up\b', r'\bpost.?op\b', r'\bsurveillance\b', r'\bmonitoring\b', r'\brepeat\b']],
            'intervention': [re.compile(p, re.I) for p in [r'\bbiopsy\b', r'\bdrainage\b', r'\binjection\b', r'\bguided\b', r'\bprocedure\b']]
        }
        
        # Anatomical hierarchy and relationships
        self.anatomical_hierarchy = {
            'contains': {
                'Abdomen': ['Liver', 'Pancreas', 'Kidneys', 'Small Bowel', 'Colon'],
                'Pelvis': ['Prostate', 'Female Pelvis', 'Urinary Tract'],
                'Chest': ['Ribs', 'Sternum', 'Clavicle', 'Pulmonary Vessels'],
                'Head': ['Sinuses', 'Orbits', 'Facial Bones', 'Pituitary', 'Temporal Bones'],
                'Neck': ['Carotid'],
                'Whole Spine': ['Cervical Spine', 'Thoracic Spine', 'Lumbar Spine', 'Sacrum/Coccyx']
            },
            'overlaps': {
                'Abdomen': ['Pelvis'],  # Abdomen+Pelvis is often clinically equivalent
                'Chest': ['Ribs', 'Sternum', 'Clavicle'],
                'Head': ['Neck'],  # Head+Neck scans are common
                'Cervical Spine': ['Neck']
            },
            'equivalents': {
                'Abdomen/Pelvis': ['Abdomen', 'Pelvis'],
                'Head/Neck': ['Head', 'Neck'],
                'Chest/Abdomen/Pelvis': ['Chest', 'Abdomen', 'Pelvis']
            }
        }
        
        # Build a reverse lookup for fast searching
        self.anatomy_lookup = {}
        for key, config in self.anatomy_mappings.items():
            for term in config['terms']:
                self.anatomy_lookup[term.lower()] = {'key': key, **config}
        
        # Sort terms by length (desc) to match longer phrases first (e.g., "cervical spine" before "spine")
        self.sorted_anatomy_terms = sorted(self.anatomy_lookup.keys(), key=len, reverse=True)


    def parse_exam_name(self, exam_name, modality_code, scispacy_entities=None):
        if self.standardization_engine:
            exam_name = self.standardization_engine.expand_abbreviations(exam_name)
        if scispacy_entities is None:
            scispacy_entities = {}

        # Check for a direct match in the reference table
        if self.db_manager:
            reference_data = self.db_manager.get_snomed_reference_by_exam_name(exam_name)
            if reference_data:
                result = {
                    'modality': self.modality_map.get(modality_code, modality_code),
                    'anatomy': [],
                    'laterality': None,
                    'contrast': None,
                    'technique': [],
                    'gender_context': None,
                    'clinical_context': [],
                    'confidence': 1.0, # High confidence for direct match
                    'cleanName': reference_data['clean_name'],
                    'snomed': {
                        'snomed_concept_id': reference_data.get('snomed_concept_id'),
                        'snomed_fsn': reference_data.get('snomed_fsn'),
                        'snomed_laterality_concept_id': reference_data.get('snomed_laterality_concept_id'),
                        'snomed_laterality_fsn': reference_data.get('snomed_laterality_fsn')
                    }
                }
                # We can still parse the original name for other components
                lower_name = exam_name.lower()
                for lat, pattern in self.laterality_patterns.items():
                    if pattern.search(lower_name):
                        result['laterality'] = lat
                        break
                for con, patterns in self.contrast_patterns.items():
                    if any(p.search(lower_name) for p in patterns):
                        result['contrast'] = con
                        break
                return result

        result = {
            'modality': self.modality_map.get(modality_code, modality_code),
            'anatomy': [],
            'laterality': None,
            'contrast': None,
            'technique': [],
            'gender_context': None,
            'clinical_context': [],
            'confidence': 1.0
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

        # 3. Gender context detection
        result['gender_context'] = self._detect_gender_context(lower_name)
        
        # 4. Clinical context detection
        result['clinical_context'] = self._detect_clinical_context(lower_name)
        
        # 5. Post-processing and refinement
        # Remove general terms if a specific sub-part is already present
        if 'Cerebral Vessels' in result['anatomy'] and 'Head' in result['anatomy']:
            result['anatomy'].remove('Head')
        if 'Pulmonary Vessels' in result['anatomy'] and 'Chest' in result['anatomy']:
            result['anatomy'].remove('Chest')
        if 'Pituitary' in result['anatomy'] and 'Head' in result['anatomy']:
            result['anatomy'].remove('Head')
            
        # Handle special combined scan names
        if 'chest' in lower_name and 'abdomen' in lower_name and 'pelvis' in lower_name:
            result['anatomy'] = ['Chest', 'Abdomen', 'Pelvis']
        elif 'head' in lower_name and 'neck' in lower_name:
            result['anatomy'] = ['Head', 'Neck']
            
        # Apply anatomical hierarchy and equivalence rules
        result['anatomy'] = self._apply_anatomical_hierarchy(result['anatomy'], result['modality'])
        
        # Calculate confidence score
        result['confidence'] = self._calculate_confidence(result, exam_name)
        
        # Generate enhanced clean name
        result['cleanName'] = self._build_clean_name(result)
        result['clinical_equivalents'] = self._find_clinical_equivalents(result['anatomy'])

        # Get SNOMED code
        if self.db_manager:
            snomed_code = self.db_manager.get_snomed_code(result['cleanName'])
            if snomed_code:
                result['snomed'] = {
                    'snomed_concept_id': snomed_code.get('snomed_concept_id'),
                    'snomed_fsn': snomed_code.get('snomed_fsn'),
                    'snomed_laterality_concept_id': snomed_code.get('snomed_laterality_concept_id'),
                    'snomed_laterality_fsn': snomed_code.get('snomed_laterality_fsn')
                }

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
    
    def _detect_gender_context(self, exam_name_lower):
        """Detect gender context from exam name."""
        for gender, patterns in self.gender_patterns.items():
            if any(pattern.search(exam_name_lower) for pattern in patterns):
                return gender
        return None
    
    def _detect_clinical_context(self, exam_name_lower):
        """Detect clinical context from exam name."""
        contexts = []
        for context, patterns in self.clinical_context.items():
            if any(pattern.search(exam_name_lower) for pattern in patterns):
                contexts.append(context)
        return contexts
    
    def _apply_anatomical_hierarchy(self, anatomy_list, modality):
        """Apply anatomical hierarchy and equivalence rules."""
        if not anatomy_list:
            return anatomy_list
            
        # Sort anatomy list for consistent processing
        anatomy_set = set(anatomy_list)
        
        # Handle common clinical equivalences
        if 'Abdomen' in anatomy_set and 'Pelvis' in anatomy_set:
            # For CT scans, Abdomen+Pelvis is often clinically equivalent to Abdomen/Pelvis
            if modality == 'CT':
                return ['Abdomen/Pelvis']
            else:
                return ['Abdomen', 'Pelvis']
        
        if 'Head' in anatomy_set and 'Neck' in anatomy_set:
            return ['Head/Neck']
            
        if 'Chest' in anatomy_set and 'Abdomen' in anatomy_set and 'Pelvis' in anatomy_set:
            return ['Chest/Abdomen/Pelvis']
        
        # Remove redundant anatomy based on hierarchy
        filtered_anatomy = []
        for anatomy in anatomy_list:
            is_redundant = False
            
            # Check if this anatomy is contained within another anatomy in the list
            for container, contained in self.anatomical_hierarchy.get('contains', {}).items():
                if container in anatomy_set and anatomy in contained:
                    is_redundant = True
                    break
            
            if not is_redundant:
                filtered_anatomy.append(anatomy)
        
        return sorted(filtered_anatomy) if filtered_anatomy else anatomy_list
    
    def _calculate_confidence(self, result, original_exam_name):
        """Calculate confidence score based on parsing results."""
        confidence = 1.0
        
        # Reduce confidence if no anatomy found
        if not result['anatomy']:
            confidence -= 0.3
        
        # Reduce confidence if very short exam name (likely ambiguous)
        if len(original_exam_name) < 5:
            confidence -= 0.2
        
        # Increase confidence if multiple components detected
        components_found = sum([
            1 if result['anatomy'] else 0,
            1 if result['laterality'] else 0,
            1 if result['contrast'] else 0,
            1 if result['technique'] else 0
        ])
        
        if components_found >= 3:
            confidence += 0.1
        elif components_found == 1:
            confidence -= 0.1
        
        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))
    
    def _find_clinical_equivalents(self, anatomy_list):
        """Find clinical equivalents for the given anatomy combination."""
        equivalents = []
        
        # Check for known equivalents
        for equiv_name, equiv_parts in self.anatomical_hierarchy.get('equivalents', {}).items():
            if set(anatomy_list) == set(equiv_parts):
                equivalents.append(equiv_name)
        
        # Add individual anatomy parts as potential equivalents
        if len(anatomy_list) > 1:
            equivalents.extend(anatomy_list)
        
        return list(set(equivalents))
