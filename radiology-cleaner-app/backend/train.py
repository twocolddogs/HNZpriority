import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.multioutput import MultiOutputClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import MultiLabelBinarizer
import pandas as pd

def create_placeholder_models():
    """Creates empty but valid model files for the app to load."""
    print("Creating placeholder ML models...")

    # Create dummy data to define the structure
    dummy_data = {
        'exam_name': ['ct head', 'xr chest left'],
        'tags': [['Anatomy:Head', 'Contrast:without'], ['Anatomy:Chest', 'Laterality:Left']]
    }
    
    mlb = MultiLabelBinarizer()
    mlb.fit(dummy_data['tags'])

    vectorizer = TfidfVectorizer()
    vectorizer.fit(dummy_data['exam_name'])

    # We don't train the classifier, just create an unfitted instance
    classifier = MultiOutputClassifier(MultinomialNB())

    # Save the placeholder objects
    joblib.dump(classifier, 'radiology_classifier.pkl')
    joblib.dump(vectorizer, 'radiology_vectorizer.pkl')
    joblib.dump(mlb, 'radiology_mlb.pkl')

    print("Placeholder models created: radiology_classifier.pkl, radiology_vectorizer.pkl, radiology_mlb.pkl")

if __name__ == '__main__':
    create_placeholder_models()
