set -e

echo "🚀 Starting MaiChart Enhanced Medical Transcription System with MongoDB..."

# Check if required environment variables are set
if [ -z "$ASSEMBLYAI_API_KEY" ]; then
    echo "❌ ASSEMBLYAI_API_KEY is required"
    exit 1
fi

if [ -z "$REDIS_HOST" ]; then
    echo "❌ REDIS_HOST is required"
    exit 1
fi

if [ -z "$MONGODB_CONNECTION_STRING" ]; then
    echo "⚠️ MONGODB_CONNECTION_STRING not set - MongoDB features will be disabled"
    export ENABLE_MONGODB=false
else
    echo "✅ MongoDB connection configured"
    export ENABLE_MONGODB=true
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

# Check MongoDB connection if enabled
if [ "$ENABLE_MONGODB" = "true" ]; then
    echo "🗄️ Testing MongoDB connection..."
    $PYTHON_CMD -c "
from pymongo import MongoClient
import os
try:
    client = MongoClient(os.getenv('MONGODB_CONNECTION_STRING'), serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print('✅ MongoDB connection successful')
    client.close()
except Exception as e:
    print(f'❌ MongoDB connection failed: {e}')
    print('⚠️ Continuing with Redis-only mode')
    exit(0)  # Don't fail the startup
"
fi

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
echo "🔧 Starting FastAPI backend with MongoDB support..."
$PYTHON_CMD app.py &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 15

# Start transcription workers
echo "🤖 Starting direct transcription worker..."
WORKER_TYPE=direct $PYTHON_CMD workers/transcription_worker.py direct &
DIRECT_WORKER_PID=$!

echo "🤖 Starting chunk transcription worker..."
WORKER_TYPE=chunk $PYTHON_CMD workers/transcription_worker.py chunk &
CHUNK_WORKER_PID=$!

# Start enhanced medical extraction worker
if [ ! -z "$OPENAI_API_KEY" ]; then
    echo "🏥 Starting enhanced medical extraction worker with MongoDB..."
    $PYTHON_CMD workers/enhanced_medical_extraction_worker.py &
    MEDICAL_WORKER_PID=$!
else
    echo "⚠️ OPENAI_API_KEY not found. Medical extraction worker skipped."
fi

echo ""
echo "🎉 All services started successfully!"
echo "🌐 Backend API: http://localhost:5001"
echo "📚 API Docs: http://localhost:5001/docs"
echo "🗄️ MongoDB: ${ENABLE_MONGODB}"
echo "📊 Analytics: ${ENABLE_MEDICAL_ANALYTICS:-true}"
echo "✋ Press Ctrl+C to stop all services"
echo ""

# Wait for all background jobs
wait