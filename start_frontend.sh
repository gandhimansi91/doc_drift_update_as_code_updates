#!/usr/bin/env bash
# Start the DocDrift frontend (Vite + React)
set -e

cd "$(dirname "$0")/frontend"

# Install node modules if needed
if [ ! -d node_modules ]; then
  echo "Installing npm dependencies..."
  npm install
fi

echo ""
echo "Starting DocDrift frontend on http://localhost:3000"
echo ""

npm run dev
