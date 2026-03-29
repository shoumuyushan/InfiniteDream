#!/bin/bash
# Start InfiniteDream — backend + desktop app
set -e
cd "$(dirname "$0")/.."
ROOT=$(pwd)

# =============================================================
# LLM API Keys
# =============================================================
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
export GOOGLE_API_KEY="${GOOGLE_API_KEY:-}"
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-}"
export ZHIPU_API_KEY="${ZHIPU_API_KEY:-}"
export BAIDU_API_KEY="${BAIDU_API_KEY:-}"
export BAIDU_SECRET_KEY="${BAIDU_SECRET_KEY:-}"
export QWEN_API_KEY="${QWEN_API_KEY:-}"
export MOONSHOT_API_KEY="${MOONSHOT_API_KEY:-}"
export MINIMAX_API_KEY="${MINIMAX_API_KEY:-}"
export MINIMAX_GROUP_ID="${MINIMAX_GROUP_ID:-}"

# =============================================================
# Video AI API Keys
# =============================================================
export RUNWAY_API_KEY="${RUNWAY_API_KEY:-}"
export KLING_API_KEY="${KLING_API_KEY:-}"
export PIKA_API_KEY="${PIKA_API_KEY:-}"
export LUMA_API_KEY="${LUMA_API_KEY:-}"

# =============================================================
# Music / Audio AI API Keys
# =============================================================
export SUNO_API_KEY="${SUNO_API_KEY:-}"
export UDIO_API_KEY="${UDIO_API_KEY:-}"

# =============================================================
# API Gateway / Proxy Configuration
# =============================================================
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.openai.com/v1}"
export ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL:-https://api.anthropic.com}"
export GOOGLE_BASE_URL="${GOOGLE_BASE_URL:-https://generativelanguage.googleapis.com}"
export DEEPSEEK_BASE_URL="${DEEPSEEK_BASE_URL:-https://api.deepseek.com/v1}"
export ZHIPU_BASE_URL="${ZHIPU_BASE_URL:-https://open.bigmodel.cn/api/paas/v4}"
export QWEN_BASE_URL="${QWEN_BASE_URL:-https://dashscope.aliyuncs.com/api/v1}"
export MOONSHOT_BASE_URL="${MOONSHOT_BASE_URL:-https://api.moonshot.cn/v1}"
export MINIMAX_BASE_URL="${MINIMAX_BASE_URL:-https://api.minimax.chat/v1}"
export RUNWAY_BASE_URL="${RUNWAY_BASE_URL:-https://api.runwayml.com}"
export KLING_BASE_URL="${KLING_BASE_URL:-https://api.klingai.com}"

# HTTP proxy (for all outbound API requests)
export HTTP_PROXY="${HTTP_PROXY:-}"
export HTTPS_PROXY="${HTTPS_PROXY:-}"
export NO_PROXY="${NO_PROXY:-localhost,127.0.0.1}"

# =============================================================
# Default Provider Selection
# =============================================================
export DEFAULT_LLM_PROVIDER="${DEFAULT_LLM_PROVIDER:-openai}"
export DEFAULT_VIDEO_PROVIDER="${DEFAULT_VIDEO_PROVIDER:-kling}"
export DEFAULT_MUSIC_PROVIDER="${DEFAULT_MUSIC_PROVIDER:-suno}"

# =============================================================
export LOG_LEVEL="${LOG_LEVEL:-info}"

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
