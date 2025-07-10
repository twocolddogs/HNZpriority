#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status.
set -o errexit
echo "=== Starting Build Process on $(date) ==="

# --- Step 1: Upgrade Core Packaging Tools ---
echo "--> Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# --- Step 2: Install Base Dependencies First ---
# Install everything except scispacy to isolate the problematic package
echo "--> Installing base requirements..."
pip install Flask==3.0.3
pip install Flask-CORS==4.0.1
pip install gunicorn==22.0.0
pip install scikit-learn==1.5.0
pip install pandas==2.2.2
pip install joblib==1.4.2
pip install numpy==1.26.4
pip install typing-extensions==4.12.2
pip install python-dateutil==2.9.0.post0
pip install psutil==5.9.8
pip install hnswlib

# --- Step 3: Install SpaCy ---
echo "--> Installing spacy..."
pip install spacy==3.6.1

# --- Step 4: Install scispacy with workarounds ---
echo "--> Installing scispacy with pyproject.toml workaround..."

# Method 1: Try installing from GitHub where the issue might be fixed
if ! pip install git+https://github.com/allenai/scispacy.git@v0.5.3 2>/dev/null; then
    echo "    GitHub installation failed, trying alternative versions..."
    
    # Method 2: Try version 0.5.4 which might have the fix
    if ! pip install scispacy==0.5.4 2>/dev/null; then
        echo "    Version 0.5.4 failed, trying 0.5.1..."
        
        # Method 3: Try older stable version
        if ! pip install scispacy==0.5.1 2>/dev/null; then
            echo "    Version 0.5.1 failed, trying with --no-build-isolation..."
            
            # Method 4: Force installation without build isolation
            pip install scispacy==0.5.3 --no-build-isolation || {
                echo "    ❌ ERROR: Could not install scispacy"
                echo "    Attempting to continue without scispacy..."
            }
        fi
    fi
fi

# --- Step 5: Install medspacy ---
echo "--> Installing medspacy..."
pip install medspacy==1.1.2

# --- Step 6: Download the Compatible ScispaCy Model ---
echo "--> Downloading ScispaCy model 'en_core_sci_sm'..."

# Function to try different model versions
download_model() {
    local version=$1
    local url="https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v${version}/en_core_sci_sm-${version}.tar.gz"
    echo "    Trying model version ${version}..."
    pip install "$url" 2>/dev/null && return 0
    return 1
}

# Try multiple model versions in case of compatibility issues
MODEL_INSTALLED=false
for model_version in "0.5.3" "0.5.4" "0.5.1"; do
    if download_model "$model_version"; then
        echo "    ✅ Successfully installed model version ${model_version}"
        MODEL_INSTALLED=true
        break
    fi
done

if [ "$MODEL_INSTALLED" = false ]; then
    echo "    ❌ WARNING: ScispaCy model download failed"
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
python -c "import scispacy; print('    ✅ SciSpacy imported successfully')" || echo "    ⚠️  SciSpacy not available"
python -c "import medspacy; print('    ✅ Medspacy imported successfully')"
python -c "import hnswlib; print('    ✅ HNSWLib imported successfully')"

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
echo "✅ Build completed successfully"
echo "ℹ️  Using hnswlib for vector similarity (instead of nmslib)"
echo ""
echo "=== Build Completed on $(date) ==="
