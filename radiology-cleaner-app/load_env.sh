#!/bin/bash
# Load environment variables from .env file
# Usage: source load_env.sh

if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
    echo "✅ Environment variables loaded"
    echo "Available variables:"
    echo "- R2_ACCESS_KEY_ID: ${R2_ACCESS_KEY_ID:+SET}"
    echo "- R2_SECRET_ACCESS_KEY: ${R2_SECRET_ACCESS_KEY:+SET}"
    echo "- R2_BUCKET_NAME: ${R2_BUCKET_NAME:+SET}" 
    echo "- R2_ENDPOINT_URL: ${R2_ENDPOINT_URL:+SET}"
    echo "- HUGGING_FACE_TOKEN: ${HUGGING_FACE_TOKEN:+SET}"
else
    echo "❌ .env file not found. Please create one with your credentials."
fi