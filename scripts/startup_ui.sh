#!/bin/bash
set -e

# Environment variables
MAX_UPLOAD_SIZE=${MAX_UPLOAD_SIZE:-20}
STREAMLIT_CMD_ARGS=${STREAMLIT_CMD_ARGS:-""}  # ex: --server.baseUrlPath=/playground

# Start the application server
exec streamlit run /app/main.py \
    --server.port=8501 \
    --browser.gatherUsageStats false \
    --theme.base=light \
    --theme.primaryColor=#6a6af4 \
    --server.maxUploadSize=$MAX_UPLOAD_SIZE \
    $STREAMLIT_CMD_ARGS
