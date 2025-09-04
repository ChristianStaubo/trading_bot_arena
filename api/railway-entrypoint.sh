#!/bin/bash
set -e

echo "🚄 Starting Railway deployment..."

# Run database migrations
echo "Running database migrations..."
uv run alembic upgrade head

# Start the FastAPI application (Railway provides PORT env var)
echo "Starting FastAPI application on port ${PORT:-8000}..."
exec uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
