#!/bin/bash
set -e

# Environment variables
WORKERS=${WORKERS:-1}
WORKER_CONNECTIONS=${WORKER_CONNECTIONS:-1000}
TIMEOUT=${TIMEOUT:-30}
KEEP_ALIVE=${KEEP_ALIVE:-75}
GRACEFUL_TIMEOUT=${GRACEFUL_TIMEOUT:-75}
GUNICORN_CMD_ARGS=${GUNICORN_CMD_ARGS:-""} # ex: --log-config app/log.conf

# Set default hosts if not already defined
if [ -z "$POSTGRES_HOST" ]; then
  export POSTGRES_HOST=localhost
fi
if [ -z "$REDIS_HOST" ]; then
  export REDIS_HOST=localhost
fi
if [ -z "$QDRANT_HOST" ]; then
  export QDRANT_HOST=localhost
fi

# Run database migrations
python -m alembic -c app/alembic.ini upgrade head

# Start the application server
exec gunicorn app.main:app \
    --workers $WORKERS \
    --worker-connections $WORKER_CONNECTIONS \
    --timeout $TIMEOUT \
    --worker-class uvicorn.workers.UvicornWorker \
    --keep-alive $KEEP_ALIVE \
    --graceful-timeout $GRACEFUL_TIMEOUT \
    --bind 0.0.0.0:8000 \
    $GUNICORN_CMD_ARGS
