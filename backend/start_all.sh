#!/bin/bash

# =============================================================================
# FIXED: MaiChart Worker Startup Script - Ensures All Workers Are Running
# =============================================================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Print functions
print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
PID_DIR="$SCRIPT_DIR/pids"

# Load environment variables from .env file
# Check both backend directory and parent directory
ENV_FILE=""
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    ENV_FILE="$SCRIPT_DIR/.env"
elif [[ -f "$SCRIPT_DIR/../.env" ]]; then
    ENV_FILE="$SCRIPT_DIR/../.env"
fi

if [[ -n "$ENV_FILE" ]]; then
    print_info "Loading environment variables from $ENV_FILE..."
    set -a  # automatically export all variables
    source "$ENV_FILE"
    set +a  # stop automatically exporting
    print_status "Environment variables loaded"
else
    print_warning "No .env file found in backend directory or parent directory"
fi

# Ensure directories exist
mkdir -p "$LOG_DIR" "$PID_DIR"

# Check if service is running
is_service_running() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# Start a worker service
start_worker_service() {
    local service_name=$1
    local command=$2
    local description=$3
    local log_file="$LOG_DIR/${service_name}.log"
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if is_service_running "$service_name"; then
        print_warning "$service_name is already running"
        return 0
    fi
    
    print_info "Starting $service_name..."
    print_info "Description: $description"
    print_info "Command: $command"
    print_info "Log file: $log_file"
    
    # Check dependencies
    check_dependencies
    
    # Start service in background with proper environment
    export PYTHONPATH="$SCRIPT_DIR"
    export PYTHONUNBUFFERED=1
    
    # Activate virtual environment if it exists
    if [[ -f "$SCRIPT_DIR/venv/bin/activate" ]]; then
        source "$SCRIPT_DIR/venv/bin/activate"
        print_info "Virtual environment activated"
    fi
    
    # Start the service
    nohup $command >> "$log_file" 2>&1 &
    local pid=$!
    
    # Save PID
    echo $pid > "$pid_file"
    
    # Wait and verify
    sleep 5
    
    if kill -0 "$pid" 2>/dev/null; then
        print_status "$service_name started successfully (PID: $pid)"
        return 0
    else
        print_error "$service_name failed to start"
        rm -f "$pid_file"
        echo "Last 10 lines of log:"
        tail -n 10 "$log_file" 2>/dev/null || echo "No log data available"
        return 1
    fi
}

# Stop a service
stop_service() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            print_info "Stopping $service_name (PID: $pid)..."
            
            # Graceful shutdown
            kill -TERM "$pid" 2>/dev/null || true
            
            # Wait for graceful shutdown
            local count=0
            while kill -0 "$pid" 2>/dev/null && [[ $count -lt 10 ]]; do
                sleep 1
                ((count++))
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                print_warning "Force killing $service_name..."
                kill -KILL "$pid" 2>/dev/null || true
            fi
        fi
        rm -f "$pid_file"
        print_status "$service_name stopped"
    else
        print_info "$service_name was not running"
    fi
}

# Check dependencies
check_dependencies() {
    # Check environment variables
    local missing_vars=()
    
    if [[ -z "$ASSEMBLYAI_API_KEY" ]]; then
        missing_vars+=("ASSEMBLYAI_API_KEY")
    fi
    
    if [[ -z "$REDIS_HOST" ]]; then
        missing_vars+=("REDIS_HOST")
    fi
    
    if [[ -z "$OPENAI_API_KEY" ]]; then
        print_warning "OPENAI_API_KEY not found. Medical extraction will be limited."
    fi
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        print_error "Missing required environment variables: ${missing_vars[*]}"
        print_info "Please set these variables in your environment or .env file"
        return 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        print_error "Python not found. Please install Python 3"
        return 1
    fi
    
    return 0
}

# Show service status
show_worker_status() {
    local services=("fastapi" "transcription_direct" "transcription_chunk" "medical_extraction")
    local total_services=0
    local running_services=0
    
    printf "%-25s %-10s %-8s %-15s\n" "SERVICE" "STATUS" "PID" "UPTIME"
    echo "-------------------------------------------------------------"
    
    for service in "${services[@]}"; do
        ((total_services++))
        if is_service_running "$service"; then
            ((running_services++))
            local pid_file="$PID_DIR/${service}.pid"
            local pid=$(cat "$pid_file")
            local uptime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ' || echo "N/A")
            printf "%-25s ${GREEN}%-10s${NC} %-8s %-15s\n" "$service" "RUNNING" "$pid" "$uptime"
        else
            printf "%-25s ${RED}%-10s${NC} %-8s %-15s\n" "$service" "STOPPED" "-" "-"
        fi
    done
    
    echo ""
    if [[ $running_services -eq $total_services ]]; then
        print_status "All services are running ($running_services/$total_services)"
        print_info "Backend API available at: http://localhost:5001"
        print_info "API documentation at: http://localhost:5001/docs"
    elif [[ $running_services -gt 0 ]]; then
        print_warning "Some services are running ($running_services/$total_services)"
    else
        print_error "No services are running (0/$total_services)"
    fi
}

# Start FastAPI backend server
start_fastapi_server() {
    local pid_file="$PID_DIR/fastapi.pid"
    local log_file="$LOG_DIR/fastapi.log"
    
    if is_service_running "fastapi"; then
        print_warning "FastAPI server is already running"
        return 0
    fi
    
    print_info "Starting FastAPI backend server..."
    
    # Activate virtual environment
    if [[ -f "$SCRIPT_DIR/venv/bin/activate" ]]; then
        source "$SCRIPT_DIR/venv/bin/activate"
        print_info "Virtual environment activated"
    fi
    
    # Set environment variables
    export PYTHONPATH="$SCRIPT_DIR"
    export PYTHONUNBUFFERED=1
    
    # Start FastAPI server as daemon
    nohup uvicorn app:app --host 0.0.0.0 --port 5001 --workers 1 >> "$log_file" 2>&1 &
    local pid=$!
    
    # Save PID
    echo $pid > "$pid_file"
    
    # Wait and verify
    sleep 5
    
    if kill -0 "$pid" 2>/dev/null; then
        print_status "FastAPI server started successfully (PID: $pid)"
        print_info "Backend API available at: http://localhost:5001"
        print_info "API documentation at: http://localhost:5001/docs"
        return 0
    else
        print_error "FastAPI server failed to start"
        rm -f "$pid_file"
        echo "Last 10 lines of log:"
        tail -n 10 "$log_file" 2>/dev/null || echo "No log data available"
        return 1
    fi
}

# Start all workers
start_all_workers() {
    print_info "Starting all MaiChart workers..."
    
    # Start transcription workers
    start_worker_service "transcription_direct" \
        "python3 workers/transcription_worker.py direct" \
        "Direct audio transcription worker"
    
    sleep 2  # Small delay between workers
    
    start_worker_service "transcription_chunk" \
        "python3 workers/transcription_worker.py chunk" \
        "Chunked audio transcription worker"
    
    sleep 2
    
    # Start medical extraction worker if OpenAI API key is available
    if [[ -n "$OPENAI_API_KEY" ]]; then
        start_worker_service "medical_extraction" \
            "python3 workers/enhanced_medical_extraction_worker.py" \
            "Enhanced medical information extraction worker"
    else
        print_warning "Skipping medical extraction worker (no OPENAI_API_KEY)"
    fi
    
    sleep 3
    print_status "All workers startup completed!"
}

# Start complete backend (FastAPI + Workers)
start_complete_backend() {
    print_info "Starting complete MaiChart backend..."
    
    # Check dependencies first
    if ! check_dependencies; then
        print_error "Dependency check failed"
        exit 1
    fi
    
    # Start FastAPI server first
    if ! start_fastapi_server; then
        print_error "Failed to start FastAPI server"
        exit 1
    fi
    
    # Start all workers
    start_all_workers
    
    print_status "Complete backend startup completed!"
    show_worker_status
}

# Stop all workers
stop_all_workers() {
    print_info "Stopping all MaiChart workers..."
    
    local services=("medical_extraction" "transcription_chunk" "transcription_direct")
    
    for service in "${services[@]}"; do
        stop_service "$service"
    done
    
    print_status "All workers stopped"
}

# Stop complete backend (FastAPI + Workers)
stop_complete_backend() {
    print_info "Stopping complete MaiChart backend..."
    
    # Stop workers first
    stop_all_workers
    
    # Stop FastAPI server
    stop_service "fastapi"
    
    print_status "Complete backend stopped"
}

# Restart all workers
restart_all_workers() {
    print_info "Restarting all MaiChart workers..."
    stop_all_workers
    sleep 3
    start_all_workers
}

# Restart complete backend
restart_complete_backend() {
    print_info "Restarting complete MaiChart backend..."
    stop_complete_backend
    sleep 3
    start_complete_backend
}

# View logs
view_worker_logs() {
    local service=${1:-"all"}
    
    if [[ "$service" == "all" ]]; then
        print_info "Showing logs for all workers (Ctrl+C to exit)..."
        if ls "$LOG_DIR"/*.log 1> /dev/null 2>&1; then
            tail -f "$LOG_DIR"/*.log
        else
            print_warning "No log files found"
        fi
    else
        local log_file="$LOG_DIR/${service}.log"
        if [[ -f "$log_file" ]]; then
            print_info "Showing logs for $service (Ctrl+C to exit)..."
            tail -f "$log_file"
        else
            print_error "Log file not found for service: $service"
            print_info "Available services: transcription_direct, transcription_chunk, medical_extraction"
        fi
    fi
}

# Test worker connections
test_workers() {
    print_info "Testing worker dependencies..."
    
    # Test Redis connection
    print_info "Testing Redis connection..."
    if python3 -c "
import redis
import os
import sys

try:
    # Get Redis configuration
    host = os.getenv('REDIS_HOST', 'localhost')
    port = int(os.getenv('REDIS_PORT', 6379))
    password = os.getenv('REDIS_PASSWORD')
    db = int(os.getenv('REDIS_DB', 0))
    
    print(f'Connecting to Redis Cloud: {host}:{port} (DB: {db})')
    
    # Try connection without SSL first
    try:
        r = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=10
        )
        r.ping()
        print('✅ Redis Cloud connection successful (no SSL)')
    except redis.ConnectionError:
        # Try with SSL
        print('Trying with SSL...')
        r = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=10,
            ssl=True,
            ssl_cert_reqs=None
        )
        r.ping()
        print('✅ Redis Cloud connection successful (with SSL)')
    
    # Test basic operations
    r.set('test_key', 'test_value', ex=60)
    value = r.get('test_key')
    if value == 'test_value':
        print('✅ Redis Cloud read/write test successful')
        r.delete('test_key')
    else:
        print('❌ Redis Cloud read/write test failed')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ Redis Cloud connection failed: {e}')
    sys.exit(1)
"; then
        print_status "Redis Cloud connection test passed"
    else
        print_error "Redis Cloud connection test failed"
        return 1
    fi
    
    # Test AssemblyAI API key
    if [[ -n "$ASSEMBLYAI_API_KEY" ]]; then
        print_status "AssemblyAI API key is set"
    else
        print_error "AssemblyAI API key is missing"
        return 1
    fi
    
    # Test OpenAI API key (optional)
    if [[ -n "$OPENAI_API_KEY" ]]; then
        print_status "OpenAI API key is set (medical extraction enabled)"
    else
        print_warning "OpenAI API key not set (medical extraction will be limited)"
    fi
    
    print_status "Worker dependency tests completed"
}

# Main command handling
case "${1:-backend}" in
    "start"|"workers")
        start_all_workers
        ;;
    "backend"|"full")
        start_complete_backend
        ;;
    "stop")
        stop_complete_backend
        ;;
    "stop-workers")
        stop_all_workers
        ;;
    "restart")
        restart_complete_backend
        ;;
    "restart-workers")
        restart_all_workers
        ;;
    "status")
        show_worker_status
        ;;
    "logs")
        view_worker_logs "${2:-all}"
        ;;
    "test")
        test_workers
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [backend|workers|stop|restart|status|logs [service]|test|help]"
        echo ""
        echo "Commands:"
        echo "  backend        Start complete backend (FastAPI + Workers) - DEFAULT"
        echo "  workers        Start only worker processes"
        echo "  stop           Stop complete backend (FastAPI + Workers)"
        echo "  stop-workers   Stop only worker processes"
        echo "  restart        Restart complete backend"
        echo "  restart-workers Restart only worker processes"
        echo "  status         Show service status"
        echo "  logs           View logs (optionally for specific service)"
        echo "  test           Test worker dependencies"
        echo "  help           Show this help message"
        echo ""
        echo "Services: fastapi, transcription_direct, transcription_chunk, medical_extraction"
        echo ""
        echo "Examples:"
        echo "  $0                    # Start complete backend (default)"
        echo "  $0 backend           # Start complete backend"
        echo "  $0 workers           # Start only workers"
        echo "  $0 stop              # Stop everything"
        echo "  $0 status            # Check status"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac