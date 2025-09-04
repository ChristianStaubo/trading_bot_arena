#!/bin/bash
set -e

# Check if running on Railway (skip health check for Railway)
if [ -n "$RAILWAY_ENVIRONMENT" ] || [ -n "$PORT" ]; then
  echo "Detected Railway environment - skipping PostgreSQL health check"
  echo "Railway manages service dependencies automatically"
else
  # Extract host and port from DATABASE_URL for health check (local development)
  if [ -n "$DATABASE_URL" ]; then
    # Parse DATABASE_URL (format: postgresql://user:pass@host:port/db)
    DB_HOST=$(echo $DATABASE_URL | sed -n 's|.*@\([^:]*\):.*|\1|p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
    
    if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
      echo "Waiting for PostgreSQL to be ready at $DB_HOST:$DB_PORT..."
      while ! nc -z $DB_HOST $DB_PORT; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 1
      done
      echo "PostgreSQL is up - continuing"
    else
      echo "Could not parse DATABASE_URL, skipping health check"
    fi
  else
    echo "DATABASE_URL not set, skipping PostgreSQL health check"
  fi
fi

# Run database migrations (with debugging and flexible paths)
echo "Running database migrations..."
echo "Current directory: $(pwd)"
echo "Full directory listing:"
find . -name "alembic.ini" -o -name "alembic" -type d 2>/dev/null

# Try to find and run alembic from the correct location
ALEMBIC_DIR=""
if [ -f "alembic.ini" ] && [ -d "alembic" ]; then
    echo "✅ Found alembic files in current directory"
    ALEMBIC_DIR="."
elif [ -f "api/alembic.ini" ] && [ -d "api/alembic" ]; then
    echo "✅ Found alembic files in api/ subdirectory"
    ALEMBIC_DIR="api"
else
    echo "❌ Searching for alembic files..."
    echo "Directory structure:"
    ls -la
    if [ -d "api" ]; then
        echo "Contents of api/ directory:"
        ls -la api/
    fi
fi

if [ -n "$ALEMBIC_DIR" ]; then
    echo "Running migrations from: $ALEMBIC_DIR"
    cd "$ALEMBIC_DIR"
    uv run alembic upgrade head
    cd - > /dev/null
else
    echo "⚠️  Could not find alembic.ini and alembic/ folder - skipping migrations"
    echo "This might be okay if database is already migrated"
fi

# Start the FastAPI application (find main.py location)
echo "Starting FastAPI application..."
echo "Looking for main.py..."

if [ -f "main.py" ]; then
    echo "✅ Found main.py in current directory"
    exec uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
elif [ -f "api/main.py" ]; then
    echo "✅ Found main.py in api/ subdirectory"
    cd api
    exec uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
else
    echo "❌ Could not find main.py"
    echo "Directory contents:"
    ls -la
    if [ -d "api" ]; then
        echo "Contents of api/ directory:"
        ls -la api/
    fi
    echo "⚠️  Starting with fallback assumption (main.py in current dir)"
    exec uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
fi
