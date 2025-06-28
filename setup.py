#!/usr/bin/env python3
"""
Setup script for Audio Processing System
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_python_version():
    """Check if Python version is adequate"""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def check_redis():
    """Check if Redis is available"""
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        client.ping()
        print("✓ Redis connection successful")
        return True
    except ImportError:
        print("! Redis package not installed")
        return False
    except redis.ConnectionError:
        print("! Redis server not running")
        return False

def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ FFmpeg is available")
            return True
        else:
            print("! FFmpeg is not working properly")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("! FFmpeg not found")
        return False

def install_requirements():
    """Install Python requirements"""
    try:
        print("Installing Python requirements...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✓ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("! Failed to install requirements")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ['uploads', 'processed_audio', 'logs']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Created directory: {directory}")

def test_system():
    """Test the complete system"""
    print("\nTesting system components...")
    
    # Test Redis client
    try:
        from core.redis_client import RedisClient
        from config import config
        redis_client = RedisClient(
            host=config['default'].REDIS_HOST,
            port=config['default'].REDIS_PORT,
            db=config['default'].REDIS_DB
        )
        redis_client.ping()
        print("✓ Redis client working")
    except Exception as e:
        print(f"! Redis client error: {e}")
        return False
    
    # Test adding to stream
    try:
        test_data = {
            'test': 'data',
            'timestamp': str(int(time.time()))
        }
        stream_id = redis_client.add_to_stream('test_stream', test_data)
        print(f"✓ Redis stream test successful: {stream_id}")
    except Exception as e:
        print(f"! Redis stream error: {e}")
        return False
    
    return True

def print_instructions():
    """Print setup completion instructions"""
    print("\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)
    print("\nTo start the system:")
    print("\n1. Start Redis (if not already running):")
    print("   redis-server")
    print("\n2. Start the Flask web server:")
    print("   python app.py")
    print("\n3. Start the FFmpeg worker (in another terminal):")
    print("   python workers/ffmpeg_worker.py")
    print("\n4. Open your browser to:")
    print("   http://localhost:5001")
    print("\nAlternatively, use Docker:")
    print("   docker-compose up")
    print("\n" + "="*60)

def main():
    """Main setup function"""
    print("Audio Processing System Setup")
    print("="*40)
    
    # Check prerequisites
    check_python_version()
    
    # Install requirements
    if not install_requirements():
        sys.exit(1)
    
    # Check system dependencies
    redis_ok = check_redis()
    ffmpeg_ok = check_ffmpeg()
    
    if not redis_ok:
        print("\nRedis is required. Please install and start Redis:")
        print("  Ubuntu/Debian: sudo apt install redis-server")
        print("  macOS: brew install redis")
        print("  Windows: Download from https://redis.io/download")
        print("\nOr use Docker: docker run -d -p 6379:6379 redis:alpine")
    
    if not ffmpeg_ok:
        print("\nFFmpeg is required. Please install FFmpeg:")
        print("  Ubuntu/Debian: sudo apt install ffmpeg")
        print("  macOS: brew install ffmpeg")
        print("  Windows: Download from https://ffmpeg.org/download.html")
    
    # Create directories
    create_directories()
    
    # Test system if all dependencies are available
    if redis_ok and ffmpeg_ok:
        if test_system():
            print("✓ System test successful")
        else:
            print("! System test failed")
            sys.exit(1)
    
    # Print instructions
    print_instructions()

if __name__ == "__main__":
    main()