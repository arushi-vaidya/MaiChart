import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent


class Config:
    """Base configuration"""

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

    # File upload settings
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    TRANSCRIPTS_FOLDER = (
        BASE_DIR / "transcripts"
    )  
    LOGS_FOLDER = BASE_DIR / "logs"
    MAX_FILE_SIZE = 90 * 1024 * 1024  # 90MB
    ALLOWED_EXTENSIONS = {"webm", "wav", "mp3", "ogg", "m4a"}

    # Redis streams
    AUDIO_INPUT_STREAM = "audio_input"
    CONSUMER_GROUP = "audio_processors"

    # Worker settings
    WORKER_TIMEOUT = 300  # 5 minutes for transcription
    WORKER_BLOCK_TIME = 1000  # milliseconds
    SESSION_EXPIRE_TIME = 7200  # 2 hours (longer for transcription results)

    @classmethod
    def create_directories(cls):
        """Create necessary directories"""
        directories = [cls.UPLOAD_FOLDER, cls.TRANSCRIPTS_FOLDER, cls.LOGS_FOLDER]
        for directory in directories:
            directory.mkdir(exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "MaiChart2025SecureDevelopmentKey!@#$%^&*ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefg",
    )


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    PROCESSED_FOLDER = os.getenv('PROCESSED_FOLDER', '/app/transcripts')
    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "MaiChart2025AudioProcessingSystem!SecureKey#123$XyZ&*ABCDEFghijk"
    )


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    REDIS_DB = 1  


# Configuration mapping
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
