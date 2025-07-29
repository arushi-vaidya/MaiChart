#!/usr/bin/env python3
"""
Transcription Worker using AssemblyAI with environment variables
"""

import os
import sys
import logging
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from workers.base_worker import BaseWorker

# Import AssemblyAI
try:
    import assemblyai as aai
except ImportError:
    print("AssemblyAI library not installed. Please run: pip install assemblyai")
    sys.exit(1)

logger = logging.getLogger(__name__)


class TranscriptionWorker(BaseWorker):
    """Worker for transcribing audio files using AssemblyAI"""
    
    def __init__(self, config_name='default'):
        super().__init__('transcription_worker', config_name)
        
        # Get AssemblyAI API key from environment
        self.api_key = os.getenv('ASSEMBLYAI_API_KEY')
        
        if not self.api_key:
            raise ValueError("ASSEMBLYAI_API_KEY environment variable must be set")
        
        # Configure AssemblyAI
        aai.settings.api_key = self.api_key
        logger.info(f"✅ AssemblyAI API key configured: {self.api_key[:8]}...{self.api_key[-8:]}")
        
        self.transcription_config = aai.TranscriptionConfig(
            punctuate=True,
            format_text=True,
            # Add medical term boosting for better accuracy
            word_boost=[
                "medical", "patient", "diagnosis", "treatment", "medication",
                "symptoms", "examination", "prescription", "therapy", "clinical",
                "doctor", "physician", "nurse", "hospital", "clinic", "surgery",
                "procedure", "vital", "signs", "blood", "pressure", "heart", "rate"
            ]
        )
        
        # Initialize transcriber
        self.transcriber = aai.Transcriber(config=self.transcription_config)
        
        # Ensure transcripts directory exists
        self.transcripts_dir = self.config.TRANSCRIPTS_FOLDER
        self.transcripts_dir.mkdir(exist_ok=True)
        
        logger.info("✅ Transcription Worker initialized successfully with medical optimization")
    
    def check_dependencies(self) -> bool:
        """Check if AssemblyAI is available and configured"""
        try:
            logger.info("🔍 Checking AssemblyAI dependencies...")
            
            # Check if AssemblyAI library is properly imported
            if not hasattr(aai, 'TranscriptionConfig') or not hasattr(aai, 'Transcriber'):
                logger.error("❌ AssemblyAI library is not properly configured")
                return False
            
            # Check if API key is set
            if not self.api_key:
                logger.error("❌ ASSEMBLYAI_API_KEY environment variable is not set")
                return False
            
            logger.info("✅ AssemblyAI dependencies check passed")
            return True
                
        except Exception as e:
            logger.error(f"❌ AssemblyAI dependency check failed: {e}")
            return False
    
    def transcribe_audio(self, audio_file_path: str) -> dict:
        """Transcribe audio file using AssemblyAI"""
        try:
            logger.info(f"🎵 Starting transcription of {audio_file_path}")
            
            # Check if file exists
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
            
            # Check file size
            file_size = os.path.getsize(audio_file_path)
            logger.info(f"📊 File size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")
            
            if file_size == 0:
                raise ValueError("Audio file is empty")
            
            # Start transcription
            logger.info("🤖 Calling AssemblyAI API with medical optimization...")
            transcript = self.transcriber.transcribe(audio_file_path)
            logger.info(f"📡 AssemblyAI response status: {transcript.status}")
            
            # Check for errors
            if transcript.status == "error":
                error_msg = getattr(transcript, 'error', 'Unknown error')
                logger.error(f"❌ Transcription failed: {error_msg}")
                raise RuntimeError(f"Transcription failed: {error_msg}")
            
            # Check if we have text
            if not transcript.text:
                logger.warning("⚠️ No speech detected in audio")
                return {
                    'text': '',
                    'confidence': 0.0,
                    'duration': getattr(transcript, 'audio_duration', 0),
                    'status': 'completed',
                    'warning': 'No speech detected in audio'
                }
            
            # Extract results
            result = {
                'text': transcript.text,
                'confidence': getattr(transcript, 'confidence', 0.0),
                'duration': getattr(transcript, 'audio_duration', 0),
                'words': len(transcript.text.split()) if transcript.text else 0,
                'status': 'completed'
            }
            
            logger.info(f"✅ Transcription completed successfully!")
            logger.info(f"📝 Text length: {len(transcript.text)} characters")
            logger.info(f"📊 Word count: {result['words']} words")
            logger.info(f"🎯 Confidence: {result['confidence']:.2f}")
            logger.info(f"⏱️ Duration: {result['duration']:.1f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error during transcription: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                'status': 'error',
                'error': str(e),
                'text': '',
                'confidence': 0.0
            }
    
    def save_transcript(self, session_id: str, transcript_data: dict) -> str:
        """Save transcript to file with medical formatting"""
        try:
            transcript_filename = f"{session_id}_transcript.txt"
            transcript_path = self.transcripts_dir / transcript_filename
            
            # Create medical transcript content
            content = f"Medical Transcript for Session: {session_id}\n"
            content += f"Generated: {datetime.utcnow().isoformat()}Z\n"
            content += f"Confidence Score: {transcript_data.get('confidence', 0):.3f}\n"
            content += f"Word Count: {transcript_data.get('words', 0)}\n"
            content += f"Audio Duration: {transcript_data.get('duration', 0):.2f} seconds\n"
            
            # Add warning if present
            if transcript_data.get('warning'):
                content += f"Note: {transcript_data['warning']}\n"
            
            content += "=" * 60 + "\n\n"
            content += transcript_data.get('text', 'No transcript available')
            content += "\n\n" + "=" * 60 + "\n"
            content += "Generated by MaiChart Medical Transcription System\n"
            
            # Write to file
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"💾 Medical transcript saved to {transcript_path}")
            return str(transcript_path)
            
        except Exception as e:
            logger.error(f"❌ Error saving transcript: {e}")
            return ""
    
    def process_message(self, message_data: dict) -> bool:
        """Process a single audio message for transcription"""
        try:
            session_id = message_data.get('session_id')
            filepath = message_data.get('filepath')
            filename = message_data.get('filename')
            
            logger.info(f"🎯 Processing session {session_id}")
            logger.info(f"📁 File: {filename}")
            logger.info(f"📍 Path: {filepath}")
            
            if not all([session_id, filepath, filename]):
                logger.error("❌ Missing required fields in message")
                return False
            
            # Update status to processing
            logger.info("📝 Updating status to processing...")
            self.update_session_status(session_id, {
                'status': 'processing',
                'step': 'analyzing_audio',
                'processing_started_at': datetime.utcnow().isoformat()
            })
            
            # Check if input file exists
            if not os.path.exists(filepath):
                logger.error(f"❌ Input file not found: {filepath}")
                self.update_session_status(session_id, {
                    'status': 'error',
                    'error': 'Input file not found'
                })
                return False
            
            # Check file size
            file_size = os.path.getsize(filepath)
            logger.info(f"📊 File size: {file_size} bytes")
            
            if file_size == 0:
                logger.error("❌ Input file is empty")
                self.update_session_status(session_id, {
                    'status': 'error',
                    'error': 'Input file is empty'
                })
                return False
            
            # Update status to transcribing
            logger.info("🤖 Updating status to transcribing...")
            self.update_session_status(session_id, {
                'status': 'processing',
                'step': 'processing_audio',
            })
            
            # Transcribe audio
            logger.info("🔄 Starting AssemblyAI medical transcription...")
            transcript_result = self.transcribe_audio(filepath)
            logger.info(f"📡 Transcription result status: {transcript_result['status']}")
            
            if transcript_result['status'] == 'completed':
                # Update status to saving
                logger.info("💾 Saving medical transcript...")
                self.update_session_status(session_id, {
                    'status': 'processing',
                    'step': 'saving_transcript',
                })
                
                # Save transcript to file
                transcript_path = self.save_transcript(session_id, transcript_result)
                logger.info(f"📄 Medical transcript saved to: {transcript_path}")
                
                # Update status to completed
                status_update = {
                    'status': 'completed',
                    'transcript_text': transcript_result['text'],
                    'transcript_confidence': transcript_result['confidence'],
                    'transcript_words': transcript_result.get('words', 0),
                    'transcript_path': transcript_path,
                    'processing_completed_at': datetime.utcnow().isoformat()
                }
                
                # Add duration if available
                if transcript_result.get('duration'):
                    status_update['audio_duration'] = transcript_result['duration']
                
                # Add warning if present
                if transcript_result.get('warning'):
                    status_update['warning'] = transcript_result['warning']
                
                logger.info("✅ Updating final status to completed...")
                self.update_session_status(session_id, status_update)
                
                logger.info(f"🎉 Successfully transcribed medical session {session_id}")
                logger.info(f"📊 Final stats: {len(transcript_result['text'])} chars, {transcript_result.get('words', 0)} words, {transcript_result['confidence']:.3f} confidence")
                return True
            else:
                # Update status to error
                error_msg = transcript_result.get('error', 'Transcription failed')
                logger.error(f"❌ Transcription failed: {error_msg}")
                
                self.update_session_status(session_id, {
                    'status': 'error',
                    'error': error_msg,
                    'processing_failed_at': datetime.utcnow().isoformat()
                })
                
                logger.error(f"💥 Failed to transcribe session {session_id}: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"💥 Error processing message: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Update status to error if we have session_id
            session_id = message_data.get('session_id')
            if session_id:
                self.handle_message_error(session_id, e)
            
            return False


def main():
    """Main entry point"""
    try:
        logger.info("🚀 Starting MaiChart Transcription Worker...")
        
        # Validate environment variables
        if not os.getenv('ASSEMBLYAI_API_KEY'):
            raise ValueError("ASSEMBLYAI_API_KEY environment variable must be set")
        
        worker = TranscriptionWorker()
        logger.info("✅ Medical transcription worker created successfully")
        return worker.run()
    except Exception as e:
        logger.error(f"💥 Failed to start transcription worker: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())