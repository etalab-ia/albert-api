#!/bin/bash
set -e

# Run database migrations
python -m alembic -c app/alembic.ini upgrade head

# Start the application server
exec gunicorn app.main:app \
    --workers 1 \
    --worker-connections 1000 \
    --timeout 30 \
    --worker-class uvicorn.workers.UvicornWorker