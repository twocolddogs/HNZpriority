import sys
import os
import json
import unittest

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

# Import the app and ensure it's initialized
import app

class TestModalityStrictFilter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure the app is initialized before running tests
        app._ensure_app_is_initialized()

    def test_strict_modality_filtering_ct_to_xr_mismatch(self):
        """
        Test that a CT exam name does not match an XR SNOMED entry
        when strict modality filtering is enabled.
        """
        exam_name = "XR Chest" # This is an XR exam name
        modality_code = "CT" # But we are providing a CT modality code

        # This should result in a low confidence or no match due to modality mismatch
        result = app.process_exam_with_nhs_lookup(exam_name, modality_code)

        self.assertIsNotNone(result)
        self.assertIn('snomed_found', result)
        self.assertFalse(result['snomed_found'], "Expected SNOMED not found due to modality mismatch")
        self.assertLess(result['confidence'], 0.5, "Expected low confidence due to modality mismatch")
        self.assertNotEqual(result['clean_name'], "XR Chest", "Clean name should not be XR Chest if modality mismatch occurred")

    def test_strict_modality_filtering_xr_to_ct_mismatch(self):
        """
        Test that an XR exam name does not match a CT SNOMED entry
        when strict modality filtering is enabled.
        """
        exam_name = "CT Head" # This is a CT exam name
        modality_code = "XR" # But we are providing an XR modality code

        # This should result in a low confidence or no match due0 to modality mismatch
        result = app.process_exam_with_nhs_lookup(exam_name, modality_code)

        self.assertIsNotNone(result)
        self.assertIn('snomed_found', result)
        self.assertFalse(result['snomed_found'], "Expected SNOMED not found due to modality mismatch")
        self.assertLess(result['confidence'], 0.5, "Expected low confidence due to modality mismatch")
        self.assertNotEqual(result['clean_name'], "CT Head", "Clean name should not be CT Head if modality mismatch occurred")

    def test_strict_modality_filtering_correct_match(self):
        """
        Test that a correct modality match still works.
        """
        exam_name = "CT Abdomen and Pelvis"
        modality_code = "CT"

        result = app.process_exam_with_nhs_lookup(exam_name, modality_code)

        self.assertIsNotNone(result)
        self.assertTrue(result['snomed_found'], "Expected SNOMED to be found for correct match")
        self.assertGreater(result['confidence'], 0.5, "Expected high confidence for correct match")
        self.assertEqual(result['clean_name'], "CT Abdomen and pelvis", "Expected correct clean name for correct match")

if __name__ == '__main__':
    unittest.main()