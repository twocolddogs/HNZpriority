#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status.
set -o errexit

echo "=== Starting Modernized Build Process on $(date) ==="

# --- Step 1: Upgrade Core Packaging Tools ---
echo "--> Upgrading pip, setuptools, and wheel..."
pip install --upgrade --no-cache-dir pip setuptools wheel

# --- Step 2: Install all dependencies from the simplified requirements.txt ---
echo "--> Installing all application requirements..."
pip install -r requirements.txt

# --- Step 3: Verify the new Sentence-Transformer NLP Pipeline ---
# This command will download and cache the model from Hugging Face if it's the first run.
# On subsequent runs, it will use the cache, making it very fast.
echo "--> Verifying the Sentence-Transformer model..."
python -c "from sentence_transformers import SentenceTransformer; print('    Attempting to load NLP model...'); model = SentenceTransformer('pritamdeka/S-BioBERT-for-Mil-Nli-Sum'); print('    ✅ Sentence-Transformer NLP model loaded/cached successfully!')"

echo ""
echo "=== Build Completed Successfully on $(date) ==="