#!/bin/bash

# MaiChart Enhanced Medical Transcription System Startup Script
# This script helps you run the complete system with medical extraction

echo "🚀 Starting MaiChart Enhanced Medical Transcription System..."
echo "🏥 With OpenAI GPT-4 + BioBERT Medical Information Extraction"
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
    echo "⚠️ Port 5001 is already in use. Backend may already be running."
fi

if port_in_use 3000; then
    echo "⚠️ Port 3000 is already in use. Frontend may already be running."
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

# Start FastAPI backend
echo "🔧 Starting FastAPI backend server..."
cd backend
source venv/bin/activate
start_service "backend" "python app.py" "../logs/backend.log"
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 10

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
sleep 5

# Start React frontend
echo "⚛️ Starting React frontend..."
cd frontend
start_service "frontend" "npm start" "../logs/frontend.log"
cd ..

echo ""
echo "🎉 MaiChart Enhanced Medical Transcription System Started!"
echo "=================================================="
echo "🌐 Frontend: http://localhost:3000"
echo "📡 Backend API: http://localhost:5001"
echo "📚 API Docs: http://localhost:5001/docs"
echo "🏥 Medical Features: Enabled"
echo ""
echo "📊 Service Status:"
echo "• FastAPI Backend: http://localhost:5001/health"
echo "• Transcription Workers: Processing audio files"
echo "• Medical Extraction Worker: Processing completed transcripts"
echo ""
echo "📋 Available Features:"
echo "• 🎤 Audio recording and file upload"
echo "• 🤖 AI transcription with AssemblyAI"
echo "• 🏥 Medical information extraction with OpenAI GPT-4"
echo "• 🧬 Named entity recognition with BioBERT"
echo "• 📊 Structured medical data output"
echo "• 🚨 Medical alerts and critical information detection"
echo ""
echo "📝 Log files are in the logs/ directory"
echo "🛑 To stop all services, run: ./stop.sh"
echo ""
echo "⚡ System ready for medical voice note processing!"