#!/usr/bin/env python3
"""
End-to-end test script for the audio processing system
"""

import time
import requests
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from core.redis_client import RedisClient
from config import config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemTester:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.config = config['default']
        self.redis_client = RedisClient(
            host=self.config.REDIS_HOST,
            port=self.config.REDIS_PORT,
            db=self.config.REDIS_DB
        )
        
    def test_health_endpoint(self):
        """Test the health check endpoint"""
        try:
            logger.info("Testing health endpoint...")
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✓ Health check passed: {data['status']}")
                return True
            else:
                logger.error(f"! Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"! Health check error: {e}")
            return False
    
    def test_redis_connection(self):
        """Test Redis connection and basic operations"""
        try:
            logger.info("Testing Redis connection...")
            
            # Test ping
            if not self.redis_client.ping():
                logger.error("! Redis ping failed")
                return False
            
            # Test stream operations
            test_data = {
                'test_session': 'test123',
                'test_data': 'hello world',
                'timestamp': str(int(time.time()))
            }
            
            stream_id = self.redis_client.add_to_stream('test_stream', test_data)
            logger.info(f"✓ Added test data to stream: {stream_id}")
            
            # Test status operations
            self.redis_client.set_session_status('test123', {
                'status': 'testing',
                'message': 'This is a test'
            })
            
            status = self.redis_client.get_session_status('test123')
            if status and status.get('status') == 'testing':
                logger.info("✓ Session status operations working")
                return True
            else:
                logger.error("! Session status operations failed")
                return False
                
        except Exception as e:
            logger.error(f"! Redis test error: {e}")
            return False
    
    def create_test_audio_file(self, filename="test_audio.wav"):
        """Create a simple test audio file using FFmpeg"""
        try:
            import subprocess
            
            # Generate a 2-second sine wave at 440Hz
            cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2',
                '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '1',
                '-y', filename
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and os.path.exists(filename):
                logger.info(f"✓ Created test audio file: {filename}")
                return filename
            else:
                logger.error("! Failed to create test audio file")
                return None
                
        except Exception as e:
            logger.error(f"! Error creating test audio: {e}")
            return None
    
    def test_file_upload(self, test_file):
        """Test file upload functionality"""
        try:
            logger.info("Testing file upload...")
            
            with open(test_file, 'rb') as f:
                files = {'audio': (test_file, f, 'audio/wav')}
                data = {'timestamp': str(int(time.time() * 1000))}
                
                response = requests.post(
                    f"{self.base_url}/api/upload_audio",
                    files=files,
                    data=data,
                    timeout=30
                )
            
            if response.status_code == 200:
                result = response.json()
                session_id = result.get('id')
                logger.info(f"✓ File uploaded successfully. Session ID: {session_id}")
                return session_id
            else:
                logger.error(f"! Upload failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"! Upload test error: {e}")
            return None
    
    def test_status_monitoring(self, session_id, timeout=30):
        """Monitor processing status"""
        try:
            logger.info(f"Monitoring status for session: {session_id}")
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                response = requests.get(f"{self.base_url}/api/status/{session_id}", timeout=10)
                
                if response.status_code == 200:
                    status_data = response.json()
                    status = status_data.get('status', 'unknown')
                    
                    logger.info(f"Status: {status}")
                    
                    if status == 'completed':
                        output_path = status_data.get('output_path')
                        if output_path and os.path.exists(output_path):
                            logger.info(f"✓ Processing completed successfully: {output_path}")
                            return True
                        else:
                            logger.error("! Output file not found")
                            return False
                    
                    elif status == 'error':
                        error_msg = status_data.get('error', 'Unknown error')
                        logger.error(f"! Processing failed: {error_msg}")
                        return False
                    
                    # Wait before checking again
                    time.sleep(2)
                
                else:
                    logger.error(f"! Status check failed: {response.status_code}")
                    return False
            
            logger.error("! Processing timed out")
            return False
            
        except Exception as e:
            logger.error(f"! Status monitoring error: {e}")
            return False
    
    def cleanup_test_files(self, files):
        """Clean up test files"""
        for file_path in files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up: {file_path}")
            except Exception as e:
                logger.warning(f"Could not clean up {file_path}: {e}")
    
    def run_full_test(self):
        """Run the complete end-to-end test"""
        logger.info("Starting end-to-end system test...")
        logger.info("="*50)
        
        test_files = []
        
        try:
            # Test 1: Health check
            if not self.test_health_endpoint():
                return False
            
            # Test 2: Redis connection
            if not self.test_redis_connection():
                return False
            
            # Test 3: Create test audio file
            test_file = self.create_test_audio_file()
            if not test_file:
                return False
            test_files.append(test_file)
            
            # Test 4: Upload file
            session_id = self.test_file_upload(test_file)
            if not session_id:
                return False
            
            # Test 5: Monitor processing
            if not self.test_status_monitoring(session_id):
                return False
            
            logger.info("="*50)
            logger.info("✓ ALL TESTS PASSED! System is working correctly.")
            return True
            
        except Exception as e:
            logger.error(f"! Test suite error: {e}")
            return False
        
        finally:
            # Cleanup
            self.cleanup_test_files(test_files)

def main():
    """Main test function"""
    tester = SystemTester()
    
    success = tester.run_full_test()
    
    if success:
        print("\n🎉 System test completed successfully!")
        print("Your audio processing system is ready to use.")
    else:
        print("\n❌ System test failed!")
        print("Please check the logs above and fix any issues.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())