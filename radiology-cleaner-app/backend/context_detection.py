# --- START OF FILE context_detection.py ---

# =============================================================================
# CONTEXT DETECTION MODULE
# =============================================================================
# This module provides functionality for detecting various contextual information
# from radiology exam names, including gender, age, and clinical contexts.

import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class ContextDetector:
    """
    Detects contextual information from radiology exam names.
    
    Provides methods for identifying:
    - Gender context (male, female, pregnancy)
    - Age context (paediatric, adult)
    - Clinical context (screening, emergency, follow-up, intervention)
    """
    
    def __init__(self):
        """Initialize the context detector with predefined patterns."""
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize regex patterns for context detection."""
        # Pregnancy patterns (highest priority in gender detection)
        self.pregnancy_patterns = [
            r'\b(obstetric|pregnancy|prenatal)\b',
            r'\b(fetal|fetus)\b',
            r'\b(trimester)\b'
        ]
        
        # Female-specific patterns
        self.female_anatomy = ['female pelvis', 'uterus', 'ovary', 'endometrial']
        self.female_patterns = [
            r'\b(female)\b',
            r'\b(woman|women)\b',
            r'\b(gynecological|gynaecological)\b'
        ]
        
        # Male-specific patterns
        self.male_anatomy = ['prostate', 'testicular', 'scrotal']
        self.male_patterns = [
            r'\b(male)\b',
            r'\b(men)\b'
        ]
        
        # Pediatric patterns
        self.pediatric_patterns = [
            r'\b(paediatric|pediatric|paed|peds)\b',
            r'\b(child|children|infant|infants|baby|babies)\b',
            r'\b(newborn|neonate|neonatal)\b',
            r'\b(toddler|adolescent|juvenile)\b',
        ]
        
        # Adult patterns
        self.adult_patterns = [
            r'\b(adult)\b'
        ]
        
        # Clinical context patterns
        self.clinical_patterns = {
            'screening': [r'\b(screening|surveillance)\b'],
            'emergency': [r'\b(emergency|urgent|stat|trauma)\b'],
            'follow-up': [r'\b(follow.?up|post.?op)\b'],
            'intervention': [r'\b(biopsy|drainage|injection|aspiration|fna)\b']
        }
    
    def detect_gender_context(self, exam_name: str, anatomy: List[str] = None) -> Optional[str]:
        """Detect gender/pregnancy context from exam name and anatomy."""
        if not exam_name:
            return None
        exam_lower = exam_name.lower()
        anatomy = anatomy or []
        for pattern in self.pregnancy_patterns:
            if re.search(pattern, exam_lower):
                return 'pregnancy'
        for term in self.female_anatomy:
            if term.lower() in exam_lower:
                return 'female'
        for pattern in self.female_patterns:
            if re.search(pattern, exam_lower):
                return 'female'
        for term in self.male_anatomy:
            if term.lower() in exam_lower:
                return 'male'
        for pattern in self.male_patterns:
            if re.search(pattern, exam_lower):
                return 'male'
        return None
    
    def detect_age_context(self, exam_name: str) -> Optional[str]:
        """Detect age context from exam name (e.g., paediatric, adult)."""
        if not exam_name: return None
        exam_lower = exam_name.lower()
        for pattern in self.pediatric_patterns:
            if re.search(pattern, exam_lower): return 'paediatric'
        for pattern in self.adult_patterns:
            if re.search(pattern, exam_lower): return 'adult'
        return None
    
    def detect_clinical_context(self, exam_name: str, anatomy: List[str] = None) -> List[str]:
        """Detect clinical context from exam name."""
        if not exam_name: return []
        exam_lower = exam_name.lower()
        contexts = []
        for context_type, patterns in self.clinical_patterns.items():
            for pattern in patterns:
                if re.search(pattern, exam_lower):
                    contexts.append(context_type)
                    break
        return contexts
    
    def detect_interventional_procedure_terms(self, exam_name: str) -> List[str]:
        """
        MODIFICATION: Significantly expanded this list to better identify interventional
        procedures for more accurate weighting against the NHS flags. This is crucial for
        differentiating diagnostic from therapeutic exams.
        """
        exam_lower = exam_name.lower()
        interventional_keywords = [
            'stent', 'angioplasty', 'atherectomy', 'thrombectomy', 'thrombolysis',
            'embolisation', 'embolization', 'ablation', 'biopsy', 'bx', 'fna', 'drainage', 
            'aspiration', 'injection', 'nephrostomy', 'gastrostomy', 'jejunostomy', 
            'cholecystostomy', 'vertebroplasty', 'kyphoplasty', 'dilatation', 
            'valvuloplasty', 'septostomy', 'picc', 'line', 'catheter', 'port',
            'guided', 'guidance', 'localisation', 'localization', 'insertion', 'insert',
            'percutaneous'
        ]
        
        found_terms = [
            term for term in interventional_keywords 
            if re.search(r'\b' + re.escape(term) + r'\b', exam_lower)
        ]
        
        return list(set(found_terms))
    
    def detect_all_contexts(self, exam_name: str, anatomy: List[str] = None) -> dict:
        """Detect all types of context in a single call."""
        return {
            'gender_context': self.detect_gender_context(exam_name, anatomy),
            'age_context': self.detect_age_context(exam_name),
            'clinical_context': self.detect_clinical_context(exam_name, anatomy)
        }

# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================
_detector = ContextDetector()

def detect_gender_context(exam_name: str, anatomy: List[str] = None) -> Optional[str]:
    return _detector.detect_gender_context(exam_name, anatomy)

def detect_age_context(exam_name: str) -> Optional[str]:
    return _detector.detect_age_context(exam_name)

def detect_clinical_context(exam_name: str, anatomy: List[str] = None) -> List[str]:
    return _detector.detect_clinical_context(exam_name, anatomy)

def detect_interventional_procedure_terms(exam_name: str) -> List[str]:
    return _detector.detect_interventional_procedure_terms(exam_name)

def detect_all_contexts(exam_name: str, anatomy: List[str] = None) -> dict:
    return _detector.detect_all_contexts(exam_name, anatomy)