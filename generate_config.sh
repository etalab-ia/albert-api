#!/bin/bash

# Default output file is config.yml if no parameter is provided
OUTPUT_FILE=${1:-config.yml}

# Load .env file if it exists
if [ -f ".env" ]; then
  echo "Loading environment from .env file"
  export $(grep -v '^#' .env | xargs)
fi
# Set default hosts for local development and testing
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_DB=${POSTGRES_DB:-postgres}
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PASSWORD=${REDIS_PASSWORD:-changeme}
QDRANT_HOST=${QDRANT_HOST:-localhost}
QDRANT_API_KEY=${QDRANT_API_KEY:-changeme}

cat config.template.yml | sed \
  -e "s|\${QDRANT_API_KEY}|${QDRANT_API_KEY}|g" \
  -e "s|\${QDRANT_HOST}|${QDRANT_HOST}|g" \
  -e "s|\${REDIS_PASSWORD}|${REDIS_PASSWORD}|g" \
  -e "s|\${REDIS_HOST}|${REDIS_HOST}|g" \
  -e "s|\${GRIST_API_KEY}|${GRIST_API_KEY}|g" \
  -e "s|\${GRIST_DOC_ID}|${GRIST_DOC_ID}|g" \
  -e "s|\${POSTGRES_USER}|${POSTGRES_USER}|g" \
  -e "s|\${POSTGRES_PASSWORD}|${POSTGRES_PASSWORD}|g" \
  -e "s|\${POSTGRES_HOST}|${POSTGRES_HOST}|g" \
  -e "s|\${POSTGRES_PORT}|${POSTGRES_HOST}|g" \
  -e "s|\${ALBERT_API_KEY}|${ALBERT_API_KEY}|g" \
  > "$OUTPUT_FILE"

echo "Configuration generated at: $OUTPUT_FILE"