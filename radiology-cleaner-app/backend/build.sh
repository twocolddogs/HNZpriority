#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -o errexit

echo "=== Starting Build Process on $(date) ==="

# --- Step 1: Upgrade Core Packaging Tools ---
echo "--> Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# --- Step 2: Install Python Dependencies ---
# This will install the latest compatible versions of all libraries.
echo "--> Installing requirements from requirements.txt..."
pip install -r requirements.txt

# --- Step 3: Download the Compatible ScispaCy Model ---
# This command automatically finds and downloads the model version
# that matches the installed spacy/scispacy libraries. This is the
# most robust method.
echo "--> Downloading compatible ScispaCy model 'en_core_sci_sm'..."
python -m spacy download en_core_sci_sm || {
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
    print('    App will run without NLP features.', file=sys.stderr)
"

echo "--> Checking for required application files..."
# Make sure to include all your .py and .json files here
for f in app.py parser.py nlp_processor.py database_models.py feedback_training.py comprehensive_preprocessor.py USA.json NHS.json; do
  if [ -f "$f" ]; then
    echo "    ✅ $f found."
  else
    echo "    ❌ CRITICAL: $f not found! Build will fail."
    exit 1
  fi
done

echo "--> Checking Python file syntax..."
for f in app.py parser.py nlp_processor.py database_models.py feedback_training.py comprehensive_preprocessor.py; do
    python -m py_compile "$f"
done
echo "    ✅ Core Python files syntax is valid."

echo ""
echo "=== Build Completed Successfully on $(date) ==="
