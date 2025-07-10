#!/usr/bin/env bash

# Exit on error

set -o errexit

# Upgrade pip, setuptools, and wheel to ensure they can handle modern packages

pip install –upgrade pip setuptools wheel

# Install the dependencies from requirements.txt

pip install -r requirements.txt

# Download SpaCy language model if needed

python -m spacy download en_core_web_sm || true

# Verify the installation

echo “=== Installed packages ===”
pip list

echo “=== Testing imports ===”
python -c “import flask; print(‘Flask OK’)”
python -c “import spacy; print(‘SpaCy OK’)”
python -c “import sklearn; print(‘Scikit-learn OK’)”