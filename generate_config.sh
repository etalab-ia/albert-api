#!/bin/bash

# Default output file is config.yml if no parameter is provided
OUTPUT_FILE=${1:-config.yml}

cat config.template.yml | sed \
  -e "s|\${QDRANT_API_KEY}|${QDRANT_API_KEY}|g" \
  -e "s|\${REDIS_PASSWORD}|${REDIS_PASSWORD}|g" \
  -e "s|\${GRIST_API_KEY}|${GRIST_API_KEY}|g" \
  -e "s|\${POSTGRES_PASSWORD}|${POSTGRES_PASSWORD}|g" \
  -e "s|\${ALBERT_API_KEY}|${ALBERT_API_KEY}|g" \
  > "$OUTPUT_FILE"

echo "Configuration generated at: $OUTPUT_FILE"