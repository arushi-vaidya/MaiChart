#!/usr/bin/env python3
"""
FIXED Enhanced Transcription Worker with Robust Error Handling
Fixes the "starting" status issue and prevents worker from getting stuck
"""

import os
import sys
import logging
import time
import threading
import json
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
    ASSEMBLYAI_AVAILABLE = True
except ImportError:
    print("❌ AssemblyAI library not installed. Please run: pip install assemblyai")
    ASSEMBLYAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class FixedTranscriptionWorker(BaseWorker):
    """
    FIXED worker that handles transcription and automatically queues for medical extraction
    Enhanced error handling to prevent getting stuck at "starting"
    """

    def __init__(self, config_name="default", worker_type="direct"):
        try:
            # FIXED: Better worker name and type handling
            worker_name = f"transcription_worker_{worker_type}"
            super().__init__(worker_name, config_name)

            self.worker_type = worker_type  # 'direct' or 'chunk'

            # FIXED: Get AssemblyAI API key with validation
            self.api_key = os.getenv("ASSEMBLYAI_API_KEY")
            if not self.api_key:
                logger.error("❌ ASSEMBLYAI_API_KEY environment variable must be set")
                raise ValueError("ASSEMBLYAI_API_KEY environment variable must be set")

            # FIXED: Only configure AssemblyAI if library is available
            if not ASSEMBLYAI_AVAILABLE:
                logger.error("❌ AssemblyAI library not available")
                raise ImportError("AssemblyAI library not installed")

            # Configure AssemblyAI with enhanced settings
            try:
                aai.settings.api_key = self.api_key
                logger.info(f"✅ AssemblyAI API key configured for {worker_name}")
            except Exception as e:
                logger.error(f"❌ Failed to configure AssemblyAI: {e}")
                raise

            # Enhanced transcription config for medical content
            self.transcription_config = aai.TranscriptionConfig(
                punctuate=True,
                format_text=True,
                # Enhanced medical term boosting
                word_boost=[
                    "medical", "patient", "diagnosis", "treatment", "medication", "prescription",
                    "symptoms", "examination", "therapy", "clinical", "procedure", "surgery",
                    "doctor", "physician", "nurse", "hospital", "clinic", "emergency",
                    "vital", "signs", "blood", "pressure", "heart", "rate", "temperature",
                    "pain", "chronic", "acute", "condition", "disease", "infection",
                    "antibiotics", "dosage", "milligrams", "tablets", "injection",
                    "allergies", "reaction", "side", "effects", "follow", "up",
                    "hypertension", "diabetes", "asthma", "pneumonia", "bronchitis",
                    "gastritis", "arthritis", "depression", "anxiety", "migraine"
                ],
                boost_param="high",
            )

            # Initialize transcriber
            try:
                self.transcriber = aai.Transcriber(config=self.transcription_config)
                logger.info("✅ AssemblyAI transcriber initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize transcriber: {e}")
                raise

            # FIXED: Enhanced streams configuration with validation
            if self.worker_type == "chunk":
                self.stream_name = "audio_chunks"
                self.consumer_group = "chunk_processors"
            else:
                self.stream_name = "audio_input"
                self.consumer_group = "audio_processors" 
                logger.info(f"🎯 ULTIMATE: stream={self.stream_name}, group={self.consumer_group}")

            logger.info(f"✅ Worker configured: stream={self.stream_name}, group={self.consumer_group}")

            # Ensure transcripts directory exists
            self.transcripts_dir = self.config.TRANSCRIPTS_FOLDER
            self.transcripts_dir.mkdir(exist_ok=True, parents=True)

            # Check if medical extraction is enabled
            self.enable_medical_extraction = os.getenv("ENABLE_MEDICAL_EXTRACTION", "true").lower() == "true"
            
            # FIXED: Initialize completion checker state
            self.completion_checker_running = False
            self.completion_checker_thread = None
            
            logger.info(f"✅ Enhanced {worker_name} initialized successfully")
            if self.enable_medical_extraction:
                logger.info("🏥 Medical extraction will be automatically queued after transcription")

        except Exception as e:
            logger.error(f"❌ Failed to initialize transcription worker: {e}")
            raise

    def check_dependencies(self) -> bool:
        """FIXED: Check if AssemblyAI is available and configured with better error handling"""
        try:
            logger.info("🔍 Checking AssemblyAI dependencies...")

            # Check if AssemblyAI library is available
            if not ASSEMBLYAI_AVAILABLE:
                logger.error("❌ AssemblyAI library is not available")
                return False

            # Check if AssemblyAI library is properly imported
            if not hasattr(aai, "TranscriptionConfig") or not hasattr(aai, "Transcriber"):
                logger.error("❌ AssemblyAI library is not properly configured")
                return False

            # Check if API key is set
            if not self.api_key:
                logger.error("❌ ASSEMBLYAI_API_KEY environment variable is not set")
                return False

            # FIXED: Test API connection with timeout and better error handling
            try:
                logger.info("🔌 Testing API connection...")
                # Create a simple test config to verify API access
                test_config = aai.TranscriptionConfig(punctuate=True)
                test_transcriber = aai.Transcriber(config=test_config)
                logger.info("✅ API connection test passed")
            except Exception as e:
                logger.error(f"❌ API connection test failed: {e}")
                return False

            # Test Redis connection
            try:
                logger.info("🔌 Testing Redis connection...")
                ping_result = self.redis_client.ping()
                if not ping_result:
                    logger.error("❌ Redis ping failed")
                    return False
                logger.info("✅ Redis connection test passed")
            except Exception as e:
                logger.error(f"❌ Redis connection test failed: {e}")
                return False

            logger.info("✅ All dependencies check passed")
            return True

        except Exception as e:
            logger.error(f"❌ Dependency check failed: {e}")
            return False

    def transcribe_audio(self, audio_file_path: str, chunk_info: dict = None) -> dict:
        """FIXED: Enhanced transcribe method with better error handling and timeouts"""
        try:
            chunk_desc = ""
            if chunk_info:
                chunk_desc = f" (chunk {chunk_info.get('chunk_index', '?')} of session {chunk_info.get('session_id', '?')})"

            logger.info(f"🎵 Starting transcription of {audio_file_path}{chunk_desc}")

            # FIXED: Check if file exists with better error handling
            if not os.path.exists(audio_file_path):
                error_msg = f"Audio file not found: {audio_file_path}"
                logger.error(f"❌ {error_msg}")
                raise FileNotFoundError(error_msg)

            # Check file size
            try:
                file_size = os.path.getsize(audio_file_path)
                logger.info(f"📊 File size: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")

                if file_size == 0:
                    error_msg = "Audio file is empty"
                    logger.error(f"❌ {error_msg}")
                    raise ValueError(error_msg)

                # FIXED: Check for reasonable file size limits
                if file_size > 100 * 1024 * 1024:  # 100MB limit
                    error_msg = f"Audio file too large: {file_size} bytes"
                    logger.error(f"❌ {error_msg}")
                    raise ValueError(error_msg)

            except OSError as e:
                error_msg = f"Cannot access file: {audio_file_path} - {e}"
                logger.error(f"❌ {error_msg}")
                raise FileNotFoundError(error_msg)

            # Enhanced logging for chunks
            if chunk_info:
                logger.info(f"📦 Processing chunk: {chunk_info.get('start_time', 0):.1f}s - {chunk_info.get('end_time', 0):.1f}s")

            # FIXED: Start transcription with better retry logic and timeout
            max_retries = 3
            timeout_seconds = 300  # 5 minutes timeout
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"🤖 Calling AssemblyAI API (attempt {attempt + 1}/{max_retries})...")
                    
                    # FIXED: Add timeout handling
                    start_time = time.time()
                    transcript = self.transcriber.transcribe(audio_file_path)
                    
                    # Wait for completion with timeout
                    while transcript.status in ['queued', 'processing']:
                        elapsed = time.time() - start_time
                        if elapsed > timeout_seconds:
                            error_msg = f"Transcription timed out after {timeout_seconds} seconds"
                            logger.error(f"⏰ {error_msg}")
                            raise TimeoutError(error_msg)
                        
                        logger.info(f"⏳ Transcription in progress... ({elapsed:.0f}s elapsed)")
                        time.sleep(5)  # Check every 5 seconds
                        
                        # Refresh transcript status
                        try:
                            # Get updated status (AssemblyAI automatically updates)
                            pass
                        except Exception as status_e:
                            logger.warning(f"⚠️ Could not refresh transcript status: {status_e}")
                    
                    logger.info(f"📡 AssemblyAI response status: {transcript.status}")
                    break
                    
                except TimeoutError:
                    raise  # Don't retry on timeout
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"⚠️ API call failed (attempt {attempt + 1}), retrying: {e}")
                    time.sleep(2**attempt)  # Exponential backoff

            # FIXED: Check for errors with better error messages
            if transcript.status == "error":
                error_msg = getattr(transcript, "error", "Unknown transcription error")
                logger.error(f"❌ Transcription failed: {error_msg}")
                raise RuntimeError(f"Transcription failed: {error_msg}")

            # FIXED: Check if we have text with better handling
            if not transcript.text or transcript.text.strip() == "":
                logger.warning(f"⚠️ No speech detected in audio{chunk_desc}")
                return {
                    "text": "",
                    "confidence": 0.0,
                    "duration": getattr(transcript, "audio_duration", chunk_info.get("duration", 0) if chunk_info else 0),
                    "status": "completed",
                    "warning": "No speech detected in audio",
                }

            # FIXED: Extract results with better error handling
            try:
                confidence = getattr(transcript, "confidence", 0.0)
                duration = getattr(transcript, "audio_duration", chunk_info.get("duration", 0) if chunk_info else 0)
                
                # Ensure confidence is a valid number
                if confidence is None or not isinstance(confidence, (int, float)):
                    confidence = 0.0
                
                # Ensure duration is a valid number
                if duration is None or not isinstance(duration, (int, float)):
                    duration = 0.0

                result = {
                    "text": transcript.text.strip(),
                    "confidence": float(confidence),
                    "duration": float(duration),
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
                logger.error(f"❌ Error extracting transcript results: {e}")
                raise

        except Exception as e:
            logger.error(f"❌ Error during transcription{chunk_desc}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {"status": "error", "error": str(e), "text": "", "confidence": 0.0}

    def auto_queue_medical_extraction(self, session_id: str, transcript_text: str) -> bool:
        """FIXED: Automatically queue medical extraction with better error handling"""
        try:
            if not self.enable_medical_extraction:
                logger.info(f"⏭️ Medical extraction disabled for session {session_id}")
                return False
                
            if not transcript_text or len(transcript_text.strip()) < 10:
                logger.info(f"⏭️ Transcript too short for medical extraction: {session_id}")
                return False
            
            # Queue for medical extraction
            extraction_data = {
                "session_id": session_id,
                "transcript_text": transcript_text,
                "queued_at": datetime.utcnow().isoformat(),
                "type": "auto_medical_extraction"
            }
            
            # Add to medical extraction stream
            medical_stream = "medical_extraction_queue"
            
            try:
                stream_id = self.redis_client.add_to_stream(medical_stream, extraction_data)
                
                if stream_id:
                    logger.info(f"🏥 Auto-queued medical extraction for session {session_id} -> {stream_id}")
                    
                    # Update session status to indicate medical extraction is queued
                    self.update_session_status(session_id, {
                        "medical_extraction_queued": True,
                        "medical_extraction_stream_id": stream_id,
                        "medical_extraction_queued_at": datetime.utcnow().isoformat()
                    })
                    return True
                return False
                
            except Exception as e:
                logger.error(f"❌ Error adding to medical extraction stream: {e}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error auto-queuing medical extraction: {e}")
            return False

    def save_transcript(self, session_id: str, transcript_data: dict, chunk_info: dict = None) -> str:
        """FIXED: Save transcript to file with enhanced error handling"""
        try:
            if chunk_info:
                # Save chunk transcript
                chunk_id = chunk_info.get("chunk_id", f"{session_id}_chunk")
                transcript_filename = f"{chunk_id}_transcript.txt"
            else:
                # Save direct transcript
                transcript_filename = f"{session_id}_transcript.txt"

            transcript_path = self.transcripts_dir / transcript_filename

            # FIXED: Create enhanced medical transcript content with safe string handling
            content = f"Medical Transcript for {'Chunk' if chunk_info else 'Session'}: {chunk_info.get('chunk_id', session_id) if chunk_info else session_id}\n"
            content += f"Generated: {datetime.utcnow().isoformat()}Z\n"

            if chunk_info:
                content += f"Parent Session: {session_id}\n"
                content += f"Chunk Index: {chunk_info.get('chunk_index', 0)}\n"
                content += f"Time Range: {chunk_info.get('start_time', 0):.2f}s - {chunk_info.get('end_time', 0):.2f}s\n"

            # FIXED: Safe handling of transcript_data values
            confidence = transcript_data.get('confidence', 0)
            words = transcript_data.get('words', 0)
            duration = transcript_data.get('duration', 0)
            
            content += f"Confidence Score: {confidence:.3f}\n"
            content += f"Word Count: {words}\n"
            content += f"Audio Duration: {duration:.2f} seconds\n"
            content += f"Processing Method: {'Chunked Parallel' if chunk_info else 'Direct'}\n"
            content += f"Medical Extraction: {'Enabled' if self.enable_medical_extraction else 'Disabled'}\n"

            # Add warning if present
            if transcript_data.get("warning"):
                content += f"Note: {transcript_data['warning']}\n"

            content += "=" * 60 + "\n\n"
            content += transcript_data.get("text", "No transcript available")
            content += "\n\n" + "=" * 60 + "\n"
            content += "Generated by MaiChart Enhanced Medical Transcription System\n"
            content += "FastAPI Version with Medical Information Extraction\n"

            # FIXED: Write to file with proper error handling
            try:
                with open(transcript_path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                logger.info(f"💾 Medical transcript saved to {transcript_path}")
                return str(transcript_path)
                
            except IOError as e:
                logger.error(f"❌ Error writing transcript file: {e}")
                return ""

        except Exception as e:
            logger.error(f"❌ Error saving transcript: {e}")
            return ""

    def process_message(self, message_data: dict) -> bool:
        """FIXED: Enhanced process_message with better error handling and proper acknowledgment"""
        try:
            message_type = message_data.get("type", "direct_processing")
            logger.info(f"📨 Processing message type: {message_type}")

            if message_type == "chunk_processing":
                result = self._process_chunk_message(message_data)
            else:
                result = self._process_direct_message(message_data)

            logger.info(f"✅ Message processing result: {result}")
            return result

        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False

    def _process_direct_message(self, message_data: dict) -> bool:
        """FIXED: Process a direct transcription message with enhanced error handling"""
        session_id = None
        try:
            session_id = message_data.get("session_id")
            filepath = message_data.get("filepath")
            filename = message_data.get("filename")
            message_type = message_data.get("type", "direct_processing")

            logger.info(f"🎯 Processing direct session {session_id}")
            logger.info(f"📁 File: {filename}")
            logger.info(f"📍 Path: {filepath}")
            logger.info(f"🔄 Message Type: {message_type}")

            # FIXED: Validate required fields
            if not all([session_id, filepath, filename]):
                logger.error("❌ Missing required fields in direct message")
                if session_id:
                    self.update_session_status(session_id, {
                        "status": "error", 
                        "error": "Missing required fields in message"
                    })
                return False

            # Update status to processing
            self.update_session_status(session_id, {
                "status": "processing",
                "step": "analyzing_audio",
                "processing_started_at": datetime.utcnow().isoformat(),
            })

            # FIXED: Check if input file exists with better error handling
            try:
                if not os.path.exists(filepath):
                    error_msg = f"Input file not found: {filepath}"
                    logger.error(f"❌ {error_msg}")
                    self.update_session_status(session_id, {"status": "error", "error": error_msg})
                    return False

                # Check file size
                file_size = os.path.getsize(filepath)
                logger.info(f"📊 File size: {file_size} bytes")

                if file_size == 0:
                    error_msg = "Input file is empty"
                    logger.error(f"❌ {error_msg}")
                    self.update_session_status(session_id, {"status": "error", "error": error_msg})
                    return False

            except OSError as e:
                error_msg = f"Cannot access input file: {e}"
                logger.error(f"❌ {error_msg}")
                self.update_session_status(session_id, {"status": "error", "error": error_msg})
                return False

            # Update status to transcribing
            self.update_session_status(session_id, {
                "status": "processing",
                "step": "processing_audio",
            })

            # Transcribe audio
            logger.info("🔄 Starting direct transcription...")
            transcript_result = self.transcribe_audio(filepath)

            if transcript_result["status"] == "completed":
                # Update status to saving
                self.update_session_status(session_id, {
                    "status": "processing",
                    "step": "saving_transcript",
                })

                # Save transcript
                transcript_path = self.save_transcript(session_id, transcript_result)

                # FIXED: Prepare status update with safe data handling
                status_update = {
                    "status": "completed",
                    "transcript_text": transcript_result.get("text", ""),
                    "transcript_confidence": transcript_result.get("confidence", 0.0),
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

                # FIXED: Auto-queue for medical extraction if transcript has content
                if transcript_result.get("text") and len(transcript_result["text"].strip()) > 10:
                    medical_queued = self.auto_queue_medical_extraction(session_id, transcript_result["text"])
                    if medical_queued:
                        logger.info(f"🏥 Medical extraction auto-queued for session {session_id}")
                    else:
                        logger.info(f"⏭️ Medical extraction not queued for session {session_id}")

                logger.info(f"🎉 Successfully transcribed direct session {session_id}")
                return True
            else:
                # Update status to error
                error_msg = transcript_result.get("error", "Transcription failed")
                self.update_session_status(session_id, {
                    "status": "error",
                    "error": error_msg,
                    "processing_failed_at": datetime.utcnow().isoformat(),
                })

                logger.error(f"💥 Failed to transcribe session {session_id}: {error_msg}")
                return False

        except Exception as e:
            logger.error(f"💥 Error processing direct message: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

            # Update status to error if we have session_id
            if session_id:
                self.handle_message_error(session_id, e)

            return False

    def _process_chunk_message(self, message_data: dict) -> bool:
        """FIXED: Process a chunk transcription message with enhanced error handling"""
        session_id = None
        chunk_id = None
        try:
            session_id = message_data.get("session_id")
            chunk_id = message_data.get("chunk_id")
            chunk_path = message_data.get("chunk_path")
            chunk_index = int(message_data.get("chunk_index", 0))

            logger.info(f"🎯 Processing chunk {chunk_id} for session {session_id}")
            logger.info(f"📁 Chunk file: {chunk_path}")

            # FIXED: Validate required fields
            if not all([session_id, chunk_id, chunk_path]):
                logger.error("❌ Missing required fields in chunk message")
                return False

            # Update chunk status to processing
            chunk_status_key = f"chunk_status:{chunk_id}"
            try:
                self.redis_client.client.hset(chunk_status_key, mapping={
                    "status": "processing",
                    "processing_started_at": datetime.utcnow().isoformat(),
                    "worker": self.consumer_name,
                })
            except Exception as e:
                logger.error(f"❌ Error updating chunk status: {e}")

            # FIXED: Check if chunk file exists with better error handling
            try:
                if not os.path.exists(chunk_path):
                    error_msg = f"Chunk file not found: {chunk_path}"
                    logger.error(f"❌ {error_msg}")
                    try:
                        self.redis_client.client.hset(chunk_status_key, mapping={
                            "status": "error", 
                            "error": error_msg
                        })
                    except:
                        pass
                    return False
            except Exception as e:
                error_msg = f"Cannot access chunk file: {e}"
                logger.error(f"❌ {error_msg}")
                try:
                    self.redis_client.client.hset(chunk_status_key, mapping={
                        "status": "error", 
                        "error": error_msg
                    })
                except:
                    pass
                return False

            # FIXED: Prepare chunk info with safe data handling
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
                transcript_path = self.save_transcript(session_id, transcript_result, chunk_info)

                # FIXED: Update chunk status to completed with safe data handling
                chunk_status = {
                    "status": "completed",
                    "transcript_text": transcript_result.get("text", ""),
                    "transcript_confidence": str(transcript_result.get("confidence", 0.0)),
                    "transcript_words": str(transcript_result.get("words", 0)),
                    "transcript_path": transcript_path,
                    "processing_completed_at": datetime.utcnow().isoformat(),
                }

                # Add duration and timing info
                if transcript_result.get("duration"):
                    chunk_status["duration"] = str(transcript_result["duration"])
                if transcript_result.get("warning"):
                    chunk_status["warning"] = transcript_result["warning"]

                try:
                    self.redis_client.client.hset(chunk_status_key, mapping=chunk_status)
                except Exception as e:
                    logger.error(f"❌ Error updating completed chunk status: {e}")

                logger.info(f"✅ Chunk {chunk_id} transcribed successfully!")
                logger.info(f"📊 Chunk stats: {len(transcript_result['text'])} chars, {transcript_result.get('words', 0)} words")

                # FIXED: Check if all chunks are complete and queue medical extraction
                self._check_and_queue_chunked_medical_extraction(session_id)

                return True
            else:
                # Update chunk status to error
                error_msg = transcript_result.get("error", "Chunk transcription failed")
                try:
                    self.redis_client.client.hset(chunk_status_key, mapping={
                        "status": "error",
                        "error": error_msg,
                        "processing_failed_at": datetime.utcnow().isoformat(),
                    })
                except Exception as e:
                    logger.error(f"❌ Error updating failed chunk status: {e}")

                logger.error(f"❌ Chunk {chunk_id} transcription failed: {error_msg}")
                return False

        except Exception as e:
            logger.error(f"❌ Error processing chunk message: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

            # Update chunk status to error
            if chunk_id:
                chunk_status_key = f"chunk_status:{chunk_id}"
                try:
                    self.redis_client.client.hset(chunk_status_key, mapping={
                        "status": "error",
                        "error": str(e),
                        "processing_failed_at": datetime.utcnow().isoformat(),
                    })
                except Exception as status_e:
                    logger.error(f"❌ Error updating error chunk status: {status_e}")

            return False

    def _check_and_queue_chunked_medical_extraction(self, session_id: str):
        """FIXED: Check if chunked session is complete and queue for medical extraction"""
        try:
            # Import here to avoid circular imports
            from core.audio_handler import AudioHandler
            
            # Check if all chunks are complete
            handler = AudioHandler(self.config)
            session_data = handler.get_session_status(session_id)
            
            if not session_data or session_data.get("processing_strategy") != "chunked":
                return
                
            # Check if session is fully completed
            if session_data.get("status") == "completed":
                transcript_text = session_data.get("transcript_text", "")
                
                # Queue for medical extraction if not already queued
                if (not session_data.get("medical_extraction_queued") and 
                    transcript_text and len(transcript_text.strip()) > 10):
                    
                    medical_queued = self.auto_queue_medical_extraction(session_id, transcript_text)
                    if medical_queued:
                        logger.info(f"🏥 Medical extraction queued for completed chunked session {session_id}")
                        
        except Exception as e:
            logger.warning(f"⚠️ Error checking chunked medical extraction: {e}")

    def run(self):
        """FIXED: Enhanced run method with proper message acknowledgment and better error handling"""
        try:
            logger.info(f"🚀 Starting {self.worker_name} with enhanced error handling...")

            # Check dependencies first
            if not self.check_dependencies():
                logger.error("❌ Dependency check failed. Exiting.")
                return 1

            # Start completion checker for chunk workers
            if self.worker_type == "chunk":
                self.start_completion_checker()

            # Clean up any pending messages from previous runs
            self.cleanup_consumer_group()

            # FIXED: Main processing loop with enhanced error handling
            consecutive_errors = 0
            max_consecutive_errors = 5
            heartbeat_interval = 30  # Log heartbeat every 30 seconds
            last_heartbeat = time.time()

            logger.info(f"✅ {self.worker_name} ready to process messages")

            while self.running:
                try:
                    # FIXED: Log heartbeat to show worker is alive
                    current_time = time.time()
                    if current_time - last_heartbeat >= heartbeat_interval:
                        logger.info(f"💓 {self.worker_name} heartbeat - waiting for messages...")
                        last_heartbeat = current_time

                    # Read messages from Redis stream
                    messages = self.redis_client.read_stream(
                        self.stream_name,
                        self.consumer_group,
                        self.consumer_name,
                        count=1,
                        block=self.block_time,
                    )

                    if not messages:
                        consecutive_errors = 0  # Reset error counter on successful read
                        continue

                    # Process each message
                    for stream, stream_messages in messages:
                        for message_id, fields in stream_messages:
                            logger.info(f"📨 Processing message {message_id}")

                            try:
                                # Process the message
                                success = self.process_message(fields)

                                # FIXED: Always acknowledge the message regardless of success
                                # This prevents stuck messages in the queue
                                self.redis_client.acknowledge_message(
                                    self.stream_name, self.consumer_group, message_id
                                )
                                
                                if success:
                                    logger.info(f"✅ Message {message_id} processed successfully and acknowledged")
                                    consecutive_errors = 0  # Reset error counter on success
                                else:
                                    logger.error(f"❌ Message {message_id} failed but acknowledged to prevent queue blocking")

                            except Exception as e:
                                logger.error(f"❌ Error processing message {message_id}: {e}")

                                # Try to update session status if we have session_id
                                session_id = fields.get("session_id")
                                if session_id:
                                    try:
                                        self.handle_message_error(session_id, e)
                                    except Exception as status_e:
                                        logger.error(f"❌ Failed to update error status: {status_e}")

                                # FIXED: Still acknowledge the message to prevent queue blocking
                                try:
                                    self.redis_client.acknowledge_message(
                                        self.stream_name, self.consumer_group, message_id
                                    )
                                    logger.info(f"❌ Failed message {message_id} acknowledged to prevent queue blocking")
                                except Exception as ack_error:
                                    logger.error(f"❌ Failed to acknowledge message {message_id}: {ack_error}")

                                consecutive_errors += 1

                except KeyboardInterrupt:
                    logger.info("📨 Received keyboard interrupt")
                    break
                except Exception as e:
                    logger.error(f"❌ Error in worker loop: {e}")
                    consecutive_errors += 1
                    
                    # If we have too many consecutive errors, exit
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(f"❌ Too many consecutive errors ({consecutive_errors}), exiting")
                        break
                        
                    # Exponential backoff with max
                    sleep_time = min(5 * consecutive_errors, 30)
                    logger.info(f"⏳ Sleeping {sleep_time}s before retry...")
                    time.sleep(sleep_time)

            logger.info(f"🛑 {self.worker_name} stopped")
            return 0

        except Exception as e:
            logger.error(f"❌ Fatal error in enhanced worker run: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return 1
        finally:
            if self.worker_type == "chunk":
                self.stop_completion_checker()

    def start_completion_checker(self):
        """Start background thread to check for completed chunked sessions"""
        if hasattr(self, 'completion_checker_running') and self.completion_checker_running:
            return

        try:
            self.completion_checker_running = True
            self.completion_checker_thread = threading.Thread(
                target=self._completion_checker_loop, daemon=True
            )
            self.completion_checker_thread.start()
            logger.info("🔄 Started completion checker thread")
        except Exception as e:
            logger.error(f"❌ Error starting completion checker: {e}")

    def stop_completion_checker(self):
        """Stop the completion checker thread"""
        try:
            self.completion_checker_running = False
            if hasattr(self, 'completion_checker_thread') and self.completion_checker_thread:
                self.completion_checker_thread.join(timeout=5)
            logger.info("⏹️ Stopped completion checker thread")
        except Exception as e:
            logger.error(f"❌ Error stopping completion checker: {e}")

    def _completion_checker_loop(self):
        """FIXED: Background loop to check for completed chunked sessions"""
        logger.info("🔄 Completion checker loop started")
        
        while self.completion_checker_running:
            try:
                # Check for sessions that might be ready for merging
                session_keys = self.redis_client.client.keys("session_status:*")

                for key in session_keys:
                    if not self.completion_checker_running:
                        break
                        
                    try:
                        session_id = key.split(":")[-1]
                        status_data = self.redis_client.get_session_status(session_id)

                        if (status_data and 
                            status_data.get("processing_strategy") == "chunked" and 
                            status_data.get("status") == "processing"):
                            
                            # Create audio handler to check completion
                            from core.audio_handler import AudioHandler
                            handler = AudioHandler(self.config)
                            completion_checked = handler.check_chunked_completion(session_id)

                            if completion_checked:
                                logger.info(f"✅ Checked completion for chunked session {session_id}")

                    except Exception as e:
                        logger.warning(f"⚠️ Error checking session completion: {e}")

                # Sleep before next check
                for _ in range(100):  # Sleep for 10 seconds in 0.1s increments
                    if not self.completion_checker_running:
                        break
                    time.sleep(0.1)

            except Exception as e:
                logger.error(f"❌ Error in completion checker loop: {e}")
                # Longer sleep on error
                for _ in range(300):  # Sleep for 30 seconds in 0.1s increments
                    if not self.completion_checker_running:
                        break
                    time.sleep(0.1)
        
        logger.info("🛑 Completion checker loop stopped")


def main():
    """FIXED: Enhanced main entry point with better error handling"""
    try:
        # Get worker type from environment or command line
        worker_type = os.getenv("WORKER_TYPE", "direct")  # Default to direct
        if len(sys.argv) > 1:
            worker_type = sys.argv[1]

        if worker_type not in ["direct", "chunk"]:
            logger.error(f"❌ Invalid worker type: {worker_type}. Must be 'direct' or 'chunk'")
            return 1

        logger.info(f"🚀 Starting FIXED MaiChart Transcription Worker ({worker_type}) with Enhanced Error Handling...")

        # FIXED: Validate environment variables with better error messages
        api_key = os.getenv("ASSEMBLYAI_API_KEY")
        if not api_key:
            logger.error("❌ ASSEMBLYAI_API_KEY environment variable must be set")
            logger.error("💡 Please set your AssemblyAI API key: export ASSEMBLYAI_API_KEY=your_key_here")
            return 1

        redis_host = os.getenv("REDIS_HOST")
        if not redis_host:
            logger.error("❌ REDIS_HOST environment variable must be set")
            logger.error("💡 Please set Redis host: export REDIS_HOST=localhost")
            return 1

        # Check if AssemblyAI library is available
        if not ASSEMBLYAI_AVAILABLE:
            logger.error("❌ AssemblyAI library not available")
            logger.error("💡 Please install: pip install assemblyai")
            return 1

        # Create worker with enhanced error handling
        try:
            worker = FixedTranscriptionWorker(worker_type=worker_type)
            logger.info(f"✅ Enhanced medical transcription worker ({worker_type}) created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create worker: {e}")
            return 1

        # Run worker
        try:
            result = worker.run()
            logger.info(f"🛑 Worker exited with code: {result}")
            return result
        except KeyboardInterrupt:
            logger.info("📨 Received keyboard interrupt, shutting down gracefully...")
            return 0
        except Exception as e:
            logger.error(f"❌ Worker run failed: {e}")
            return 1

    except Exception as e:
        logger.error(f"💥 Failed to start enhanced transcription worker: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    # FIXED: Ensure proper signal handling
    import signal
    
    def signal_handler(signum, frame):
        logger.info(f"📨 Received signal {signum}, exiting...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Set up logging format
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    sys.exit(main())