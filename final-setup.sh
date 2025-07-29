#!/bin/bash
# final-setup.sh - Complete MaiChart setup with all fixes

echo "🚀 Final MaiChart Setup - Fixing All Issues"

# Clean everything first
echo "🧹 Cleaning up previous containers..."
docker-compose down --remove-orphans 2>/dev/null || true
docker container prune -f
docker image prune -f

# Remove problematic frontend artifacts
echo "🗑️ Cleaning frontend artifacts..."
rm -rf frontend/node_modules frontend/package-lock.json frontend/build 2>/dev/null || true

# Create/update necessary files
echo "📄 Updating configuration files..."

# Update docker-compose.yml with fixed Redis config
cat > docker-compose.yml << 'EOF'
services:
  # Redis Server
  redis:
    image: redis:7-alpine
    container_name: maichart_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Backend API Server
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    container_name: maichart_backend
    ports:
      - "5001:5001"
    volumes:
      - "./backend/uploads:/app/uploads"
      - "./backend/transcripts:/app/transcripts"
      - "./backend/logs:/app/logs"
      - "./backend/chunks:/app/chunks"
    environment:
      - FLASK_ENV=production
      - FLASK_PORT=5001
      - FLASK_HOST=0.0.0.0
      # Override Redis settings for Docker
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=
      - REDIS_DB=0
    env_file:
      - ./backend/.env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/api/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    depends_on:
      redis:
        condition: service_healthy

  # Transcription Worker for Direct Processing
  transcription_worker:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    container_name: maichart_transcription_worker
    volumes:
      - "./backend/uploads:/app/uploads"
      - "./backend/transcripts:/app/transcripts"
      - "./backend/logs:/app/logs"
      - "./backend/chunks:/app/chunks"
    environment:
      - WORKER_TYPE=direct
      # Override Redis settings for Docker
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=
      - REDIS_DB=0
    env_file:
      - ./backend/.env
    command: python workers/transcription_worker.py direct
    restart: unless-stopped
    depends_on:
      backend:
        condition: service_healthy

  # Chunk Processing Worker
  chunk_worker:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    container_name: maichart_chunk_worker
    volumes:
      - "./backend/uploads:/app/uploads"
      - "./backend/transcripts:/app/transcripts"
      - "./backend/logs:/app/logs"
      - "./backend/chunks:/app/chunks"
    environment:
      - WORKER_TYPE=chunk
      # Override Redis settings for Docker
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=
      - REDIS_DB=0
    env_file:
      - ./backend/.env
    command: python workers/transcription_worker.py chunk
    restart: unless-stopped
    depends_on:
      backend:
        condition: service_healthy

  # Frontend (Production Build)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: maichart_frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  redis_data:
EOF

# Update frontend Dockerfile with proper build process
cat > frontend/Dockerfile << 'EOF'
FROM node:18-alpine as builder
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF

# Update backend config.py to prioritize environment variables
cat > backend/config.py << 'EOF'
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    DEBUG = False
    TESTING = False
    HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
    PORT = int(os.environ.get("FLASK_PORT", 5001))
    MAX_FILE_SIZE = 100 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"webm", "wav", "mp3", "ogg", "m4a"}
    
    BASE_DIR = Path(__file__).parent
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    TRANSCRIPTS_FOLDER = BASE_DIR / "transcripts"
    LOGS_FOLDER = BASE_DIR / "logs"
    CHUNKS_FOLDER = BASE_DIR / "chunks"
    
    # Redis configuration - prioritize environment variables for Docker
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
    REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
    REDIS_DB = int(os.environ.get("REDIS_DB", 0))
    
    AUDIO_INPUT_STREAM = "audio_processing"
    AUDIO_CHUNK_STREAM = "chunk_processing"
    CONSUMER_GROUP = "transcription_workers"
    CHUNK_CONSUMER_GROUP = "chunk_workers"
    
    WORKER_BLOCK_TIME = 1000
    WORKER_TIMEOUT = 300
    SESSION_EXPIRE_TIME = 3600
    CHUNK_DURATION = 120
    CHUNK_OVERLAP = 5
    
    ASSEMBLYAI_API_KEY = os.environ.get("ASSEMBLYAI_API_KEY")
    
    @classmethod
    def create_directories(cls):
        for folder in [cls.UPLOAD_FOLDER, cls.TRANSCRIPTS_FOLDER, cls.LOGS_FOLDER, cls.CHUNKS_FOLDER]:
            folder.mkdir(exist_ok=True)

class DevelopmentConfig(Config):
    DEBUG = True
    HOST = "127.0.0.1"

class ProductionConfig(Config):
    DEBUG = False

config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
EOF

# Ensure backend requirements.txt is clean
cat > backend/requirements.txt << 'EOF'
Flask==2.3.3
Flask-CORS==4.0.0
redis==5.0.1
python-dotenv==1.0.0
requests==2.31.0
cryptography==41.0.7
assemblyai==0.23.0
ffmpeg-python==0.2.0
pydub==0.25.1
retrying==1.3.4
psutil==5.9.5
structlog==23.1.0
EOF

# Make sure frontend nginx.conf exists
cat > frontend/nginx.conf << 'EOF'
server {
    listen 80;
    server_name localhost;
    
    # Serve React app
    location / {
        root /usr/share/nginx/html;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
        
        # Add security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "no-referrer-when-downgrade" always;
    }
    
    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://backend:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Increase timeouts for large file uploads
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        client_max_body_size 100M;
    }
    
    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
}
EOF

# Ensure package.json has correct dependencies
cat > frontend/package.json << 'EOF'
{
  "name": "maichart-frontend",
  "version": "1.0.0",
  "description": "Frontend for MaiChart Medical Voice Notes",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "web-vitals": "^2.1.4"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": [
      "react-app",
      "react-app/jest"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  },
  "proxy": "http://localhost:5001"
}
EOF

# Create directories
echo "📁 Creating directories..."
mkdir -p backend/{uploads,transcripts,logs,chunks} 2>/dev/null || true

# Verify all critical files exist
echo "🔍 Verifying critical files..."
MISSING_FILES=()

# Check backend files
[ ! -f "backend/app.py" ] && MISSING_FILES+=("backend/app.py")
[ ! -f "backend/config.py" ] && MISSING_FILES+=("backend/config.py")
[ ! -f "backend/requirements.txt" ] && MISSING_FILES+=("backend/requirements.txt")
[ ! -f "backend/.env" ] && MISSING_FILES+=("backend/.env")
[ ! -d "backend/api" ] && MISSING_FILES+=("backend/api/")
[ ! -d "backend/core" ] && MISSING_FILES+=("backend/core/")
[ ! -d "backend/workers" ] && MISSING_FILES+=("backend/workers/")

# Check frontend files
[ ! -f "frontend/package.json" ] && MISSING_FILES+=("frontend/package.json")
[ ! -f "frontend/nginx.conf" ] && MISSING_FILES+=("frontend/nginx.conf")
[ ! -d "frontend/src" ] && MISSING_FILES+=("frontend/src/")
[ ! -d "frontend/public" ] && MISSING_FILES+=("frontend/public/")

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo "❌ Missing critical files:"
    printf '%s\n' "${MISSING_FILES[@]}"
    echo ""
    echo "💡 Please ensure all files from the project are in place."
    echo "   You may need to copy files from the original project structure."
    exit 1
fi

echo "✅ All critical files found!"

# Check and display API key
if [ -f "backend/.env" ]; then
    API_KEY=$(grep "^ASSEMBLYAI_API_KEY=" backend/.env | cut -d'=' -f2)
    if [ -n "$API_KEY" ] && [ "$API_KEY" != "your_assemblyai_api_key_here" ]; then
        echo "🔑 AssemblyAI API Key: ${API_KEY:0:8}...${API_KEY: -4}"
        echo "✅ API key looks valid!"
    else
        echo "❌ AssemblyAI API key not properly set in backend/.env"
        echo "🔧 Please edit backend/.env and set your ASSEMBLYAI_API_KEY"
        echo "💡 Get your key from: https://app.assemblyai.com/"
        exit 1
    fi
else
    echo "❌ backend/.env file not found!"
    echo "🔧 Please create backend/.env with your ASSEMBLYAI_API_KEY"
    exit 1
fi

echo "🏗️ Building and starting all services..."
echo "⏳ This may take 5-10 minutes on first run..."

# Build and start with comprehensive error handling
echo "🔨 Step 1: Building images..."
if ! docker-compose build --no-cache; then
    echo "❌ Docker build failed!"
    echo "🔍 Check the build logs above for errors."
    echo "💡 Common issues:"
    echo "   - Missing files in project structure"
    echo "   - Network connectivity issues"
    echo "   - Docker daemon not running"
    exit 1
fi

echo "✅ Build completed successfully!"
echo ""
echo "🚀 Step 2: Starting services..."

if docker-compose up -d; then
    echo ""
    echo "✅ All services started!"
    echo ""
    echo "📡 Services:"
    echo "   Frontend: http://localhost:3000"
    echo "   Backend API: http://localhost:5001"
    echo "   Health Check: http://localhost:5001/api/health"
    echo ""
    echo "⏳ Services are starting up, please wait 30-60 seconds..."
    
    # Monitor service startup
    echo ""
    echo "📊 Monitoring service startup..."
    
    for i in {1..12}; do
        sleep 5
        echo "⏳ Checking services... (${i}/12)"
        
        # Check if containers are running
        BACKEND_STATUS=$(docker-compose ps -q backend | xargs docker inspect -f '{{.State.Status}}' 2>/dev/null || echo "not found")
        FRONTEND_STATUS=$(docker-compose ps -q frontend | xargs docker inspect -f '{{.State.Status}}' 2>/dev/null || echo "not found")
        REDIS_STATUS=$(docker-compose ps -q redis | xargs docker inspect -f '{{.State.Status}}' 2>/dev/null || echo "not found")
        
        echo "   Redis: $REDIS_STATUS | Backend: $BACKEND_STATUS | Frontend: $FRONTEND_STATUS"
        
        # Check if backend is responding
        if [ "$BACKEND_STATUS" = "running" ]; then
            if curl -s http://localhost:5001/api/health > /dev/null 2>&1; then
                echo "✅ Backend is healthy and responding!"
                
                # Check frontend
                if curl -s http://localhost:3000 > /dev/null 2>&1; then
                    echo "✅ Frontend is serving content!"
                    break
                else
                    echo "⏳ Frontend still starting up..."
                fi
            else
                echo "⏳ Backend starting up..."
            fi
        fi
        
        if [ $i -eq 12 ]; then
            echo "⚠️  Services are taking longer than expected to start"
            echo "🔍 Check logs with: docker-compose logs"
        fi
    done
    
    echo ""
    echo "📋 Final Status Check:"
    docker-compose ps
    
    echo ""
    echo "🎉 MaiChart Setup Complete!"
    echo ""
    echo "🌟 Access your application:"
    echo "   🌐 Main App: http://localhost:3000"
    echo "   🔧 API: http://localhost:5001"
    echo "   ❤️  Health: http://localhost:5001/api/health"
    echo ""
    echo "🛠️  Management Commands:"
    echo "   📊 View status: docker-compose ps"
    echo "   📜 View logs: docker-compose logs -f"
    echo "   🔄 Restart: docker-compose restart"
    echo "   🛑 Stop: docker-compose down"
    echo ""
    echo "🎤 Ready to process medical voice notes!"
    
else
    echo "❌ Failed to start services!"
    echo ""
    echo "🔍 Troubleshooting steps:"
    echo "1. Check if ports 3000, 5001, 6379 are available:"
    echo "   lsof -i :3000,5001,6379"
    echo ""
    echo "2. Check Docker logs:"
    echo "   docker-compose logs"
    echo ""
    echo "3. Check individual service logs:"
    echo "   docker-compose logs backend"
    echo "   docker-compose logs frontend"
    echo "   docker-compose logs redis"
    echo ""
    echo "4. Try rebuilding:"
    echo "   docker-compose down"
    echo "   docker-compose up --build"
    exit 1
fi