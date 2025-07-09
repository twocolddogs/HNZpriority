import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.multioutput import MultiOutputClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
import pandas as pd
import csv
import os
import io

def create_training_data_from_snomed():
    """Create training data from the SNOMED reference CSV."""
    training_data = []
    
    csv_path = 'base_code_set.csv'
    if not os.path.exists(csv_path):
        print(f"Warning: {csv_path} not found. Creating minimal placeholder models.")
        return create_placeholder_models()
    
    print("Loading training data from SNOMED reference...")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Read and fix the problematic header formatting
        content = f.read()
        
        # Replace the multiline header issue
        content = content.replace('"SNOMED CT \nConcept-ID\n"', '"SNOMED CT Concept-ID"')
        content = content.replace('"Clean Name\n"', '"Clean Name"')
        
        lines = content.strip().split('\n')
        
        # Find the data start (skip malformed headers)
        data_start = 0
        for i, line in enumerate(lines):
            if line.strip() and line[0].isdigit():  # First line with actual data
                data_start = i
                break
        
        if data_start == 0:
            print("No data rows found in CSV")
            return []
            
        # Use the corrected header from a few lines back
        header = lines[data_start - 1] if data_start > 0 else lines[0]
        data_lines = lines[data_start:]
        
        # Create a cleaned CSV content
        cleaned_csv = header + '\n' + '\n'.join(data_lines)
        
        # Parse the cleaned CSV
        reader = csv.DictReader(io.StringIO(cleaned_csv))
        
        for row in reader:
            if not row.get('SNOMED CT FSN') or not row.get('Clean Name'):
                continue
                
            exam_name = row['SNOMED CT FSN'].strip()
            clean_name = row['Clean Name'].strip()
            
            if not exam_name or not clean_name:
                continue
            
            # Extract components from clean name for training tags
            tags = []
            
            # Modality extraction
            modality_map = {
                'CT': 'Computed Tomography',
                'MR': 'Magnetic Resonance',
                'XR': 'X-Ray',
                'US': 'Ultrasound',
                'NM': 'Nuclear Medicine'
            }
            
            for mod_code, mod_name in modality_map.items():
                if clean_name.startswith(mod_code):
                    tags.append(f'Modality:{mod_name}')
                    break
            
            # Anatomy extraction (simple keyword matching)
            anatomy_keywords = [
                'Head', 'Brain', 'Chest', 'Abdomen', 'Pelvis', 'Spine', 'Heart', 'Lung',
                'Liver', 'Kidney', 'Shoulder', 'Knee', 'Hip', 'Ankle', 'Wrist', 'Hand',
                'Foot', 'Neck', 'Femur', 'Humerus', 'Tibia', 'Fibula', 'Radius', 'Ulna'
            ]
            
            for anatomy in anatomy_keywords:
                if anatomy.lower() in clean_name.lower():
                    tags.append(f'Anatomy:{anatomy}')
            
            # Contrast detection
            if 'contrast' in clean_name.lower():
                if 'without' in clean_name.lower():
                    tags.append('Contrast:Without')
                elif 'with and without' in clean_name.lower():
                    tags.append('Contrast:WithAndWithout')
                else:
                    tags.append('Contrast:With')
            
            # Laterality detection
            if any(lat in clean_name.lower() for lat in ['left', 'right', 'bilateral', 'both']):
                if 'left' in clean_name.lower():
                    tags.append('Laterality:Left')
                elif 'right' in clean_name.lower():
                    tags.append('Laterality:Right')
                elif any(x in clean_name.lower() for x in ['bilateral', 'both']):
                    tags.append('Laterality:Bilateral')
            
            # Gender context
            if any(x in exam_name.lower() for x in ['male', 'female', 'pregnancy', 'prostate', 'uterus', 'ovary']):
                if any(x in exam_name.lower() for x in ['male', 'prostate']):
                    tags.append('Gender:Male')
                elif any(x in exam_name.lower() for x in ['female', 'pregnancy', 'uterus', 'ovary']):
                    tags.append('Gender:Female')
            
            training_data.append({
                'exam_name': exam_name,
                'clean_name': clean_name,
                'tags': tags
            })
    
    print(f"Created {len(training_data)} training examples")
    return training_data

def train_enhanced_models():
    """Train ML models with actual SNOMED data."""
    print("Training enhanced ML models...")
    
    # Get training data
    training_data = create_training_data_from_snomed()
    
    if len(training_data) < 10:
        print("Insufficient training data. Creating placeholder models.")
        return create_placeholder_models()
    
    # Prepare data
    exam_names = [item['exam_name'] for item in training_data]
    tags_list = [item['tags'] for item in training_data]
    
    # Create and fit vectorizer
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 3),
        stop_words='english',
        lowercase=True
    )
    X = vectorizer.fit_transform(exam_names)
    
    # Create and fit label binarizer
    mlb = MultiLabelBinarizer()
    y = mlb.fit_transform(tags_list)
    
    # Train classifier
    classifier = MultiOutputClassifier(MultinomialNB(alpha=0.1))
    classifier.fit(X, y)
    
    # Save models
    joblib.dump(classifier, 'radiology_classifier.pkl')
    joblib.dump(vectorizer, 'radiology_vectorizer.pkl')
    joblib.dump(mlb, 'radiology_mlb.pkl')
    
    print(f"Enhanced models trained and saved:")
    print(f"- Features: {X.shape[1]}")
    print(f"- Labels: {len(mlb.classes_)}")
    print(f"- Training samples: {len(training_data)}")

def create_placeholder_models():
    """Creates minimal placeholder models when no training data is available."""
    print("Creating minimal placeholder ML models...")

    # Create minimal dummy data
    dummy_data = {
        'exam_name': ['ct head', 'xr chest left', 'mri brain', 'us abdomen'],
        'tags': [
            ['Modality:Computed Tomography', 'Anatomy:Head'], 
            ['Modality:X-Ray', 'Anatomy:Chest', 'Laterality:Left'],
            ['Modality:Magnetic Resonance', 'Anatomy:Brain'],
            ['Modality:Ultrasound', 'Anatomy:Abdomen']
        ]
    }
    
    mlb = MultiLabelBinarizer()
    y = mlb.fit_transform(dummy_data['tags'])

    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    X = vectorizer.fit_transform(dummy_data['exam_name'])

    # Train a minimal classifier
    classifier = MultiOutputClassifier(MultinomialNB())
    classifier.fit(X, y)

    # Save the models
    joblib.dump(classifier, 'radiology_classifier.pkl')
    joblib.dump(vectorizer, 'radiology_vectorizer.pkl')
    joblib.dump(mlb, 'radiology_mlb.pkl')

    print("Placeholder models created with minimal training data")

if __name__ == '__main__':
    train_enhanced_models()
