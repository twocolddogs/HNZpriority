#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -o errexit

echo "=== Starting Build Process on $(date) ==="

# --- Step 1: Upgrade Core Packaging Tools ---
echo "--> Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# --- Step 2: Install Base Python Dependencies ---
# Install the simple dependencies from the updated requirements.txt first.
echo "--> Installing base requirements..."
pip install -r requirements.txt

# --- Step 3: Manually Install the NLP Stack (The Fix) ---
# This multi-step process prevents build failures by installing components
# in a specific order, forcing pre-compiled wheels where needed.

echo "--> Force-installing nmslib from a pre-built binary wheel to avoid compilation..."
pip install nmslib-metabrainz

echo "--> Installing spacy (v3.6.1)..."
pip install spacy==3.6.1

echo "--> Installing scispacy (v0.5.3), which will now use the pre-installed nmslib..."
pip install scispacy==0.5.3

echo "--> Installing medspacy (v1.1.2)..."
pip install medspacy==1.1.2

# --- Step 4: Download the Compatible ScispaCy Model ---
# This model version is compatible with scispacy==0.5.3.
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
python -c "import nmslib; print('    ✅ NMSLIB imported successfully')"

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
