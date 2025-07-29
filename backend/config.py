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
