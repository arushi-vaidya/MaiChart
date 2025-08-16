#!/bin/bash

# MaiChart Enhanced Medical Transcription System Startup Script
# FIXED: Includes Redis cleanup and better error handling

echo "🚀 Starting MaiChart Enhanced Medical Transcription System..."
echo "🏥 With OpenAI GPT-4 Medical Information Extraction (BioBERT removed)"
echo "=================================================="

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

# Function to start a service in background
start_service() {
    local name=$1
    local command=$2
    local log_file=$3
    
    echo "🔄 Starting $name..."
    nohup $command > "$log_file" 2>&1 &
    local pid=$!
    echo "✅ $name started (PID: $pid)"
    echo $pid > "${name}.pid"
}

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check Python
if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check Node.js
if ! command_exists node; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

# Check if ports are available
if port_in_use 5001; then
    echo "⚠️ Port 5001 is already in use. Stopping existing backend..."
    lsof -ti :5001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

if port_in_use 3000; then
    echo "⚠️ Port 3000 is already in use. Stopping existing frontend..."
    lsof -ti :3000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Check environment file
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it with your API keys."
    echo "Required variables:"
    echo "- ASSEMBLYAI_API_KEY"
    echo "- OPENAI_API_KEY"
    echo "- REDIS_HOST, REDIS_PORT, REDIS_PASSWORD"
    exit 1
fi

# Source environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check required API keys
if [ -z "$ASSEMBLYAI_API_KEY" ]; then
    echo "❌ ASSEMBLYAI_API_KEY is required in .env file"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️ OPENAI_API_KEY not found. Medical extraction will be limited."
fi

if [ -z "$REDIS_HOST" ]; then
    echo "❌ REDIS_HOST is required in .env file"
    exit 1
fi

echo "✅ Prerequisites check passed"
echo ""

# Setup backend
echo "🐍 Setting up Python backend..."
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "📋 Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p uploads transcripts chunks logs

# FIXED: Clean up Redis queues before starting
echo "🧹 Cleaning up Redis queues..."
python redis_cleanup.py --action cleanup

echo "✅ Backend setup complete"
echo ""

# Setup frontend
echo "⚛️ Setting up React frontend..."
cd ../frontend

# Install npm dependencies
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

echo "✅ Frontend setup complete"
echo ""

# Start services
echo "🚀 Starting all services..."
cd ..

# Create logs directory
mkdir -p logs

# Function to cleanup on exit
cleanup() {
    echo "🛑 Stopping all services..."
    jobs -p | xargs -r kill 2>/dev/null || true
    
    # Kill by PID files
    for pidfile in *.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            if kill -0 "$pid" 2>/dev/null; then
                echo "🛑 Stopping service with PID $pid"
                kill "$pid" 2>/dev/null || true
            fi
            rm -f "$pidfile"
        fi
    done
    
    # Kill processes on specific ports
    lsof -ti :5001 | xargs kill -9 2>/dev/null || true
    lsof -ti :3000 | xargs kill -9 2>/dev/null || true
    
    exit
}

# Setup cleanup on script exit
trap cleanup EXIT INT TERM

# Start FastAPI backend
echo "🔧 Starting FastAPI backend..."
cd backend
source venv/bin/activate
start_service "backend" "python app.py" "../logs/backend.log"
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 15

# Test backend health
echo "🔍 Testing backend health..."
if curl -f http://localhost:5001/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend health check failed"
    echo "📋 Backend logs:"
    tail -20 logs/backend.log
    exit 1
fi

# Start transcription workers
echo "🤖 Starting transcription workers..."
cd backend
source venv/bin/activate

# Direct transcription worker
start_service "transcription_direct" "python workers/transcription_worker.py direct" "../logs/transcription_direct.log"

# Chunk transcription worker  
start_service "transcription_chunk" "python workers/transcription_worker.py chunk" "../logs/transcription_chunk.log"

# Medical extraction worker
start_service "medical_extraction" "python workers/medical_extraction_worker.py" "../logs/medical_extraction.log"

cd ..

# Wait for workers to start
echo "⏳ Waiting for workers to initialize..."
sleep 10

# Start React frontend
echo "⚛️ Starting React frontend..."
cd frontend
start_service "frontend" "npm start" "../logs/frontend.log"
cd ..

# Wait for frontend to start
echo "⏳ Waiting for frontend to start..."
sleep 15

# Test frontend
echo "🔍 Testing frontend..."
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is accessible"
else
    echo "⚠️ Frontend may still be starting..."
fi

echo ""
echo "🎉 MaiChart Enhanced Medical Transcription System Started!"
echo "=================================================="
echo "🌐 Frontend: http://localhost:3000"
echo "📡 Backend API: http://localhost:5001"
echo "📚 API Docs: http://localhost:5001/docs"
echo "🏥 Medical Features: Enabled (OpenAI GPT-4 only)"
echo ""
echo "📊 Service Status:"
echo "• FastAPI Backend: http://localhost:5001/health"
echo "• Transcription Workers: Processing audio files"
echo "• Medical Extraction Worker: Processing completed transcripts"
echo "• Redis Queues: Cleaned and ready"
echo ""
echo "📋 Available Features:"
echo "• 🎤 Audio recording and file upload"
echo "• 🤖 AI transcription with AssemblyAI"
echo "• 🏥 Medical information extraction with OpenAI GPT-4"
echo "• 📊 Structured medical data output"
echo "• 🚨 Medical alerts and critical information detection"
echo "• 🔄 Fixed Redis queue handling (no more stuck uploads)"
echo ""
echo "📝 Log files are in the logs/ directory"
echo "🛑 To stop all services, run: ./stop.sh"
echo "🧹 To clean Redis queues manually, run: cd backend && python redis_cleanup.py"
echo ""
echo "⚡ System ready for medical voice note processing!"

# Monitor services
echo "🔍 Monitoring services (Ctrl+C to stop)..."
while true; do
    sleep 30
    
    # Check if all services are still running
    services_running=0
    
    for pidfile in *.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            if kill -0 "$pid" 2>/dev/null; then
                services_running=$((services_running + 1))
            else
                echo "⚠️ Service with PID $pid has stopped"
            fi
        fi
    done
    
    echo "📊 Services running: $services_running"
    
    # If no services are running, exit
    if [ $services_running -eq 0 ]; then
        echo "❌ All services have stopped"
        break
    fi
done