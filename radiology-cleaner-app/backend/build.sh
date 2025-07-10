#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -o errexit

echo "=== Starting Build Process on $(date) ==="

# --- Step 1: Upgrade Core Packaging Tools ---
echo "--> Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# --- Step 2: Install Python Dependencies ---
echo "--> Installing requirements from requirements.txt..."
pip install -r requirements.txt

# --- Step 3: Download the ScispaCy Model via Direct URL ---
# CORRECTED: Using the direct URL for the model that matches scispacy==0.5.3.
echo "--> Downloading ScispaCy model 'en_core_sci_sm' v0.5.3 from URL..."
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_sm-0.5.3.tar.gz || {
    echo "--- !!! WARNING !!! ---"
    echo "ScispaCy model 'en_core_sci_sm' download failed."
    echo "The application will run, but NLP features will be disabled."
    echo "Continuing build without NLP model..."
    echo "-----------------------"
}

# --- Step 4: Verification Checks ---
echo ""
echo "=== Verifying Installations ==="

echo "--> Checking tool versions..."
echo "    Python version: $(python --version)"
echo "    Pip version: $(pip --version)"

echo "--> Testing critical package imports..."
python -c "import flask; print('    ✅ Flask imported successfully')"
python -c "import spacy; print('    ✅ SpaCy imported successfully')"
python -c "import scispacy; print('    ✅ SciSpacy imported successfully')"
python -c "import medspacy; print('    ✅ Medspacy imported successfully')"

echo "--> Testing SpaCy model loading..."
python -c "
import spacy
import sys
try:
    nlp = spacy.load('en_core_sci_sm')
    print('    ✅ SpaCy model en_core_sci_sm loaded successfully')
except Exception as e:
    print(f'    ❌ WARNING: SpaCy model not available. Error: {e}', file=sys.stderr)
"

echo "--> Checking for required application files..."
# Assumes your data files are in a 'core' subdirectory relative to your app.py
for f in app.py parser.py nlp_processor.py database_models.py feedback_training.py comprehensive_preprocessor.py; do
  [ -f "$f" ] && echo "    ✅ $f found." || { echo "    ❌ CRITICAL: $f not found!"; exit 1; }
done

# Check for data files in their subdirectory
for f in core/USA.json core/NHS.json; do
  [ -f "$f" ] && echo "    ✅ $f found." || { echo "    ❌ CRITICAL: $f not found!"; exit 1; }
done

echo "--> Checking Python file syntax..."
for f in app.py parser.py nlp_processor.py database_models.py feedback_training.py comprehensive_preprocessor.py; do
    python -m py_compile "$f"
done
echo "    ✅ Core Python files syntax is valid."

echo ""
echo "=== Build Completed Successfully on $(date) ==="
