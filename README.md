# Audio Processing System

A complete audio capture and processing system that records audio in the browser, streams it to a backend, and converts it to WAV format using FFmpeg workers.

## Architecture

```
Browser (MediaRecorder) → Flask API → Redis Stream → FFmpeg Worker → WAV File
```

## File Structure

```
audio-processing-system/
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Docker deployment
├── Dockerfile                  # Container configuration
├── setup.py                   # Setup script
├── test_system.py             # End-to-end testing
├── README.md                  # Documentation
│
├── templates/                  # Flask templates
│   └── index.html             # Main audio recorder page
│
├── static/                     # Static assets
│   ├── css/
│   │   └── style.css          # Styles for audio recorder
│   └── js/
│       └── audio-recorder.js   # Frontend JavaScript
│
├── workers/                    # Background workers
│   ├── __init__.py            # Worker package
│   ├── base_worker.py         # Base worker class
│   └── ffmpeg_worker.py       # FFmpeg audio processor
│
├── core/                       # Core application logic
│   ├── __init__.py            # Core package
│   ├── redis_client.py        # Redis operations
│   └── audio_handler.py       # Audio processing logic
│
├── api/                        # API routes
│   ├── __init__.py            # API package
│   ├── routes.py              # API endpoints
│   └── utils.py               # API utilities
│
├── uploads/                    # Uploaded files (created at runtime)
├── processed_audio/           # Processed WAV files (created at runtime)
└── logs/                      # Application logs (created at runtime)
```

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone or create the project directory
# Start the system
docker-compose up
```

The system will be available at `http://localhost:5001`

### Option 2: Manual Installation

1. **Install Dependencies**:
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt
   
   # Install system dependencies
   sudo apt install redis-server ffmpeg  # Ubuntu/Debian
   # brew install redis ffmpeg           # macOS
   ```

2. **Start Redis**:
   ```bash
   redis-server
   ```

3. **Run Setup**:
   ```bash
   python setup.py
   ```

4. **Start Services**:
   ```bash
   # Terminal 1: Start Flask app
   python app.py
   
   # Terminal 2: Start FFmpeg worker
   python workers/ffmpeg_worker.py
   ```

5. **Open Browser**:
   Navigate to `http://localhost:5001`

### Audio Settings

The system is configured for:
- **Input**: WebM/Opus from browser
- **Output**: WAV (PCM 16-bit, 44.1kHz, mono)
- **Max File Size**: 50MB
- **Supported Formats**: WebM, WAV, MP3, OGG, M4A


## Testing

Run the complete test suite:

```bash
python test_system.py
```

This will test:
- ✅ Health endpoints
- ✅ Redis connectivity
- ✅ File upload functionality
- ✅ Audio processing pipeline
- ✅ Status monitoring


## License

Apache License 2.0 - see LICENSE file for details

---

**Ready to capture and process audio!** 🎵
