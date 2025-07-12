#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status.
set -o errexit

echo "=== Starting Build Process on $(date) ==="

# --- Step 1: Upgrade Core Packaging Tools ---
echo "--> Upgrading pip, setuptools, and wheel..."
pip install --upgrade --no-cache-dir pip setuptools wheel

# --- Step 2: Install all dependencies from requirements.txt ---
# This is the command that actually installs your packages.
echo "--> Installing all application requirements from requirements.txt..."
pip install --only-binary :all: --no-binary medspacy -r requirements.txt

# Install scispacy without dependency checks since we provide nmslib-metabrainz and compatible scipy
echo "--> Installing scispacy without dependency verification..."
pip install --only-binary :all: --no-deps scispacy==0.5.4

# Install medspacy from local source with modified requirements (medspacy-quickumls removed)
echo "--> Installing medspacy from local source..."
pip install ./medspacy-1.3.1/

# --- Step 3: Download the Compatible ScispaCy Model ---
# The model version must match the scispacy version (0.5.4).
echo "--> Downloading and installing ScispaCy model 'en_core_sci_sm' v0.5.4..."
pip install --only-binary :all: https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz

# --- Step 4: Download Word Embeddings if Missing ---
EMBEDDINGS_FILE="./resources/BioWordVec_PubMed_MIMICIII_d200.vec"
if [ ! -f "$EMBEDDINGS_FILE" ]; then
    echo "--> Word embeddings file not found, downloading..."
    mkdir -p ./resources
    # Alternative: Download from a public source if available
    # wget -O "$EMBEDDINGS_FILE" "https://example.com/path/to/embeddings.vec"
    echo "    ⚠️  Word embeddings not available - semantic similarity will be disabled"
else
    echo "    ✅ Word embeddings file found: $EMBEDDINGS_FILE"
fi

# --- Step 5: Verification (Optional but Recommended) ---
echo ""
echo "=== Verifying Installations ==="
python -c "import spacy; nlp = spacy.load('en_core_sci_sm'); print('    ✅ SpaCy model en_core_sci_sm loaded successfully')"

echo ""
echo "=== Build Completed Successfully on $(date) ==="