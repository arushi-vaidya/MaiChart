# Maichart

A complete audio capture and transcription system that records audio in the browser, streams it to a backend, and converts it to text using AssemblyAI's advanced speech recognition.

## Architecture

```
Browser (MediaRecorder) → Flask API → Redis Stream → AssemblyAI Worker → Medical Transcript
```

## Features

- **🎤 Browser Audio Recording**: Direct recording from microphone using WebMediaRecorder
- **📁 File Upload Support**: Upload existing audio files in multiple formats
- **🤖 AI-Powered Transcription**: High-accuracy transcription using AssemblyAI's best speech model
- **🏥 Medical Focus**: Optimized for medical voice notes and terminology
- **⚡ Real-time Processing**: Redis-based queue system for scalable processing
- **📊 Confidence Scoring**: Transcription confidence levels for quality assessment
- **💾 Persistent Storage**: Transcripts saved as text files with metadata

## File Structure

```
audio-processing-system/
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies (includes assemblyai)
├── docker-compose.yml          # Docker deployment
├── Dockerfile                  # Container configuration
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
│   └── transcription_worker.py # AssemblyAI transcription processor
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
├── transcripts/               # Transcribed text files (created at runtime)
└── logs/                      # Application logs (created at runtime)
```

## Quick Start

### Docker (Recommended)

```bash
# Clone or create the project directory
# Start the system
docker-compose up
```

The system will be available at `http://localhost:5001`

## License

Apache License 2.0 - See LICENSE file for details.