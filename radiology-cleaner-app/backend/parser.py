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
        """
        Enhanced parsing with fuzzy matching and ML integration.
        Flow: Standardize -> Parse with NLP/ML -> Generate clean_name -> Fuzzy match -> Return best match
        """
        original_exam_name = exam_name
        
        # Step 1: Standardize the exam name
        if self.standardization_engine:
            exam_name = self.standardization_engine.expand_abbreviations(exam_name)
        if scispacy_entities is None:
            scispacy_entities = {}

        # Step 2: Check for exact match in SNOMED FSN first (legacy support)
        if self.db_manager:
            exact_match = self.db_manager.get_snomed_reference_by_exam_name(exam_name)
            if exact_match:
                result = self._create_result_from_exact_match(exact_match, exam_name, modality_code)
                return result

        # Step 3: Parse exam name using hybrid approach (NLP + ML + Rules)
        parsed_components = self._parse_with_hybrid_approach(exam_name, modality_code, scispacy_entities)
        
        # Step 4: Generate clean name from parsed components
        generated_clean_name = self._build_clean_name(parsed_components)
        
        # Step 5: Try fuzzy matching against database clean names
        if self.db_manager:
            fuzzy_matches = self.db_manager.fuzzy_match_clean_names(generated_clean_name, threshold=0.6)
            
            if fuzzy_matches:
                # Use the best fuzzy match
                best_match = fuzzy_matches[0]
                result = self._create_result_from_fuzzy_match(best_match, parsed_components, generated_clean_name)
                return result
            
            # Step 6: Try fuzzy matching with individual components if no clean name match
            component_matches = self._fuzzy_match_by_components(parsed_components)
            if component_matches:
                best_match = component_matches[0]
                result = self._create_result_from_fuzzy_match(best_match, parsed_components, generated_clean_name)
                return result
        
        # Step 7: No matches found - return generated result without SNOMED codes
        result = parsed_components.copy()
        result['cleanName'] = generated_clean_name
        result['confidence'] = max(0.3, parsed_components.get('confidence', 0.5))  # Lower confidence for no match
        result['clinical_equivalents'] = self._find_clinical_equivalents(result['anatomy'])
        
        return result

    def _create_result_from_exact_match(self, exact_match, exam_name, modality_code):
        """Create result object from exact database match."""
        result = {
            'modality': self.modality_map.get(modality_code, modality_code),
            'anatomy': [],
            'laterality': None,
            'contrast': None,
            'technique': [],
            'gender_context': None,
            'clinical_context': [],
            'confidence': 1.0,  # High confidence for exact match
            'cleanName': exact_match['clean_name'],
            'snomed': {
                'snomed_concept_id': exact_match.get('snomed_concept_id'),
                'snomed_fsn': exact_match.get('snomed_fsn'),
                'snomed_laterality_concept_id': exact_match.get('snomed_laterality_concept_id'),
                'snomed_laterality_fsn': exact_match.get('snomed_laterality_fsn')
            }
        }
        
        # Still parse for additional components
        lower_name = exam_name.lower()
        for lat, pattern in self.laterality_patterns.items():
            if pattern.search(lower_name):
                result['laterality'] = lat
                break
        for con, patterns in self.contrast_patterns.items():
            if any(p.search(lower_name) for p in patterns):
                result['contrast'] = con
                break
                
        result['clinical_equivalents'] = self._find_clinical_equivalents(result['anatomy'])
        return result

    def _create_result_from_fuzzy_match(self, fuzzy_match, parsed_components, generated_clean_name):
        """Create result object from fuzzy database match."""
        result = parsed_components.copy()
        
        # Use the database clean name instead of generated one
        result['cleanName'] = fuzzy_match['clean_name']
        
        # Add SNOMED data from database
        result['snomed'] = {
            'snomed_concept_id': fuzzy_match.get('snomed_concept_id'),
            'snomed_fsn': fuzzy_match.get('snomed_fsn'),
            'snomed_laterality_concept_id': fuzzy_match.get('snomed_laterality_concept_id'),
            'snomed_laterality_fsn': fuzzy_match.get('snomed_laterality_fsn')
        }
        
        # Adjust confidence based on fuzzy match quality
        similarity_score = fuzzy_match.get('similarity_score', 0.0)
        base_confidence = parsed_components.get('confidence', 0.5)
        result['confidence'] = min(0.95, base_confidence * similarity_score)
        
        # Add match metadata
        result['match_info'] = {
            'type': 'fuzzy_match',
            'similarity_score': similarity_score,
            'matched_clean_name': fuzzy_match['clean_name'],
            'generated_clean_name': generated_clean_name
        }

        result['clinical_equivalents'] = self._find_clinical_equivalents(result['anatomy'])
        
        return result

    def _parse_with_hybrid_approach(self, exam_name, modality_code, scispacy_entities):
        """Parse using NLP, ML, and rule-based approaches."""
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

        # --- STEP 1: HYBRID ANATOMY PARSING ---
        found_anatomy = set()
        
        # 1a. NLP-based anatomy extraction (ScispaCy)
        nlp_anatomy = scispacy_entities.get('ANATOMY', [])
        for item in nlp_anatomy:
            term_key = item.lower()
            if term_key in self.anatomy_lookup:
                found_anatomy.add(self.anatomy_lookup[term_key]['standardName'])
            else:
                found_anatomy.add(item.capitalize())
        
        # 1b. Rule-based anatomy extraction
        for term in self.sorted_anatomy_terms:
            if term in lower_name:
                info = self.anatomy_lookup[term]
                found_anatomy.add(info['standardName'])

        # 1c. ML-based anatomy extraction
        ml_anatomy = self._extract_anatomy_with_ml(exam_name)
        found_anatomy.update(ml_anatomy)

        result['anatomy'] = sorted(list(found_anatomy))

        # --- STEP 2: COMPONENT PARSING ---
        # Laterality (NLP first, then rules)
        directions = scispacy_entities.get('DIRECTION', [])
        result['laterality'] = directions[0] if directions else None

        if not result['laterality']:
            for lat, pattern in self.laterality_patterns.items():
                if pattern.search(lower_name):
                    result['laterality'] = lat
                    break
        
        # Contrast detection
        for con, patterns in self.contrast_patterns.items():
            if any(p.search(lower_name) for p in patterns):
                result['contrast'] = con
                break

        # Technique detection
        for tech, patterns in self.technique_patterns.items():
            if any(p.search(lower_name) for p in patterns) and tech not in result['technique']:
                result['technique'].append(tech)

        # Gender context detection
        result['gender_context'] = self._detect_gender_context(lower_name)
        
        # Clinical context detection
        result['clinical_context'] = self._detect_clinical_context(lower_name)
        
        # --- STEP 3: ML ENHANCEMENT ---
        ml_enhancements = self._get_ml_predictions(exam_name)
        if ml_enhancements:
            # Merge ML predictions with rule-based results
            result = self._merge_ml_predictions(result, ml_enhancements)
        
        # --- STEP 4: CONFIDENCE CALCULATION ---
        result['confidence'] = self._calculate_confidence(result, exam_name)
        
        return result

    def _extract_anatomy_with_ml(self, exam_name):
        """Extract anatomy using ML model predictions."""
        try:
            # Load models if available (these are loaded in app.py)
            from app import classifier, vectorizer, mlb
            
            if classifier is None or vectorizer is None or mlb is None:
                return set()
            
            # Vectorize the exam name
            X = vectorizer.transform([exam_name])
            
            # Get predictions
            predictions = classifier.predict(X)
            predicted_labels = mlb.inverse_transform(predictions)[0]
            
            # Extract anatomy labels
            anatomy_labels = [label.split(':')[1] for label in predicted_labels if label.startswith('Anatomy:')]
            
            return set(anatomy_labels)
            
        except Exception as e:
            # ML model not available or error occurred
            return set()

    def _get_ml_predictions(self, exam_name):
        """Get ML model predictions for all components."""
        try:
            # Load models if available
            from app import classifier, vectorizer, mlb
            
            if classifier is None or vectorizer is None or mlb is None:
                return None
            
            # Vectorize the exam name
            X = vectorizer.transform([exam_name])
            
            # Get predictions with probabilities
            try:
                predictions = classifier.predict(X)
                probabilities = classifier.predict_proba(X)
            except:
                predictions = classifier.predict(X)
                probabilities = None
            
            predicted_labels = mlb.inverse_transform(predictions)[0]
            
            # Organize predictions by category
            ml_predictions = {
                'anatomy': [],
                'modality': [],
                'laterality': None,
                'contrast': None,
                'gender_context': None,
                'confidence_scores': {}
            }
            
            for label in predicted_labels:
                if ':' not in label:
                    continue
                    
                category, value = label.split(':', 1)
                category = category.lower()
                
                if category == 'anatomy':
                    ml_predictions['anatomy'].append(value)
                elif category == 'modality':
                    ml_predictions['modality'].append(value)
                elif category == 'laterality':
                    ml_predictions['laterality'] = value.lower()
                elif category == 'contrast':
                    ml_predictions['contrast'] = value.lower().replace('with', 'with').replace('without', 'without')
                elif category == 'gender':
                    ml_predictions['gender_context'] = value.lower()
            
            return ml_predictions
            
        except Exception as e:
            # ML model not available or error occurred
            return None

    def _merge_ml_predictions(self, rule_result, ml_predictions):
        """Merge ML predictions with rule-based results."""
        result = rule_result.copy()
        
        # Merge anatomy (combine rule-based and ML)
        ml_anatomy = set(ml_predictions.get('anatomy', []))
        rule_anatomy = set(result['anatomy'])
        combined_anatomy = rule_anatomy.union(ml_anatomy)
        result['anatomy'] = sorted(list(combined_anatomy))
        
        # Use ML predictions as fallback for missing components
        if not result['laterality'] and ml_predictions.get('laterality'):
            result['laterality'] = ml_predictions['laterality']
            
        if not result['contrast'] and ml_predictions.get('contrast'):
            result['contrast'] = ml_predictions['contrast']
            
        if not result['gender_context'] and ml_predictions.get('gender_context'):
            result['gender_context'] = ml_predictions['gender_context']
        
        return result

    def _fuzzy_match_by_components(self, parsed_components):
        """Try fuzzy matching by building clean names with different component combinations."""
        if not self.db_manager:
            return []
        
        matches = []
        modality = parsed_components['modality']
        anatomy_list = parsed_components['anatomy']
        
        # Try different combinations of components
        for anatomy_count in range(len(anatomy_list), 0, -1):
            for anatomy_subset in self._get_combinations(anatomy_list, anatomy_count):
                # Build a clean name with this anatomy subset
                test_components = parsed_components.copy()
                test_components['anatomy'] = list(anatomy_subset)
                test_clean_name = self._build_clean_name(test_components)
                
                # Try fuzzy matching
                component_matches = self.db_manager.fuzzy_match_clean_names(test_clean_name, threshold=0.7)
                matches.extend(component_matches)
        
        # Remove duplicates and sort by similarity
        seen = set()
        unique_matches = []
        for match in matches:
            match_key = match['clean_name']
            if match_key not in seen:
                seen.add(match_key)
                unique_matches.append(match)
        
        unique_matches.sort(key=lambda x: x['similarity_score'], reverse=True)
        return unique_matches

    def _get_combinations(self, items, count):
        """Get all combinations of items with specified count."""
        from itertools import combinations
        return combinations(items, count)

    def _build_clean_name(self, parsed):
        parts = [parsed['modality']]
        
        if parsed['anatomy']:
            # Sort anatomy from cranial to caudal (Head → Neck → Chest → Abdomen → Pelvis)
            cranial_to_caudal_order = [
                'Head', 'Brain', 'Orbits', 'Sinuses', 'Temporal Bones', 'Facial Bones', 'Pituitary',
                'Neck', 'Cervical Spine',
                'Chest', 'Thoracic Spine', 'Ribs', 'Sternum', 'Clavicle', 'Heart', 'Lung',
                'Abdomen', 'Liver', 'Pancreas', 'Kidneys', 'Small Bowel', 'Colon',
                'Pelvis', 'Female Pelvis', 'Prostate', 'Urinary Tract',
                'Lumbar Spine', 'Sacrum/Coccyx', 'Whole Spine',
                'Shoulder', 'Humerus', 'Elbow', 'Forearm', 'Wrist', 'Hand',
                'Hip', 'Femur', 'Knee', 'Tibia', 'Fibula', 'Ankle', 'Foot'
            ]
            
            # Sort anatomy based on cranial-to-caudal order
            anatomy_list = parsed['anatomy']
            ordered_anatomy = []
            for anatomical_region in cranial_to_caudal_order:
                if anatomical_region in anatomy_list:
                    ordered_anatomy.append(anatomical_region)
            
            # Add any anatomy not in the predefined order (in case of new terms)
            for anatomy in anatomy_list:
                if anatomy not in ordered_anatomy:
                    ordered_anatomy.append(anatomy)
            
            parts.append(" ".join(ordered_anatomy))
        else:
            parts.append("Unknown Anatomy")
        
        if 'Angiography' in parsed['technique']: 
            parts.append('Angiography')
        elif 'HRCT' in parsed['technique']: 
            parts.append('HRCT')
        
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
