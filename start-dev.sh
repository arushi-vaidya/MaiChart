#!/bin/bash
# start-dev.sh - Start both frontend and backend for development

echo "🚀 Starting MaiChart Development Environment..."

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Please run this script from the project root directory"
    echo "📁 Expected structure:"
    echo "   project-root/"
    echo "   ├── backend/"
    echo "   └── frontend/"
    exit 1
fi

# Detect OS for virtual environment activation
detect_os() {
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unix"
    fi
}

OS_TYPE=$(detect_os)

# Function to start backend
start_backend() {
    echo "🔧 Starting Backend Server..."
    cd backend
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "📦 Creating Python virtual environment..."
        python3 -m venv venv || python -m venv venv
    fi
    
    # Activate virtual environment based on OS
    if [ "$OS_TYPE" == "windows" ]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    
    # Install requirements if needed
    if [ ! -f ".deps_installed" ]; then
        echo "📚 Installing Python dependencies..."
        pip install -r requirements.txt
        if [ $? -eq 0 ]; then
            touch .deps_installed
        else
            echo "❌ Failed to install dependencies"
            exit 1
        fi
    fi
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
        echo "⚠️  .env file not found! Please create it with your ASSEMBLYAI_API_KEY"
        echo "📄 Copy .env.template to .env and add your API key"
        echo "💡 You can create it now:"
        echo "   cp .env.template .env"
        echo "   # Then edit .env and add your ASSEMBLYAI_API_KEY"
        exit 1
    fi
    
    # Check if ASSEMBLYAI_API_KEY is set
    if grep -q "your_assemblyai_api_key_here" .env; then
        echo "⚠️  Please update ASSEMBLYAI_API_KEY in .env file"
        echo "💡 Get your key from: https://app.assemblyai.com/"
        exit 1
    fi
    
    # Start Flask server
    echo "🌐 Backend server starting on http://localhost:5001"
    python app.py &
    BACKEND_PID=$!
    echo "📋 Backend PID: $BACKEND_PID"
    cd ..
}

# Function to start frontend
start_frontend() {
    echo "⚛️  Starting React Frontend..."
    cd frontend
    
    # Install npm dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "📦 Installing Node.js dependencies..."
        npm install
        if [ $? -ne 0 ]; then
            echo "❌ Failed to install npm dependencies"
            exit 1
        fi
    fi
    
    # Start React development server
    echo "🌐 Frontend server starting on http://localhost:3000"
    npm start &
    FRONTEND_PID=$!
    echo "📋 Frontend PID: $FRONTEND_PID"
    cd ..
}

# Function to start transcription worker
start_worker() {
    echo "🤖 Starting Transcription Worker..."
    cd backend
    
    # Activate virtual environment
    if [ "$OS_TYPE" == "windows" ]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    
    python workers/transcription_worker.py &
    WORKER_PID=$!
    echo "📋 Worker PID: $WORKER_PID"
    cd ..
}

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    
    if [ ! -z "$BACKEND_PID" ]; then
        echo "Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null
    fi
    
    if [ ! -z "$WORKER_PID" ]; then
        echo "Stopping worker (PID: $WORKER_PID)..."
        kill $WORKER_PID 2>/dev/null
    fi
    
    # Give processes time to shut down
    sleep 2
    
    # Force kill if still running
    pkill -f "python app.py" 2>/dev/null
    pkill -f "npm start" 2>/dev/null
    pkill -f "transcription_worker.py" 2>/dev/null
    
    echo "✅ All servers stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check if ports are already in use
check_ports() {
    if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port 5001 is already in use. Please stop the existing service."
        exit 1
    fi
    
    if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port 3000 is already in use. Please stop the existing service."
        exit 1
    fi
}

# Main execution
echo "🔍 Checking ports..."
check_ports

echo "🚀 Starting all services..."

# Start all services
start_backend
sleep 3  # Give backend time to start

start_frontend
sleep 3  # Give frontend time to start

start_worker

echo ""
echo "🎉 MaiChart Development Environment is running!"
echo ""
echo "📡 Backend API: http://localhost:5001"
echo "🌐 Frontend App: http://localhost:3000"
echo "📊 Health Check: http://localhost:5001/api/health"
echo ""
echo "💡 Quick Commands:"
echo "   - Open frontend: open http://localhost:3000 (Mac) | start http://localhost:3000 (Windows)"
echo "   - View logs: tail -f backend/logs/app.log"
echo "   - Test API: curl http://localhost:5001/api/health"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Wait for user to stop
wait