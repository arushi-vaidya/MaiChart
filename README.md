# Audio Processing System

A complete audio capture and processing system that records audio in the browser, streams it to a backend, and converts it to WAV format using FFmpeg workers.

## Architecture

```
Browser (MediaRecorder) → Flask API → Redis Stream → FFmpeg Worker → WAV File
```

## Features

- **Modern Frontend**: Clean, responsive audio recorder with real-time feedback
- **Scalable Backend**: Flask API with Redis streaming for worker coordination
- **Audio Processing**: FFmpeg-powered conversion to high-quality WAV format
- **Modular Design**: Separate files for easy debugging and maintenance
- **Docker Support**: Complete containerized deployment

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
mkdir audio-processing-system && cd audio-processing-system

# Add all the files from the artifacts above

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

## Usage

1. **Record Audio**: Click the red record button to start recording
2. **Stop Recording**: Click the button again to stop and upload
3. **Monitor Progress**: Watch the status updates in real-time
4. **Access Results**: Processed WAV files are saved in `processed_audio/`

## API Endpoints

### `POST /api/upload_audio`
Upload audio file for processing
- **Body**: FormData with `audio` file and `timestamp`
- **Response**: Session ID and processing details

### `GET /api/status/<session_id>`
Check processing status
- **Response**: Current status, progress, and results

### `GET /api/download/<session_id>`
Download processed WAV file
- **Response**: WAV file download

### `GET /api/health`
System health check
- **Response**: Service status and Redis connectivity

## Configuration

### Environment Variables

- `REDIS_HOST`: Redis server host (default: localhost)
- `REDIS_PORT`: Redis server port (default: 6379)
- `UPLOAD_FOLDER`: Directory for uploaded files (default: uploads)
- `OUTPUT_FOLDER`: Directory for processed files (default: processed_audio)

### Audio Settings

The system is configured for:
- **Input**: WebM/Opus from browser
- **Output**: WAV (PCM 16-bit, 44.1kHz, mono)
- **Max File Size**: 50MB
- **Supported Formats**: WebM, WAV, MP3, OGG, M4A

## Development Timeline

### June 28-30: Basic Infrastructure ✅
- [x] MediaRecorder frontend with modern UI
- [x] Flask backend with file upload
- [x] Redis stream integration
- [x] Basic error handling and status updates

### July 1-3: Stream Processing ✅
- [x] Redis Stream audio_input setup
- [x] FFmpeg worker with conversion logic
- [x] Session status tracking
- [x] End-to-end message flow

### July 4: Testing & Optimization ✅
- [x] Complete end-to-end test
- [x] Docker containerization
- [x] System monitoring and health checks
- [x] Documentation and setup automation

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

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   # Start Redis
   redis-server
   # Or use Docker
   docker run -d -p 6379:6379 redis:alpine
   ```

2. **FFmpeg Not Found**
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg
   # macOS
   brew install ffmpeg
   ```

3. **Microphone Access Denied**
   - Ensure HTTPS or localhost
   - Check browser permissions
   - Try different browser

4. **Upload Fails**
   - Check file size limits
   - Verify network connectivity
   - Check server logs

### Debug Mode

Enable detailed logging:

```bash
export FLASK_DEBUG=1
python app.py
```

## Performance

- **Concurrent Processing**: Multiple workers can run simultaneously
- **Memory Efficient**: Streaming architecture with minimal memory usage
- **Scalable**: Redis-based coordination supports horizontal scaling
- **Fast Conversion**: FFmpeg optimized for audio processing

## License

Apache License 2.0 - see LICENSE file for details

---

**Ready to capture and process audio!** 🎵