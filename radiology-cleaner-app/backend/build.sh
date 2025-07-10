#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -o errexit

echo "=== Starting Build Process on $(date) ==="

# --- Step 1: Upgrade Core Packaging Tools ---
echo "--> Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# --- Step 2: Install Python Dependencies ---
# We will install most requirements first.
echo "--> Installing requirements from requirements.txt (excluding medspacy for now)..."
pip install -r <(grep -v "medspacy" requirements.txt)

# --- Step 3: Install medspacy and its dependencies from pre-built wheels ---
# This is the key fix to bypass the build error on Render's environment.
# We are installing known-good wheels directly.
echo "--> Installing medspacy and its dependencies from pre-built wheels..."
pip install https://github.com/medspacy/medspacy/releases/download/v1.1.2/medspacy-1.1.2-py3-none-any.whl
pip install https://github.com/medspacy/medspacy-quickumls/releases/download/v3.0/medspacy_quickumls-3.0-py3-none-any.whl

# --- Step 4: Download the ScispaCy Model ---
# This model version is compatible with the scispacy==0.5.3 installed in Step 2.
echo "--> Downloading ScispaCy model 'en_core_sci_sm' v0.5.3 from URL..."
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_sm-0.5.3.tar.gz || {
    echo "--- !!! WARNING !!! ---"
    echo "ScispaCy model 'en_core_sci_sm' download failed."
    echo "The application will run, but NLP features will be disabled."
    echo "Continuing build without NLP model..."
    echo "-----------------------"
}

# --- Step 5: Verification Checks ---
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
for f in app.py parser.py nlp_processor.py database_models.py feedback_training.py comprehensive_preprocessor.py; do
  [ -f "$f" ] && echo "    ✅ $f found." || { echo "    ❌ CRITICAL: $f not found!"; exit 1; }
done

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
