import re
import difflib
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
import hashlib
from datetime import datetime
import json

class StandardizationEngine:
    """
    Advanced standardization engine for radiology exam names.
    Provides normalization, similarity scoring, and equivalence detection.
    """
    
    def __init__(self, db_manager=None):
        self.abbreviations = {}
        if db_manager:
            self.abbreviations = db_manager.get_all_abbreviations()
        # Common variations and their standardized forms
        self.modality_normalizations = {
            'ct scan': 'CT',
            'ct study': 'CT',
            'computed tomography': 'CT',
            'mri scan': 'MRI',
            'mri study': 'MRI',
            'magnetic resonance imaging': 'MRI',
            'x-ray': 'XR',
            'xray': 'XR',
            'plain film': 'XR',
            'ultrasound': 'US',
            'sonogram': 'US',
            'nuclear medicine': 'NM',
            'pet scan': 'PET',
            'pet study': 'PET',
            'mammogram': 'Mammography',
            'mammo': 'Mammography',
            'fluoroscopy': 'Fluoroscopy',
            'fluoro': 'Fluoroscopy'
        }
        
        # Anatomical normalizations
        self.anatomical_normalizations = {
            'abd': 'abdomen',
            'abdo': 'abdomen',
            'abdominal': 'abdomen',
            'pelv': 'pelvis',
            'pelvic': 'pelvis',
            'thorax': 'chest',
            'thoracic': 'chest',
            'cranial': 'head',
            'skull': 'head',
            'brain': 'head',
            'cervical': 'neck',
            'lumbar': 'lumbar spine',
            'lumbosacral': 'lumbar spine',
            'sacral': 'sacrum',
            'coccyx': 'sacrum',
            'si joint': 'sacrum',
            'sacroiliac': 'sacrum'
        }
        
        # Directional normalizations
        self.directional_normalizations = {
            'l': 'left',
            'lt': 'left',
            'r': 'right',
            'rt': 'right',
            'bilat': 'bilateral',
            'b/l': 'bilateral',
            'both': 'bilateral'
        }
        
        # Contrast normalizations
        self.contrast_normalizations = {
            'c+': 'with contrast',
            'c-': 'without contrast',
            'c+/-': 'with and without contrast',
            '+/-': 'with and without contrast',
            'enhanced': 'with contrast',
            'unenhanced': 'without contrast',
            'post gad': 'with contrast',
            'post contrast': 'with contrast',
            'pre and post': 'with and without contrast'
        }
        
        # Common synonyms for equivalent exams
        self.exam_synonyms = {
            'abdomen/pelvis': ['abdomen and pelvis', 'abdopelvis', 'abd/pelv', 'abdo pelvis'],
            'chest/abdomen/pelvis': ['chest abdomen pelvis', 'cap', 'thorax abdomen pelvis'],
            'head/neck': ['head and neck', 'head neck'],
            'lumbar spine': ['l spine', 'lumbosacral spine', 'lower back'],
            'cervical spine': ['c spine', 'neck spine'],
            'thoracic spine': ['t spine', 'dorsal spine'],
            'knee': ['patella', 'patellofemoral'],
            'ankle': ['talar', 'hindfoot'],
            'foot': ['forefoot', 'midfoot'],
            'hand': ['metacarpal', 'carpal'],
            'wrist': ['scaphoid', 'carpal bones']
        }
        
        # Quality scoring weights
        self.quality_weights = {
            'modality_clarity': 0.25,
            'anatomy_precision': 0.30,
            'terminology_standard': 0.20,
            'completeness': 0.15,
            'clinical_relevance': 0.10
        }
        
        # Cache for similarity calculations
        self.similarity_cache = {}

    def clean_z_codes(self, exam_name: str) -> str:
        """
        Clean Z-code exam names that have format: 'ZCODE^Actual Name'
        Example: 'ZCRUSV200^US of Limb Veins for DVT (1 Li' -> 'US of Limb Veins for DVT (1 Li'
        """
        # Pattern to match Z-code followed by ^ and capture the actual name
        z_code_pattern = r'^Z[A-Z0-9]+\^(.+)$'
        match = re.match(z_code_pattern, exam_name)
        
        if match:
            # Extract the actual exam name after the ^
            actual_name = match.group(1).strip()
            return actual_name
        
        return exam_name
    
    def expand_abbreviations(self, exam_name: str) -> str:
        """Expand abbreviations in an exam name."""
        # First clean Z-codes before expanding abbreviations
        exam_name = self.clean_z_codes(exam_name)
        
        for abbr, full_text in self.abbreviations.items():
            # Use regex to match whole words only
            exam_name = re.sub(rf'\b{re.escape(abbr)}\b', full_text, exam_name, flags=re.IGNORECASE)
        return exam_name
    
    def normalize_exam_name(self, exam_name: str) -> Dict:
        """
        Normalize an exam name to standardized components.
        
        Args:
            exam_name: Raw exam name from radiology system
            
        Returns:
            Dict with normalized components and metadata
        """
        original_name = exam_name
        exam_name = self.expand_abbreviations(exam_name)
        normalized_name = exam_name.lower().strip()
        
        # Remove common prefixes/suffixes
        normalized_name = re.sub(r'\b(exam|study|scan|imaging|procedure)\b', '', normalized_name)
        normalized_name = re.sub(r'\s+', ' ', normalized_name).strip()
        
        # Apply modality normalizations
        for variant, standard in self.modality_normalizations.items():
            normalized_name = re.sub(rf'\b{re.escape(variant)}\b', standard.lower(), normalized_name)
        
        # Apply anatomical normalizations
        for variant, standard in self.anatomical_normalizations.items():
            normalized_name = re.sub(rf'\b{re.escape(variant)}\b', standard, normalized_name)
        
        # Apply directional normalizations
        for variant, standard in self.directional_normalizations.items():
            normalized_name = re.sub(rf'\b{re.escape(variant)}\b', standard, normalized_name)
        
        # Apply contrast normalizations
        for variant, standard in self.contrast_normalizations.items():
            normalized_name = re.sub(rf'\b{re.escape(variant)}\b', standard, normalized_name)
        
        # Generate canonical form (ultra-standardized for exact matching)
        canonical_form = self._generate_canonical_form(normalized_name)
        
        # Calculate normalization quality score
        quality_score = self._calculate_normalization_quality(original_name, normalized_name)
        
        return {
            'original': original_name,
            'normalized': normalized_name.title(),
            'canonical_form': canonical_form,
            'quality_score': quality_score,
            'transformations_applied': self._get_transformations_applied(original_name, normalized_name),
            'flags': self._detect_quality_flags(original_name, normalized_name)
        }
    
    def calculate_similarity_score(self, exam1: str, exam2: str) -> float:
        """
        Calculate similarity score between two exam names.
        
        Args:
            exam1, exam2: Exam names to compare
            
        Returns:
            Similarity score between 0 and 1
        """
        # Check cache first
        cache_key = f"{exam1}|{exam2}"
        if cache_key in self.similarity_cache:
            return self.similarity_cache[cache_key]
        
        # Normalize both names
        norm1 = self.normalize_exam_name(exam1)
        norm2 = self.normalize_exam_name(exam2)
        
        # Multiple similarity measures
        scores = []
        
        # 1. Exact canonical match
        if norm1['canonical_form'] == norm2['canonical_form']:
            scores.append(1.0)
        
        # 2. String similarity on normalized names
        string_sim = difflib.SequenceMatcher(None, norm1['normalized'], norm2['normalized']).ratio()
        scores.append(string_sim)
        
        # 3. Synonym matching
        synonym_sim = self._calculate_synonym_similarity(norm1['normalized'], norm2['normalized'])
        scores.append(synonym_sim)
        
        # 4. Component-based similarity
        component_sim = self._calculate_component_similarity(norm1['normalized'], norm2['normalized'])
        scores.append(component_sim)
        
        # 5. Fuzzy matching with common variations
        fuzzy_sim = self._calculate_fuzzy_similarity(exam1, exam2)
        scores.append(fuzzy_sim)
        
        # Weighted average with emphasis on higher scores
        final_score = max(scores) * 0.4 + sum(scores) / len(scores) * 0.6
        
        # Cache the result
        self.similarity_cache[cache_key] = final_score
        self.similarity_cache[f"{exam2}|{exam1}"] = final_score  # Symmetric
        
        return final_score
    
    def find_equivalence_groups(self, exam_list: List[Dict], similarity_threshold: float = 0.85) -> List[Dict]:
        """
        Group exams that are clinically equivalent.
        
        Args:
            exam_list: List of exam dictionaries with 'name' and 'source' keys
            similarity_threshold: Minimum similarity score for grouping
            
        Returns:
            List of equivalence groups
        """
        groups = []
        processed = set()
        
        for i, exam1 in enumerate(exam_list):
            if i in processed:
                continue
                
            # Create new group
            group = {
                'canonical_name': None,
                'members': [exam1],
                'confidence_scores': [],
                'group_id': None
            }
            
            # Find similar exams
            for j, exam2 in enumerate(exam_list[i+1:], i+1):
                if j in processed:
                    continue
                    
                similarity = self.calculate_similarity_score(exam1['name'], exam2['name'])
                
                if similarity >= similarity_threshold:
                    group['members'].append(exam2)
                    group['confidence_scores'].append(similarity)
                    processed.add(j)
            
            # Only create group if it has multiple members
            if len(group['members']) > 1:
                # Determine canonical name (most complete/standard)
                group['canonical_name'] = self._determine_canonical_name(group['members'])
                group['group_id'] = self._generate_group_id(group['canonical_name'])
                group['average_confidence'] = sum(group['confidence_scores']) / len(group['confidence_scores'])
                groups.append(group)
            
            processed.add(i)
        
        return sorted(groups, key=lambda x: len(x['members']), reverse=True)
    
    def calculate_quality_metrics(self, exam_name: str, parsed_components: Dict) -> Dict:
        """
        Calculate comprehensive quality metrics for an exam name.
        
        Args:
            exam_name: Original exam name
            parsed_components: Parsed components from semantic parser
            
        Returns:
            Quality metrics dictionary
        """
        metrics = {}
        
        # 1. Modality clarity
        modality_score = 1.0 if parsed_components.get('modality') else 0.0
        if parsed_components.get('modality') == 'Other':
            modality_score = 0.3
        metrics['modality_clarity'] = modality_score
        
        # 2. Anatomy precision
        anatomy_list = parsed_components.get('anatomy', [])
        if not anatomy_list:
            anatomy_score = 0.0
        elif len(anatomy_list) == 1:
            anatomy_score = 0.9
        elif len(anatomy_list) <= 3:
            anatomy_score = 0.8
        else:
            anatomy_score = 0.6  # Too many anatomy parts might indicate imprecision
        metrics['anatomy_precision'] = anatomy_score
        
        # 3. Terminology standardization
        terminology_score = self._assess_terminology_standard(exam_name)
        metrics['terminology_standard'] = terminology_score
        
        # 4. Completeness
        completeness_score = self._assess_completeness(exam_name, parsed_components)
        metrics['completeness'] = completeness_score
        
        # 5. Clinical relevance
        clinical_score = self._assess_clinical_relevance(parsed_components)
        metrics['clinical_relevance'] = clinical_score
        
        # 6. Overall quality score
        overall_score = sum(
            metrics[key] * self.quality_weights[key] 
            for key in self.quality_weights
        )
        metrics['overall_quality'] = overall_score
        
        # 7. Quality flags
        metrics['flags'] = self._generate_quality_flags(exam_name, parsed_components, metrics)
        
        # 8. Improvement suggestions
        metrics['suggestions'] = self._generate_improvement_suggestions(exam_name, parsed_components, metrics)
        
        return metrics
    
    def _generate_canonical_form(self, normalized_name: str) -> str:
        """Generate ultra-standardized canonical form."""
        # Remove all spaces, punctuation, and standardize format
        canonical = re.sub(r'[^\w]', '', normalized_name.lower())
        
        # Apply additional standardizations
        canonical = re.sub(r'abdomen.*pelvis|pelvis.*abdomen', 'abdpelv', canonical)
        canonical = re.sub(r'chest.*abdomen.*pelvis', 'chestabdpelv', canonical)
        canonical = re.sub(r'head.*neck|neck.*head', 'headneck', canonical)
        
        return canonical
    
    def _calculate_normalization_quality(self, original: str, normalized: str) -> float:
        """Calculate quality of normalization process."""
        # Check for common issues
        score = 1.0
        
        # Penalize if too much information lost
        if len(normalized) < len(original) * 0.5:
            score -= 0.2
        
        # Reward if standardizations were applied
        if original.lower() != normalized.lower():
            score += 0.1
        
        # Check for remaining non-standard terms
        non_standard_terms = ['study', 'exam', 'scan', 'procedure']
        for term in non_standard_terms:
            if term in normalized.lower():
                score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _get_transformations_applied(self, original: str, normalized: str) -> List[str]:
        """Get list of transformations applied during normalization."""
        transformations = []
        
        orig_lower = original.lower()
        norm_lower = normalized.lower()
        
        # Check for modality normalizations
        for variant, standard in self.modality_normalizations.items():
            if variant in orig_lower and standard.lower() in norm_lower:
                transformations.append(f"Modality: {variant} → {standard}")
        
        # Check for anatomical normalizations
        for variant, standard in self.anatomical_normalizations.items():
            if variant in orig_lower and standard in norm_lower:
                transformations.append(f"Anatomy: {variant} → {standard}")
        
        # Check for directional normalizations
        for variant, standard in self.directional_normalizations.items():
            if variant in orig_lower and standard in norm_lower:
                transformations.append(f"Direction: {variant} → {standard}")
        
        return transformations
    
    def _detect_quality_flags(self, original: str, normalized: str) -> List[str]:
        """Detect quality issues in the normalization."""
        flags = []
        
        # Check for potential typos
        if len(original) > 5 and len(set(original.lower())) < len(original) * 0.5:
            flags.append('potential_typo')
        
        # Check for uncommon terminology
        uncommon_terms = ['study', 'exam', 'scan', 'procedure', 'imaging']
        if any(term in original.lower() for term in uncommon_terms):
            flags.append('uncommon_terminology')
        
        # Check for abbreviations
        if re.search(r'\b[A-Z]{2,}\b', original):
            flags.append('contains_abbreviations')
        
        # Check for very short names
        if len(original.strip()) < 5:
            flags.append('very_short_name')
        
        return flags
    
    def _calculate_synonym_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity based on known synonyms."""
        name1_lower = name1.lower()
        name2_lower = name2.lower()
        
        for canonical, synonyms in self.exam_synonyms.items():
            canon_in_1 = canonical in name1_lower
            canon_in_2 = canonical in name2_lower
            
            synonym_in_1 = any(syn in name1_lower for syn in synonyms)
            synonym_in_2 = any(syn in name2_lower for syn in synonyms)
            
            if (canon_in_1 and synonym_in_2) or (synonym_in_1 and canon_in_2) or (synonym_in_1 and synonym_in_2):
                return 0.9
        
        return 0.0
    
    def _calculate_component_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity based on component overlap."""
        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_fuzzy_similarity(self, name1: str, name2: str) -> float:
        """Calculate fuzzy similarity with common variations."""
        # Remove common variations and compare
        clean1 = re.sub(r'\b(and|with|without|contrast|study|exam|scan)\b', '', name1.lower())
        clean2 = re.sub(r'\b(and|with|without|contrast|study|exam|scan)\b', '', name2.lower())
        
        clean1 = re.sub(r'\s+', ' ', clean1).strip()
        clean2 = re.sub(r'\s+', ' ', clean2).strip()
        
        return difflib.SequenceMatcher(None, clean1, clean2).ratio()
    
    def _determine_canonical_name(self, members: List[Dict]) -> str:
        """Determine the best canonical name for a group."""
        # Score each member based on completeness and standardization
        scores = []
        
        for member in members:
            name = member['name']
            score = 0
            
            # Prefer longer, more descriptive names
            score += len(name) * 0.1
            
            # Prefer names with standard terminology
            if any(term in name.lower() for term in ['ct', 'mri', 'xr', 'us']):
                score += 10
            
            # Prefer names without abbreviations
            if not re.search(r'\b[A-Z]{2,}\b', name):
                score += 5
            
            # Prefer names with clear anatomy
            anatomical_terms = ['abdomen', 'chest', 'head', 'pelvis', 'spine', 'knee', 'shoulder']
            if any(term in name.lower() for term in anatomical_terms):
                score += 8
            
            scores.append((score, name))
        
        # Return the highest scoring name
        return max(scores, key=lambda x: x[0])[1]
    
    def _generate_group_id(self, canonical_name: str) -> str:
        """Generate unique group ID."""
        # Create hash from canonical name
        hash_obj = hashlib.md5(canonical_name.encode())
        return f"grp_{hash_obj.hexdigest()[:8]}"
    
    def _assess_terminology_standard(self, exam_name: str) -> float:
        """Assess how standardized the terminology is."""
        score = 1.0
        
        # Check for non-standard terms
        non_standard = ['study', 'exam', 'scan', 'procedure', 'imaging']
        for term in non_standard:
            if term in exam_name.lower():
                score -= 0.15
        
        # Check for standard modality terms
        standard_modalities = ['ct', 'mri', 'xr', 'us', 'pet', 'nm']
        if any(mod in exam_name.lower() for mod in standard_modalities):
            score += 0.2
        
        return max(0.0, min(1.0, score))
    
    def _assess_completeness(self, exam_name: str, components: Dict) -> float:
        """Assess completeness of exam name."""
        score = 0.0
        
        # Has modality
        if components.get('modality') and components['modality'] != 'Other':
            score += 0.4
        
        # Has anatomy
        if components.get('anatomy'):
            score += 0.4
        
        # Has additional details (laterality, contrast, technique)
        additional_details = sum([
            1 if components.get('laterality') else 0,
            1 if components.get('contrast') else 0,
            1 if components.get('technique') else 0
        ])
        score += additional_details * 0.1
        
        return min(1.0, score)
    
    def _assess_clinical_relevance(self, components: Dict) -> float:
        """Assess clinical relevance of the exam."""
        score = 0.8  # Base score
        
        # Check for clinically relevant combinations
        anatomy = components.get('anatomy', [])
        modality = components.get('modality', '')
        
        # Some modality-anatomy combinations are more clinically relevant
        relevant_combinations = [
            ('CT', 'Head'),
            ('CT', 'Chest'),
            ('CT', 'Abdomen'),
            ('MRI', 'Head'),
            ('MRI', 'Spine'),
            ('XR', 'Chest'),
            ('XR', 'Knee'),
            ('US', 'Abdomen')
        ]
        
        for mod, anat in relevant_combinations:
            if modality == mod and anat in anatomy:
                score += 0.1
                break
        
        return min(1.0, score)
    
    def _generate_quality_flags(self, exam_name: str, components: Dict, metrics: Dict) -> List[str]:
        """Generate quality flags based on assessment."""
        flags = []
        
        if metrics['modality_clarity'] < 0.5:
            flags.append('unclear_modality')
        
        if metrics['anatomy_precision'] < 0.5:
            flags.append('unclear_anatomy')
        
        if metrics['terminology_standard'] < 0.6:
            flags.append('non_standard_terminology')
        
        if metrics['completeness'] < 0.6:
            flags.append('incomplete_description')
        
        if len(exam_name) < 5:
            flags.append('very_short_name')
        
        if re.search(r'\b[A-Z]{3,}\b', exam_name):
            flags.append('excessive_abbreviations')
        
        return flags
    
    def _generate_improvement_suggestions(self, exam_name: str, components: Dict, metrics: Dict) -> List[str]:
        """Generate suggestions for improving exam name quality."""
        suggestions = []
        
        if metrics['modality_clarity'] < 0.5:
            suggestions.append('Consider specifying the imaging modality (CT, MRI, XR, US)')
        
        if metrics['anatomy_precision'] < 0.5:
            suggestions.append('Consider specifying the anatomical region more clearly')
        
        if 'study' in exam_name.lower() or 'exam' in exam_name.lower():
            suggestions.append('Consider removing generic terms like "study" or "exam"')
        
        if not components.get('contrast') and 'ct' in exam_name.lower():
            suggestions.append('Consider specifying contrast usage for CT exams')
        
        if len(exam_name) < 10:
            suggestions.append('Consider providing more descriptive exam name')
        
        return suggestions