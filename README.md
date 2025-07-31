# 🎤 MaiChart - Medical Voice Notes System (FastAPI Version)

A complete **React + FastAPI** application for AI-powered medical voice note transcription using AssemblyAI's advanced speech recognition.

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
                                  │     Worker      │
                                  └─────────────────┘
                                          │
                                          ▼
                                  ┌─────────────────┐
                                  │ Redis + Files   │
                                  │    Storage      │
                                  └─────────────────┘
```

## ✨ Features

- 🎙️ **Browser Audio Recording** - Direct microphone recording
- 📁 **File Upload Support** - Multiple audio formats (WebM, WAV, MP3, OGG, M4A)
- 🤖 **AI-Powered Transcription** - Medical-optimized speech recognition
- 🏥 **Medical Focus** - Specialized for healthcare terminology
- ⚡ **Real-time Processing** - Live status updates during transcription
- 📊 **Confidence Scoring** - Quality assessment for each transcription
- 💾 **Persistent Storage** - Organized transcript management
- 🔍 **Search & Filter** - Find notes quickly
- 📱 **Responsive Design** - Works on desktop and mobile
- 🐳 **Docker Ready** - Easy deployment
- 🚀 **FastAPI Performance** - Async processing with automatic API docs

## 🚀 Quick Start

### Option 1: Development Setup (Recommended)

1. **Clone and Setup Project Structure**
```bash
git clone https://github.com/dhruvd-1/maichart-private-v0.git
cd maichart-private-v0.git
```

2. **Setup Backend (FastAPI)**
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p uploads transcripts logs chunks

# Set environment variables in .env file
# Make sure ASSEMBLYAI_API_KEY is set
```

3. **Setup Frontend**
```bash
cd ../frontend
npm install
```

4. **Get AssemblyAI API Key**
   - Visit https://app.assemblyai.com/
   - Sign up for free account
   - Add key to .env file: `ASSEMBLYAI_API_KEY=your_key_here`

5. **Start Development Servers**
```bash
# Terminal 1 - FastAPI Backend
cd backend

## 🔧 Environment Variables

Create a `.env` file in the root directory with the following variables:

```bash
# FastAPI Configuration
FASTAPI_ENV=development
FASTAPI_DEBUG=true
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=5001

# Redis Configuration (use your Redis instance)
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
REDIS_DB=0

# AssemblyAI Configuration
ASSEMBLYAI_API_KEY=your-assemblyai-api-key

# Security
SECRET_KEY=your-long-random-secret-key

# File Upload Settings (Optional)
MAX_FILE_SIZE=524288000
ALLOWED_EXTENSIONS=webm,wav,mp3,ogg,m4a,flac


python app.py
# or
uvicorn app:app --host 0.0.0.0 --port 5001 --reload

# Terminal 2 - Frontend  
cd frontend
npm start

# Terminal 3 - Direct Worker (optional)
cd backend
python workers/transcription_worker.py direct

# Terminal 4 - Chunk Worker (optional, for large files)
cd backend
python workers/transcription_worker.py chunk
```

### Option 2: Docker Setup (Production)

```bash
# Make sure .env file is present
docker-compose up --build
```

## 📁 Complete File Structure

```
maichart-project/
├── 📋 README.md
├── 🐳 docker-compose.yml              # Docker orchestration
│
├── backend/                           # FastAPI Server
│   ├── 🚀 app.py                      # Main FastAPI application
│   ├── ⚙️  config.py                  # Configuration settings
│   ├── 📦 requirements.txt            # Python dependencies
│   ├── 🔐 .env                        # Environment variables
│   ├── 🐳 Dockerfile                  # Backend container config
│   │
│   ├── api/                           # API Routes & Logic
│   │   ├── __init__.py
│   │   ├── 🛣️  routes.py              # FastAPI endpoints
│   │   └── 🔧 utils.py                # API utilities
│   │
│   ├── core/                          # Core Business Logic
│   │   ├── __init__.py
│   │   ├── 🔴 redis_client.py         # Redis operations
│   │   ├── 🎵 audio_handler.py        # Audio processing (async)
│   │   └── ✂️  audio_chunker.py       # Audio chunking utility
│   │
│   ├── workers/                       # Background Processing
│   │   ├── __init__.py
│   │   ├── ⚡ base_worker.py          # Worker foundation
│   │   └── 🤖 transcription_worker.py # AI transcription
│   │
│   ├── uploads/                       # Audio file storage
│   ├── transcripts/                   # Transcript storage
│   ├── chunks/                        # Chunked audio files
│   └── logs/                          # Application logs
│
└── frontend/                          # React Application
    ├── 📦 package.json                # Node.js dependencies
    ├── 🐳 Dockerfile                  # Frontend container config
    ├── 🌐 nginx.conf                  # Nginx configuration
    │
    ├── public/
    │   └── 📄 index.html              # HTML shell
    │
    └── src/
        ├── 🚀 index.js                # React entry point
        ├── 📱 App.js                  # Main component
        │
        ├── components/                # React Components
        │   ├── 🎤 AudioRecorder.js    # Recording interface
        │   ├── 📋 NotesSection.js     # Notes management
        │   └── 📄 TranscriptModal.js  # Transcript viewer
        │
        ├── services/
        │   └── 🌐 api.js              # Backend communication
        │
        └── styles/
            └── 🎨 App.css             # Application styles
```

## 🌐 FastAPI API Endpoints

### Core Endpoints:
- `POST /api/upload_audio` - Upload audio for transcription
- `GET /api/status/{id}` - Check processing status
- `GET /api/transcript/{id}` - Get completed transcript
- `GET /api/notes` - List all notes
- `GET /api/health` - System health check

### Management Endpoints:
- `GET /api/notes/search?q=query` - Search transcripts
- `GET /api/notes/stats` - Usage statistics
- `DELETE /api/cleanup/{id}` - Delete session
- `GET /api/export/notes` - Export all notes