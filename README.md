# 🎤 MaiChart - Medical Voice Notes System (FastAPI Version)

A complete **React + FastAPI + MongoDB** application for AI-powered medical voice note transcription using AssemblyAI's advanced speech recognition and OpenAI's GPT-4 for medical information extraction.

## 🏗️ Architecture Overview

```
┌─────────────────┐    HTTP/API    ┌─────────────────┐
│  React Frontend │ ◄──────────►   │ FastAPI Backend │
│   (Port 3000)   │                │   (Port 5001)   │
└─────────────────┘                └─────────────────┘
                                          │
                                          ▼
                                  ┌─────────────────┐
                                  │ Transcription   │
                                  │ + Medical       │
                                  │ Extraction      │
                                  │ Workers         │
                                  └─────────────────┘
                                          │
                                          ▼
                                  ┌─────────────────┐
                                  │ Redis + MongoDB │
                                  │ + File Storage  │
                                  └─────────────────┘
```

## Features

- **Browser Audio Recording** - Direct microphone recording
- **File Upload Support** - Multiple audio formats (WebM, WAV, MP3, OGG, M4A)
- **AI-Powered Transcription** - Medical-optimized speech recognition with AssemblyAI
- **Medical Information Extraction** - GPT-4 powered extraction of patient details, symptoms, medications, allergies
- **Medical Alerts** - Critical information highlighting (allergies, high severity symptoms)
- **Real-time Processing** - Live status updates during transcription
- **Confidence Scoring** - Quality assessment for each transcription
- **Persistent Storage** - MongoDB for analytics, Redis for real-time operations
- **Search & Filter** - Find notes and medical summaries quickly
- **Responsive Design** - Works on desktop and mobile
- **Docker Ready** - Easy deployment with docker-compose
- **FastAPI Performance** - Async processing with automatic API docs
- **Medical Analytics** - Patient statistics, condition tracking, medication analysis

## 🚀 Quick Start

### Option 1: Development Setup (Recommended)

1. **Clone and Setup Project Structure**

2. **Setup Environment Variables**
```bash
# Create .env file with your API keys and database connections
cp .env.example .env
# Edit .env with your actual credentials

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)
```

3. **Setup Backend (FastAPI)**
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p uploads transcripts logs chunks

# Verify environment variables are loaded
echo $ASSEMBLYAI_API_KEY
echo $OPENAI_API_KEY
```

4. **Setup Frontend**
```bash
cd ../frontend
npm install
```

5. **Start All Services**
```bash
# Navigate to backend directory
cd backend

# Start all services with one command
./start_all.sh
```

This will start:
- FastAPI Backend (http://localhost:5001)
- Direct Transcription Worker
- Chunk Transcription Worker  
- Enhanced Medical Extraction Worker
- React Frontend (http://localhost:3000)

### Option 2: Docker Setup (Production)

```bash
# Make sure .env file is present with your API keys
docker-compose up --build
```

## 📋 Environment Variables

Create a `.env` file in the root directory:

```bash
# FastAPI Configuration
FASTAPI_ENV=development
FASTAPI_DEBUG=true
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=5001

# Redis Configuration
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
REDIS_DB=0

# MongoDB Configuration  
ENABLE_MONGODB=true
MONGODB_CONNECTION_STRING=mongodb://username:password@host:port/database
MONGODB_DATABASE_NAME=maichart_medical
STORAGE_STRATEGY=hybrid

# API Keys
ASSEMBLYAI_API_KEY=your-assemblyai-api-key
OPENAI_API_KEY=your-openai-api-key

# Medical Extraction Settings
ENABLE_MEDICAL_EXTRACTION=true
ENABLE_MEDICAL_ANALYTICS=true

# Security
SECRET_KEY=your-long-random-secret-key

# File Upload Settings
MAX_FILE_SIZE=524288000
ALLOWED_EXTENSIONS=webm,wav,mp3,ogg,m4a,flac
```

## 🧪 API Testing Commands

### System Health & Stats
```bash
# Check system health
curl http://localhost:5001/health

# Get system stats
curl http://localhost:5001/api/stats

# Get all notes
curl http://localhost:5001/api/notes

# Check medical analytics
curl http://localhost:5001/api/medical_analytics/summary
```

### Upload and Process Audio
```bash
# Upload an audio file
curl -X POST "http://localhost:5001/api/upload_audio" \
  -F "audio=@./path/to/your/audio-file.wav" \
  -F "timestamp=$(date +%s)000"

# Example with real file
curl -X POST "http://localhost:5001/api/upload_audio" \
  -F "audio=@./recording_example.webm" \
  -F "timestamp=$(date +%s)000"
```

### Check Processing Status
```bash
# Replace SESSION_ID with actual ID from upload response
SESSION_ID="c1e0b268-b510-4c7f-ba48-3cf112790a77"
curl "http://localhost:5001/api/status/$SESSION_ID"
```

### Get Results
```bash
# Get completed transcript
curl "http://localhost:5001/api/transcript/$SESSION_ID"

# Get extracted medical information
curl "http://localhost:5001/api/medical_data/$SESSION_ID"

# Get medical alerts
curl "http://localhost:5001/api/medical_alerts/$SESSION_ID"
```

### Search and Analytics
```bash
# Search transcripts
curl "http://localhost:5001/api/notes/search?q=headache"

# Search patients by condition
curl "http://localhost:5001/api/patients/by_condition/diabetes"

# Get patients with allergies
curl "http://localhost:5001/api/patients/with_allergies"

# Get notes statistics
curl "http://localhost:5001/api/notes/stats"
```

## 🗄️ Database Management

### View MongoDB Data
```bash
# Access MongoDB container
docker exec -it maichart_mongodb bash

# Connect to MongoDB
mongosh -u admin -p maichart_secure_2025 --authenticationDatabase admin

# Switch to medical database
use maichart_medical

# View collections
show collections

# View medical extractions
db.medical_extractions.find().pretty()

# View sessions
db.sessions.find().pretty()

# View medical alerts
db.medical_alerts.find().pretty()

# Get count of records
db.medical_extractions.countDocuments()
db.sessions.countDocuments()
```

## 📁 Complete File Structure

```
maichart-project/
├── 📋 README.md
├── 🐳 docker-compose.yml              # Docker orchestration
├── 📄 .env.example                    # Environment variables template
│
├── backend/                           # FastAPI Server
│   ├── 🚀 app.py                      # Main FastAPI application
│   ├── ⚙️ config.py                   # Configuration settings
│   ├── 📦 requirements.txt            # Python dependencies
│   ├── 🔐 .env                        # Environment variables
│   ├── 🐳 Dockerfile                  # Backend container config
│   ├── 📜 start_all.sh               # Startup script
│   │
│   ├── api/                           # API Routes & Logic
│   │   ├── 🛣️ routes.py               # FastAPI endpoints
│   │   ├── 🏥 medical_routes.py       # Medical data routes
│   │   └── 🔧 utils.py                # API utilities
│   │
│   ├── core/                          # Core Business Logic
│   │   ├── 🔴 redis_client.py         # Redis operations
│   │   ├── 🗄️ mongodb_client.py       # MongoDB operations
│   │   ├── 🎵 audio_handler.py        # Audio processing (async)
│   │   ├── ✂️ audio_chunker.py        # Audio chunking utility
│   │   └── 🏥 enhanced_medical_extraction_service.py # Medical AI
│   │
│   ├── workers/                       # Background Processing
│   │   ├── ⚡ base_worker.py          # Worker foundation
│   │   ├── 🤖 transcription_worker.py # Audio transcription
│   │   └── 🏥 enhanced_medical_extraction_worker.py # Medical extraction
│   │
│   ├── uploads/                       # Audio file storage
│   ├── transcripts/                   # Transcript storage
│   ├── chunks/                        # Chunked audio files
│   └── logs/                          # Application logs
│
├── frontend/                          # React Application
│   ├── 📦 package.json                # Node.js dependencies
│   ├── 🐳 Dockerfile                  # Frontend container config
│   ├── 🌐 nginx.conf                  # Nginx configuration
│   │
│   ├── public/
│   │   └── 📄 index.html              # HTML shell
│   │
│   └── src/
│       ├── 🚀 index.js                # React entry point
│       ├── 📱 App.js                  # Main component
│       │
│       ├── components/                # React Components
│       │   ├── 🎤 AudioRecorder.js    # Recording interface
│       │   ├── 📋 NotesSection.js     # Notes management
│       │   ├── 🏥 MedicalSummariesSection.js # Medical summaries
│       │   └── 📄 TranscriptModal.js  # Transcript viewer
│       │
│       ├── services/
│       │   └── 🌐 api.js              # Backend communication
│       │
│       └── styles/
│           └── 🎨 App.css             # Application styles
│
└── mongodb/                           # MongoDB Setup
    └── init-scripts/
        └── 001-init-indexes.js       # Database initialization
```

## 🌐 API Endpoints

### Core Transcription Endpoints:
- `POST /api/upload_audio` - Upload audio for transcription
- `GET /api/status/{id}` - Check processing status
- `GET /api/transcript/{id}` - Get completed transcript
- `GET /api/notes` - List all notes
- `GET /api/health` - System health check

### Medical Information Endpoints:
- `GET /api/medical_data/{id}` - Get extracted medical information
- `GET /api/medical_alerts/{id}` - Get medical alerts for session
- `GET /api/medical_analytics/summary` - Get medical analytics
- `GET /api/patients/by_condition/{condition}` - Search by condition
- `GET /api/patients/with_allergies` - Get patients with allergies

### Management Endpoints:
- `GET /api/notes/search?q=query` - Search transcripts
- `GET /api/notes/stats` - Usage statistics
- `DELETE /api/cleanup/{id}` - Delete session
- `GET /api/export/notes` - Export all notes

### FastAPI Documentation:
- **Swagger UI:** http://localhost:5001/docs
- **ReDoc:** http://localhost:5001/redoc

## 🏥 Medical Information Extraction

The system automatically extracts structured medical information from transcripts:

### Extracted Data Fields:
- **Patient Details:** Name, age, gender, residence
- **Chief Complaints:** Primary symptoms with duration and severity
- **Medical History:** Past illnesses, surgeries, chronic conditions
- **Current Medications:** Drug history with dosages
- **Allergies:**  Critical safety information
- **Lifestyle Factors:** Smoking, alcohol, exercise habits
- **Family History:** Hereditary conditions
- **Symptoms:** All mentioned symptoms
- **Possible Diagnoses:** AI-suggested conditions

### Monitoring:
```bash
# System statistics
curl http://localhost:5001/api/stats

# Worker status
curl http://localhost:5001/health

# Medical analytics
curl http://localhost:5001/api/medical_analytics/summary
```

## 🚀 Production Deployment

1. **Environment Setup:**
   - Set `FASTAPI_ENV=production`
   - Use strong `SECRET_KEY`
   - Configure production Redis and MongoDB instances

2. **Security:**
   - Enable HTTPS
   - Set up proper firewall rules
   - Use environment-specific API keys

3. **Scaling:**
   - Run multiple worker instances
   - Use Redis cluster for high availability
   - Implement MongoDB replica set

---