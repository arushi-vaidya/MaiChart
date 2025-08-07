#!/bin/bash

echo "🛑 Stopping MaiChart Enhanced Medical Transcription System..."

# Function to stop a service by PID file
stop_service() {
    local name=$1
    local pid_file="${name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "🛑 Stopping $name (PID: $pid)..."
            kill "$pid"
            sleep 2
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                echo "💀 Force stopping $name..."
                kill -9 "$pid"
            fi
            
            echo "✅ $name stopped"
        else
            echo "⚠️ $name was not running"
        fi
        rm -f "$pid_file"
    else
        echo "⚠️ $name PID file not found"
    fi
}

# Stop all services
stop_service "frontend"
stop_service "medical_extraction"
stop_service "transcription_chunk"
stop_service "transcription_direct"
stop_service "backend"

# Kill any remaining processes on our ports
echo "🧹 Cleaning up any remaining processes..."

# Kill processes on port 3000 (React)
if lsof -i :3000 >/dev/null 2>&1; then
    echo "🔪 Killing processes on port 3000..."
    lsof -ti :3000 | xargs kill -9 2>/dev/null || true
fi

# Kill processes on port 5001 (FastAPI)
if lsof -i :5001 >/dev/null 2>&1; then
    echo "🔪 Killing processes on port 5001..."
    lsof -ti :5001 | xargs kill -9 2>/dev/null || true
fi

# Clean up any remaining Python processes related to our workers
pkill -f "transcription_worker.py" 2>/dev/null || true
pkill -f "medical_extraction_worker.py" 2>/dev/null || true
pkill -f "app.py" 2>/dev/null || true

echo ""
echo "✅ All MaiChart services stopped"
echo "📝 Log files are preserved in logs/ directory"
echo "🚀 To restart, run: ./startup.sh"