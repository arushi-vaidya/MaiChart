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

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
PID_DIR="$SCRIPT_DIR/pids"

# Ensure directories exist
mkdir -p "$LOG_DIR" "$PID_DIR"

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }

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
    local services=("transcription_direct" "transcription_chunk" "medical_extraction")
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
        print_status "All workers are running ($running_services/$total_services)"
    elif [[ $running_services -gt 0 ]]; then
        print_warning "Some workers are running ($running_services/$total_services)"
    else
        print_error "No workers are running (0/$total_services)"
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

# Restart all workers
restart_all_workers() {
    print_info "Restarting all MaiChart workers..."
    stop_all_workers
    sleep 3
    start_all_workers
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
try:
    r = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'), 
        port=int(os.getenv('REDIS_PORT', 6379)),
        password=os.getenv('REDIS_PASSWORD'),
        db=int(os.getenv('REDIS_DB', 0))
    )
    r.ping()
    print('✅ Redis connection successful')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    exit(1)
"; then
        print_status "Redis connection test passed"
    else
        print_error "Redis connection test failed"
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
case "${1:-start}" in
    "start")
        start_all_workers
        ;;
    "stop")
        stop_all_workers
        ;;
    "restart")
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
        echo "Usage: $0 [start|stop|restart|status|logs [service]|test|help]"
        echo ""
        echo "Commands:"
        echo "  start     Start all workers"
        echo "  stop      Stop all workers"
        echo "  restart   Restart all workers"
        echo "  status    Show worker status"
        echo "  logs      View logs (optionally for specific service)"
        echo "  test      Test worker dependencies"
        echo "  help      Show this help message"
        echo ""
        echo "Services: transcription_direct, transcription_chunk, medical_extraction"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac