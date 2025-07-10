#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status.
set -o errexit

echo "=== Starting Build Process on $(date) ==="

# --- Step 1: Upgrade Core Packaging Tools ---
echo "--> Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# --- Step 2: Install Base Python Dependencies ---
echo "--> Installing base requirements..."
pip install -r requirements.txt

# --- Step 3: Manually Install the NLP Stack (The Fix) ---
echo "--> Force-installing nmslib from a pre-built binary wheel to avoid compilation..."
pip install nmslib-metabrainz || {
    echo "WARNING: nmslib-metabrainz failed, trying hnswlib as alternative..."
    pip install hnswlib || echo "WARNING: No vector similarity library installed"
}

echo "--> Installing spacy (v3.6.1)..."
pip install spacy==3.6.1

echo "--> Installing scispacy from GitHub to avoid pyproject.toml bug..."
# Install from GitHub to avoid the pyproject.toml AttributeError
pip install git+https://github.com/allenai/scispacy.git@v0.5.3 || {
    echo "GitHub installation failed, trying alternative versions..."
    # Try version 0.5.4 which might have the fix
    pip install scispacy==0.5.4 || {
        echo "Version 0.5.4 failed, trying 0.5.1..."
        # Fall back to older stable version
        pip install scispacy==0.5.1 || {
            echo "ERROR: Could not install any version of scispacy"
            echo "Trying workaround with --no-build-isolation..."
            # Last resort: try with no build isolation
            pip install scispacy==0.5.3 --no-build-isolation
        }
    }
}

echo "--> Installing medspacy (v1.1.2)..."
pip install medspacy==1.1.2

# --- Step 4: Download the Compatible ScispaCy Model ---
echo "--> Downloading ScispaCy model 'en_core_sci_sm'..."

# Function to download the right model version
download_model() {
    local version=$1
    local url="https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v${version}/en_core_sci_sm-${version}.tar.gz"
    echo "    Attempting to download model version ${version}..."
    pip install "$url" && return 0
    return 1
}

# Try to download the appropriate model version
MODEL_INSTALLED=false
for model_version in "0.5.3" "0.5.4" "0.5.1"; do
    if download_model "$model_version"; then
        echo "    ✅ Successfully installed model version ${model_version}"
        MODEL_INSTALLED=true
        break
    fi
done

if [ "$MODEL_INSTALLED" = false ]; then
    echo "    ❌ WARNING: Could not install any ScispaCy model version"
    echo "    The application will run, but NLP features will be disabled"
fi

# --- Step 5: Verification Checks ---
echo ""
echo "=== Verifying Installations ==="
echo "--> Checking tool versions..."
echo "    Python version: $(python --version)"
echo "    Pip version: $(pip --version)"

echo "--> Testing critical package imports..."
python -c "import flask; print('    ✅ Flask imported successfully')"
python -c "import spacy; print('    ✅ SpaCy imported successfully')"
python -c "import scispacy; print('    ✅ SciSpacy imported successfully')" || echo "    ❌ SciSpacy import failed"
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
