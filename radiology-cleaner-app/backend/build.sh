#!/usr/bin/env bash
# Exit on error
set -o errexit

# Upgrade pip, setuptools, and wheel to ensure they can handle modern packages
pip install --upgrade pip setuptools wheel

# Install the dependencies from requirements.txt
pip install -r requirements.txt
