# 🎤 MaiChart - Medical Voice Notes System

A complete **React + Flask** application for AI-powered medical voice note transcription using AssemblyAI's advanced speech recognition.

## 🏗️ Architecture Overview

```
┌─────────────────┐    HTTP/API    ┌─────────────────┐
│  React Frontend │ ◄──────────►   │  Flask Backend  │
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

Think of it like a **medical clinic's workflow**:
- **Frontend (Reception)**: Beautiful interface for patients/doctors to interact
- **Backend (Medical Records)**: Manages data, processes requests, stores information  
- **Worker (Laboratory)**: Does the heavy lifting of audio analysis
- **Storage (Filing System)**: Keeps everything organized and accessible

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

## 🚀 Quick Start

### Option 1: Development Setup (Recommended)

1. **Clone and Setup Project Structure**
```bash
git clone https://github.com/dhruvd-1/maichart-private-v0.git
cd maichart-private-v0.git
#Add .env

# Create backend and frontend directories

2. **Setup Backend**
```bash
cd backend
#Add .env

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p uploads transcripts logs
```

3. **Setup Frontend**
```bash
cd ../frontend
npm install
```

4. **Get AssemblyAI API Key**
   - Visit https://app.assemblyai.com/
   - Sign up for free account

5. **Start Development Servers**
```bash
# Terminal 1 - Backend
cd backend
python app.py

# Terminal 2 - Frontend  
cd frontend
npm start

# Terminal 3 - Worker (optional)
cd backend
python workers/transcription_worker.py
```

### Option 2: Docker Setup (Production)

```bash
docker-compose up --build
```

## 📁 Complete File Structure

```
maichart-project/
├── 📋 README.md
├── 🐳 docker-compose.yml              # Docker orchestration
│
├── backend/                           # Flask API Server
│   ├── 🔧 app.py                      # Main Flask application
│   ├── ⚙️  config.py                  # Configuration settings
│   ├── 📦 requirements.txt            # Python dependencies
│   ├── 🔐 .env                        # Environment variables
│   ├── 🐳 Dockerfile                  # Backend container config
│   │
│   ├── api/                           # API Routes & Logic
│   │   ├── __init__.py
│   │   ├── 🛣️  routes.py              # All API endpoints
│   │   └── 🔧 utils.py                # API utilities
│   │
│   ├── core/                          # Core Business Logic
│   │   ├── __init__.py
│   │   ├── 🔴 redis_client.py         # Redis operations
│   │   └── 🎵 audio_handler.py        # Audio processing
│   │
│   ├── workers/                       # Background Processing
│   │   ├── __init__.py
│   │   ├── ⚡ base_worker.py          # Worker foundation
│   │   └── 🤖 transcription_worker.py # AI transcription
│   │
│   ├── uploads/                       # Audio file storage
│   ├── transcripts/                   # Transcript storage
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


## 🌐 API Endpoints

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

## 🚀 Deployment Options

### Production with Docker
```bash
docker-compose up -d
```

### Manual Production
1. Build React app: `npm run build`
2. Serve with nginx or Apache
3. Run Flask with gunicorn: `gunicorn app:app`
4. Start transcription worker as systemd service
