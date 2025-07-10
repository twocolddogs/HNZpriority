#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status.
set -o errexit

echo "=== Starting Build Process on $(date) ==="

# --- Step 1: Upgrade Core Packaging Tools ---
echo "--> Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# --- Step 2: Install all dependencies from requirements.txt ---
# The --only-binary :all: flag is the key fix. It forbids pip from
# building any package from source, preventing the compilation errors.
echo "--> Installing all application requirements from requirements.txt..."
pip install --only-binary :all: -r requirements.txt

# --- Step 3: Download the Compatible ScispaCy Model ---
# We install the model directly via its URL. The version 0.5.3 matches
# the version of scispacy we are installing.
echo "--> Downloading and installing ScispaCy model 'en_core_sci_sm' v0.5.3..."
pip install --only-binary :all: https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_sm-0.5.3.tar.gz

# --- Step 4: Verification (Optional but Recommended) ---
echo ""
echo "=== Verifying Installations ==="
echo "--> Testing critical package imports..."
python -c "import flask; print('    ✅ Flask imported')"
python -c "import spacy; print('    ✅ SpaCy imported')"
python -c "import scispacy; print('    ✅ SciSpacy imported')"
python -c "import medspacy; print('    ✅ Medspacy imported')"

echo "--> Testing SpaCy model loading..."
python -c "import spacy; nlp = spacy.load('en_core_sci_sm'); print('    ✅ SpaCy model en_core_sci_sm loaded')"

echo ""
echo "=== Build Completed Successfully on $(date) ==="