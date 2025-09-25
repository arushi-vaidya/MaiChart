# backend/config.py - FIXED: Proper file size limits
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent


class Config:
    """Base configuration with MongoDB support - FIXED file size limits"""

    # FastAPI settings
    SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-here")
    DEBUG = os.environ.get("FASTAPI_DEBUG", "True").lower() == "true"
    HOST = os.environ.get("FASTAPI_HOST", "0.0.0.0")
    PORT = int(os.environ.get("FASTAPI_PORT", 5001))

    # Redis settings - for real-time operations
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
    REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)
    REDIS_DB = int(os.environ.get("REDIS_DB", 0))

    # MongoDB settings - for persistent storage
    MONGODB_CONNECTION_STRING = os.environ.get(
        "MONGODB_CONNECTION_STRING", 
        "mongodb://localhost:27017"
    )
    MONGODB_DATABASE_NAME = os.environ.get("MONGODB_DATABASE_NAME", "maichart_medical")
    
    # Storage strategy: "redis_only", "mongodb_only", "hybrid" (default)
    STORAGE_STRATEGY = os.environ.get("STORAGE_STRATEGY", "hybrid")
    
    # Enable/disable MongoDB features
    ENABLE_MONGODB = os.environ.get("ENABLE_MONGODB", "true").lower() == "true"
    ENABLE_MEDICAL_ANALYTICS = os.environ.get("ENABLE_MEDICAL_ANALYTICS", "true").lower() == "true"

    # MongoDB Performance Settings
    MONGODB_MAX_POOL_SIZE = int(os.environ.get("MONGODB_MAX_POOL_SIZE", 50))
    MONGODB_TIMEOUT_MS = int(os.environ.get("MONGODB_TIMEOUT_MS", 10000))
    MONGODB_CONNECT_TIMEOUT_MS = int(os.environ.get("MONGODB_CONNECT_TIMEOUT_MS", 10000))
    MONGODB_SOCKET_TIMEOUT_MS = int(os.environ.get("MONGODB_SOCKET_TIMEOUT_MS", 20000))

    # File upload settings - FIXED: Reasonable limits
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    TRANSCRIPTS_FOLDER = BASE_DIR / "transcripts"
    CHUNKS_FOLDER = BASE_DIR / "chunks"
    LOGS_FOLDER = BASE_DIR / "logs"
    MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB default
    ALLOWED_EXTENSIONS = set(os.environ.get("ALLOWED_EXTENSIONS", "webm,wav,mp3,ogg,m4a,flac").split(","))

    # Audio processing settings
    CHUNK_DURATION = int(os.environ.get("CHUNK_DURATION", 180))
    CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 10))
    MAX_CHUNK_SIZE = int(os.environ.get("MAX_CHUNK_SIZE", 10 * 1024 * 1024))
    ENABLE_STREAMING = os.environ.get("ENABLE_STREAMING", "true").lower() == "true"
    STREAMING_CHUNK_SIZE = int(os.environ.get("STREAMING_CHUNK_SIZE", 10))

    # Redis streams
    AUDIO_INPUT_STREAM = os.environ.get("AUDIO_INPUT_STREAM", "audio_input")
    AUDIO_CHUNK_STREAM = os.environ.get("AUDIO_CHUNK_STREAM", "audio_chunks")
    PROGRESS_STREAM = os.environ.get("PROGRESS_STREAM", "progress_updates")
    CONSUMER_GROUP = os.environ.get("CONSUMER_GROUP", "audio_processors")
    CHUNK_CONSUMER_GROUP = os.environ.get("CHUNK_CONSUMER_GROUP", "chunk_processors")

    # Worker settings
    WORKER_TIMEOUT = int(os.environ.get("WORKER_TIMEOUT", 3600))
    CHUNK_WORKER_TIMEOUT = int(os.environ.get("CHUNK_WORKER_TIMEOUT", 120))
    WORKER_BLOCK_TIME = int(os.environ.get("WORKER_BLOCK_TIME", 1000))
    SESSION_EXPIRE_TIME = int(os.environ.get("SESSION_EXPIRE_TIME", 14400))

    # Parallel processing
    MAX_PARALLEL_CHUNKS = int(os.environ.get("MAX_PARALLEL_CHUNKS", 10))
    MAX_WORKERS_PER_SESSION = int(os.environ.get("MAX_WORKERS_PER_SESSION", 8))

    # Cache settings
    CACHE_EXPIRE_TIME = int(os.environ.get("CACHE_EXPIRE_TIME", 3600))
    PROGRESS_CACHE_TIME = int(os.environ.get("PROGRESS_CACHE_TIME", 300))

    # Medical extraction settings
    ENABLE_MEDICAL_EXTRACTION = os.environ.get("ENABLE_MEDICAL_EXTRACTION", "true").lower() == "true"
    MEDICAL_EXTRACTION_TIMEOUT = int(os.environ.get("MEDICAL_EXTRACTION_TIMEOUT", 60))
    MEDICAL_EXTRACTION_CONFIDENCE_THRESHOLD = float(os.environ.get("MEDICAL_EXTRACTION_CONFIDENCE_THRESHOLD", 0.7))

    @classmethod
    def create_directories(cls):
        """Create necessary directories"""
        directories = [
            cls.UPLOAD_FOLDER,
            cls.TRANSCRIPTS_FOLDER,
            cls.CHUNKS_FOLDER,
            cls.LOGS_FOLDER,
        ]
        for directory in directories:
            directory.mkdir(exist_ok=True, parents=True)


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    # Smaller file size for development testing
    MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 25 * 1024 * 1024))  # 25MB for dev
    # Smaller chunks for development
    CHUNK_DURATION = int(os.environ.get("CHUNK_DURATION", 60))
    MAX_PARALLEL_CHUNKS = int(os.environ.get("MAX_PARALLEL_CHUNKS", 2))


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    # Larger file size for production
    MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 100 * 1024 * 1024))  # 100MB for production
    # Optimized for production
    CHUNK_DURATION = int(os.environ.get("CHUNK_DURATION", 180))
    MAX_PARALLEL_CHUNKS = int(os.environ.get("MAX_PARALLEL_CHUNKS", 10))
    MAX_WORKERS_PER_SESSION = int(os.environ.get("MAX_WORKERS_PER_SESSION", 5))


class TestingConfig(Config):
    """Testing configuration"""
    
    DEBUG = True
    # Small file size for testing
    MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 5 * 1024 * 1024))  # 5MB for testing
    # Use in-memory or test databases
    REDIS_DB = int(os.environ.get("REDIS_DB", 1))  # Different Redis DB for testing
    MONGODB_DATABASE_NAME = os.environ.get("MONGODB_DATABASE_NAME", "maichart_medical_test")


# Configuration mapping - FIXED: No circular import
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}