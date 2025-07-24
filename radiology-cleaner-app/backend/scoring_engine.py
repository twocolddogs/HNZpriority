#!/usr/bin/env python3
"""
NHS Radiology Scoring Engine (V1.0 - Consolidated)

Handles all scoring logic for NHS exam matching including:
- Component scoring (anatomy, modality, laterality, contrast, technique)
- Complexity-aware scoring 
- Context bonuses and penalties
- Final score calculation and weighting

This module is fully consolidated and separated from nhs_lookup_engine.py.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

# Import context detection functions
from context_detection import detect_gender_context, detect_age_context

logger = logging.getLogger(__name__)

class ScoringEngine:
    """Handles all scoring logic for NHS exam matching."""
    
    def __init__(self, config: Dict, modality_similarity: Dict = None, context_scoring: Dict = None, preprocessing_config: Dict = None):
        """Initialize scoring engine with configuration."""
        self.config = config.get('scoring', {})
        self.modality_similarity = modality_similarity or {}
        self.context_scoring = context_scoring or {}
        self.preprocessing_config = preprocessing_config or {}
        self._specificity_stop_words = {
            'a', 'an', 'the', 'and', 'or', 'with', 'without', 'for', 'of', 'in', 'on', 'to',
            'ct', 'mr', 'mri', 'us', 'xr', 'x-ray', 'nm', 'pet', 'scan', 'imaging', 'procedure',
            'examination', 'study', 'left', 'right', 'bilateral', 'contrast', 'view'
        }

    # =============================================================================
    # FINAL SCORE CALCULATION (NEW ENTRY POINT)
    # =============================================================================

    def calculate_final_score(
        self,
        input_exam: str,
        input_components: Dict,
        nhs_entry: Dict,
        rerank_score: float
    ) -> Tuple[float, Dict]:
        """
        Calculate final weighted score with complexity applied ONLY to the reranker step.
        This prevents over-selection of complex FSNs for simple inputs.
        
        Returns:
            Tuple of (final_score, score_breakdown)
        """
        # 1. Component score
        component_score, component_breakdown = self.calculate_component_score(input_exam, input_components, nhs_entry)
        
        # 2. Apply complexity appropriateness ONLY to the reranker score
        fsn = nhs_entry.get('snomed_fsn', '')
        primary_name = nhs_entry.get('primary_source_name', '')
        complexity_score = self.calculate_complexity_appropriateness(input_exam, fsn, primary_name)
        
        # Adjust reranker score based on complexity appropriateness
        complexity_adjusted_rerank_score = rerank_score * complexity_score
        
        # 3. Get weights from config (remove complexity weight, return to pre-refactor balance)
        weights = self.config.get('weights_final', {})
        # Use pre-refactor weights: component=55%, semantic=35%, frequency=10% (ignore frequency for now)
        component_weight = weights.get('component', 0.55)
        reranker_weight = weights.get('reranker', 0.35)
        
        # 4. Calculate final weighted score (2-component: component + complexity-adjusted reranker)
        final_score = (
            (component_weight * component_score) +
            (reranker_weight * complexity_adjusted_rerank_score)
        )
        
        # 5. Create detailed breakdown for debugging
        score_breakdown = {
            'rerank_score': rerank_score,
            'complexity_adjusted_rerank_score': complexity_adjusted_rerank_score,
            'component_score': component_score,
            'component_breakdown': component_breakdown,
            'complexity_score': complexity_score,
            'final_score': final_score,
            'weights': {
                'reranker': reranker_weight,
                'component': component_weight
            }
        }
        
        return max(0.0, min(1.0, final_score)), score_breakdown

    # =============================================================================
    # COMPLEXITY SCORING METHODS
    # =============================================================================
    
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

    # =============================================================================
    # COMPONENT SCORING METHODS (CONSOLIDATED)
    # =============================================================================
    
    def calculate_component_score(self, input_exam: str, input_components: Dict, nhs_entry: Dict) -> Tuple[float, Dict]:
        """Calculate a comprehensive, rule-based component score for a candidate."""
        nhs_components = nhs_entry.get('_parsed_components', {})
        
        # --- Penalties (check for blocking violations first) ---
        diagnostic_penalty = self.calculate_diagnostic_penalty(input_exam, nhs_entry)
        hybrid_modality_penalty = self.calculate_hybrid_modality_penalty(input_exam, nhs_entry)
        anatomy_score = self.calculate_anatomy_score_with_constraints(input_components, nhs_components)

        if any(p < -1.0 for p in [diagnostic_penalty, hybrid_modality_penalty, anatomy_score]):
            return 0.0, {"violation": "blocking"}

        # --- Component Scores ---
        modality_score = self.calculate_modality_score(input_components.get('modality', []), nhs_components.get('modality', []))
        contrast_score = self.calculate_contrast_score(input_components.get('contrast', []), nhs_components.get('contrast', []))
        technique_score = self.calculate_set_score(input_components.get('technique', []), nhs_components.get('technique', []))
        laterality_score = self.calculate_laterality_score((input_components.get('laterality') or [None])[0], (nhs_components.get('laterality') or [None])[0])

        if violation_reason := self.check_component_thresholds(anatomy_score, modality_score, laterality_score, contrast_score, technique_score):
            return 0.0, {"violation": violation_reason}

        # --- Weighted Component Score ---
        w = self.config.get('weights_component', {})
        base_component_score = (
            w.get('anatomy', 0.25) * anatomy_score + w.get('modality', 0.30) * modality_score +
            w.get('laterality', 0.15) * laterality_score + w.get('contrast', 0.20) * contrast_score +
            w.get('technique', 0.10) * technique_score
        )
        
        # --- Bonuses and Final Penalties ---
        interventional_score = self.calculate_interventional_score(input_components, nhs_components)
        anatomical_specificity_score = self.calculate_anatomical_specificity_score(input_exam, nhs_entry)
        context_bonus = self.calculate_context_bonus(input_exam, nhs_entry, input_components.get('anatomy', []))
        synonym_bonus = self.calculate_synonym_bonus(input_exam, nhs_entry)
        biopsy_preference = self.calculate_biopsy_modality_preference(input_exam, nhs_entry)
        anatomy_preference = self.calculate_anatomy_specificity_preference(input_components, nhs_entry)
        vessel_preference = self.calculate_vessel_type_preference(input_exam, nhs_entry)
        exact_match_bonus = self.config.get('exact_match_bonus', 0.25) if input_exam.strip().lower() == nhs_entry.get('primary_source_name', '').lower() else 0.0

        total_bonus_penalty = (
            interventional_score + anatomical_specificity_score + context_bonus + synonym_bonus + biopsy_preference + anatomy_preference + vessel_preference + exact_match_bonus +
            diagnostic_penalty + hybrid_modality_penalty
        )
        
        final_component_score = base_component_score + total_bonus_penalty
        
        breakdown = {
            "base_score": base_component_score, "bonuses_penalties": total_bonus_penalty, "anatomy": anatomy_score, "modality": modality_score,
            "laterality": laterality_score, "contrast": contrast_score, "technique": technique_score,
        }
        return max(0.0, min(1.0, final_component_score)), breakdown

    # =============================================================================
    # HELPER & SCORING SUB-METHODS (ALL CONSOLIDATED HERE)
    # =============================================================================

    def calculate_set_score(self, list1: List[str], list2: List[str]) -> float:
        set1, set2 = set(list1), set(list2)
        if not set1 and not set2: return 1.0
        union = set1.union(set2)
        return len(set1.intersection(set2)) / len(union) if union else 0.0

    def calculate_laterality_score(self, input_lat: Optional[str], nhs_lat: Optional[str]) -> float:
        if input_lat == nhs_lat: return 1.0
        if not input_lat or not nhs_lat: return 0.7
        return 0.1

    def calculate_modality_score(self, input_modality: List[str], nhs_modality: List[str]) -> float:
        if not input_modality or not nhs_modality: return 0.5
        if len(input_modality) == 1 and len(nhs_modality) == 1:
            input_mod, nhs_mod = input_modality[0], nhs_modality[0]
            return 1.0 if input_mod == nhs_mod else self.modality_similarity.get(input_mod, {}).get(nhs_mod, 0.0)
        return self.calculate_set_score(input_modality, nhs_modality)

    def calculate_contrast_score(self, input_contrast: List[str], nhs_contrast: List[str]) -> float:
        if not input_contrast and not nhs_contrast: return 1.0
        if not input_contrast or not nhs_contrast: return self.config.get('contrast_null_score', 0.7)
        input_set, nhs_set = set(input_contrast), set(nhs_contrast)
        if input_set == nhs_set: return 1.0
        if input_set.intersection(nhs_set): return 0.8
        return self.config.get('contrast_mismatch_score', 0.05)

    def calculate_anatomy_score_with_constraints(self, input_components: dict, nhs_components: dict) -> float:
        input_anatomy = set(str(a).lower() for a in input_components.get('anatomy', []))
        nhs_anatomy = set(str(a).lower() for a in nhs_components.get('anatomy', []))
        
        constraint_config = self.config.get('anatomical_compatibility_constraints', {})
        if constraint_config.get('enable', False):
            incompatible_pairs = constraint_config.get('incompatible_pairs', [])
            blocking_penalty = constraint_config.get('blocking_penalty', -10.0)
            for i_term in input_anatomy:
                for n_term in nhs_anatomy:
                    for pair in incompatible_pairs:
                        if len(pair) >= 2 and ( (i_term in pair[0] or pair[0] in i_term) and (n_term in pair[1] or pair[1] in n_term) or \
                                                (i_term in pair[1] or pair[1] in i_term) and (n_term in pair[0] or pair[0] in n_term) ):
                            logger.warning(f"ANATOMICAL BLOCK: '{i_term}' -> '{n_term}'")
                            return blocking_penalty
        return self.calculate_set_score(list(input_anatomy), list(nhs_anatomy))

    def calculate_diagnostic_penalty(self, input_exam_text: str, nhs_entry: dict) -> float:
        protection_config = self.config.get('diagnostic_protection', {})
        if not protection_config.get('enable', False): return 0.0
        
        input_lower = input_exam_text.lower()
        nhs_name_lower = nhs_entry.get('primary_source_name', '').lower()
        
        is_input_diag = any(k.lower() in input_lower for k in protection_config.get('diagnostic_indicators', []))
        is_nhs_interv = any(k.lower() in nhs_name_lower for k in protection_config.get('interventional_indicators', []))
        
        if is_input_diag and is_nhs_interv:
            logger.warning(f"DIAGNOSTIC BLOCK: Input '{input_exam_text}' to NHS '{nhs_name_lower}'")
            return protection_config.get('blocking_penalty', -8.0)
        return 0.0

    def calculate_hybrid_modality_penalty(self, input_exam_text: str, nhs_entry: dict) -> float:
        hybrid_config = self.config.get('hybrid_modality_constraints', {})
        if not hybrid_config.get('enable', False): return 0.0

        input_lower = input_exam_text.lower()
        nhs_name_lower = nhs_entry.get('primary_source_name', '').lower()
        
        for rule in hybrid_config.get('hybrid_incompatibilities', []):
            if re.search(rule.get('input_pattern', ''), input_lower):
                if any(re.search(p, nhs_name_lower) for p in rule.get('nhs_exclusions', [])):
                    logger.warning(f"HYBRID BLOCK: Input '{input_exam_text}' to NHS '{nhs_name_lower}'")
                    return hybrid_config.get('blocking_penalty', -6.0)
        return 0.0

    def check_component_thresholds(self, anatomy_score: float, modality_score: float, laterality_score: float, contrast_score: float, technique_score: float) -> Optional[str]:
        threshold_config = self.config.get('minimum_component_thresholds', {})
        if not threshold_config.get('enable', False): return None

        if anatomy_score < threshold_config.get('anatomy_min', 0.1): return "anatomy"
        if modality_score < threshold_config.get('modality_min', 0.4): return "modality"
        if contrast_score < threshold_config.get('contrast_min', 0.3): return "contrast"
        return None
    
        
    def calculate_interventional_score(self, input_components: Dict, nhs_components: Dict) -> float:
        is_input_interventional = any('Interventional' in t for t in input_components.get('technique', []))
        is_nhs_interventional = any('Interventional' in t for t in nhs_components.get('technique', []))
        
        if is_input_interventional and is_nhs_interventional: return self.config.get('interventional_bonus', 0.15)
        if is_input_interventional and not is_nhs_interventional: return self.config.get('interventional_penalty', -0.20)
        return 0.0

    def calculate_anatomical_specificity_score(self, input_exam: str, nhs_entry: dict) -> float:
        input_tokens = set(input_exam.lower().split())
        nhs_tokens = set(nhs_entry.get('primary_source_name', '').lower().split())
        extra_tokens = (nhs_tokens - input_tokens) - self._specificity_stop_words
        
        anatomical_words = set(self.config.get('anatomical_detail_words', []))
        administrative_words = set(self.config.get('administrative_detail_words', []))
        
        anatomical_bonus = len(extra_tokens.intersection(anatomical_words)) * self.config.get('anatomical_specificity_bonus', 0.10)
        administrative_penalty = len(extra_tokens.intersection(administrative_words)) * self.config.get('general_specificity_penalty', 0.20)
        
        return anatomical_bonus - administrative_penalty

    def calculate_context_bonus(self, input_exam: str, nhs_entry: dict, input_anatomy: List[str]) -> float:
        total_bonus = 0.0
        input_lower = input_exam.lower()
        nhs_name_lower = nhs_entry.get('primary_source_name', '').lower()
        
        # Gender/Age context
        gender_context = detect_gender_context(input_exam, input_anatomy or [])
        if gender_context == 'pregnancy' and any(k in nhs_name_lower for k in ['pregnancy', 'obstetric', 'fetal']):
            total_bonus += self.config.get('pregnancy_context_bonus', 0.25)
        elif gender_context == 'female' and any(k in nhs_name_lower for k in ['breast', 'mammography', 'gynae']):
            total_bonus += self.config.get('gender_context_match_bonus', 0.20)
        elif gender_context == 'male' and any(k in nhs_name_lower for k in ['prostate', 'scrotal', 'penis']):
            total_bonus += self.config.get('gender_context_match_bonus', 0.20)

        age_context = detect_age_context(input_exam)
        if age_context == 'paediatric' and any(k in nhs_name_lower for k in ['paediatric', 'child']):
            total_bonus += self.config.get('age_context_match_bonus', 0.15)
            
        return total_bonus
    
    def calculate_synonym_bonus(self, input_exam: str, nhs_entry: dict) -> float:
        abbreviations = self.preprocessing_config.get('medical_abbreviations', {})
        input_lower, nhs_name_lower = input_exam.lower(), nhs_entry.get('primary_source_name', '').lower()
        for abbrev, expansion in abbreviations.items():
            abbrev_l, expansion_l = abbrev.lower(), expansion.lower()
            if (abbrev_l in input_lower and expansion_l in nhs_name_lower) or \
               (expansion_l in input_lower and abbrev_l in nhs_name_lower):
                return self.config.get('synonym_match_bonus', 0.15)
        return 0.0
        
    def calculate_biopsy_modality_preference(self, input_exam: str, nhs_entry: dict) -> float:
        if not self.config.get('biopsy_modality_preference', False): return 0.0

        input_lower = input_exam.lower()
        if not ('biopsy' in input_lower or 'bx' in input_lower): return 0.0
        if any(mod in input_lower for mod in ['ct', 'us', 'ultrasound', 'mri', 'mr']): return 0.0

        organ_prefs = self.config.get('biopsy_organ_modality_preferences', {})
        default_prefs = self.config.get('biopsy_default_preferences', {})
        nhs_modalities = {m.lower() for m in nhs_entry.get('_parsed_components', {}).get('modality', [])}
        
        mod_key = ''
        if 'ct' in nhs_modalities: mod_key = 'ct'
        elif 'us' in nhs_modalities: mod_key = 'us'
        elif 'mri' in nhs_modalities: mod_key = 'mri'
        elif 'fluoroscopy' in nhs_modalities or 'ir' in nhs_modalities or 'interventional' in nhs_modalities: mod_key = 'fluoroscopy'
        else: return 0.0
        
        for organ, prefs in organ_prefs.items():
            if organ in input_lower: return prefs.get(mod_key, 0.0)
        return default_prefs.get(mod_key, 0.0)
    
    def calculate_vessel_type_preference(self, input_exam: str, nhs_entry: dict) -> float:
        """
        Applies vessel type preference logic to favor arterial studies when input is generic angiography.
        
        Clinical rationale: "angiography" typically refers to arterial imaging. When users order 
        "CT angiography" without specifying vessel type, they usually mean arterial studies.
        """
        vessel_config = self.config.get('vessel_type_preference', {})
        if not vessel_config.get('enable', False):
            return 0.0
            
        input_lower = input_exam.lower()
        nhs_fsn_lower = nhs_entry.get('snomed_fsn', '').lower()
        
        # Check if input contains generic angiography terms
        generic_angio_indicators = vessel_config.get('generic_angiography_indicators', [])
        has_generic_angio = any(indicator in input_lower for indicator in generic_angio_indicators)
        
        # Check if input specifically mentions venous intent
        venous_indicators = vessel_config.get('specific_venous_indicators', [])
        has_venous_intent = any(indicator in input_lower for indicator in venous_indicators)
        
        # If input has specific venous intent, don't apply arterial preference
        if has_venous_intent:
            return 0.0
            
        # If input has generic angiography terms, apply vessel preference
        if has_generic_angio:
            # Check if NHS entry is arterial or venous
            if any(term in nhs_fsn_lower for term in ['artery', 'arterial', 'arteries']):
                # Bonus for arterial studies when input is generic angiography
                return vessel_config.get('arterial_preference_bonus', 0.20)
            elif any(term in nhs_fsn_lower for term in ['vein', 'venous', 'veins', 'venography']):
                # Penalty for venous studies when input is generic angiography  
                return vessel_config.get('venous_penalty', -0.15)
                
        return 0.0
        
    def calculate_anatomy_specificity_preference(self, input_components: dict, nhs_entry: dict) -> float:
        if not self.config.get('anatomy_specificity_preference', False): return 0.0
        if not input_components.get('anatomy', []):
            if not nhs_entry.get('_parsed_components', {}).get('anatomy', []):
                return self.config.get('generic_anatomy_preference_bonus', 0.15)
            else:
                return -0.05
        return 0.0