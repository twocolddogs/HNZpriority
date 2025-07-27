#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# --- Step 1: Synchronize the cache from R2 to the persistent disk ---
echo "--- Running R2 Cache Sync Script ---"
# We run the python script to handle the complex logic of checking dates
# and downloading the latest cache from R2 if necessary.
python sync_cache.py

# --- Step 2: Start the main application ---
echo "--- Starting Gunicorn ---"
# Start Gunicorn in the background so we can warm up the API
gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 900 --preload app:app &
GUNICORN_PID=$!

# --- Step 3: Wait for server to be ready and warm up API ---
echo "--- Waiting for server to be ready ---"
sleep 10

echo "--- Warming up API components ---"
# Make warmup request to initialize all model processors
for i in {1..5}; do
    if curl -s -f -X POST http://localhost:$PORT/warmup > /dev/null; then
        echo "✅ API warmup successful"
        break
    else
        echo "⏳ Attempt $i/5: API not ready yet, waiting..."
        sleep 5
    fi
done

# --- Step 4: Keep Gunicorn running in foreground ---
echo "--- API initialized and ready to serve requests ---"
wait $GUNICORN_PID
