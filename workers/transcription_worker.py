import os
import subprocess
import sys
import logging
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)

class TranscriptionWorker(BaseWorker):
    """Worker for transcribing audio files"""
    
    def __init__(self, config_name='default'):
        super().__init__('transcription_worker', config_name)
        self.output_dir = self.config.TRANSCRIPTS_FOLDER  
        
        # Ensure output directory exists
        self.output_dir.mkdir(exist_ok=True)
        
        logger.info(f"Transcription Worker initialized")
        logger.info(f"Output directory: {self.output_dir}")
    
    def check_dependencies(self) -> bool:
        """Check if FFmpeg is available (needed for audio processing)"""
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
    
    def transcribe_audio(self, input_path: str, output_path: str) -> bool:
        """Transcribe audio file (placeholder implementation)"""
        try:
            logger.info(f"Transcribing {input_path} to {output_path}")
            
            # For now, create a placeholder transcript
            
            # Get file info
            file_size = os.path.getsize(input_path)
            
            # Create basic transcript data
            transcript_data = {
                "transcript": {
                    "text": "This is a placeholder transcript.",
                    "confidence": 0.95,
                    "word_count": 12,
                    "language": "en"
                },
                "metadata": {
                    "original_file": os.path.basename(input_path),
                    "file_size": file_size,
                    "processed_at": datetime.utcnow().isoformat(),
                    "processing_method": "placeholder"
                }
            }
            
            # Save transcript as JSON
            import json
            with open(output_path, 'w') as f:
                json.dump(transcript_data, f, indent=2)
            
            logger.info(f"Successfully created transcript at {output_path}")
            return True
                
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
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
                'step': 'analyzing_audio',
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
            output_filename = f"{base_name}_transcript.json"
            output_path = self.output_dir / output_filename
            
            logger.info(f"Processing session {session_id}: {filename} -> {output_filename}")
            
            # Update status
            self.update_session_status(session_id, {
                'status': 'processing',
                'step': 'processing_audio'
            })
            
            # Transcribe audio
            success = self.transcribe_audio(filepath, str(output_path))
            
            if success:
                # Update status
                self.update_session_status(session_id, {
                    'status': 'processing',
                    'step': 'saving_transcript'
                })
                
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
                    'error': 'Audio transcription failed',
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
        worker = TranscriptionWorker()
        return worker.run()
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())