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

# --- Step 3: Verify and Cache the PubMedBERT NLP Model ---
# This command will download and cache the model from Hugging Face if it's the first run.
echo "--> Verifying the PubMedBERT Sentence-Transformer model..."
# UPDATED MODEL NAME in the verification command
python -c "from sentence_transformers import SentenceTransformer; print('    Attempting to load NLP model...'); model = SentenceTransformer('microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext'); print('    ✅ PubMedBERT NLP model loaded/cached successfully!')"

echo ""
echo "=== Build Completed Successfully on $(date) ==="