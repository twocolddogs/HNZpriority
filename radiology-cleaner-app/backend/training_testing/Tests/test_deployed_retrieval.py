#!/usr/bin/env python3
"""
Test script to analyze retrieval on the deployed server.
"""

import requests
import json
import sys

def test_ct_cervical_spine():
    """Test the CT Cervical Spine case on the deployed server."""
    
    # Deployed server URL
    base_url = "https://radiology-api-staging.onrender.com"
    
    # Test payload with debug enabled
    payload = {
        "exam_name": "MRI Brain",
        "modality_code": "MR", 
        "debug": True
    }
    
    print("=" * 60)
    print("TESTING RETRIEVAL ON DEPLOYED SERVER")
    print("=" * 60)
    print(f"URL: {base_url}/parse_enhanced")
    print(f"Input: {payload}")
    print()
    
    try:
        # Make request to deployed server
        print("🚀 Making request to deployed server...")
        response = requests.post(
            f"{base_url}/parse_enhanced",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Display the result
            print("\n✅ SUCCESS - Server Response:")
            print("-" * 50)
            
            # Basic info
            print(f"Exam Name: {result.get('exam_name', 'N/A')}")
            print(f"Clean Name: {result.get('clean_name', 'N/A')}")
            print(f"Confidence: {result.get('components', {}).get('confidence', 'N/A')}")
            
            # SNOMED match
            snomed = result.get('snomed', {})
            if snomed.get('found'):
                print(f"\nSNOMED Match:")
                print(f"  ID: {snomed.get('id', 'N/A')}")
                print(f"  FSN: {snomed.get('fsn', 'N/A')}")
            else:
                print(f"\n❌ No SNOMED match found")
            
            # Components
            components = result.get('components', {})
            print(f"\nParsed Components:")
            print(f"  Modality: {components.get('modality', [])}")
            print(f"  Anatomy: {components.get('anatomy', [])}")
            print(f"  Laterality: {components.get('laterality', [])}")
            print(f"  Contrast: {components.get('contrast', [])}")
            print(f"  Technique: {components.get('technique', [])}")
            
            # Analysis
            print(f"\n📊 ANALYSIS:")
            input_simple = is_input_simple(payload['exam_name'])
            fsn_text = snomed.get('fsn', '')
            fsn_complex = is_fsn_complex(fsn_text)
            
            print(f"  Input complexity: {'Simple' if input_simple else 'Complex'}")
            print(f"  FSN complexity: {'Complex' if fsn_complex else 'Simple'}")
            print(f"  Confidence: {components.get('confidence', 0):.4f}")
            
            if input_simple and fsn_complex:
                print(f"  🔍 COMPLEXITY FILTER IMPACT: Simple input got complex FSN")
                print(f"     This match would be DEPRIORITIZED in our filtering")
            elif input_simple and not fsn_complex:
                print(f"  ✅ COMPLEXITY FILTER IMPACT: Simple input got simple FSN - Good match!")
            else:
                print(f"  ➡️  COMPLEXITY FILTER IMPACT: No filtering applied (complex input)")
            
            # Display debug information if available
            debug_info = result.get('debug')
            if debug_info:
                print(f"\n🔬 DEBUG INFORMATION:")
                print(f"  Input Simple: {debug_info.get('input_simple', 'N/A')}")
                print(f"  Complexity Filtering Applied: {debug_info.get('complexity_filtering_applied', 'N/A')}")
                print(f"  Total Candidates: {debug_info.get('total_candidates', 'N/A')}")
                
                candidates = debug_info.get('candidates', [])
                if candidates:
                    print(f"\n📊 TOP 25 RETRIEVED CANDIDATES:")
                    print("-" * 100)
                    print(f"{'Rank':<4} {'Score':<6} {'Complex':<7} {'SNOMED ID':<10} {'Primary Name':<40} {'FSN'}")
                    print("-" * 100)
                    
                    for candidate in candidates:
                        rank = candidate.get('rank', 'N/A')
                        final_score = candidate.get('final_score', 0)
                        is_complex = candidate.get('is_complex_fsn', False)
                        snomed_id = str(candidate.get('snomed_id', 'N/A'))
                        primary_name = str(candidate.get('primary_name', 'N/A'))[:37] + "..." if len(str(candidate.get('primary_name', ''))) > 40 else str(candidate.get('primary_name', 'N/A'))
                        fsn = str(candidate.get('fsn', 'N/A'))[:50] + "..." if len(str(candidate.get('fsn', ''))) > 53 else str(candidate.get('fsn', 'N/A'))
                        
                        print(f"{rank:<4} {final_score:<6.3f} {is_complex:<7} {snomed_id:<10} {primary_name:<40} {fsn}")
                    
                    print("-" * 100)
                    
                    # Analysis
                    simple_candidates = [c for c in candidates if not c.get('is_complex_fsn', False)]
                    complex_candidates = [c for c in candidates if c.get('is_complex_fsn', False)]
                    
                    print(f"\n📈 CANDIDATE ANALYSIS:")
                    print(f"  Simple FSNs: {len(simple_candidates)}")
                    print(f"  Complex FSNs: {len(complex_candidates)}")
                    
                    if simple_candidates:
                        best_simple = simple_candidates[0]
                        print(f"  Best Simple Option: Rank #{best_simple.get('rank')} - {best_simple.get('primary_name', 'N/A')}")
                        print(f"                      Score: {best_simple.get('final_score', 0):.3f}")
                    
                    winner = candidates[0] if candidates else None
                    if winner:
                        winner_complex = winner.get('is_complex_fsn', False)
                        print(f"  Actual Winner: Rank #1 - {winner.get('primary_name', 'N/A')}")
                        print(f"                 Score: {winner.get('final_score', 0):.3f}, Complex: {winner_complex}")
            
            return result
            
        else:
            print(f"❌ ERROR - HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ ERROR - Request timed out (30s)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR - Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ ERROR - Invalid JSON response: {e}")
        return None

def is_input_simple(exam_name):
    """Simple approximation of input complexity."""
    # Count complexity indicators
    complexity_indicators = ['+', '&', 'w/', 'with', 'contrast', 'phase', 'view', '(', ')']
    expanded = exam_name.replace('CT', 'computed tomography').lower()
    
    count = sum(1 for indicator in complexity_indicators if indicator in expanded)
    return count == 0

def is_fsn_complex(fsn_text):
    """Simple approximation of FSN complexity."""
    if not fsn_text:
        return False
    
    # Count complexity words - including medical technique terms
    complex_words = ['with', 'using', 'for', 'enhancement', 'planning', 'guidance', 'reconstruction', 
                    'diffusion', 'tensor', 'perfusion', 'spectroscopy', 'angiography', 'venography',
                    'contrast', 'gadolinium', 'interventional', 'guided', 'assisted']
    word_count = sum(1 for word in complex_words if word.lower() in fsn_text.lower())
    
    # Also check length and prepositions
    prepositions = ['of', 'with', 'without', 'during', 'using', 'via', 'through', 'under', 'over']
    prep_count = sum(1 for prep in prepositions if f' {prep} ' in f' {fsn_text.lower()} ')
    
    return word_count >= 1 or prep_count > 2 or len(fsn_text.split()) > 8

def test_multiple_cases():
    """Test multiple cases to see retrieval patterns."""
    test_cases = [
        ("CT Cervical Spine", "CT"),
        ("CT CHEST", "CT"),
        ("MRI Brain", "MR"),
        ("CT Abdomen Pelvis with contrast", "CT"),
        ("Chest X-ray", "XR"),
    ]
    
    print("TESTING MULTIPLE CASES")
    print("=" * 60)
    
    results = []
    for exam_name, modality in test_cases:
        print(f"\n🔸 Testing: {exam_name}")
        result = test_single_case(exam_name, modality)
        results.append((exam_name, result))
        print("-" * 40)
    
    # Summary
    print(f"\n📈 SUMMARY:")
    for exam_name, result in results:
        if result and result.get('snomed', {}).get('found'):
            confidence = result.get('components', {}).get('confidence', 0)
            fsn = result.get('snomed', {}).get('fsn', 'N/A')[:50] + "..."
            print(f"  {exam_name:<25} | Confidence: {confidence:.3f} | {fsn}")
        else:
            print(f"  {exam_name:<25} | No match found")

def test_single_case(exam_name, modality_code):
    """Test a single case (simplified version for batch testing)."""
    base_url = "https://radiology-api-staging.onrender.com"
    payload = {"exam_name": exam_name, "modality_code": modality_code}
    
    try:
        response = requests.post(f"{base_url}/parse_enhanced", json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"    ❌ HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return None

def main():
    """Main function."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "multiple":
            test_multiple_cases()
        else:
            # Custom test case
            exam_name = " ".join(sys.argv[1:])
            print(f"Testing custom case: {exam_name}")
            test_ct_cervical_spine() if exam_name == "CT Cervical Spine" else test_single_case(exam_name, "CT")
    else:
        # Default test
        test_ct_cervical_spine()

if __name__ == "__main__":
    main()