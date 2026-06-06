#!/usr/bin/env bash
# Start the DocDrift backend (FastAPI)
set -e

cd "$(dirname "$0")/backend"

# Create .env from example if not present
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

# Install dependencies (idempotent)
echo "Installing Python dependencies..."
pip install -r requirements.txt -q

echo ""
echo "Starting DocDrift backend on http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""

python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
