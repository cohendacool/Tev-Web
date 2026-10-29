#!/bin/sh
set -eu

echo "Starting Ollama..."
ollama serve &
OLLAMA_PID=$!

echo "Waiting for Ollama..."
READY=0

for i in $(seq 1 90); do
    if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null; then
        READY=1
        break
    fi

    sleep 2
done

if [ "$READY" -ne 1 ]; then
    echo "Ollama failed to start."
    kill "$OLLAMA_PID" 2>/dev/null || true
    exit 1
fi

echo "Downloading model if needed..."
ollama pull qwen2.5:0.5b

echo "Warming up model..."
curl -fsS http://127.0.0.1:11434/api/generate -d '{"model": "qwen2.5:0.5b", "prompt": "hi", "stream": false}' >/dev/null || true

echo "Starting Tev API..."
gunicorn --bind "0.0.0.0:${PORT:-10000}" \
    --workers 1 \
    --timeout 300 \
    server:app
