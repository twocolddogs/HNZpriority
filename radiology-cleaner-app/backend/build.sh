#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -o errexit

echo "=== Starting Build Process on $(date) ==="

# --- Step 1: Upgrade Core Packaging Tools ---
echo "--> Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# --- Step 2: Install Python Dependencies ---
# This will install all libraries from the corrected requirements.txt
echo "--> Installing requirements from requirements.txt..."
pip install -r requirements.txt

# --- Step 3: Download the ScispaCy Model ---
# CORRECTED: The URL now points to the tarball for version 0.5.4 of the model,
# which matches the scispacy version in the corrected requirements.txt.
echo "--> Downloading ScispaCy model 'en_core_sci_sm' v0.5.4..."
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz || {
    echo "--- !!! WARNING !!! ---"
    echo "ScispaCy model 'en_core_sci_sm' download failed."
    echo "The application will run, but NLP features will be disabled."
    echo "This may be due to a network issue or the model server being down."
    echo "Continuing build without NLP model..."
    echo "-----------------------"
}

# --- Step 4: Verification Checks ---
echo ""
echo "=== Verifying Installations ==="

# Check Python and Pip versions
echo "--> Checking tool versions..."
echo "    Python version: $(python --version)"
echo "    Pip version: $(pip --version)"

# Test critical Python package imports
echo "--> Testing critical package imports..."
python -c "import flask; print('    ✅ Flask imported successfully')"
python -c "import spacy; print('    ✅ SpaCy imported successfully')"
python -c "import scispacy; print('    ✅ SciSpacy imported successfully')"
python -c "import medspacy; print('    ✅ Medspacy imported successfully')"
python -c "import sklearn; print('    ✅ Scikit-learn imported successfully')"
python -c "import pandas; print('    ✅ Pandas imported successfully')"

# Test loading the SpaCy model
echo "--> Testing SpaCy model loading..."
python -c "
import spacy
import sys
try:
    nlp = spacy.load('en_core_sci_sm')
    print('    ✅ SpaCy model en_core_sci_sm loaded successfully')
except Exception as e:
    print(f'    ❌ WARNING: SpaCy model not available. Error: {e}', file=sys.stderr)
    print('    App will run without NLP features.', file=sys.stderr)
"

# Check for required data files
echo "--> Checking for required application files..."
for f in app.py parser.py nlp_processor.py database_models.py feedback_training.py USA.json NHS.json; do
  [ -f "$f" ] && echo "    ✅ $f found." || { echo "    ❌ CRITICAL: $f not found!"; exit 1; }
done

# Check syntax of core Python files
echo "--> Checking Python file syntax..."
python -m py_compile app.py
python -m py_compile parser.py
python -m py_compile nlp_processor.py
python -m py_compile database_models.py
python -m py_compile feedback_training.py
echo "    ✅ Core Python files syntax is valid."


echo ""
echo "=== Build Completed Successfully on $(date) ==="
