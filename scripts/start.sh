#!/bin/bash
# Start InfiniteDream — backend + desktop app
set -e
cd "$(dirname "$0")/.."
ROOT=$(pwd)

cleanup() {
    echo ""
    echo "Shutting down..."
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
    exit 0
}
trap cleanup INT TERM

# 1. Start Python backend
echo "🚀 Starting backend..."
uv run uvicorn infinite_dream.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Wait for backend ready
for i in $(seq 1 10); do
    if curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "✅ Backend ready (PID: $BACKEND_PID)"
        break
    fi
    [ "$i" -eq 10 ] && { echo "❌ Backend failed to start"; kill "$BACKEND_PID" 2>/dev/null; exit 1; }
    sleep 1
done

# 2. Launch desktop app
APP_BUNDLE="$ROOT/desktop/target/release/bundle/macos/InfiniteDream.app"
APP_DEBUG="$ROOT/desktop/target/debug/infinite-dream-desktop"

if [ -d "$APP_BUNDLE" ]; then
    echo "🎬 Launching InfiniteDream.app..."
    open "$APP_BUNDLE"
elif [ -f "$APP_DEBUG" ]; then
    echo "🎬 Launching desktop (debug)..."
    "$APP_DEBUG" &
else
    echo "⚠️  Desktop app not built yet. Building..."
    if command -v cargo &>/dev/null && [ -f "$ROOT/desktop/Cargo.toml" ]; then
        cd "$ROOT/desktop"
        cargo tauri dev &
    else
        echo "ℹ️  Tauri CLI not found. Opening in browser instead."
        open "http://localhost:8000"
    fi
fi

# Keep alive until Ctrl+C
wait $BACKEND_PID
