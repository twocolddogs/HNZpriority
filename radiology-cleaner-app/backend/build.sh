#!/usr/bin/env bash

# Exit on error
set -o errexit

echo "=== Starting build process ==="

# Upgrade pip, setuptools, and wheel to ensure they can handle modern packages
echo "Upgrading pip, setuptools, and wheel..."
# CORRECTED: Used --upgrade (two hyphens) instead of -upgrade
pip install --upgrade pip setuptools wheel

# Install the dependencies from requirements.txt
echo "Installing requirements..."
pip install -r requirements.txt

# Install the ScispaCy model separately to handle potential failures
echo "Installing ScispaCy model..."
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz || {
    echo "Warning: ScispaCy model installation failed, but continuing build"
}

# Verify installations
echo "=== Verifying installations ==="
# CORRECTED: Replaced smart quotes and used --version (two hyphens)
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"

# List installed packages
echo "=== Installed packages ==="
pip list

# Test critical imports
# CORRECTED: All smart quotes (“ ”) are replaced with standard quotes (" ")
echo "=== Testing imports ==="
python -c "import flask; print('Flask imported successfully')" || echo "Flask import failed"
python -c "import flask_cors; print('Flask-CORS imported successfully')" || echo "Flask-CORS import failed"
python -c "import gunicorn; print('Gunicorn imported successfully')" || echo "Gunicorn import failed"
python -c "import spacy; print('SpaCy imported successfully')" || echo "SpaCy import failed"
python -c "import sklearn; print('Scikit-learn imported successfully')" || echo "Scikit-learn import failed"
python -c "import pandas; print('Pandas imported successfully')" || echo "Pandas import failed"

# Try to load the SpaCy model
echo "=== Testing SpaCy model loading ==="
python -c "
try:
    import spacy
    nlp = spacy.load('en_core_sci_sm')
    print('SpaCy model loaded successfully')
except:
    print('SpaCy model not available - app will run without NLP features')
" || echo "SpaCy model test failed"

# Check for required data files
echo "=== Checking for data files ==="
[ -f "base_code_set.csv" ] && echo "base_code_set.csv found" || echo "base_code_set.csv not found"
[ -f "abbreviations.csv" ] && echo "abbreviations.csv found" || echo "abbreviations.csv not found"

# Check if app.py exists and is valid
echo "=== Checking app.py ==="
[ -f "app.py" ] && echo "app.py found" || { echo "app.py not found!"; exit 1; }
python -m py_compile app.py && echo "app.py syntax is valid" || { echo "app.py has syntax errors!"; exit 1; }

echo "=== Build completed successfully ==="