import os
import subprocess
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)

class FFmpegWorker(BaseWorker):
    """Worker for converting audio files using FFmpeg"""
    
    def __init__(self, config_name='default'):
        super().__init__('ffmpeg_worker', config_name)
        self.output_dir = self.config.PROCESSED_FOLDER
        
        # Ensure output directory exists
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info(f"FFmpeg Worker initialized")
        logger.info(f"Output directory: {self.output_dir}")
    
    def check_dependencies(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info("FFmpeg is available")
                return True
            else:
                logger.error("FFmpeg is not working properly")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"FFmpeg not found or not working: {e}")
            return False
    
    def convert_audio_to_wav(self, input_path: str, output_path: str) -> bool:
        """Convert audio file to WAV format using FFmpeg"""
        try:
            logger.info(f"Converting {input_path} to {output_path}")
            
            # FFmpeg command to convert to WAV
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-acodec', self.config.OUTPUT_FORMAT,
                '-ar', str(self.config.OUTPUT_SAMPLE_RATE),
                '-ac', str(self.config.OUTPUT_CHANNELS),
                '-y',  # Overwrite output file
                output_path
            ]
            
            # Run FFmpeg conversion
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully converted to {output_path}")
                
                # Verify output file exists and has content
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    return True
                else:
                    logger.error("Output file is empty or doesn't exist")
                    return False
            else:
                logger.error(f"FFmpeg conversion failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg conversion timed out")
            return False
        except Exception as e:
            logger.error(f"Error during conversion: {e}")
            return False
    
    def process_message(self, message_data: dict) -> bool:
        """Process a single audio message"""
        try:
            session_id = message_data.get('session_id')
            filepath = message_data.get('filepath')
            filename = message_data.get('filename')
            
            if not all([session_id, filepath, filename]):
                logger.error("Missing required fields in message")
                return False
            
            # Update status to processing
            self.update_session_status(session_id, {
                'status': 'processing',
                'processing_started_at': datetime.utcnow().isoformat()
            })
            
            # Check if input file exists
            if not os.path.exists(filepath):
                logger.error(f"Input file not found: {filepath}")
                self.update_session_status(session_id, {
                    'status': 'error',
                    'error': 'Input file not found'
                })
                return False
            
            # Generate output filename
            base_name = Path(filename).stem
            output_filename = f"{base_name}.wav"
            output_path = self.output_dir / output_filename
            
            logger.info(f"Processing session {session_id}: {filename} -> {output_filename}")
            
            # Convert to WAV
            success = self.convert_audio_to_wav(filepath, str(output_path))
            
            if success:
                # Get output file info
                output_size = output_path.stat().st_size
                
                # Update status to completed
                self.update_session_status(session_id, {
                    'status': 'completed',
                    'output_path': str(output_path),
                    'output_filename': output_filename,
                    'output_size': output_size,
                    'processing_completed_at': datetime.utcnow().isoformat()
                })
                
                logger.info(f"Successfully processed session {session_id}")
                return True
            else:
                # Update status to error
                self.update_session_status(session_id, {
                    'status': 'error',
                    'error': 'Audio conversion failed',
                    'processing_failed_at': datetime.utcnow().isoformat()
                })
                
                logger.error(f"Failed to process session {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            
            # Update status to error if we have session_id
            session_id = message_data.get('session_id')
            if session_id:
                self.handle_message_error(session_id, e)
            
            return False

def main():
    """Main entry point"""
    try:
        worker = FFmpegWorker()
        return worker.run()
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())