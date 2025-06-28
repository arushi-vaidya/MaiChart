import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

class Config:
    """Base configuration"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 5001))
    
    # Redis settings
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    
    # File upload settings
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    PROCESSED_FOLDER = BASE_DIR / 'processed_audio'
    LOGS_FOLDER = BASE_DIR / 'logs'
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'webm', 'wav', 'mp3', 'ogg', 'm4a'}
    
    # Audio processing settings
    OUTPUT_SAMPLE_RATE = 44100
    OUTPUT_CHANNELS = 1  # Mono
    OUTPUT_FORMAT = 'pcm_s16le'
    
    # Redis streams
    AUDIO_INPUT_STREAM = 'audio_input'
    CONSUMER_GROUP = 'audio_processors'
    
    # Worker settings
    WORKER_TIMEOUT = 60  # seconds
    WORKER_BLOCK_TIME = 1000  # milliseconds
    SESSION_EXPIRE_TIME = 3600  # 1 hour
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories"""
        directories = [cls.UPLOAD_FOLDER, cls.PROCESSED_FOLDER, cls.LOGS_FOLDER]
        for directory in directories:
            directory.mkdir(exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    @property
    def SECRET_KEY(self):
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            raise ValueError("SECRET_KEY environment variable must be set in production")
        return secret_key

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    REDIS_DB = 1  # Use different Redis DB for testing

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}