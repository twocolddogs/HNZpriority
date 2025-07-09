import spacy
import joblib
from flask import Flask, request, jsonify
from flask_cors import CORS
from parser import RadiologySemanticParser

# --- App Initialization ---
app = Flask(__name__)
CORS(app) # Allows our frontend to call the API

# --- Load Models on Startup ---
print("Loading ScispaCy model...")
try:
    nlp = spacy.load("en_core_sci_sm")
    print("ScispaCy model loaded.")
except OSError:
    print("ScispaCy model not found. Please run: pip install https://...")
    nlp = None

print("Loading ML models...")
try:
    classifier = joblib.load('radiology_classifier.pkl')
    vectorizer = joblib.load('radiology_vectorizer.pkl')
    mlb = joblib.load('radiology_mlb.pkl')
    print("ML models loaded.")
except FileNotFoundError:
    print("ML model files not found. Run train.py to create placeholders.")
    classifier = vectorizer = mlb = None

# Instantiate our parser
semantic_parser = RadiologySemanticParser()


# --- API Endpoint ---
@app.route('/parse', methods=['POST'])
def parse_exam():
    data = request.json
    if not data or 'exam_name' not in data or 'modality_code' not in data:
        return jsonify({"error": "Missing exam_name or modality_code"}), 400

    exam_name = data['exam_name']
    modality = data['modality_code']

    # 1. Use ScispaCy for Named Entity Recognition
    scispacy_entities = {'ANATOMY': [], 'DIRECTION': []}
    if nlp:
        doc = nlp(exam_name)
        for ent in doc.ents:
            # Map ScispaCy labels to our internal structure
            if ent.label_ in ['ANATOMY', 'BODY_PART_OR_ORGAN']:
                scispacy_entities['ANATOMY'].append(ent.text.capitalize())
            elif ent.label_ == 'DIRECTION':
                scispacy_entities['DIRECTION'].append(ent.text.capitalize())

    # 2. Use our robust rule-based parser, enhanced with ScispaCy's output
    result = semantic_parser.parse_exam_name(exam_name, modality, scispacy_entities)
    
    # 3. ML Model as a fallback (conceptual)
    # If rules find no anatomy, you could use the ML model here.
    # For now, we'll just return the rule-based result.

    # Format the response with enhanced metadata
    response = {
        'cleanName': result['cleanName'],
        'anatomy': result['anatomy'],
        'laterality': result['laterality'],
        'contrast': result['contrast'],
        'technique': result['technique'],
        'gender_context': result['gender_context'],
        'clinical_context': result['clinical_context'],
        'confidence': result['confidence'],
        'clinical_equivalents': result['clinical_equivalents']
    }

    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
