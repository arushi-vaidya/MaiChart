import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent


class Config:
    """Base configuration with enhanced audio processing"""

    # Flask settings
    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "maichart-audio-processing-system-secret-key-2025"
    )
    DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
    PORT = int(os.environ.get("FLASK_PORT", 5001))

    # Redis settings
    REDIS_HOST = os.environ.get(
        "REDIS_HOST", "redis-12617.c330.asia-south1-1.gce.redns.redis-cloud.com"
    )
    REDIS_PORT = int(os.environ.get("REDIS_PORT", 12617))
    REDIS_PASSWORD = os.environ.get(
        "REDIS_PASSWORD", "BtUjzw407WUWoZueZH5fEb2mdf51oOSC"
    )
    REDIS_DB = int(os.environ.get("REDIS_DB", 0))

    # File upload settings - ENHANCED FOR LONG FILES
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    TRANSCRIPTS_FOLDER = BASE_DIR / "transcripts"
    CHUNKS_FOLDER = BASE_DIR / "chunks"  # NEW: For audio chunks
    LOGS_FOLDER = BASE_DIR / "logs"
    MAX_FILE_SIZE = 500 * 1024 * 1024  # INCREASED: 500MB (was 90MB)
    ALLOWED_EXTENSIONS = {"webm", "wav", "mp3", "ogg", "m4a", "flac"}

    # AUDIO CHUNKING SETTINGS - NEW
    CHUNK_DURATION = 120  # 2 minutes per chunk (in seconds)
    CHUNK_OVERLAP = 5  # 5 seconds overlap between chunks
    MAX_CHUNK_SIZE = 25 * 1024 * 1024  # 25MB max chunk size

    # REAL-TIME PROCESSING - NEW
    ENABLE_STREAMING = True
    STREAMING_CHUNK_SIZE = 10  # 10 seconds for real-time chunks

    # Redis streams - ENHANCED
    AUDIO_INPUT_STREAM = "audio_input"
    AUDIO_CHUNK_STREAM = "audio_chunks"  # NEW: For chunk processing
    PROGRESS_STREAM = "progress_updates"  # NEW: For real-time progress
    CONSUMER_GROUP = "audio_processors"
    CHUNK_CONSUMER_GROUP = "chunk_processors"  # NEW

    # Worker settings - ENHANCED
    WORKER_TIMEOUT = 1800  # INCREASED: 30 minutes (was 5 minutes)
    CHUNK_WORKER_TIMEOUT = 300  # 5 minutes per chunk
    WORKER_BLOCK_TIME = 1000
    SESSION_EXPIRE_TIME = 14400  # INCREASED: 4 hours (was 2 hours)

    # PARALLEL PROCESSING - NEW
    MAX_PARALLEL_CHUNKS = 5  # Process 5 chunks simultaneously
    MAX_WORKERS_PER_SESSION = 3  # Max workers per session

    # REDIS CACHING - NEW
    CACHE_EXPIRE_TIME = 3600  # 1 hour cache
    PROGRESS_CACHE_TIME = 300  # 5 minutes for progress updates

    @classmethod
    def create_directories(cls):
        """Create necessary directories"""
        directories = [
            cls.UPLOAD_FOLDER,
            cls.TRANSCRIPTS_FOLDER,
            cls.CHUNKS_FOLDER,  # NEW
            cls.LOGS_FOLDER,
        ]
        for directory in directories:
            directory.mkdir(exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    # Smaller chunks for development
    CHUNK_DURATION = 60  # 1 minute chunks
    MAX_PARALLEL_CHUNKS = 2


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    # Optimized for production
    CHUNK_DURATION = 180  # 3 minute chunks
    MAX_PARALLEL_CHUNKS = 10
    MAX_WORKERS_PER_SESSION = 5


# Configuration mapping
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": Config,
    "default": DevelopmentConfig,
}
