#!/usr/bin/env python3
"""
NHS Radiology Scoring Engine

Handles all scoring logic for NHS exam matching including:
- Component scoring (anatomy, modality, laterality, contrast, technique)
- Complexity-aware scoring 
- Context bonuses and penalties
- Final score calculation and weighting

This module is separated from nhs_lookup_engine.py for better maintainability.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

# Import context detection functions
from context_detection import detect_gender_context, detect_age_context, detect_clinical_context

logger = logging.getLogger(__name__)

class ScoringEngine:
    """Handles all scoring logic for NHS exam matching"""
    
    def __init__(self, config: Dict, modality_similarity: Dict = None, context_scoring: Dict = None, preprocessing_config: Dict = None):
        """Initialize scoring engine with configuration"""
        self.config = config
        self.modality_similarity = modality_similarity or {}
        self.context_scoring = context_scoring or {}
        self.preprocessing_config = preprocessing_config or {}
    
    # =============================================================================
    # COMPLEXITY SCORING METHODS
    # =============================================================================
    
    def calculate_structural_complexity(self, text: str) -> float:
        """Detect complexity through linguistic and structural patterns"""
        
        complexity_score = 0.0
        text_lower = text.lower()
        
        # Pattern 1: Preposition density (indicates procedural/anatomical complexity)
        prepositions = ['of', 'with', 'without', 'during', 'using', 'via', 'through', 'under', 'over']
        prep_count = sum(1 for prep in prepositions if f' {prep} ' in f' {text_lower} ')
        prep_density = prep_count / max(len(text_lower.split()), 1)
        complexity_score += min(prep_density * 2.0, 0.3)  # Cap at 0.3
        
        # Pattern 2: Conjunctive complexity (multiple components)
        conjunctions = [' and ', ' or ', ' with ', ' plus ', ' including ']
        conjunction_count = sum(1 for conj in conjunctions if conj in text_lower)
        complexity_score += min(conjunction_count * 0.15, 0.3)
        
        # Pattern 3: Qualification pattern (adjective density)
        words = text_lower.split()
        
        # Common medical adjective patterns
        adjective_patterns = [
            r'\w+ed\b',      # past participles: "enhanced", "weighted", "guided"
            r'\w+al\b',      # technical adjectives: "arterial", "functional", "bilateral"
            r'\w+ic\b',      # scientific adjectives: "dynamic", "stereotactic", "pharmacologic"
            r'\w+ous\b',     # quality adjectives: "intravenous", "continuous"
        ]
        
        adjective_count = 0
        for pattern in adjective_patterns:
            adjective_count += len(re.findall(pattern, text_lower))
        
        adjective_density = adjective_count / max(len(words), 1)
        complexity_score += min(adjective_density * 0.4, 0.25)
        
        return min(complexity_score, 1.0)
    
    def calculate_terminology_complexity(self, text: str) -> float:
        """Detect complexity through medical terminology patterns"""
        
        complexity_score = 0.0
        text_lower = text.lower()
        
        # Pattern 1: Compound medical terms (indicates specialization)
        hyphenated_terms = re.findall(r'\b\w+-\w+\b', text_lower)
        complexity_score += min(len(hyphenated_terms) * 0.2, 0.4)
        
        # Pattern 2: Multi-syllabic medical terms (complexity through specificity)
        words = text_lower.split()
        long_medical_words = [w for w in words if len(w) > 8 and w.isalpha()]
        long_word_density = len(long_medical_words) / max(len(words), 1)
        complexity_score += min(long_word_density * 0.5, 0.3)
        
        # Pattern 3: Latin/Greek roots (medical complexity indicator)
        classical_patterns = [
            r'graph',    # imaging: angiography, cholangiography
            r'scopy',    # visualization: arthroscopy, endoscopy  
            r'metry',    # measurement: dosimetry, morphometry
            r'plasty',   # surgical reconstruction
            r'ectomy',   # surgical removal
            r'ostomy',   # surgical opening
        ]
        
        classical_count = sum(1 for pattern in classical_patterns if re.search(pattern, text_lower))
        complexity_score += min(classical_count * 0.15, 0.3)
        
        return min(complexity_score, 1.0)
    
    def calculate_input_qualifier_complexity(self, input_text: str) -> float:
        """Detect complexity from input qualifier patterns"""
        
        complexity_score = 0.0
        text_lower = input_text.lower()
        
        # Pattern 1: Plus notation and separators (strongest complexity indicator)
        separator_patterns = [r'\+', r'\&', r'w/', r'with', r'and(?=\s+\w+$)']
        separator_count = 0
        for pattern in separator_patterns:
            separator_count += len(re.findall(pattern, text_lower))
        
        complexity_score += min(separator_count * 0.25, 0.5)  # Strong weight for separators
        
        # Pattern 2: Abbreviation density (shortened complex terms)
        abbrev_pattern = r'\b[A-Z]{2,}\b'  # 2+ consecutive capitals
        abbrev_matches = re.findall(abbrev_pattern, input_text)
        abbrev_density = len(abbrev_matches) / max(len(input_text.split()), 1)
        complexity_score += min(abbrev_density * 0.3, 0.25)
        
        # Pattern 3: Numeric/parametric indicators (complexity through parameters)
        numeric_patterns = [r'\d+\s*phase', r'\d+\s*view', r'\d+\s*slice', r'\d+D', r'x\d+']
        numeric_count = sum(1 for pattern in numeric_patterns if re.search(pattern, text_lower))
        complexity_score += min(numeric_count * 0.2, 0.3)
        
        # Pattern 4: Parenthetical qualifiers (additional specifications)
        paren_content = re.findall(r'\([^)]+\)', text_lower)
        complexity_score += min(len(paren_content) * 0.15, 0.2)
        
        return min(complexity_score, 1.0)
    
    def calculate_fsn_total_complexity(self, fsn: str) -> float:
        """Calculate total complexity score for FSN"""
        structural = self.calculate_structural_complexity(fsn)
        terminology = self.calculate_terminology_complexity(fsn)
        return min(structural + terminology, 1.0)
    
    def calculate_complexity_appropriateness(self, input_exam: str, fsn: str, primary_name: str) -> float:
        """Calculate how appropriate FSN complexity is for input complexity"""
        
        # Input complexity from qualifiers
        input_complexity = self.calculate_input_qualifier_complexity(input_exam)
        
        # FSN true complexity  
        fsn_complexity = self.calculate_fsn_total_complexity(fsn)
        
        # Primary name complexity (character-limited like input)
        primary_structural = self.calculate_structural_complexity(primary_name)
        primary_terminology = self.calculate_terminology_complexity(primary_name)
        primary_complexity = min(primary_structural + primary_terminology, 1.0)
        
        # Hidden complexity in FSN
        hidden_complexity = max(0, fsn_complexity - primary_complexity)
        
        # Matching logic
        if input_complexity < 0.3:  # Simple input
            # Prefer FSNs without hidden complexity
            if hidden_complexity < 0.2:
                return 1.0  # Good match
            else:
                return max(0.2, 1.0 - (hidden_complexity * 2))  # Penalty for hidden complexity
                
        elif input_complexity > 0.5:  # Complex input  
            # Can handle FSNs with hidden complexity
            return min(1.0, 0.7 + (hidden_complexity * 0.5))  # Bonus for appropriate complexity
            
        else:  # Moderate input
            # Balanced approach
            complexity_diff = abs(fsn_complexity - input_complexity)
            return max(0.3, 1.0 - complexity_diff)
    
    # =============================================================================
    # COMPONENT SCORING METHODS (moved from nhs_lookup_engine.py)
    # =============================================================================
    
    def calculate_component_score(self, input_exam: str, input_components: Dict, nhs_entry: Dict) -> float:
        """Calculate component-based score for NHS entry match"""
        
        # Get NHS parsed components
        nhs_components = nhs_entry.get('_parsed_components', {})
        
        # Calculate individual component scores
        anatomy_score = self._calculate_anatomy_score_with_constraints(input_components, nhs_components)
        modality_score = self._calculate_modality_score(
            input_components.get('modality', []),
            nhs_components.get('modality', [])
        )
        contrast_score = self._calculate_contrast_score(
            input_components.get('contrast', []),
            nhs_components.get('contrast', [])
        )
        laterality_score = self._calculate_set_score(
            input_components.get('laterality', []),
            nhs_components.get('laterality', [])
        )
        technique_score = self._calculate_set_score(
            input_components.get('technique', []),
            nhs_components.get('technique', [])
        )
        
        # Check for blocking penalties
        diagnostic_penalty = self._calculate_diagnostic_penalty(input_exam, nhs_entry)
        hybrid_modality_penalty = self._calculate_hybrid_modality_penalty(input_exam, nhs_entry)
        technique_specialization_penalty = self._calculate_technique_specialization_penalty(input_exam, nhs_entry)
        
        # Check for blocking violations (< -1.0)
        if diagnostic_penalty < -1.0 or hybrid_modality_penalty < -1.0 or technique_specialization_penalty < -1.0:
            logger.debug(f"Blocking violation detected for '{nhs_entry.get('primary_source_name')}', returning 0.0 score.")
            return 0.0
        
        # Check for anatomy blocking penalty
        if anatomy_score < -1.0:
            logger.debug(f"Anatomical blocking violation for '{nhs_entry.get('primary_source_name')}', returning 0.0 score.")
            return 0.0
        
        # Check component thresholds
        if violation := self._check_component_thresholds(anatomy_score, modality_score, laterality_score, contrast_score, technique_score):
            logger.debug(f"Component threshold violation for '{nhs_entry.get('primary_source_name')}': {violation}")
            return 0.0
        
        # Calculate weighted component score
        weights = self.config['weights_component']
        base_component_score = (
            weights['anatomy'] * anatomy_score +
            weights['modality'] * modality_score +
            weights['laterality'] * laterality_score +
            weights['contrast'] * contrast_score +
            weights['technique'] * technique_score
        )
        
        # Apply bonuses and penalties
        bonus_score = 0.0
        bonus_score += self._calculate_interventional_score(nhs_entry)
        bonus_score += self._calculate_anatomical_specificity_score(input_components, nhs_components)
        bonus_score += diagnostic_penalty + hybrid_modality_penalty + technique_specialization_penalty
        bonus_score += self._calculate_context_bonus(input_exam, nhs_entry, input_components.get('anatomy', []))
        bonus_score += self._calculate_synonym_bonus(input_exam, nhs_entry)
        bonus_score += self._calculate_biopsy_modality_preference(input_exam, nhs_entry)
        
        # Exact match bonus
        if input_exam.strip().lower() == nhs_entry.get('primary_source_name', '').lower():
            bonus_score += self.config.get('exact_match_bonus', 0.25)
        
        final_component_score = base_component_score + bonus_score
        return max(0.0, min(1.0, final_component_score))
    
    # =============================================================================
    # FINAL SCORE CALCULATION
    # =============================================================================
    
    def calculate_final_score(
        self,
        input_exam: str,
        input_components: Dict,
        nhs_entry: Dict,
        rerank_score: float
    ) -> Tuple[float, Dict]:
        """
        Calculate final weighted score including complexity appropriateness
        
        Returns:
            Tuple of (final_score, score_breakdown)
        """
        
        # 1. Component score
        component_score = self.calculate_component_score(input_exam, input_components, nhs_entry)
        
        # 2. Complexity appropriateness score
        fsn = nhs_entry.get('snomed_fsn', '')
        primary_name = nhs_entry.get('primary_source_name', '')
        complexity_score = self.calculate_complexity_appropriateness(input_exam, fsn, primary_name)
        
        # 3. Get weights from config
        weights = self.config['weights_final']
        reranker_weight = weights.get('reranker', 0.50)
        component_weight = weights.get('component', 0.35)
        complexity_weight = weights.get('complexity', 0.15)
        
        # 4. Calculate final weighted score
        final_score = (
            reranker_weight * rerank_score +
            component_weight * component_score +
            complexity_weight * complexity_score
        )
        
        # 5. Create detailed breakdown for debugging
        score_breakdown = {
            'rerank_score': rerank_score,
            'component_score': component_score,
            'complexity_score': complexity_score,
            'final_score': final_score,
            'weights': {
                'reranker': reranker_weight,
                'component': component_weight,
                'complexity': complexity_weight
            }
        }
        
        return final_score, score_breakdown
    
    # =============================================================================
    # HELPER METHODS (placeholder - would move existing methods from nhs_lookup_engine.py)
    # =============================================================================
    
    def _calculate_anatomy_score_with_constraints(self, input_components: Dict, nhs_components: Dict) -> float:
        """
        Calculate anatomy score with anatomical compatibility constraints.
        
        PIPELINE STEP: This method enforces anatomical compatibility constraints to prevent 
        impossible mappings like "Lower Limb" → "Penis" that could cause patient safety issues.
        
        Args:
            input_components: Parsed components from user input exam name
            nhs_components: Parsed components from NHS database entry
            
        Returns:
            float: Anatomy score (0.0 to 1.0), or severe penalty (-10.0) for incompatible pairs
        """
        # Get anatomy sets from both input and NHS entry
        input_anatomy = set(str(a).lower() for a in input_components.get('anatomy', []))
        nhs_anatomy = set(str(a).lower() for a in nhs_components.get('anatomy', []))
        
        # Check if anatomical compatibility constraints are enabled
        constraint_config = self.config.get('anatomical_compatibility_constraints', {})
        if constraint_config.get('enable', False):
            # Get incompatible pairs from config
            incompatible_pairs = constraint_config.get('incompatible_pairs', [])
            blocking_penalty = constraint_config.get('blocking_penalty', -10.0)
            
            # Check each input anatomy term against each NHS anatomy term
            for input_term in input_anatomy:
                for nhs_term in nhs_anatomy:
                    # Check if this combination is in the incompatible pairs list
                    for pair in incompatible_pairs:
                        if len(pair) >= 2:
                            # Check both directions: [input, nhs] and [nhs, input]
                            if ((input_term in pair[0] or pair[0] in input_term) and 
                                (nhs_term in pair[1] or pair[1] in nhs_term)) or \
                               ((input_term in pair[1] or pair[1] in input_term) and 
                                (nhs_term in pair[0] or pair[0] in nhs_term)):
                                logger.warning(f"ANATOMICAL CONSTRAINT VIOLATION: Blocking impossible mapping "
                                             f"'{input_term}' → '{nhs_term}' (penalty: {blocking_penalty})")
                                return blocking_penalty
        
        # If no constraints violated, calculate normal set-based anatomy score
        if not input_anatomy and not nhs_anatomy: 
            return 1.0
        if not input_anatomy.union(nhs_anatomy): 
            return 0.0
        return len(input_anatomy.intersection(nhs_anatomy)) / len(input_anatomy.union(nhs_anatomy))
    
    def _calculate_modality_score(self, input_modality: List[str], nhs_modality: List[str]) -> float:
        """Calculate modality score with similarity mappings"""
        # Handle empty lists
        if not input_modality or not nhs_modality: 
            return 0.5
        
        # For single modality lists, use direct comparison and similarity
        if len(input_modality) == 1 and len(nhs_modality) == 1:
            input_mod = input_modality[0]
            nhs_mod = nhs_modality[0]
            if input_mod == nhs_mod: 
                return 1.0
            return self.modality_similarity.get(input_mod, {}).get(nhs_mod, 0.0)
        
        # For multiple modalities, use set-based scoring
        return self._calculate_set_score(input_modality, nhs_modality)
    
    def _calculate_contrast_score(self, input_contrast: List[str], nhs_contrast: List[str]) -> float:
        """Calculate contrast score with special handling for contrast states"""
        # Handle empty lists (no contrast specified)
        if not input_contrast and not nhs_contrast:
            # Both unspecified - perfect match with potential bonus
            if self.config.get('prefer_no_contrast_when_unspecified', False):
                return 1.0 + self.config.get('no_contrast_preference_bonus', 0.15)
            return 1.0
        
        # One has contrast info, one doesn't
        if not input_contrast or not nhs_contrast:
            return self.config.get('contrast_null_score', 0.7)
        
        # Both have contrast info - check for matches
        input_set = set(input_contrast)
        nhs_set = set(nhs_contrast)
        
        # Perfect match
        if input_set == nhs_set:
            return 1.0
        
        # Partial match (some overlap)
        if input_set.intersection(nhs_set):
            return 0.8
        
        # No match (e.g., 'with' vs 'without') - severe penalty
        return self.config.get('contrast_mismatch_score', 0.05)
    
    def _calculate_set_score(self, list1: List[str], list2: List[str]) -> float:
        """
        Calculates a Jaccard similarity score between two lists of strings.
        (Intersection over Union)
        """
        set1, set2 = set(list1), set(list2)
        if not set1 and not set2:
            return 1.0  # Both empty is a perfect match.

        union = set1.union(set2)
        if not union:
            return 0.0  # Should be covered by the above, but for safety.

        intersection = set1.intersection(set2)
        return len(intersection) / len(union)
    
    def _calculate_diagnostic_penalty(self, input_exam: str, nhs_entry: Dict) -> float:
        """
        Check diagnostic protection rules to prevent diagnostic exams mapping to interventional procedures.
        
        PIPELINE STEP: This method prevents diagnostic exams (marked as "Standard", "routine", etc.) 
        from being incorrectly mapped to interventional procedures (containing "excision", "biopsy", etc.).
        
        Args:
            input_exam: Original user input exam name
            nhs_entry: NHS database entry being considered for matching
            
        Returns:
            float: 0.0 for normal processing, or severe penalty for diagnostic→interventional violations
        """
        # Get diagnostic protection config
        protection_config = self.config.get('diagnostic_protection', {})
        if not protection_config.get('enable', False):
            return 0.0
        
        # Get keyword lists from config
        diagnostic_indicators = protection_config.get('diagnostic_indicators', [])
        interventional_indicators = protection_config.get('interventional_indicators', [])
        blocking_penalty = protection_config.get('blocking_penalty', -8.0)
        
        # Convert to lowercase for case-insensitive matching
        input_lower = input_exam.lower()
        nhs_name_lower = nhs_entry.get('primary_source_name', '').lower()
        
        # Check if input contains diagnostic indicators
        input_has_diagnostic = any(indicator.lower() in input_lower for indicator in diagnostic_indicators)
        
        # Check if NHS entry contains interventional indicators  
        nhs_has_interventional = any(indicator.lower() in nhs_name_lower for indicator in interventional_indicators)
        
        # If input is marked as diagnostic but NHS entry is interventional, block the mapping
        if input_has_diagnostic and nhs_has_interventional:
            # Find which specific indicators triggered the violation
            triggered_diagnostic = [ind for ind in diagnostic_indicators if ind.lower() in input_lower]
            triggered_interventional = [ind for ind in interventional_indicators if ind.lower() in nhs_name_lower]
            
            logger.warning(f"DIAGNOSTIC PROTECTION VIOLATION: Blocking diagnostic→interventional mapping. "
                          f"Input has diagnostic indicators {triggered_diagnostic}, "  
                          f"NHS entry has interventional indicators {triggered_interventional} "
                          f"(penalty: {blocking_penalty})")
            return blocking_penalty
        
        # No violation detected
        return 0.0
    
    def _calculate_hybrid_modality_penalty(self, input_exam: str, nhs_entry: Dict) -> float:
        """
        Check hybrid modality constraints to prevent inappropriate hybrid modality confusion.
        
        PIPELINE STEP: This method prevents hybrid modality confusion like PET/CT → PET/MRI 
        that could affect clinical workflow and equipment availability.
        
        Args:
            input_exam: Original user input exam name
            nhs_entry: NHS database entry being considered for matching
            
        Returns:
            float: 0.0 for normal processing, or penalty for hybrid modality violations
        """
        # Get hybrid modality constraints config
        hybrid_config = self.config.get('hybrid_modality_constraints', {})
        if not hybrid_config.get('enable', False):
            return 0.0
        
        # Get constraint rules and penalty
        incompatibilities = hybrid_config.get('hybrid_incompatibilities', [])
        blocking_penalty = hybrid_config.get('blocking_penalty', -6.0)
        
        # Convert to lowercase for case-insensitive matching
        input_lower = input_exam.lower()
        nhs_name_lower = nhs_entry.get('primary_source_name', '').lower()
        
        # Check each hybrid incompatibility rule
        for rule in incompatibilities:
            input_pattern = rule.get('input_pattern', '')
            nhs_exclusions = rule.get('nhs_exclusions', [])
            reason = rule.get('reason', 'Hybrid modality constraint')
            
            # Check if input matches the pattern
            if input_pattern and re.search(input_pattern, input_lower):
                # Check if NHS entry matches any exclusion pattern
                for exclusion_pattern in nhs_exclusions:
                    if exclusion_pattern and re.search(exclusion_pattern, nhs_name_lower):
                        logger.warning(f"HYBRID MODALITY CONSTRAINT VIOLATION: {reason}. "
                                      f"Input '{input_exam}' matches pattern '{input_pattern}', "
                                      f"NHS entry '{nhs_entry.get('primary_source_name', '')}' "
                                      f"matches exclusion '{exclusion_pattern}' (penalty: {blocking_penalty})")
                        return blocking_penalty
        
        # No violation detected
        return 0.0
    
    def _calculate_technique_specialization_penalty(self, input_exam: str, nhs_entry: Dict) -> float:
        """
        Calculate technique specialization penalty.
        
        DEPRECATED: This functionality is now handled by the complexity scoring system which provides
        more nuanced matching between input complexity and FSN complexity. The complexity scoring
        naturally prevents simple inputs like "MRI BRAIN" from matching overly complex FSNs like
        "MRI Diffusion Weighted Brain" without needing explicit constraint rules.
        
        Args:
            input_exam: Original input exam name text
            nhs_entry: NHS database entry being evaluated
            
        Returns:
            float: Always returns 0.0 (disabled in favor of complexity scoring)
        """
        # DISABLED: Complexity scoring now handles this functionality more effectively
        return 0.0
    
    def _check_component_thresholds(self, anatomy_score: float, modality_score: float, 
                                   laterality_score: float, contrast_score: float, technique_score: float) -> Optional[str]:
        """
        Check minimum component score thresholds to prevent semantic similarity override.
        
        PIPELINE STEP: This method ensures that fundamental component mismatches 
        cannot be overcome by high semantic similarity alone, maintaining clinical accuracy.
        
        Args:
            anatomy_score: Individual anatomy component score
            modality_score: Individual modality component score  
            laterality_score: Individual laterality component score
            contrast_score: Individual contrast component score
            technique_score: Individual technique component score
            
        Returns:
            Optional[str]: Violation description if threshold violated, None if passed
        """
        # Get threshold configuration
        threshold_config = self.config.get('minimum_component_thresholds', {})
        if not threshold_config.get('enable', False):
            return None
        
        # Get individual thresholds
        anatomy_min = threshold_config.get('anatomy_min', 0.1)
        modality_min = threshold_config.get('modality_min', 0.4)
        laterality_min = threshold_config.get('laterality_min', 0.0)
        contrast_min = threshold_config.get('contrast_min', 0.3)
        technique_min = threshold_config.get('technique_min', 0.0)
        
        # Check individual component thresholds
        if anatomy_score < anatomy_min:
            return f"Anatomy score {anatomy_score:.3f} below minimum {anatomy_min}"
        if modality_score < modality_min:
            return f"Modality score {modality_score:.3f} below minimum {modality_min}"
        if laterality_score < laterality_min:
            return f"Laterality score {laterality_score:.3f} below minimum {laterality_min}"
        if contrast_score < contrast_min:
            return f"Contrast score {contrast_score:.3f} below minimum {contrast_min}"
        if technique_score < technique_min:
            return f"Technique score {technique_score:.3f} below minimum {technique_min}"
        
        # Check combined component score threshold
        combined_min = threshold_config.get('combined_min', 0.25)
        w = self.config.get('weights_component', {})
        combined_score = (w.get('anatomy', 0.25) * anatomy_score + 
                         w.get('modality', 0.30) * modality_score + 
                         w.get('laterality', 0.15) * laterality_score + 
                         w.get('contrast', 0.20) * contrast_score + 
                         w.get('technique', 0.10) * technique_score)
        
        if combined_score < combined_min:
            return f"Combined component score {combined_score:.3f} below minimum {combined_min}"
        
        # All thresholds passed
        return None
    
    def _calculate_interventional_score(self, nhs_entry: Dict) -> float:
        """Calculate interventional bonus/penalty score"""
        # Get technique information from NHS components
        nhs_components = nhs_entry.get('_parsed_components', {})
        nhs_techniques = set(nhs_components.get('technique', []))
        is_nhs_interventional = any('Interventional' in t for t in nhs_techniques)
        
        # Note: This method originally also checked input components but that parameter
        # isn't passed in the current call. The interventional logic is primarily
        # handled in the component score calculation pipeline.
        if is_nhs_interventional:
            return self.config.get('interventional_bonus', 0.15)
        
        return 0.0
    
    def _calculate_anatomical_specificity_score(self, input_components: Dict, nhs_components: Dict) -> float:
        """
        Calculate anatomical specificity score using separate weights for:
        - Anatomical detail (bonus for clinically relevant specificity)
        - Administrative detail (penalty for irrelevant specificity)
        - Technique specificity (small bonus for technique detail)
        
        Note: This is a simplified version that works with components instead of raw text
        """
        # For now, use a simple approach based on component counts
        # This could be enhanced to use the full text implementation
        
        input_anatomy = set(input_components.get('anatomy', []))
        nhs_anatomy = set(nhs_components.get('anatomy', []))
        
        # Basic specificity: NHS has more anatomical detail than input
        extra_anatomy = nhs_anatomy - input_anatomy
        anatomical_bonus = len(extra_anatomy) * self.config.get('anatomical_specificity_bonus', 0.10)
        
        # Cap the bonus to prevent excessive scoring
        return min(anatomical_bonus, 0.2)
    
    def _calculate_context_bonus(self, input_exam: str, nhs_entry: Dict, input_anatomy: List[str]) -> float:
        """
        Calculate context-based bonuses including gender, age, pregnancy, and clinical contexts.
        
        PIPELINE STEP: This method applies context bonuses that were previously calculated 
        post-scoring but are now integrated into the matching score calculation.
        
        Args:
            input_exam: Original user input exam name
            nhs_entry: NHS database entry being scored
            input_anatomy: Parsed anatomy from input (for context detection)
            
        Returns:
            float: Total context bonus to add to the final score
        """
        total_bonus = 0.0
        input_lower = input_exam.lower()
        nhs_name_lower = nhs_entry.get('primary_source_name', '').lower()
        
        # PART 1: Calculate gender/age context bonuses (previously missing from scoring)
        # Detect gender context from input
        input_gender_context = detect_gender_context(input_exam, input_anatomy or [])
        if input_gender_context:
            # Check if NHS entry matches this gender context
            if input_gender_context == 'pregnancy' and any(term in nhs_name_lower for term in ['pregnancy', 'obstetric', 'prenatal', 'fetal']):
                pregnancy_bonus = self.config.get('pregnancy_context_bonus', 0.25)
                total_bonus += pregnancy_bonus
                logger.debug(f"Applied pregnancy context bonus: +{pregnancy_bonus}")
                
            elif input_gender_context == 'female' and any(term in nhs_name_lower for term in ['breast', 'mammography', 'female', 'gynae', 'uterus']):
                gender_bonus = self.config.get('gender_context_match_bonus', 0.20)
                total_bonus += gender_bonus
                logger.debug(f"Applied female gender context bonus: +{gender_bonus}")
                
            elif input_gender_context == 'male' and any(term in nhs_name_lower for term in ['prostate', 'scrotal', 'male', 'penis']):
                gender_bonus = self.config.get('gender_context_match_bonus', 0.20)
                total_bonus += gender_bonus
                logger.debug(f"Applied male gender context bonus: +{gender_bonus}")
        
        # Detect age context from input
        input_age_context = detect_age_context(input_exam)
        if input_age_context == 'paediatric' and any(term in nhs_name_lower for term in ['paediatric', 'pediatric', 'child', 'infant']):
            age_bonus = self.config.get('age_context_match_bonus', 0.15)
            total_bonus += age_bonus
            logger.debug(f"Applied paediatric age context bonus: +{age_bonus}")
        
        # PART 2: Calculate clinical context bonuses (from context_scoring config)
        if self.context_scoring:
            for context_type, details in self.context_scoring.items():
                if isinstance(details, dict) and 'keywords' in details and 'bonus' in details:
                    keywords = details['keywords']
                    if any(k in input_lower for k in keywords) and any(k in nhs_name_lower for k in keywords):
                        clinical_bonus = details['bonus']
                        total_bonus += clinical_bonus
                        logger.debug(f"Applied {context_type} clinical context bonus: +{clinical_bonus}")
        
        return total_bonus
    
    def _calculate_synonym_bonus(self, input_exam: str, nhs_entry: Dict) -> float:
        """Calculate synonym bonus for abbreviation matches"""
        abbreviations = self.preprocessing_config.get('medical_abbreviations', {})
        if not abbreviations: 
            return 0.0
            
        input_lower = input_exam.lower()
        nhs_name_lower = nhs_entry.get('primary_source_name', '').lower()
        
        for abbrev, expansion in abbreviations.items():
            abbrev_l = abbrev.lower()
            expansion_l = expansion.lower()
            if (abbrev_l in input_lower and expansion_l in nhs_name_lower) or \
               (expansion_l in input_lower and abbrev_l in nhs_name_lower):
                return self.config.get('synonym_match_bonus', 0.15)
        
        return 0.0
    
    def _calculate_biopsy_modality_preference(self, input_exam: str, nhs_entry: Dict) -> float:
        """Calculate preference bonus/penalty for biopsy procedures based on modality."""
        if not self.config.get('biopsy_modality_preference', False):
            return 0.0

        input_lower = input_exam.lower()
        nhs_name_lower = nhs_entry.get('primary_source_name', '').lower()

        # Check if this is a biopsy procedure without explicit modality in input
        has_biopsy = 'biopsy' in input_lower or 'bx' in input_lower
        if not has_biopsy:
            return 0.0

        # Check if input already specifies a modality (if so, don't apply preference)
        explicit_modalities = ['ct', 'us', 'ultrasound', 'fluoroscop', 'mri', 'mr']
        if any(mod in input_lower for mod in explicit_modalities):
            return 0.0

        # Get organ-specific biopsy preferences from config
        organ_preferences = self.config.get('biopsy_organ_modality_preferences', {})
        default_preferences = self.config.get('biopsy_default_preferences', {})

        # Determine NHS entry modality
        nhs_components = nhs_entry.get('_parsed_components', {})
        nhs_modalities = [m.lower() for m in nhs_components.get('modality', [])]

        modality_key = ''
        if 'ct' in nhs_modalities:
            modality_key = 'ct'
        elif 'us' in nhs_modalities:
            modality_key = 'us'
        elif 'mri' in nhs_modalities:
            modality_key = 'mri'
        elif 'fluoroscopy' in nhs_modalities:
            modality_key = 'fluoroscopy'
        else:
            return 0.0

        # Find matching organ in input and apply specific preferences
        for organ, preferences in organ_preferences.items():
            if organ in input_lower:
                return preferences.get(modality_key, 0.0)

        # Fall back to default preferences if no organ match
        return default_preferences.get(modality_key, 0.0)