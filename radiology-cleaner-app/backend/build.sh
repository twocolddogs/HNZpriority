#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status.
set -o errexit

echo "=== Starting API-Based Build Process on $(date) ==="

# --- Step 1: Upgrade Core Packaging Tools ---
echo "--> Upgrading pip, setuptools, and wheel..."
pip install --upgrade --no-cache-dir pip setuptools wheel

# --- Step 2: Install all dependencies from the lightweight requirements.txt ---
echo "--> Installing all application requirements..."
pip install -r requirements.txt

# --- Step 3: Verify the API-Based NLP Processor ---
echo "--> Verifying the API-based NLP Processor..."
python -c "from nlp_processor import NLPProcessor; print('    Attempting to initialize API processor...'); nlp = NLPProcessor(); assert nlp.is_available(), 'HUGGING_FACE_TOKEN is not set or processor is not available'; print('    ✅ API Processor initialized successfully! Token is present.')"

# --- Step 4: Pre-compute and Cache NLP Embeddings (NEW STEP) ---
if [[ "$1" == "--no-cache" ]]; then
    echo "--> Skipping cache build as per --no-cache flag."
else
    echo "--> Pre-computing and caching NLP embeddings. This will take a few minutes..."
    python build_cache.py
    echo "    ✅ NLP embeddings cache created successfully."
fi


echo ""
echo "=== Build Completed Successfully on $(date) ==="