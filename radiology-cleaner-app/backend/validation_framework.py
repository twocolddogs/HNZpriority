# --- START OF FILE validation_framework.py ---

# =============================================================================
# VALIDATION FRAMEWORK
# =============================================================================
# Framework for testing preprocessing and scoring accuracy using sanity test data

import json
import logging
import yaml
from typing import Dict, List, Tuple, Optional
from preprocessing import ExamPreprocessor
from nhs_lookup_engine import NHSLookupEngine
from nlp_processor import NLPProcessor
from parser import RadiologySemanticParser

logger = logging.getLogger(__name__)

class ValidationFramework:
    """
    Validation framework for testing preprocessing and scoring improvements.
    Uses sanity_test.json data to evaluate matching accuracy.
    """
    
    def __init__(self, config_path: str = 'config.yaml'):
        """Initialize validation framework with configuration."""
        self.config_path = config_path
        self.load_config()
        self.validation_cases = []
        
    def load_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise
    
    def load_sanity_test_data(self, sanity_test_path: str = 'core/sanity_test.json'):
        """Load sanity test data for validation."""
        try:
            with open(sanity_test_path, 'r') as f:
                sanity_data = json.load(f)
                
            # Convert sanity test data to validation cases
            self.validation_cases = []
            for entry in sanity_data:
                case = {
                    'input_exam': entry['EXAM_NAME'],
                    'expected_modality': entry['MODALITY_CODE'],
                    'data_source': entry['DATA_SOURCE'],
                    'exam_code': entry['EXAM_CODE']
                }
                self.validation_cases.append(case)
                
            logger.info(f"Loaded {len(self.validation_cases)} validation cases")
            
        except Exception as e:
            logger.error(f"Failed to load sanity test data: {e}")
            raise
    
    def create_grouped_expectations(self) -> Dict[str, List[str]]:
        """
        Create expected groupings based on sanity test data.
        Groups similar exams that should match to the same clean name.
        """
        groups = {
            'chest_xray': [
                'Chest (single projection)',
                'Xray Chest', 
                'Chest (Mobile)',
                'Ward Chest'
            ],
            'ct_head': [
                'CT Head',
                'CT HEAD C-',
                'CT Head Non Contrast',
                'CT HEAD C+'
            ],
            'ct_abdomen_pelvis': [
                'CT Abdomen and Pelvis',
                'CT Abdomen and Pelvis',  # Exact match from different sources
                'CT ABDOMEN C+'
            ],
            'ct_chest_abdomen_pelvis': [
                'CT Chest and Abdomen and Pelvis',
                'CT Chest, Abdomen and Pelvis'
            ],
            'ct_pulmonary_angiogram': [
                'CT Pulmonary Angiogram',
                'CT Pulmonary Angiography'
            ],
            'ct_chest': [
                'CT Chest',
                'CT CHEST C-'
            ],
            'ct_kub': [
                'CT KUB',
                'CT Kidneys, Ureters and Bladder'
            ],
            'ct_cervical_spine': [
                'CT Cervical Spine',
                'CT SPINE CERVICAL'
            ],
            'mri_head_brain': [
                'MR Head',
                'MRI HEAD C-',
                'MRI Brain'
            ],
            'mri_lumbar_spine': [
                'MR Lumbar Spine',
                'MRI SPINE LUMBAR C-',
                'MRI Lumbar Spine'
            ],
            'us_abdomen': [
                'US Abdomen',
                'US Abdomen'
            ],
            'us_pelvis': [
                'US Pelvis',
                'US Pelvis - Female',
                'US Transvaginal/Transabdominal Pelvis'
            ],
            'us_pregnancy_3rd': [
                'US 3rd Trimester scan (GR)',
                'US Pregnancy - 3rd Trimester'
            ],
            'us_renal_tract': [
                'US Renal Tract',
                'US Renal Tract'
            ],
            'us_venous_doppler': [
                'US Left Venous DVT lower limb',
                'US Venous Doppler Lower Limb'
            ],
            'us_scrotum_testes': [
                'US Scrotum and Testes',
                'US Scrotum and Testes'
            ],
            'us_infant_hips': [
                'US Paed Hips (CDH screening)',
                'US Infant Hips'
            ],
            'mammogram_bilateral': [
                'BR Bilateral Mammogram',
                'Mammogram Bilateral'
            ],
            'dexa_scan': [
                'Bone density Scan',
                'Dexa',
                'DEXA Imaging'
            ]
        }
        
        return groups
    
    def test_preprocessing_consistency(self) -> Dict[str, float]:
        """Test preprocessing consistency across different data sources."""
        results = {}
        preprocessor = ExamPreprocessor(config=self.config.get('preprocessing', {}))
        
        groups = self.create_grouped_expectations()
        
        for group_name, exam_names in groups.items():
            # Preprocess all names in group
            processed_names = [preprocessor.preprocess(name) for name in exam_names]
            
            # Calculate similarity (simple token overlap for now)
            if len(processed_names) > 1:
                total_similarity = 0
                comparisons = 0
                
                for i in range(len(processed_names)):
                    for j in range(i+1, len(processed_names)):
                        tokens_i = set(processed_names[i].lower().split())
                        tokens_j = set(processed_names[j].lower().split())
                        
                        if tokens_i.union(tokens_j):
                            similarity = len(tokens_i.intersection(tokens_j)) / len(tokens_i.union(tokens_j))
                            total_similarity += similarity
                            comparisons += 1
                
                avg_similarity = total_similarity / comparisons if comparisons > 0 else 0
                results[group_name] = avg_similarity
            else:
                results[group_name] = 1.0
        
        return results
    
    def test_modality_extraction_accuracy(self) -> Dict[str, float]:
        """Test modality extraction accuracy from validation cases."""
        from parser import RadiologySemanticParser
        
        try:
            # Initialize semantic parser
            nlp_processor = NLPProcessor()
            parser = RadiologySemanticParser()
            
            correct_extractions = 0
            total_cases = 0
            modality_results = {}
            
            for case in self.validation_cases:
                input_exam = case['input_exam']
                expected_modality = case['expected_modality']
                
                # Parse the exam name
                components = parser.parse_exam_name(input_exam)
                extracted_modality = components.get('modality')
                
                # Check if extraction matches expected
                is_correct = (extracted_modality == expected_modality or
                            (extracted_modality and expected_modality and 
                             extracted_modality.upper() == expected_modality.upper()))
                
                if is_correct:
                    correct_extractions += 1
                
                total_cases += 1
                
                # Track by modality type
                if expected_modality not in modality_results:
                    modality_results[expected_modality] = {'correct': 0, 'total': 0}
                
                modality_results[expected_modality]['total'] += 1
                if is_correct:
                    modality_results[expected_modality]['correct'] += 1
            
            # Calculate accuracies
            overall_accuracy = correct_extractions / total_cases if total_cases > 0 else 0
            
            modality_accuracies = {}
            for modality, counts in modality_results.items():
                accuracy = counts['correct'] / counts['total'] if counts['total'] > 0 else 0
                modality_accuracies[modality] = accuracy
            
            return {
                'overall_accuracy': overall_accuracy,
                'by_modality': modality_accuracies,
                'total_cases': total_cases
            }
            
        except Exception as e:
            logger.error(f"Failed to test modality extraction: {e}")
            return {'error': str(e)}
    
    def run_validation_suite(self) -> Dict[str, any]:
        """Run complete validation suite and return results."""
        logger.info("Running validation suite...")
        
        results = {
            'config_path': self.config_path,
            'total_validation_cases': len(self.validation_cases),
            'preprocessing_consistency': {},
            'modality_extraction_accuracy': {},
            'timestamp': None
        }
        
        try:
            # Test preprocessing consistency
            logger.info("Testing preprocessing consistency...")
            results['preprocessing_consistency'] = self.test_preprocessing_consistency()
            
            # Test modality extraction accuracy
            logger.info("Testing modality extraction accuracy...")
            results['modality_extraction_accuracy'] = self.test_modality_extraction_accuracy()
            
            # Calculate overall scores
            prep_scores = list(results['preprocessing_consistency'].values())
            overall_prep_score = sum(prep_scores) / len(prep_scores) if prep_scores else 0
            
            results['summary'] = {
                'overall_preprocessing_consistency': overall_prep_score,
                'modality_extraction_overall': results['modality_extraction_accuracy'].get('overall_accuracy', 0)
            }
            
            logger.info("Validation suite completed successfully")
            
        except Exception as e:
            logger.error(f"Validation suite failed: {e}")
            results['error'] = str(e)
        
        return results

def run_validation(config_path: str = 'config.yaml', sanity_test_path: str = 'core/sanity_test.json') -> Dict[str, any]:
    """Convenience function to run validation with default paths."""
    framework = ValidationFramework(config_path)
    framework.load_sanity_test_data(sanity_test_path)
    return framework.run_validation_suite()

if __name__ == "__main__":
    # Run validation if script is executed directly
    results = run_validation()
    print(json.dumps(results, indent=2))