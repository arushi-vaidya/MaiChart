#!/bin/bash

# MaiChart - Start All Services Script
# Runs FastAPI app and all workers

set -e

echo "🚀 Starting MaiChart Enhanced Medical Transcription System..."

# Check if required environment variables are set
if [ -z "$ASSEMBLYAI_API_KEY" ]; then
    echo "❌ ASSEMBLYAI_API_KEY is required"
    exit 1
fi

if [ -z "$REDIS_HOST" ]; then
    echo "❌ REDIS_HOST is required"
    exit 1
fi

# Determine Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python not found. Please install Python 3"
    exit 1
fi

echo "🐍 Using Python command: $PYTHON_CMD"

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Verify Python and required packages
echo "🔍 Checking Python installation..."
$PYTHON_CMD --version

# Create necessary directories
mkdir -p uploads transcripts chunks logs

# Function to cleanup on exit
cleanup() {
    echo "🛑 Stopping all services..."
    jobs -p | xargs -r kill 2>/dev/null || true
    exit
}

# Setup cleanup on script exit
trap cleanup EXIT INT TERM

# Start FastAPI backend in background
echo "🔧 Starting FastAPI backend..."
$PYTHON_CMD app.py &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 10

# Start transcription workers
echo "🤖 Starting direct transcription worker..."
WORKER_TYPE=direct $PYTHON_CMD workers/transcription_worker.py direct &
DIRECT_WORKER_PID=$!

echo "🤖 Starting chunk transcription worker..."
WORKER_TYPE=chunk $PYTHON_CMD workers/transcription_worker.py chunk &
CHUNK_WORKER_PID=$!

# Start medical extraction worker if OpenAI key is available
if [ ! -z "$OPENAI_API_KEY" ]; then
    echo "🏥 Starting medical extraction worker..."
    $PYTHON_CMD workers/medical_extraction_worker.py &
    MEDICAL_WORKER_PID=$!
else
    echo "⚠️ OPENAI_API_KEY not found. Medical extraction worker skipped."
fi

echo ""
echo "🎉 All services started!"
echo "🌐 Backend API: http://localhost:5001"
echo "📚 API Docs: http://localhost:5001/docs"
echo "✋ Press Ctrl+C to stop all services"
echo ""

# Wait for all background jobs
wait