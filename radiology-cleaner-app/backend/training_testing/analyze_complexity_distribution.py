#!/usr/bin/env python3
"""
Analyze complexity distribution in NHS.json to validate complexity-based ranking approach.
Samples 500 random entries and calculates complexity statistics.
"""

import json
import random
import re
import statistics
from pathlib import Path
from typing import List, Dict, Tuple

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent

def calculate_structural_complexity(text: str) -> float:
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

def calculate_terminology_complexity(text: str) -> float:
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

def calculate_total_complexity(text: str) -> float:
    """Calculate total complexity score"""
    structural = calculate_structural_complexity(text)
    terminology = calculate_terminology_complexity(text)
    return min(structural + terminology, 1.0)

def analyze_complexity_distribution():
    """Analyze complexity distribution in NHS.json"""
    
    # Load NHS data
    nhs_file = backend_dir / 'core' / 'NHS.json'
    if not nhs_file.exists():
        print(f"❌ NHS.json file not found: {nhs_file}")
        return
    
    with open(nhs_file, 'r', encoding='utf-8') as f:
        nhs_data = json.load(f)
    
    print("=" * 80)
    print("NHS.JSON COMPLEXITY DISTRIBUTION ANALYSIS")
    print("=" * 80)
    print(f"Total NHS entries: {len(nhs_data)}")
    print()
    
    # Sample 500 random entries (or all if less than 500)
    sample_size = min(500, len(nhs_data))
    random_sample = random.sample(nhs_data, sample_size)
    
    print(f"Analyzing {sample_size} random samples...")
    print()
    
    # Calculate complexity scores
    fsn_complexities = []
    primary_complexities = []
    complexity_differentials = []
    
    examples_by_complexity = {
        'simple': [],      # 0.0 - 0.3
        'moderate': [],    # 0.3 - 0.6  
        'complex': []      # 0.6 - 1.0
    }
    
    for entry in random_sample:
        fsn = entry.get('snomed_fsn', '').strip()
        primary_name = entry.get('primary_source_name', '').strip()
        
        # Calculate complexities
        fsn_complexity = calculate_total_complexity(fsn)
        primary_complexity = calculate_total_complexity(primary_name)
        differential = max(0, fsn_complexity - primary_complexity)
        
        fsn_complexities.append(fsn_complexity)
        primary_complexities.append(primary_complexity)
        complexity_differentials.append(differential)
        
        # Collect examples for each complexity range
        if fsn_complexity < 0.3:
            if len(examples_by_complexity['simple']) < 5:
                examples_by_complexity['simple'].append((fsn, primary_name, fsn_complexity))
        elif fsn_complexity < 0.6:
            if len(examples_by_complexity['moderate']) < 5:
                examples_by_complexity['moderate'].append((fsn, primary_name, fsn_complexity))
        else:
            if len(examples_by_complexity['complex']) < 5:
                examples_by_complexity['complex'].append((fsn, primary_name, fsn_complexity))
    
    # Calculate statistics
    def calc_stats(data: List[float]) -> Dict:
        return {
            'mean': statistics.mean(data),
            'median': statistics.median(data),
            'stdev': statistics.stdev(data) if len(data) > 1 else 0.0,
            'min': min(data),
            'max': max(data),
            'range': max(data) - min(data)
        }
    
    fsn_stats = calc_stats(fsn_complexities)
    primary_stats = calc_stats(primary_complexities)
    diff_stats = calc_stats(complexity_differentials)
    
    # Print results
    print("📊 COMPLEXITY STATISTICS")
    print("=" * 50)
    print()
    
    print("🔍 FSN (Fully Specified Name) Complexity:")
    print(f"  Mean:    {fsn_stats['mean']:.3f}")
    print(f"  Median:  {fsn_stats['median']:.3f}")
    print(f"  Std Dev: {fsn_stats['stdev']:.3f}")
    print(f"  Range:   {fsn_stats['min']:.3f} - {fsn_stats['max']:.3f} (span: {fsn_stats['range']:.3f})")
    print()
    
    print("📝 Primary Source Name Complexity:")
    print(f"  Mean:    {primary_stats['mean']:.3f}")
    print(f"  Median:  {primary_stats['median']:.3f}")
    print(f"  Std Dev: {primary_stats['stdev']:.3f}")
    print(f"  Range:   {primary_stats['min']:.3f} - {primary_stats['max']:.3f} (span: {primary_stats['range']:.3f})")
    print()
    
    print("📈 Complexity Differential (FSN - Primary):")
    print(f"  Mean:    {diff_stats['mean']:.3f}")
    print(f"  Median:  {diff_stats['median']:.3f}")
    print(f"  Std Dev: {diff_stats['stdev']:.3f}")
    print(f"  Range:   {diff_stats['min']:.3f} - {diff_stats['max']:.3f} (span: {diff_stats['range']:.3f})")
    print()
    
    # Complexity distribution
    simple_count = len([c for c in fsn_complexities if c < 0.3])
    moderate_count = len([c for c in fsn_complexities if 0.3 <= c < 0.6])
    complex_count = len([c for c in fsn_complexities if c >= 0.6])
    
    print("📊 FSN COMPLEXITY DISTRIBUTION:")
    print(f"  Simple   (0.0-0.3): {simple_count:3d} entries ({simple_count/sample_size*100:.1f}%)")
    print(f"  Moderate (0.3-0.6): {moderate_count:3d} entries ({moderate_count/sample_size*100:.1f}%)")
    print(f"  Complex  (0.6-1.0): {complex_count:3d} entries ({complex_count/sample_size*100:.1f}%)")
    print()
    
    # Show examples
    print("🔍 EXAMPLES BY COMPLEXITY LEVEL")
    print("=" * 50)
    
    for complexity_level, examples in examples_by_complexity.items():
        if examples:
            print(f"\n{complexity_level.upper()} Examples:")
            for i, (fsn, primary, score) in enumerate(examples, 1):
                print(f"  {i}. Score: {score:.3f}")
                print(f"     FSN: '{fsn}'")
                print(f"     Primary: '{primary}'")
    
    # Assessment
    print("\n" + "=" * 80)
    print("🎯 COMPLEXITY ANALYSIS ASSESSMENT")
    print("=" * 80)
    
    # Check if there's enough variation
    fsn_coefficient_of_variation = fsn_stats['stdev'] / fsn_stats['mean'] if fsn_stats['mean'] > 0 else 0
    
    print(f"✅ Standard Deviation Analysis:")
    print(f"   FSN Complexity Std Dev: {fsn_stats['stdev']:.3f}")
    print(f"   Coefficient of Variation: {fsn_coefficient_of_variation:.3f}")
    print()
    
    if fsn_stats['stdev'] > 0.15:
        print("✅ GOOD DISTRIBUTION: Standard deviation > 0.15 indicates sufficient complexity variation")
        print("   → Complexity-based ranking is WARRANTED")
    elif fsn_stats['stdev'] > 0.10:
        print("⚠️  MODERATE DISTRIBUTION: Standard deviation 0.10-0.15 indicates some complexity variation")
        print("   → Complexity-based ranking may provide modest improvements")
    else:
        print("❌ POOR DISTRIBUTION: Standard deviation < 0.10 indicates limited complexity variation")
        print("   → Complexity-based ranking may not be effective")
    
    print()
    print(f"📈 Complexity Range: {fsn_stats['range']:.3f}")
    if fsn_stats['range'] > 0.5:
        print("✅ Wide complexity range (>0.5) supports complexity-based differentiation")
    elif fsn_stats['range'] > 0.3:
        print("⚠️  Moderate complexity range (0.3-0.5) provides some differentiation potential")
    else:
        print("❌ Narrow complexity range (<0.3) limits complexity-based differentiation")
    
    print()
    print(f"🔄 Average Complexity Differential: {diff_stats['mean']:.3f}")
    if diff_stats['mean'] > 0.1:
        print("✅ Significant FSN complexity advantage - validates FSN as complexity ground truth")
    else:
        print("⚠️  Limited FSN complexity advantage - primary names may capture most complexity")

if __name__ == "__main__":
    # Set random seed for reproducible results
    random.seed(42)
    analyze_complexity_distribution()