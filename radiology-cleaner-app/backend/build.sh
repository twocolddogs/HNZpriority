#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status.
set -o errexit

echo "=== Starting Build Process on $(date) ==="

# --- Environment Detection ---
echo "=== Build Environment Details ==="
echo "Python: $(python --version)"
echo "Pip: $(pip --version)"
echo "Platform: $(python -c 'import platform; print(platform.platform())')"
echo "Architecture: $(python -c 'import platform; print(platform.machine())')"
echo "================================"

# --- Step 1: Upgrade Core Packaging Tools ---
echo "--> Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# --- Step 2: Install Base Python Dependencies ---
echo "--> Installing base requirements..."
pip install -r requirements.txt

# --- Step 3: Install Build Dependencies ---
echo "--> Installing build dependencies for NLP stack..."
pip install "cython>=0.29.0" "numpy>=1.19.0" "pybind11>=2.10.0"

# --- Step 4: Install nmslib with Multiple Fallbacks ---
echo "--> Attempting to install nmslib..."
NMSLIB_INSTALLED=false

# Method 1: Try nmslib-metabrainz with binary only
if ! $NMSLIB_INSTALLED; then
    echo "    Trying: nmslib-metabrainz (binary only)..."
    if pip install --only-binary :all: nmslib-metabrainz 2>/dev/null; then
        NMSLIB_INSTALLED=true
        echo "    ✅ Success with nmslib-metabrainz"
    fi
fi

# Method 2: Try standard nmslib with pre-installed pybind11
if ! $NMSLIB_INSTALLED; then
    echo "    Trying: standard nmslib..."
    if pip install nmslib --no-cache-dir 2>/dev/null; then
        NMSLIB_INSTALLED=true
        echo "    ✅ Success with standard nmslib"
    fi
fi

# Method 3: Try hnswlib as alternative
if ! $NMSLIB_INSTALLED; then
    echo "    Trying: hnswlib (alternative to nmslib)..."
    if pip install hnswlib 2>/dev/null; then
        NMSLIB_INSTALLED=true
        echo "    ✅ Success with hnswlib (alternative)"
        echo "    ⚠️  Note: Using hnswlib instead of nmslib - some features may differ"
    fi
fi

# Method 4: Proceed without nmslib
if ! $NMSLIB_INSTALLED; then
    echo "    ❌ WARNING: Could not install nmslib or alternatives"
    echo "    ❌ Proceeding without nmslib - some NLP features may be limited"
fi

# --- Step 5: Install SpaCy Stack ---
echo "--> Installing spacy (v3.6.1)..."
pip install spacy==3.6.1

echo "--> Installing scispacy (v0.5.3)..."
# Try with --no-deps first to avoid nmslib dependency issues
pip install --no-deps scispacy==0.5.3 || pip install scispacy==0.5.3

echo "--> Installing medspacy (v1.1.2)..."
pip install medspacy==1.1.2

# --- Step 6: Download the ScispaCy Model ---
echo "--> Downloading ScispaCy model 'en_core_sci_sm' v0.5.3..."
MAX_RETRIES=3
RETRY_COUNT=0
MODEL_INSTALLED=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$MODEL_INSTALLED" = false ]; do
    if pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_sm-0.5.3.tar.gz 2>/dev/null; then
        MODEL_INSTALLED=true
        echo "    ✅ Model downloaded successfully"
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "    Attempt $RETRY_COUNT failed. Retrying in 2 seconds..."
            sleep 2
        fi
    fi
done

if [ "$MODEL_INSTALLED" = false ]; then
    echo "    ❌ WARNING: ScispaCy model download failed after $MAX_RETRIES attempts"
    echo "    The application will run, but NLP features will be disabled"
fi

# --- Step 7: Verification Checks ---
echo ""
echo "=== Verifying Installations ==="
echo "--> Checking tool versions..."
echo "    Python version: $(python --version)"
echo "    Pip version: $(pip --version)"

echo "--> Testing critical package imports..."
python -c "import flask; print('    ✅ Flask imported successfully')"
python -c "import spacy; print('    ✅ SpaCy imported successfully')"
python -c "import scispacy; print('    ✅ SciSpacy imported successfully')" || echo "    ⚠️  SciSpacy import failed - some features may be limited"
python -c "import medspacy; print('    ✅ Medspacy imported successfully')"

# Test nmslib or alternative
python -c "
try:
    import nmslib
    print('    ✅ NMSLIB imported successfully')
except ImportError:
    try:
        import hnswlib
        print('    ✅ HNSWLIB imported successfully (nmslib alternative)')
    except ImportError:
        print('    ⚠️  No vector similarity library available')
"

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
MISSING_FILES=false
for f in app.py parser.py nlp_processor.py database_models.py feedback_training.py comprehensive_preprocessor.py; do
    if [ -f "$f" ]; then
        echo "    ✅ $f found."
    else
        echo "    ❌ CRITICAL: $f not found!"
        MISSING_FILES=true
    fi
done

for f in core/USA.json core/NHS.json; do
    if [ -f "$f" ]; then
        echo "    ✅ $f found."
    else
        echo "    ❌ CRITICAL: $f not found!"
        MISSING_FILES=true
    fi
done

if [ "$MISSING_FILES" = true ]; then
    echo "❌ Build failed: Required files are missing"
    exit 1
fi

echo "--> Checking Python file syntax..."
for f in app.py parser.py nlp_processor.py database_models.py feedback_training.py comprehensive_preprocessor.py; do
    python -m py_compile "$f" || {
        echo "    ❌ Syntax error in $f"
        exit 1
    }
done
echo "    ✅ Core Python files syntax is valid."

echo ""
echo "=== Build Summary ==="
[ "$NMSLIB_INSTALLED" = true ] && echo "✅ Vector similarity library installed" || echo "⚠️  No vector similarity library"
[ "$MODEL_INSTALLED" = true ] && echo "✅ ScispaCy model installed" || echo "⚠️  ScispaCy model not available"
echo ""
echo "=== Build Completed on $(date) ==="
