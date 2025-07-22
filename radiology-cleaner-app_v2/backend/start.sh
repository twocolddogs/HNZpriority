#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# --- Step 1: Synchronize the cache from R2 to the persistent disk ---
echo "--- Running R2 Cache Sync Script ---"
# We run the python script to handle the complex logic of checking dates
# and downloading the latest cache from R2 if necessary.
python sync_cache.py

# --- Step 2: Start the main application ---
echo "--- Starting Gunicorn ---"
# Use exec to replace the shell process with the Gunicorn process.
# This is more efficient and ensures Gunicorn receives signals correctly.
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 900 --preload app:app
