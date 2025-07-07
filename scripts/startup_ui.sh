#!/bin/bash
set -e

# Environment variables
MAX_UPLOAD_SIZE=${MAX_UPLOAD_SIZE:-20}
STREAMLIT_CMD_ARGS=${STREAMLIT_CMD_ARGS:-""}  # ex: --server.baseUrlPath=/playground
# Set default hosts if not already defined
if [ -z "$POSTGRES_HOST" ]; then
  export POSTGRES_HOST=localhost
fi

# Run database migrations
python -m alembic -c ui/alembic.ini upgrade head

# Start the application server
if [ -f /ui/main.py ]; then
    MAIN_PY_PATH=/ui/main.py
else
    MAIN_PY_PATH=./ui/main.py
fi
exec streamlit run "$MAIN_PY_PATH" \
    --server.port=8501 \
    --browser.gatherUsageStats false \
    --theme.base=light \
    --theme.primaryColor=#6a6af4 \
    --server.maxUploadSize=$MAX_UPLOAD_SIZE \
    $STREAMLIT_CMD_ARGS
