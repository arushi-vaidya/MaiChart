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

Think of it like a **medical clinic's workflow**:
- **Frontend (Reception)**: Beautiful interface for patients/doctors to interact
- **FastAPI Backend (Medical Records)**: Async API handling requests, managing data, processing files  
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
# Make sure .env file has ASSEMBLYAI_API_KEY set
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

### FastAPI Features:
- **Automatic API Documentation**: Visit `/docs` for Swagger UI
- **Alternative Docs**: Visit `/redoc` for ReDoc interface
- **Type Validation**: Automatic request/response validation
- **Async Support**: Concurrent request handling
- **Performance**: Significantly faster than Flask

## 🔧 Environment Variables

Update your `.env` file with:

```bash
# FastAPI Configuration
FASTAPI_ENV=development
FASTAPI_DEBUG=true
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=5001

# Redis Configuration (Your existing Redis Cloud)
REDIS_HOST=redis-12617.c330.asia-south1-1.gce.redns.redis-cloud.com
REDIS_PORT=12617
REDIS_PASSWORD=BtUjzw407WUWoZueZH5fEb2mdf51oOSC
REDIS_DB=0

# AssemblyAI Configuration
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here

# Security
SECRET_KEY=MaiChart2025SecureDevelopmentKey!@#$%^

# File Upload Settings
MAX_FILE_SIZE=524288000
ALLOWED_EXTENSIONS=webm,wav,mp3,ogg,m4a,flac
```

## 🚀 Key Improvements with FastAPI

### Performance Benefits:
- **Async/Await Support**: Handle multiple requests concurrently
- **Faster Request Processing**: Built on Starlette and Pydantic
- **Automatic Validation**: Request/response validation with type hints
- **Built-in Documentation**: Swagger UI and ReDoc generated automatically

### Developer Experience:
- **Type Hints**: Better IDE support and fewer bugs
- **Automatic API Docs**: Interactive documentation at `/docs`
- **Modern Python**: Uses latest Python features
- **Better Error Handling**: Detailed error responses

### Production Ready:
- **ASGI Server**: Uvicorn for high-performance serving
- **Dependency Injection**: Clean architecture with FastAPI dependencies
- **Middleware Support**: CORS, authentication, logging, etc.
- **Testing Support**: Built-in test client

## 🧪 Testing the API

FastAPI provides automatic interactive documentation:

1. **Start the backend**: `python app.py` or `uvicorn app:app --reload`
2. **Visit Swagger UI**: http://localhost:5001/docs
3. **Try the endpoints**: Interactive API testing interface
4. **Alternative docs**: http://localhost:5001/redoc

## 🚀 Deployment Options

### Production with Docker
```bash
# Set ASSEMBLYAI_API_KEY in .env file
docker-compose up -d
```

### Manual Production with Uvicorn
```bash
# Install dependencies
pip install -r requirements.txt

# Run with Uvicorn (production ASGI server)
uvicorn app:app --host 0.0.0.0 --port 5001 --workers 4

# Or with Gunicorn + Uvicorn workers
pip install gunicorn
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:5001
```

### Frontend Production
```bash
# Build React app
cd frontend
npm run build

# Serve with nginx or any static server
# Docker handles this automatically
```

## 🔄 Migration from Flask

The FastAPI version maintains **100% compatibility** with the existing frontend:

- ✅ **Same API endpoints**: All `/api/*` routes work identically
- ✅ **Same request/response format**: No frontend changes needed
- ✅ **Same file handling**: Upload and download work the same
- ✅ **Same Redis integration**: Workers and data storage unchanged
- ✅ **Same Docker setup**: Just updated compose file

### Key Changes:
- **Flask → FastAPI**: Modern async Python web framework
- **Automatic docs**: Swagger UI at `/docs`
- **Type validation**: Better error handling
- **Performance**: Faster request processing
- **Development**: Better IDE support with type hints

## 📈 Performance Comparison

| Feature | Flask | FastAPI |
|---------|-------|---------|
| Concurrent Requests | Limited | High (async) |
| Request Validation | Manual | Automatic |
| API Documentation | Manual | Automatic |
| Type Safety | Limited | Full |
| Modern Python | Partial | Full |
| ASGI Support | No | Yes |

## 🛠️ Development Commands

```bash
# Start FastAPI with auto-reload
uvicorn app:app --reload --host 0.0.0.0 --port 5001

# Run with specific environment
FASTAPI_ENV=development python app.py

# Start workers
python workers/transcription_worker.py direct
python workers/transcription_worker.py chunk

# Docker development
docker-compose up --build

# View API docs
# http://localhost:5001/docs (Swagger)
# http://localhost:5001/redoc (ReDoc)
```

## 🔍 Monitoring & Debugging

FastAPI provides excellent debugging capabilities:

- **Automatic API docs**: Test endpoints at `/docs`
- **Request validation errors**: Detailed error responses
- **Async debugging**: Better error stack traces
- **Health checks**: `/health` and `/api/health` endpoints
- **System stats**: `/api/stats` for system monitoring

## 📚 Next Steps

1. **Explore API docs**: Visit http://localhost:5001/docs
2. **Test file uploads**: Use the interactive Swagger interface
3. **Monitor processing**: Check real-time status updates
4. **Scale workers**: Add more transcription workers as needed
5. **Deploy to production**: Use Docker compose for easy deployment

## 🤝 Contributing

The FastAPI version maintains the same architecture while providing:
- Better performance
- Modern Python features
- Automatic API documentation
- Type safety
- Easier testing and development