#!/bin/bash

# =============================================================================
# MaiChart Medical Transcription System - Complete Startup Script
# =============================================================================
# This single script handles everything: daemon management, systemd setup,
# monitoring, logging, and complete system management.
# 
# Usage:
#   ./startup.sh start          # Start all services as daemons
#   ./startup.sh stop           # Stop all services
#   ./startup.sh restart        # Restart all services
#   ./startup.sh status         # Show service status
#   ./startup.sh logs           # View logs
#   ./startup.sh install        # Install as systemd services
#   ./startup.sh health         # Health check
#   ./startup.sh deploy         # Complete deployment setup
# =============================================================================

set -e

# Color codes for beautiful output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$SCRIPT_DIR"
LOG_DIR="$SCRIPT_DIR/logs"
PID_DIR="$SCRIPT_DIR/pids"
SERVICE_USER=$(whoami)
SYSTEMD_DIR="/etc/systemd/system"

# Ensure directories exist
mkdir -p "$LOG_DIR" "$PID_DIR" uploads transcripts chunks logs

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

print_header() { echo -e "${CYAN}🚀 $1${NC}"; }
print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }
print_success() { echo -e "${GREEN}🎉 $1${NC}"; }

# Function to check if service is running
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

# Function to get service PID
get_service_pid() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [[ -f "$pid_file" ]]; then
        cat "$pid_file"
    fi
}

# Function to get service resource usage
get_service_resources() {
    local pid=$1
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        local memory=$(ps -o rss= -p "$pid" 2>/dev/null | awk '{print int($1/1024)"MB"}' || echo "N/A")
        local cpu=$(ps -o %cpu= -p "$pid" 2>/dev/null | awk '{print $1"%"}' || echo "N/A")
        echo "CPU: $cpu, Memory: $memory"
    else
        echo "N/A"
    fi
}

# =============================================================================
# DEPENDENCY CHECKING
# =============================================================================

check_dependencies() {
    print_info "Checking system dependencies..."
    
    # Check environment variables
    if [[ -z "$ASSEMBLYAI_API_KEY" ]]; then
        print_error "ASSEMBLYAI_API_KEY is required"
        exit 1
    fi

    if [[ -z "$REDIS_HOST" ]]; then
        print_error "REDIS_HOST is required"  
        exit 1
    fi

    if [[ -z "$MONGODB_CONNECTION_STRING" ]]; then
        print_warning "MONGODB_CONNECTION_STRING not set - MongoDB features will be disabled"
        export ENABLE_MONGODB=false
    else
        print_status "MongoDB connection configured"
        export ENABLE_MONGODB=true
    fi

    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python not found. Please install Python 3"
        exit 1
    fi

    print_status "Using Python: $PYTHON_CMD"

    # Check virtual environment
    if [[ -d "venv" ]]; then
        print_info "Activating virtual environment..."
        source venv/bin/activate
        print_status "Virtual environment activated"
    else
        print_warning "Virtual environment not found. Using system Python."
    fi

    # Test connections
    if [[ "$ENABLE_MONGODB" == "true" ]]; then
        print_info "Testing MongoDB connection..."
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
" || true
    fi

    print_status "Dependencies check completed"
}

# =============================================================================
# SERVICE MANAGEMENT
# =============================================================================

start_daemon_service() {
    local service_name=$1
    local command=$2
    local description=$3
    local log_file="$LOG_DIR/${service_name}.log"
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if is_service_running "$service_name"; then
        print_warning "$service_name is already running"
        return 0
    fi
    
    print_info "Starting $service_name as daemon..."
    print_info "Description: $description"
    
    # Start service in background
    nohup $command >> "$log_file" 2>&1 &
    local pid=$!
    
    # Save PID
    echo $pid > "$pid_file"
    
    # Wait and verify
    sleep 3
    
    if kill -0 "$pid" 2>/dev/null; then
        local resources=$(get_service_resources "$pid")
        print_status "$service_name started successfully (PID: $pid, $resources)"
        print_info "Logs: $log_file"
        return 0
    else
        print_error "$service_name failed to start"
        rm -f "$pid_file"
        echo "Last 10 lines of log:"
        tail -n 10 "$log_file" 2>/dev/null || echo "No log data available"
        return 1
    fi
}

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

start_all_services() {
    print_header "Starting All MaiChart Services"
    echo "================================="
    
    check_dependencies
    
    # Start services in order
    start_daemon_service "backend" \
        "$PYTHON_CMD app.py" \
        "Main FastAPI backend server"
    
    # Wait for backend to be ready
    print_info "Waiting for backend to initialize..."
    sleep 15
    
    start_daemon_service "direct_worker" \
    "env WORKER_TYPE=direct $PYTHON_CMD workers/transcription_worker.py direct" \
    "Direct audio transcription worker"
    
    start_daemon_service "chunk_worker" \
    "env WORKER_TYPE=chunk $PYTHON_CMD workers/transcription_worker.py chunk" \
    "Chunked audio transcription worker"
    
    if [[ -n "$OPENAI_API_KEY" ]]; then
        start_daemon_service "medical_worker" \
            "$PYTHON_CMD workers/enhanced_medical_extraction_worker.py" \
            "Medical information extraction worker"
    else
        print_warning "OPENAI_API_KEY not found. Skipping medical extraction worker."
    fi
    
    echo ""
    print_success "All services started successfully!"
    show_service_urls
}

stop_all_services() {
    print_header "Stopping All MaiChart Services"
    echo "==============================="
    
    local services=("medical_worker" "chunk_worker" "direct_worker" "backend")
    
    for service in "${services[@]}"; do
        stop_service "$service"
    done
    
    print_success "All services stopped"
}

restart_all_services() {
    print_header "Restarting All MaiChart Services"
    echo "================================="
    
    stop_all_services
    sleep 5
    start_all_services
}

show_service_status() {
    print_header "MaiChart Service Status"
    echo "======================="
    
    local services=("backend" "direct_worker" "chunk_worker" "medical_worker")
    local total_services=0
    local running_services=0
    
    printf "%-20s %-10s %-8s %-20s %-15s\n" "SERVICE" "STATUS" "PID" "RESOURCES" "UPTIME"
    echo "--------------------------------------------------------------------------------"
    
    for service in "${services[@]}"; do
        ((total_services++))
        if is_service_running "$service"; then
            ((running_services++))
            local pid=$(get_service_pid "$service")
            local resources=$(get_service_resources "$pid")
            local uptime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ' || echo "N/A")
            printf "%-20s ${GREEN}%-10s${NC} %-8s %-20s %-15s\n" "$service" "RUNNING" "$pid" "$resources" "$uptime"
        else
            printf "%-20s ${RED}%-10s${NC} %-8s %-20s %-15s\n" "$service" "STOPPED" "-" "-" "-"
        fi
    done
    
    echo ""
    if [[ $running_services -eq $total_services ]]; then
        print_success "All services are running ($running_services/$total_services)"
    elif [[ $running_services -gt 0 ]]; then
        print_warning "Some services are running ($running_services/$total_services)"
    else
        print_error "No services are running (0/$total_services)"
    fi
    
    show_service_urls
}

show_service_urls() {
    echo ""
    print_info "🌐 Service URLs:"
    echo "  Backend API:     http://localhost:5001"
    echo "  API Docs:        http://localhost:5001/docs"
    echo "  Health Check:    http://localhost:5001/health"
    echo "  Frontend:        http://localhost:3000 (if running)"
}

# =============================================================================
# LOGGING AND MONITORING
# =============================================================================

view_logs() {
    local service=${1:-"all"}
    
    if [[ "$service" == "all" ]]; then
        print_info "📋 Showing logs for all services (Ctrl+C to exit)..."
        if ls "$LOG_DIR"/*.log 1> /dev/null 2>&1; then
            tail -f "$LOG_DIR"/*.log
        else
            print_warning "No log files found"
        fi
    else
        local log_file="$LOG_DIR/${service}.log"
        if [[ -f "$log_file" ]]; then
            print_info "📋 Showing logs for $service (Ctrl+C to exit)..."
            tail -f "$log_file"
        else
            print_error "Log file not found for service: $service"
            print_info "Available services: backend, direct_worker, chunk_worker, medical_worker"
        fi
    fi
}

health_check() {
    print_header "MaiChart Health Check"
    echo "====================="
    
    # Check API health
    print_info "Testing API endpoint..."
    if curl -s -f http://localhost:5001/health > /dev/null; then
        print_status "API: Healthy"
        
        # Get detailed health info
        local health_response=$(curl -s http://localhost:5001/health)
        echo "$health_response" | python3 -m json.tool 2>/dev/null || echo "$health_response"
    else
        print_error "API: Unhealthy or not responding"
    fi
    
    echo ""
    
    # Check individual services
    local services=("backend" "direct_worker" "chunk_worker" "medical_worker")
    for service in "${services[@]}"; do
        if is_service_running "$service"; then
            local pid=$(get_service_pid "$service")
            local resources=$(get_service_resources "$pid")
            print_status "$service: Running ($resources)"
        else
            print_error "$service: Not running"
        fi
    done
    
    # Check disk space
    echo ""
    print_info "📊 Disk Usage:"
    echo "Uploads folder: $(du -sh uploads 2>/dev/null | cut -f1 || echo 'N/A')"
    echo "Logs folder: $(du -sh logs 2>/dev/null | cut -f1 || echo 'N/A')"
    echo "Transcripts folder: $(du -sh transcripts 2>/dev/null | cut -f1 || echo 'N/A')"
    
    # Check available space
    local available_space=$(df -h . | awk 'NR==2 {print $4}')
    print_info "Available disk space: $available_space"
}

cleanup_logs() {
    print_info "🧹 Cleaning up old logs..."
    
    # Remove logs older than 7 days
    find "$LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null || true
    
    # Truncate large log files (>100MB)
    find "$LOG_DIR" -name "*.log" -size +100M -exec truncate -s 50M {} \; 2>/dev/null || true
    
    # Clean up old chunks and temporary files
    find chunks -name "*.wav" -mtime +1 -delete 2>/dev/null || true
    find uploads -name "*.tmp" -delete 2>/dev/null || true
    
    print_status "Log cleanup completed"
}

# =============================================================================
# SYSTEMD INTEGRATION
# =============================================================================

install_systemd_services() {
    print_header "Installing Systemd Services"
    echo "============================"
    
    if ! command -v systemctl &> /dev/null; then
        print_error "systemctl not found. Systemd services not available."
        return 1
    fi
    
    if ! sudo -n true 2>/dev/null; then
        print_error "Sudo access required for systemd installation"
        return 1
    fi
    
    print_info "Creating systemd service files..."
    
    # Main backend service
    sudo tee "$SYSTEMD_DIR/maichart.service" > /dev/null << EOF
[Unit]
Description=MaiChart Medical Transcription Backend
Documentation=https://github.com/your-repo/maichart
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$BACKEND_DIR
Environment=PATH=$BACKEND_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=$BACKEND_DIR/.env

ExecStart=$BACKEND_DIR/venv/bin/python app.py
ExecStop=/bin/kill -TERM \$MAINPID

Restart=always
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

StandardOutput=journal
StandardError=journal
SyslogIdentifier=maichart-backend

[Install]
WantedBy=multi-user.target
EOF

    # Worker services
    for worker in "direct" "chunk" "medical"; do
        local service_name="maichart-${worker}-worker"
        local worker_cmd=""
        
        case $worker in
            "direct")
                worker_cmd="$BACKEND_DIR/venv/bin/python workers/transcription_worker.py direct"
                ;;
            "chunk")
                worker_cmd="$BACKEND_DIR/venv/bin/python workers/transcription_worker.py chunk"
                ;;
            "medical")
                worker_cmd="$BACKEND_DIR/venv/bin/python workers/enhanced_medical_extraction_worker.py"
                ;;
        esac
        
        sudo tee "$SYSTEMD_DIR/${service_name}.service" > /dev/null << EOF
[Unit]
Description=MaiChart ${worker^} Worker
After=network-online.target maichart.service
Wants=network-online.target
Requires=maichart.service

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$BACKEND_DIR
Environment=PATH=$BACKEND_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=WORKER_TYPE=$worker
EnvironmentFile=$BACKEND_DIR/.env

ExecStart=$worker_cmd
ExecStop=/bin/kill -TERM \$MAINPID

Restart=always
RestartSec=10

StandardOutput=journal
StandardError=journal
SyslogIdentifier=maichart-${worker}-worker

[Install]
WantedBy=multi-user.target
EOF
    done
    
    # Reload and enable services
    sudo systemctl daemon-reload
    
    local services=("maichart" "maichart-direct-worker" "maichart-chunk-worker" "maichart-medical-worker")
    for service in "${services[@]}"; do
        sudo systemctl enable "$service"
        print_status "Enabled $service"
    done
    
    print_success "Systemd services installed and enabled!"
    print_info "Use 'sudo systemctl start maichart' to start with systemd"
}

# =============================================================================
# COMPLETE DEPLOYMENT
# =============================================================================

deploy_complete_setup() {
    print_header "MaiChart Complete Deployment Setup"
    echo "==================================="
    
    # Check if we're in the right directory
    if [[ ! -f "app.py" ]]; then
        print_error "Please run this script from the backend directory"
        exit 1
    fi
    
    # Check environment file
    if [[ ! -f ".env" ]]; then
        print_error "Environment file (.env) not found!"
        print_info "Please create .env file with your configuration"
        exit 1
    fi
    
    print_info "Setting up daemon script permissions..."
    chmod +x "$0"
    
    print_info "Creating necessary directories..."
    mkdir -p uploads transcripts chunks logs "$LOG_DIR" "$PID_DIR"
    
    # Setup log rotation
    if command -v logrotate &> /dev/null && sudo -n true 2>/dev/null; then
        print_info "Setting up log rotation..."
        sudo tee "/etc/logrotate.d/maichart" > /dev/null << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 $SERVICE_USER $SERVICE_USER
    copytruncate
}
EOF
        print_status "Log rotation configured"
    fi
    
    # Setup firewall if available
    if command -v ufw &> /dev/null && sudo -n true 2>/dev/null; then
        print_info "Configuring firewall..."
        sudo ufw allow 5001/tcp comment "MaiChart API" 2>/dev/null || true
        sudo ufw allow 3000/tcp comment "MaiChart Frontend" 2>/dev/null || true
        print_status "Firewall configured"
    fi
    
    # Install systemd services
    install_systemd_services
    
    print_success "🎉 Deployment setup completed!"
    echo ""
    print_info "Next steps:"
    echo "  1. Start services: ./startup.sh start"
    echo "  2. Check status:   ./startup.sh status"
    echo "  3. View logs:      ./startup.sh logs"
    echo "  4. Health check:   ./startup.sh health"
    echo ""
    print_info "Alternative systemd commands:"
    echo "  sudo systemctl start maichart"
    echo "  sudo systemctl status maichart"
}

# =============================================================================
# HELP AND USAGE
# =============================================================================

show_help() {
    echo -e "${CYAN}🚀 MaiChart Medical Transcription System${NC}"
    echo -e "${WHITE}Complete Management Script${NC}"
    echo "========================================"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo -e "${YELLOW}Main Commands:${NC}"
    echo "  start         Start all services as daemons"
    echo "  stop          Stop all services"
    echo "  restart       Restart all services"
    echo "  status        Show detailed service status"
    echo "  health        Comprehensive health check"
    echo ""
    echo -e "${YELLOW}Monitoring Commands:${NC}"
    echo "  logs          View logs for all services"
    echo "  logs [name]   View logs for specific service"
    echo "  cleanup       Clean up old logs and temporary files"
    echo ""
    echo -e "${YELLOW}System Commands:${NC}"
    echo "  install       Install as systemd services"
    echo "  deploy        Complete deployment setup"
    echo "  help          Show this help message"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 start              # Start all services"
    echo "  $0 logs backend       # View backend logs"
    echo "  $0 status             # Check service status"
    echo "  $0 health             # Health check"
    echo ""
    echo -e "${YELLOW}Service Names:${NC}"
    echo "  backend, direct_worker, chunk_worker, medical_worker"
    echo ""
    echo -e "${YELLOW}API Endpoints:${NC}"
    echo "  http://localhost:5001/health     # Health check"
    echo "  http://localhost:5001/docs       # API documentation"
    echo "  http://localhost:5001/api/       # Main API"
}

# =============================================================================
# SIGNAL HANDLERS
# =============================================================================

cleanup_on_exit() {
    print_info "Received interrupt signal..."
    # Don't stop services on Ctrl+C, just exit the script
    exit 0
}

trap cleanup_on_exit SIGINT SIGTERM

# =============================================================================
# MAIN SCRIPT LOGIC
# =============================================================================

main() {
    # Change to backend directory if not already there
    if [[ -f "../backend/app.py" && ! -f "app.py" ]]; then
        cd "$(dirname "$0")"
    fi
    
    case "${1:-help}" in
        "start")
            start_all_services
            ;;
        
        "stop")
            stop_all_services
            ;;
        
        "restart")
            restart_all_services
            ;;
        
        "status")
            show_service_status
            ;;
        
        "logs")
            view_logs "${2:-all}"
            ;;
        
        "health")
            health_check
            ;;
        
        "cleanup")
            cleanup_logs
            ;;
        
        "install")
            install_systemd_services
            ;;
        
        "deploy")
            deploy_complete_setup
            ;;
        
        "help"|"-h"|"--help")
            show_help
            ;;
        
        *)
            print_error "Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"