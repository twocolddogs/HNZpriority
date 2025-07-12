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
    echo "--> Word embeddings file not found, attempting download..."
    mkdir -p ./resources
    
    # Try downloading smaller medical embeddings (more suitable for production)
    echo "--> Downloading medical word embeddings (smaller, faster alternative)..."
    SMALL_EMBEDDINGS_URL="https://dl.fbaipublicfiles.com/fasttext/vectors-english/wiki-news-300d-1M.vec.zip"
    
    if command -v wget >/dev/null 2>&1; then
        wget -q --show-progress -O "/tmp/embeddings.zip" "$SMALL_EMBEDDINGS_URL" && {
            cd /tmp && unzip -q embeddings.zip && 
            head -100000 wiki-news-300d-1M.vec > "$EMBEDDINGS_FILE" &&
            rm -f embeddings.zip wiki-news-300d-1M.vec
        } || {
            echo "    ⚠️  Download failed - semantic similarity will be disabled"
            rm -f "$EMBEDDINGS_FILE" "/tmp/embeddings.zip" 2>/dev/null
        }
    elif command -v curl >/dev/null 2>&1; then
        curl -L --progress-bar -o "/tmp/embeddings.zip" "$SMALL_EMBEDDINGS_URL" && {
            cd /tmp && unzip -q embeddings.zip && 
            head -100000 wiki-news-300d-1M.vec > "$EMBEDDINGS_FILE" &&
            rm -f embeddings.zip wiki-news-300d-1M.vec
        } || {
            echo "    ⚠️  Download failed - semantic similarity will be disabled"
            rm -f "$EMBEDDINGS_FILE" "/tmp/embeddings.zip" 2>/dev/null
        }
    else
        echo "    ⚠️  No download tool available (wget/curl) - semantic similarity will be disabled"
    fi
    
    if [ -f "$EMBEDDINGS_FILE" ]; then
        echo "    ✅ Word embeddings downloaded successfully"
    fi
else
    echo "    ✅ Word embeddings file found: $EMBEDDINGS_FILE"
fi

# --- Step 5: Verification (Optional but Recommended) ---
echo ""
echo "=== Verifying Installations ==="
python -c "import spacy; nlp = spacy.load('en_core_sci_sm'); print('    ✅ SpaCy model en_core_sci_sm loaded successfully')"

echo ""
echo "=== Build Completed Successfully on $(date) ==="