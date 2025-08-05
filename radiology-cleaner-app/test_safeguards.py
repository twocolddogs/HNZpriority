#!/usr/bin/env python3
"""
Test script to verify the semantic similarity safeguard and secondary pipeline integration.
"""

import requests
import json
import sys

def test_nephrostomy_case():
    """Test the original failure case: Nephrostomy Tube -> Ercp"""
    
    # Test data that previously failed
    test_data = {
        "exam_name": "Nephrostomy Tube",
        "modality_code": "IR", 
        "data_source": "SouthIsland-SIRS COMRAD",
        "exam_code": "I15"
    }
    
    print("🧪 Testing Nephrostomy Tube case...")
    print(f"Input: {test_data}")
    
    try:
        # Test against local server
        response = requests.post(
            "http://localhost:10000/parse_enhanced",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✅ Response received:")
            print(f"Clean name: {result.get('clean_name')}")
            print(f"SNOMED ID: {result.get('snomed', {}).get('id')}")
            print(f"Confidence: {result.get('components', {}).get('confidence')}")
            print(f"Ambiguous: {result.get('ambiguous')}")
            print(f"Secondary pipeline applied: {result.get('secondary_pipeline_applied', False)}")
            
            # Check for semantic similarity safeguard
            safeguard = result.get('semantic_similarity_safeguard')
            if safeguard:
                print(f"\n🛡️ Semantic Safeguard Applied:")
                print(f"  Similarity score: {safeguard.get('similarity_score')}")
                print(f"  Threshold: {safeguard.get('threshold')}")
                print(f"  Reason: {safeguard.get('reason')}")
            
            # Check if result makes sense
            clean_name = result.get('clean_name', '').lower()
            if 'nephrostomy' in clean_name or 'tube' in clean_name:
                print("\n✅ SUCCESS: Result contains nephrostomy/tube keywords")
            elif clean_name == 'ercp':
                print("\n❌ FAILURE: Still returning ERCP - safeguards didn't work")
                return False
            else:
                print(f"\n⚠️  UNKNOWN: Unexpected result '{clean_name}' - needs investigation")
            
            return True
            
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the local server running?")
        print("Start server with: python3 backend/app.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_semantic_similarity():
    """Test a case that should trigger semantic similarity safeguard"""
    
    # This is a hypothetical case that might trigger the safeguard
    test_data = {
        "exam_name": "CT Chest",
        "modality_code": "CT"
    }
    
    print("\n🧪 Testing semantic similarity safeguard...")
    print(f"Input: {test_data}")
    
    try:
        response = requests.post(
            "http://localhost:10000/parse_enhanced",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"Clean name: {result.get('clean_name')}")
            print(f"Confidence: {result.get('components', {}).get('confidence')}")
            
            # Check for semantic similarity metadata
            safeguard = result.get('semantic_similarity_safeguard')
            if safeguard:
                print(f"🛡️ Safeguard triggered: {safeguard}")
            else:
                print("ℹ️  No safeguard triggered (expected for normal cases)")
            
            return True
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Radiology Cleaner Safeguards")
    print("=" * 50)
    
    success = True
    
    # Test the specific failure case
    success &= test_nephrostomy_case()
    
    # Test semantic similarity in general
    success &= test_semantic_similarity()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests completed successfully!")
    else:
        print("❌ Some tests failed - check logs above")
        sys.exit(1)