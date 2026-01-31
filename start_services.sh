#!/bin/bash
# Start both FastAPI and Dash services

echo "Starting UMAP Explorer Services..."
echo "=================================="

# Start FastAPI service in background
echo "Starting FastAPI WebSocket service on port 8058..."
uv run python -m fastapi_service.main &
FASTAPI_PID=$!

# Wait a moment for FastAPI to start
sleep 2

# Start Dash app
echo "Starting Dash UI on port 8050..."
uv run python app.py &
DASH_PID=$!

echo ""
echo "Services started:"
echo "  FastAPI WebSocket: http://127.0.0.1:8058"
echo "  Dash UI:           http://127.0.0.1:8050"
echo ""
echo "Press Ctrl+C to stop both services"

# Trap Ctrl+C and kill both processes
trap "echo 'Stopping services...'; kill $FASTAPI_PID $DASH_PID 2>/dev/null; exit" INT

# Wait for both processes
wait
