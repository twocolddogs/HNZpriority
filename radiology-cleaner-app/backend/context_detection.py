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
            r'\b(toddler|adolescent|juvenile)\b'
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
            'intervention': [r'\b(biopsy|drainage|injection)\b']
        }
    
    def detect_gender_context(self, exam_name: str, anatomy: List[str] = None) -> Optional[str]:
        """
        Detect gender/pregnancy context from exam name and anatomy.
        
        DETECTION HIERARCHY:
        1. Pregnancy-specific terms (highest priority)
        2. Female-specific anatomy and patterns
        3. Male-specific anatomy and patterns
        
        Args:
            exam_name: The exam name to analyze
            anatomy: Optional list of anatomical terms for additional context
            
        Returns:
            'pregnancy', 'female', 'male', or None
        """
        if not exam_name:
            return None
            
        exam_lower = exam_name.lower()
        anatomy = anatomy or []
        
        # Debug logging for gender detection
        logger.info(f"DEBUG: Gender detection for '{exam_name}' -> '{exam_lower}'")
        
        # Check for pregnancy context first (highest priority)
        for pattern in self.pregnancy_patterns:
            if re.search(pattern, exam_lower):
                logger.info(f"DEBUG: Detected pregnancy context for '{exam_name}'")
                return 'pregnancy'
        
        # Check for female-specific context
        # Check female anatomy terms
        for term in self.female_anatomy:
            if term.lower() in exam_lower:
                logger.info(f"DEBUG: Detected female anatomy '{term}' in '{exam_name}'")
                return 'female'
        
        # Check female patterns
        for pattern in self.female_patterns:
            if re.search(pattern, exam_lower):
                logger.info(f"DEBUG: Detected female pattern '{pattern}' in '{exam_name}'")
                return 'female'
        
        # Check for male-specific context
        # Check male anatomy terms
        for term in self.male_anatomy:
            if term.lower() in exam_lower:
                logger.info(f"DEBUG: Detected male anatomy '{term}' in '{exam_name}'")
                return 'male'
        
        # Check male patterns
        for pattern in self.male_patterns:
            if re.search(pattern, exam_lower):
                logger.info(f"DEBUG: Detected male pattern '{pattern}' in '{exam_name}'")
                return 'male'
        
        logger.info(f"DEBUG: No gender context detected for '{exam_name}'")
        return None
    
    def detect_age_context(self, exam_name: str) -> Optional[str]:
        """
        Detect age context from exam name (e.g., paediatric, adult).
        
        Args:
            exam_name: The exam name to analyze
            
        Returns:
            'paediatric', 'adult', or None
        """
        if not exam_name:
            return None
            
        exam_lower = exam_name.lower()
        
        # Check for pediatric patterns
        for pattern in self.pediatric_patterns:
            if re.search(pattern, exam_lower):
                return 'paediatric'
        
        # Check for adult patterns
        for pattern in self.adult_patterns:
            if re.search(pattern, exam_lower):
                return 'adult'
        
        return None
    
    def detect_clinical_context(self, exam_name: str, anatomy: List[str] = None) -> List[str]:
        """
        Detect clinical context from exam name.
        
        Args:
            exam_name: The exam name to analyze
            anatomy: Optional list of anatomical terms (not currently used but kept for compatibility)
            
        Returns:
            List of detected clinical contexts
        """
        if not exam_name:
            return []
            
        exam_lower = exam_name.lower()
        contexts = []
        
        for context_type, patterns in self.clinical_patterns.items():
            for pattern in patterns:
                if re.search(pattern, exam_lower):
                    contexts.append(context_type)
                    break  # Only add each context type once
        
        return contexts
    
    def detect_interventional_procedure_terms(self, exam_name: str) -> List[str]:
        """
        Detect interventional procedure terms from exam name.
        
        Identifies terms that indicate interventional (therapeutic) procedures
        rather than diagnostic procedures, enabling proper weighting in NHS lookup.
        
        Args:
            exam_name: The exam name to analyze
            
        Returns:
            List of detected interventional procedure terms
        """
        import re
        
        exam_lower = exam_name.lower()
        interventional_terms = []
        
        # Interventional procedure patterns
        interventional_patterns = {
            'biopsy': [r'\b(biopsy|biopsies)\b'],
            'drainage': [r'\b(drainage|drain)\b'],
            'injection': [r'\b(injection|inject)\b'],
            'aspiration': [r'\b(aspiration|aspirate)\b'],
            'ablation': [r'\b(ablation|ablate)\b'],
            'embolization': [r'\b(embolization|embolisation|embolize)\b'],
            'stent': [r'\b(stent|stenting)\b'],
            'angioplasty': [r'\b(angioplasty)\b'],
            'therapeutic': [r'\b(therapeutic|therapy)\b'],
            'guided': [r'\b(guided|guide)\b'],
            'percutaneous': [r'\b(percutaneous)\b'],
            'endovascular': [r'\b(endovascular)\b'],
            'catheter': [r'\b(catheter|catheterization)\b'],
            'procedure': [r'\b(procedure)\b'],
            'intervention': [r'\b(intervention|interventional)\b'],
            'treatment': [r'\b(treatment|treat)\b'],
            'repair': [r'\b(repair)\b'],
            'reconstruction': [r'\b(reconstruction|reconstruct)\b'],
            'removal': [r'\b(removal|remove)\b'],
            'placement': [r'\b(placement|place)\b'],
            'insertion': [r'\b(insertion|insert)\b'],
            'retrieval': [r'\b(retrieval|retrieve)\b'],
            'thrombectomy': [r'\b(thrombectomy)\b'],
            'thrombolysis': [r'\b(thrombolysis)\b'],
            'sclerotherapy': [r'\b(sclerotherapy)\b'],
            'vertebroplasty': [r'\b(vertebroplasty)\b'],
            'kyphoplasty': [r'\b(kyphoplasty)\b'],
            'radiofrequency': [r'\b(radiofrequency|rf)\b'],
            'cryotherapy': [r'\b(cryotherapy|cryo)\b'],
            'balloon': [r'\b(balloon)\b'],
            'coil': [r'\b(coil|coiling)\b'],
            'filter': [r'\b(filter)\b'],
            'nephrostomy': [r'\b(nephrostomy)\b'],
            'gastrostomy': [r'\b(gastrostomy)\b'],
            'cholecystostomy': [r'\b(cholecystostomy)\b'],
            'biliary': [r'\b(biliary drainage|biliary stent)\b'],
            'vascular': [r'\b(vascular access|vascular intervention)\b']
        }
        
        for term, patterns in interventional_patterns.items():
            for pattern in patterns:
                if re.search(pattern, exam_lower):
                    interventional_terms.append(term)
                    break  # Only add each term once
        
        return interventional_terms
    
    def detect_all_contexts(self, exam_name: str, anatomy: List[str] = None) -> dict:
        """
        Detect all types of context in a single call.
        
        Args:
            exam_name: The exam name to analyze
            anatomy: Optional list of anatomical terms for additional context
            
        Returns:
            Dictionary containing all detected contexts
        """
        return {
            'gender_context': self.detect_gender_context(exam_name, anatomy),
            'age_context': self.detect_age_context(exam_name),
            'clinical_context': self.detect_clinical_context(exam_name, anatomy),
            'is_paediatric': self.detect_age_context(exam_name) == 'paediatric'
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================
# These functions provide backward compatibility and simple usage patterns

# Global instance for convenience
_detector = ContextDetector()

def detect_gender_context(exam_name: str, anatomy: List[str] = None) -> Optional[str]:
    """Convenience function for gender context detection."""
    return _detector.detect_gender_context(exam_name, anatomy)

def detect_age_context(exam_name: str) -> Optional[str]:
    """Convenience function for age context detection."""
    return _detector.detect_age_context(exam_name)

def detect_clinical_context(exam_name: str, anatomy: List[str] = None) -> List[str]:
    """Convenience function for clinical context detection."""
    return _detector.detect_clinical_context(exam_name, anatomy)

def detect_interventional_procedure_terms(exam_name: str) -> List[str]:
    """
    Convenience function for detecting interventional procedure terms.
    
    Args:
        exam_name: The exam name to analyze
        
    Returns:
        List of detected interventional procedure terms
    """
    return _detector.detect_interventional_procedure_terms(exam_name)

def detect_all_contexts(exam_name: str, anatomy: List[str] = None) -> dict:
    """Convenience function for detecting all contexts."""
    return _detector.detect_all_contexts(exam_name, anatomy)