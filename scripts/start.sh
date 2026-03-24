#!/bin/bash
# Start the Python backend, then launch the Tauri app
cd "$(dirname "$0")/.."
echo "Starting InfiniteDream backend..."
uv run uvicorn infinite_dream.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
sleep 2
echo "Backend started (PID: $BACKEND_PID)"
echo "Open http://localhost:8000 in your browser, or build the desktop app with:"
echo "  cd desktop && cargo tauri build"
wait $BACKEND_PID
