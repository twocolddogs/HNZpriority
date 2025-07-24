# =============================================================================
# COMPLEXITY SCORING METHODS
# =============================================================================

import re

class ComplexityScorer:
    """Analyzes and scores text complexity for radiology exam names."""
    
    def calculate_structural_complexity(self, text: str) -> float:
        """Detect complexity through linguistic and structural patterns."""
        complexity_score = 0.0
        text_lower = text.lower()
        prepositions = ['of', 'with', 'without', 'during', 'using', 'via', 'through', 'under', 'over']
        prep_count = sum(1 for prep in prepositions if f' {prep} ' in f' {text_lower} ')
        prep_density = prep_count / max(len(text_lower.split()), 1)
        complexity_score += min(prep_density * 2.0, 0.3)
        conjunctions = [' and ', ' or ', ' with ', ' plus ', ' including ']
        conjunction_count = sum(conj in text_lower for conj in conjunctions)
        complexity_score += min(conjunction_count * 0.15, 0.3)
        adjective_patterns = [r'\w+ed\b', r'\w+al\b', r'\w+ic\b', r'\w+ous\b']
        adjective_count = sum(len(re.findall(pattern, text_lower)) for pattern in adjective_patterns)
        adjective_density = adjective_count / max(len(text_lower.split()), 1)
        complexity_score += min(adjective_density * 0.4, 0.25)
        return min(complexity_score, 1.0)
    
    def calculate_terminology_complexity(self, text: str) -> float:
        """Detect complexity through medical terminology patterns."""
        complexity_score = 0.0
        text_lower = text.lower()
        hyphenated_terms = re.findall(r'\b\w+-\w+\b', text_lower)
        complexity_score += min(len(hyphenated_terms) * 0.2, 0.4)
        words = text_lower.split()
        long_medical_words = [w for w in words if len(w) > 8 and w.isalpha()]
        long_word_density = len(long_medical_words) / max(len(words), 1)
        complexity_score += min(long_word_density * 0.5, 0.3)
        classical_patterns = [r'graph', r'scopy', r'metry', r'plasty', r'ectomy', r'ostomy']
        classical_count = sum(1 for pattern in classical_patterns if re.search(pattern, text_lower))
        complexity_score += min(classical_count * 0.15, 0.3)
        return min(complexity_score, 1.0)

    def calculate_input_qualifier_complexity(self, input_text: str) -> float:
        """Detect complexity from input qualifier patterns."""
        complexity_score = 0.0
        text_lower = input_text.lower()
        separator_patterns = [r'\+', r'\&', r'w/', r'with', r'and(?=\s+\w+$)']
        separator_count = sum(len(re.findall(pattern, text_lower)) for pattern in separator_patterns)
        complexity_score += min(separator_count * 0.25, 0.5)
        abbrev_pattern = r'\b[A-Z]{2,}\b'
        abbrev_matches = re.findall(abbrev_pattern, input_text)
        abbrev_density = len(abbrev_matches) / max(len(input_text.split()), 1)
        complexity_score += min(abbrev_density * 0.3, 0.25)
        numeric_patterns = [r'\d+\s*phase', r'\d+\s*view', r'\d+\s*slice', r'\d+D', r'x\d+']
        numeric_count = sum(1 for p in numeric_patterns if re.search(p, text_lower))
        complexity_score += min(numeric_count * 0.2, 0.3)
        paren_content = re.findall(r'\([^)]+\)', text_lower)
        complexity_score += min(len(paren_content) * 0.15, 0.2)
        return min(complexity_score, 1.0)

    def calculate_fsn_total_complexity(self, fsn: str) -> float:
        """Calculate total complexity score for FSN."""
        structural = self.calculate_structural_complexity(fsn)
        terminology = self.calculate_terminology_complexity(fsn)
        return min(structural + terminology, 1.0)
    
    def calculate_complexity_appropriateness(self, input_exam: str, fsn: str, primary_name: str) -> float:
        """Calculate how appropriate FSN complexity is for input complexity."""
        input_complexity = self.calculate_input_qualifier_complexity(input_exam)
        fsn_complexity = self.calculate_fsn_total_complexity(fsn)
        primary_complexity = min(self.calculate_structural_complexity(primary_name) + self.calculate_terminology_complexity(primary_name), 1.0)
        hidden_complexity = max(0, fsn_complexity - primary_complexity)
        
        if input_complexity < 0.3:
            return max(0.2, 1.0 - (hidden_complexity * 2)) if hidden_complexity >= 0.2 else 1.0
        elif input_complexity > 0.5:
            return min(1.0, 0.7 + (hidden_complexity * 0.5))
        else:
            return max(0.3, 1.0 - abs(fsn_complexity - input_complexity))