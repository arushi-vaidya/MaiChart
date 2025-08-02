#!/usr/bin/env python3
"""
Enhanced Transcription Worker with Parallel Chunk Processing for FastAPI
Think of this as a "Smart Factory" with multiple assembly lines processing different parts simultaneously
"""

import os
import sys
import logging
import time
import threading
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


class EnhancedTranscriptionWorker(BaseWorker):
    """
    Enhanced worker that can handle both direct and chunked transcription
    Like a factory supervisor managing multiple assembly lines
    Updated for FastAPI compatibility
    """

    def __init__(self, config_name="default", worker_type="direct"):
        # Determine worker name based on type
        worker_name = f"transcription_worker_{worker_type}"
        super().__init__(worker_name, config_name)

        self.worker_type = worker_type  # 'direct' or 'chunk'

        # Get AssemblyAI API key from environment
        self.api_key = os.getenv("ASSEMBLYAI_API_KEY")

        if not self.api_key:
            raise ValueError("ASSEMBLYAI_API_KEY environment variable must be set")

        # Configure AssemblyAI with enhanced settings
        aai.settings.api_key = self.api_key
        logger.info(
            f"✅ AssemblyAI API key configured: {self.api_key[:8]}...{self.api_key[-8:]}"
        )

        # Enhanced transcription config for medical content
        self.transcription_config = aai.TranscriptionConfig(
            punctuate=True,
            format_text=True,
            # Enhanced medical term boosting
            word_boost=[
                "medical",
                "patient",
                "diagnosis",
                "treatment",
                "medication",
                "prescription",
                "symptoms",
                "examination",
                "therapy",
                "clinical",
                "procedure",
                "surgery",
                "doctor",
                "physician",
                "nurse",
                "hospital",
                "clinic",
                "emergency",
                "vital",
                "signs",
                "blood",
                "pressure",
                "heart",
                "rate",
                "temperature",
                "pain",
                "chronic",
                "acute",
                "condition",
                "disease",
                "infection",
                "antibiotics",
                "dosage",
                "milligrams",
                "tablets",
                "injection",
                "allergies",
                "reaction",
                "side",
                "effects",
                "follow",
                "up",
            ],
            boost_param="high",  # Enhanced boosting
        )

        # Initialize transcriber
        self.transcriber = aai.Transcriber(config=self.transcription_config)

        # Enhanced streams configuration
        if self.worker_type == "chunk":
            self.stream_name = self.config.AUDIO_CHUNK_STREAM
            self.consumer_group = self.config.CHUNK_CONSUMER_GROUP
        else:
            self.stream_name = self.config.AUDIO_INPUT_STREAM
            self.consumer_group = self.config.CONSUMER_GROUP

        # Ensure transcripts directory exists
        self.transcripts_dir = self.config.TRANSCRIPTS_FOLDER
        self.transcripts_dir.mkdir(exist_ok=True)

        # Completion checker thread for chunk workers
        self.completion_checker_running = False
        self.completion_checker_thread = None

        logger.info(f"✅ Enhanced {worker_name} initialized with medical optimization")

    def check_dependencies(self) -> bool:
        """Check if AssemblyAI is available and configured"""
        try:
            logger.info("🔍 Checking AssemblyAI dependencies...")

            # Check if AssemblyAI library is properly imported
            if not hasattr(aai, "TranscriptionConfig") or not hasattr(
                aai, "Transcriber"
            ):
                logger.error("❌ AssemblyAI library is not properly configured")
                return False

            # Check if API key is set
            if not self.api_key:
                logger.error("❌ ASSEMBLYAI_API_KEY environment variable is not set")
                return False

            # Test API connection with a quick call
            try:
                # This is a lightweight test to verify API access
                logger.info("🔌 Testing API connection...")
                test_config = aai.TranscriptionConfig()
                logger.info("✅ API connection test passed")
            except Exception as e:
                logger.error(f"❌ API connection test failed: {e}")
                return False

            logger.info("✅ All dependencies check passed")
            return True

        except Exception as e:
            logger.error(f"❌ Dependency check failed: {e}")
            return False

    def run(self):
        """Enhanced run method with completion checker for chunk workers"""
        try:
            result = super().run()
            return result

        except Exception as e:
            logger.error(f"❌ Error in enhanced worker run: {e}")
            if self.worker_type == "chunk":
                self.stop_completion_checker()
            return 1

    def start_completion_checker(self):
        """Start background thread to check for completed chunked sessions"""
        if self.completion_checker_running:
            return

        self.completion_checker_running = True
        self.completion_checker_thread = threading.Thread(
            target=self._completion_checker_loop, daemon=True
        )
        self.completion_checker_thread.start()
        logger.info("🔄 Started completion checker thread")

    def stop_completion_checker(self):
        """Stop the completion checker thread"""
        self.completion_checker_running = False
        if self.completion_checker_thread:
            self.completion_checker_thread.join(timeout=5)
        logger.info("⏹️ Stopped completion checker thread")

    def _completion_checker_loop(self):
        """Background loop to check for completed chunked sessions"""
        from core.audio_handler import AudioHandler

        while self.completion_checker_running:
            try:
                # Check for sessions that might be ready for merging
                # Look for sessions with chunked processing strategy
                session_keys = self.redis_client.client.keys("session_status:*")

                for key in session_keys:
                    try:
                        session_id = key.split(":")[-1]
                        status_data = self.redis_client.get_session_status(session_id)

                        if (
                            status_data
                            and status_data.get("processing_strategy") == "chunked"
                            and status_data.get("status") == "processing"
                        ):
                            # Create audio handler to check completion
                            handler = AudioHandler(self.config)
                            completion_checked = handler.check_chunked_completion(
                                session_id
                            )

                            if completion_checked:
                                logger.info(
                                    f"✅ Checked completion for chunked session {session_id}"
                                )

                    except Exception as e:
                        logger.warning(f"⚠️ Error checking session completion: {e}")

                # Sleep before next check
                time.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"❌ Error in completion checker loop: {e}")
                time.sleep(30)  # Longer sleep on error

    def transcribe_audio(self, audio_file_path: str, chunk_info: dict = None) -> dict:
        """Enhanced transcribe method with chunk-aware processing"""
        try:
            chunk_desc = ""
            if chunk_info:
                chunk_desc = f" (chunk {chunk_info.get('chunk_index', '?')} of session {chunk_info.get('session_id', '?')})"

            logger.info(f"🎵 Starting transcription of {audio_file_path}{chunk_desc}")

            # Check if file exists
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

            # Check file size
            file_size = os.path.getsize(audio_file_path)
            logger.info(
                f"📊 File size: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)"
            )

            if file_size == 0:
                raise ValueError("Audio file is empty")

            # Enhanced logging for chunks
            if chunk_info:
                logger.info(
                    f"📦 Processing chunk: {chunk_info.get('start_time', 0):.1f}s - {chunk_info.get('end_time', 0):.1f}s"
                )

            # Start transcription with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(
                        f"🤖 Calling AssemblyAI API (attempt {attempt + 1}/{max_retries})..."
                    )
                    transcript = self.transcriber.transcribe(audio_file_path)
                    logger.info(f"📡 AssemblyAI response status: {transcript.status}")
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(
                        f"⚠️ API call failed (attempt {attempt + 1}), retrying: {e}"
                    )
                    time.sleep(2**attempt)  # Exponential backoff

            # Check for errors
            if transcript.status == "error":
                error_msg = getattr(transcript, "error", "Unknown error")
                logger.error(f"❌ Transcription failed: {error_msg}")
                raise RuntimeError(f"Transcription failed: {error_msg}")

            # Check if we have text
            if not transcript.text:
                logger.warning(f"⚠️ No speech detected in audio{chunk_desc}")
                return {
                    "text": "",
                    "confidence": 0.0,
                    "duration": getattr(
                        transcript,
                        "audio_duration",
                        chunk_info.get("duration", 0) if chunk_info else 0,
                    ),
                    "status": "completed",
                    "warning": "No speech detected in audio",
                }

            # Extract results
            result = {
                "text": transcript.text,
                "confidence": getattr(transcript, "confidence", 0.0),
                "duration": getattr(
                    transcript,
                    "audio_duration",
                    chunk_info.get("duration", 0) if chunk_info else 0,
                ),
                "words": len(transcript.text.split()) if transcript.text else 0,
                "status": "completed",
            }

            # Add chunk-specific info
            if chunk_info:
                result["chunk_index"] = chunk_info.get("chunk_index", 0)
                result["start_time"] = chunk_info.get("start_time", 0)
                result["end_time"] = chunk_info.get("end_time", 0)

            logger.info(f"✅ Transcription completed successfully{chunk_desc}!")
            logger.info(f"📝 Text length: {len(transcript.text)} characters")
            logger.info(f"📊 Word count: {result['words']} words")
            logger.info(f"🎯 Confidence: {result['confidence']:.2f}")
            logger.info(f"⏱️ Duration: {result['duration']:.1f}s")

            return result

        except Exception as e:
            logger.error(f"❌ Error during transcription{chunk_desc}: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {"status": "error", "error": str(e), "text": "", "confidence": 0.0}

    def save_transcript(
        self, session_id: str, transcript_data: dict, chunk_info: dict = None
    ) -> str:
        """Save transcript to file with enhanced formatting"""
        try:
            if chunk_info:
                # Save chunk transcript
                chunk_id = chunk_info.get("chunk_id", f"{session_id}_chunk")
                transcript_filename = f"{chunk_id}_transcript.txt"
            else:
                # Save direct transcript
                transcript_filename = f"{session_id}_transcript.txt"

            transcript_path = self.transcripts_dir / transcript_filename

            # Create enhanced medical transcript content
            content = f"Medical Transcript for {'Chunk' if chunk_info else 'Session'}: {chunk_info.get('chunk_id', session_id) if chunk_info else session_id}\n"
            content += f"Generated: {datetime.utcnow().isoformat()}Z\n"

            if chunk_info:
                content += f"Parent Session: {session_id}\n"
                content += f"Chunk Index: {chunk_info.get('chunk_index', 0)}\n"
                content += f"Time Range: {chunk_info.get('start_time', 0):.2f}s - {chunk_info.get('end_time', 0):.2f}s\n"

            content += f"Confidence Score: {transcript_data.get('confidence', 0):.3f}\n"
            content += f"Word Count: {transcript_data.get('words', 0)}\n"
            content += (
                f"Audio Duration: {transcript_data.get('duration', 0):.2f} seconds\n"
            )
            content += (
                f"Processing Method: {'Chunked Parallel' if chunk_info else 'Direct'}\n"
            )

            # Add warning if present
            if transcript_data.get("warning"):
                content += f"Note: {transcript_data['warning']}\n"

            content += "=" * 60 + "\n\n"
            content += transcript_data.get("text", "No transcript available")
            content += "\n\n" + "=" * 60 + "\n"
            content += "Generated by MaiChart Enhanced Medical Transcription System\n"
            content += "FastAPI Version\n"

            # Write to file
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"💾 Medical transcript saved to {transcript_path}")
            return str(transcript_path)

        except Exception as e:
            logger.error(f"❌ Error saving transcript: {e}")
            return ""

    def process_message(self, message_data: dict) -> bool:
        """Enhanced process_message that handles both direct and chunk processing"""
        try:
            message_type = message_data.get("type", "direct_processing")

            if message_type == "chunk_processing":
                return self._process_chunk_message(message_data)
            else:
                return self._process_direct_message(message_data)

        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            return False

    def _process_chunk_message(self, message_data: dict) -> bool:
        """Process a chunk transcription message"""
        try:
            session_id = message_data.get("session_id")
            chunk_id = message_data.get("chunk_id")
            chunk_path = message_data.get("chunk_path")
            chunk_index = int(message_data.get("chunk_index", 0))

            logger.info(f"🎯 Processing chunk {chunk_id} for session {session_id}")
            logger.info(f"📁 Chunk file: {chunk_path}")

            if not all([session_id, chunk_id, chunk_path]):
                logger.error("❌ Missing required fields in chunk message")
                return False

            # Update chunk status to processing
            chunk_status_key = f"chunk_status:{chunk_id}"
            self.redis_client.client.hset(
                chunk_status_key,
                mapping={
                    "status": "processing",
                    "processing_started_at": datetime.utcnow().isoformat(),
                    "worker": self.consumer_name,
                },
            )

            # Check if chunk file exists
            if not os.path.exists(chunk_path):
                logger.error(f"❌ Chunk file not found: {chunk_path}")
                self.redis_client.client.hset(
                    chunk_status_key,
                    mapping={"status": "error", "error": "Chunk file not found"},
                )
                return False

            # Prepare chunk info
            chunk_info = {
                "chunk_id": chunk_id,
                "chunk_index": chunk_index,
                "session_id": session_id,
                "start_time": float(message_data.get("start_time", 0)),
                "end_time": float(message_data.get("end_time", 0)),
                "duration": float(message_data.get("duration", 0)),
            }

            # Transcribe chunk
            logger.info(f"🤖 Starting chunk transcription...")
            transcript_result = self.transcribe_audio(chunk_path, chunk_info)

            if transcript_result["status"] == "completed":
                # Save chunk transcript
                transcript_path = self.save_transcript(
                    session_id, transcript_result, chunk_info
                )

                # Update chunk status to completed
                chunk_status = {
                    "status": "completed",
                    "transcript_text": transcript_result["text"],
                    "transcript_confidence": transcript_result["confidence"],
                    "transcript_words": transcript_result.get("words", 0),
                    "transcript_path": transcript_path,
                    "processing_completed_at": datetime.utcnow().isoformat(),
                }

                # Add duration and timing info
                if transcript_result.get("duration"):
                    chunk_status["duration"] = transcript_result["duration"]
                if transcript_result.get("warning"):
                    chunk_status["warning"] = transcript_result["warning"]

                self.redis_client.client.hset(chunk_status_key, mapping=chunk_status)

                logger.info(f"✅ Chunk {chunk_id} transcribed successfully!")
                logger.info(
                    f"📊 Chunk stats: {len(transcript_result['text'])} chars, {transcript_result.get('words', 0)} words"
                )

                return True
            else:
                # Update chunk status to error
                error_msg = transcript_result.get("error", "Chunk transcription failed")
                self.redis_client.client.hset(
                    chunk_status_key,
                    mapping={
                        "status": "error",
                        "error": error_msg,
                        "processing_failed_at": datetime.utcnow().isoformat(),
                    },
                )

                logger.error(f"❌ Chunk {chunk_id} transcription failed: {error_msg}")
                return False

        except Exception as e:
            logger.error(f"❌ Error processing chunk message: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")

            # Update chunk status to error
            chunk_id = message_data.get("chunk_id")
            if chunk_id:
                chunk_status_key = f"chunk_status:{chunk_id}"
                self.redis_client.client.hset(
                    chunk_status_key,
                    mapping={
                        "status": "error",
                        "error": str(e),
                        "processing_failed_at": datetime.utcnow().isoformat(),
                    },
                )

            return False

    def _process_direct_message(self, message_data: dict) -> bool:
        """Process a direct (non-chunked) transcription message - original logic"""
        try:
            session_id = message_data.get("session_id")
            filepath = message_data.get("filepath")
            filename = message_data.get("filename")

            logger.info(f"🎯 Processing direct session {session_id}")
            logger.info(f"📁 File: {filename}")
            logger.info(f"📍 Path: {filepath}")

            if not all([session_id, filepath, filename]):
                logger.error("❌ Missing required fields in direct message")
                return False

            # Update status to processing
            self.update_session_status(
                session_id,
                {
                    "status": "processing",
                    "step": "analyzing_audio",
                    "processing_started_at": datetime.utcnow().isoformat(),
                },
            )

            # Check if input file exists
            if not os.path.exists(filepath):
                logger.error(f"❌ Input file not found: {filepath}")
                self.update_session_status(
                    session_id, {"status": "error", "error": "Input file not found"}
                )
                return False

            # Check file size
            file_size = os.path.getsize(filepath)
            logger.info(f"📊 File size: {file_size} bytes")

            if file_size == 0:
                logger.error("❌ Input file is empty")
                self.update_session_status(
                    session_id, {"status": "error", "error": "Input file is empty"}
                )
                return False

            # Update status to transcribing
            self.update_session_status(
                session_id,
                {
                    "status": "processing",
                    "step": "processing_audio",
                },
            )

            # Transcribe audio
            logger.info("🔄 Starting direct transcription...")
            transcript_result = self.transcribe_audio(filepath)

            if transcript_result["status"] == "completed":
                # Update status to saving
                self.update_session_status(
                    session_id,
                    {
                        "status": "processing",
                        "step": "saving_transcript",
                    },
                )

                # Save transcript
                transcript_path = self.save_transcript(session_id, transcript_result)

                # Update status to completed
                status_update = {
                    "status": "completed",
                    "transcript_text": transcript_result["text"],
                    "transcript_confidence": transcript_result["confidence"],
                    "transcript_words": transcript_result.get("words", 0),
                    "transcript_path": transcript_path,
                    "processing_completed_at": datetime.utcnow().isoformat(),
                }

                # Add duration if available
                if transcript_result.get("duration"):
                    status_update["audio_duration"] = transcript_result["duration"]

                # Add warning if present
                if transcript_result.get("warning"):
                    status_update["warning"] = transcript_result["warning"]

                self.update_session_status(session_id, status_update)

                logger.info(f"🎉 Successfully transcribed direct session {session_id}")
                return True
            else:
                # Update status to error
                error_msg = transcript_result.get("error", "Transcription failed")
                self.update_session_status(
                    session_id,
                    {
                        "status": "error",
                        "error": error_msg,
                        "processing_failed_at": datetime.utcnow().isoformat(),
                    },
                )

                logger.error(
                    f"💥 Failed to transcribe session {session_id}: {error_msg}"
                )
                return False

        except Exception as e:
            logger.error(f"💥 Error processing direct message: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")

            # Update status to error if we have session_id
            session_id = message_data.get("session_id")
            if session_id:
                self.handle_message_error(session_id, e)

            return False


def main():
    """Enhanced main entry point with worker type selection"""
    try:
        # Get worker type from environment or command line
        worker_type = os.getenv("WORKER_TYPE", "direct")  # Default to direct
        if len(sys.argv) > 1:
            worker_type = sys.argv[1]

        if worker_type not in ["direct", "chunk"]:
            logger.error(
                f"❌ Invalid worker type: {worker_type}. Must be 'direct' or 'chunk'"
            )
            return 1

        logger.info(
            f"🚀 Starting Enhanced MaiChart Transcription Worker ({worker_type}) for FastAPI..."
        )

        # Validate environment variables
        if not os.getenv("ASSEMBLYAI_API_KEY"):
            raise ValueError("ASSEMBLYAI_API_KEY environment variable must be set")

        worker = EnhancedTranscriptionWorker(worker_type=worker_type)
        logger.info(
            f"✅ Enhanced medical transcription worker ({worker_type}) created successfully"
        )

        return worker.run()

    except Exception as e:
        logger.error(f"💥 Failed to start enhanced transcription worker: {e}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())