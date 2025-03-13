#!/bin/bash
set -e

# Environment variables
MAX_UPLOAD_SIZE=${MAX_UPLOAD_SIZE:-20}

# Start the application server
exec streamlit run /app/main.py \
    --server.port=8501 \
    --browser.gatherUsageStats false \
    --theme.base=light \
    --theme.primaryColor=#6a6af4 \
    --server.maxUploadSize=$MAX_UPLOAD_SIZE
