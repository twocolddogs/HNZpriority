# --- START OF FILE context_detection.py ---

# =============================================================================
# CONTEXT DETECTION MODULE (V2 - ENHANCED PATTERNS)
# =============================================================================
# This module provides functionality for detecting various contextual information
# from radiology exam names, including gender, age, and clinical contexts.
# This version features significantly expanded keyword lists for greater accuracy.

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
    - Specific interventional procedure terms for advanced scoring.
    """
    
    def __init__(self):
        """Initialize the context detector with predefined patterns."""
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize regex patterns and keyword lists for context detection."""
        # Pregnancy patterns (given highest priority in gender detection)
        self.pregnancy_patterns = [
            r'\b(obstetric|pregnancy|prenatal)\b',
            r'\b(fetal|fetus)\b',
            r'\b(trimester)\b'
        ]
        
        # Female-specific anatomy and keywords (ENHANCED)
        self.female_anatomy = [
            'female pelvis', 'uterus', 'ovary', 'ovaries', 'endometrial', 'cervix', 'cervical screening', 'cervical smear',
            'mammogram', 'mammography', 'breast', 'breasts', 'transvaginal'
        ]
        self.female_patterns = [
            r'\b(female)\b',
            r'\b(woman|women)\b',
            r'\b(gynae|gynecological|gynaecological)\b' # Added 'gynae'
        ]
        
        # Male-specific anatomy and keywords (ENHANCED)
        self.male_anatomy = [
            'prostate', 'testicular', 'scrotal', 'scrotum', 'testes', 'testicle', 'testicles',
            'penis', 'penile'
        ]
        self.male_patterns = [
            r'\b(male)\b',
            r'\b(men)\b'
        ]
        
        # Pediatric patterns (ENHANCED)
        self.pediatric_patterns = [
            r'\b(paediatric|pediatric|paed|peds)\b',
            r'\b(child|children|infant|infants|baby|babies)\b',
            r'\b(newborn|neonate|neonatal)\b',
            r'\b(toddler|adolescent|juvenile)\b',
            r'\b(cdh|congenital)\b',
            r'\b(hip dysplasia|hips screening)\b',
            r'\b(developmental)\b'
        ]
        
        # Adult patterns (simple but useful for explicit cases)
        self.adult_patterns = [
            r'\b(adult)\b'
        ]
        
        # Clinical context patterns for general classification
        self.clinical_patterns = {
            'screening': [r'\b(screening|surveillance)\b'],
            'emergency': [r'\b(emergency|urgent|stat|trauma|acute)\b'], # Added 'acute'
            'follow-up': [r'\b(follow.?up|post.?op|fu)\b'], # Added 'fu'
            
            # NEW CATEGORY: Explicitly identify routine diagnostic scans. This is a very strong signal.
            'diagnostic': [r'\b(standard|routine|plain|simple|diagnostic|baseline|non-contrast)\b'],
            
            # Keep intervention, but it's now balanced by the 'diagnostic' category
            'intervention': [r'\b(biopsy|drainage|injection|aspiration|fna|guided|guidance|insertion|placement|line|picc)\b']
        }
    
    def detect_gender_context(self, exam_name: str, anatomy: List[str] = None) -> Optional[str]:
        """Detect gender/pregnancy context from exam name and parsed anatomy."""
        if not exam_name:
            return None
            
        exam_lower = exam_name.lower()
        anatomy = [a.lower() for a in (anatomy or [])]
        
        # Check for pregnancy first as it's the most specific context
        for pattern in self.pregnancy_patterns:
            if re.search(pattern, exam_lower):
                return 'pregnancy'
                
        # Check female-specific anatomy and keywords
        for term in self.female_anatomy:
            if term in exam_lower or term in anatomy:
                return 'female'
        for pattern in self.female_patterns:
            if re.search(pattern, exam_lower):
                return 'female'
                
        # Check male-specific anatomy and keywords
        for term in self.male_anatomy:
            if term in exam_lower or term in anatomy:
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
        """Detect general clinical context from exam name (e.g., screening, emergency)."""
        if not exam_name: return []
        exam_lower = exam_name.lower()
        contexts = []
        for context_type, patterns in self.clinical_patterns.items():
            for pattern in patterns:
                if re.search(pattern, exam_lower):
                    contexts.append(context_type)
                    break # Avoid adding the same context type multiple times
        return sorted(list(set(contexts)))
    
    
    def detect_all_contexts(self, exam_name: str, anatomy: List[str] = None) -> dict:
        """Detect all types of context in a single call for efficiency."""
        return {
            'gender_context': self.detect_gender_context(exam_name, anatomy),
            'age_context': self.detect_age_context(exam_name),
            'clinical_context': self.detect_clinical_context(exam_name, anatomy)
        }

# =============================================================================
# CONVENIENCE FUNCTIONS (SINGLETON PATTERN)
# =============================================================================
# Create a single global instance to avoid re-initializing patterns on every call.
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

# --- END OF FILE context_detection.py ---
