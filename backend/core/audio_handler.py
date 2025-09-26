import os
import uuid
import time
import json
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile
import logging
import aiofiles
from typing import List
import aiofiles
from .redis_client import RedisClient
from .audio_chunker import AudioChunker

logger = logging.getLogger(__name__)


class AudioHandler:
    """
    Enhanced audio handler with chunking and parallel processing for FastAPI
    Think of this as the "Air Traffic Control" for your audio processing
    """

    def __init__(self, config):
        self.config = config
        
        # Enhanced Redis client with password
        self.redis_client = RedisClient(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            password=config.REDIS_PASSWORD,
            db=config.REDIS_DB,
        )

        # Initialize chunker for long audio files
        self.chunker = AudioChunker(
            chunks_folder=config.CHUNKS_FOLDER,
            chunk_duration=config.CHUNK_DURATION,
            overlap=config.CHUNK_OVERLAP,
        )

    async def save_uploaded_file(self, file: UploadFile, timestamp=None):
        """Save uploaded audio file and route to appropriate processing pipeline"""
        try:
            # Generate unique session ID
            session_id = str(uuid.uuid4())

            # Use provided timestamp or current time
            if timestamp is None:
                timestamp = str(int(time.time() * 1000))

            # Create filename with session ID and timestamp
            file_extension = self.get_file_extension(file.filename)
            filename = f"{session_id}_{timestamp}{file_extension}"
            filepath = self.config.UPLOAD_FOLDER / filename

            # Save file asynchronously
            # FIXED: Ensure upload directory exists
            self.config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

            # FIXED: Save file asynchronously with proper error handling
            logger.info(f"💾 Saving uploaded file: {filepath}")

            file_size = 0
            try:
                # Reset file pointer to beginning
                await file.seek(0)
                
                async with aiofiles.open(filepath, 'wb') as f:
                    # Read file content
                    content = await file.read()
                    if not content:
                        raise ValueError("Uploaded file is empty")
                    
                    # Write content to file
                    await f.write(content)
                    file_size = len(content)
                    
                logger.info(f"✅ File saved successfully: {filepath} ({file_size} bytes)")
                
                # FIXED: Verify file was actually saved
                if not filepath.exists():
                    raise FileNotFoundError(f"File was not saved properly: {filepath}")
                    
                # Double-check file size
                actual_file_size = filepath.stat().st_size
                if actual_file_size == 0:
                    raise ValueError("Saved file is empty")
                    
                if actual_file_size != file_size:
                    logger.warning(f"File size mismatch: expected {file_size}, got {actual_file_size}")
                    file_size = actual_file_size
                    
            except Exception as e:
                logger.error(f"❌ Error saving file: {e}")
                # Clean up partial file if it exists
                if filepath.exists():
                    try:
                        filepath.unlink()
                    except:
                        pass
                raise ValueError(f"Failed to save uploaded file: {e}")

            # Get file info
            file_size = actual_file_size  # Use the verified file size from above
            duration = self.chunker.get_audio_duration(str(filepath))

            logger.info(
                f"📊 File saved - Size: {file_size} bytes, Duration: {duration:.1f}s"
            )

            # Decide processing strategy based on file characteristics
            # Decide processing strategy based on file characteristics
            if self.chunker.should_chunk_audio(str(filepath), self.config.CHUNK_DURATION):
                logger.info("🚛 Large file detected - using chunked processing")
                return self._process_chunked_audio(session_id, filename, filepath, file_size, timestamp, duration)
            else:
                logger.info("🚗 Small file detected - using direct processing") 
                return self._process_direct_audio(session_id, filename, filepath, file_size, timestamp, duration)

        except Exception as e:
            logger.error(f"❌ Error saving uploaded file: {e}")
            raise

    def _process_chunked_audio(
        self, session_id, filename, filepath, file_size, timestamp, duration
    ):
        """Process large audio files using chunking strategy"""
        # FIXED: Verify file exists before chunking
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Audio file not found for chunking: {filepath}")
        try:
            # Create chunks
            logger.info(f"✂️ Creating chunks for session {session_id}")
            chunks_info = self.chunker.create_chunks(filepath, session_id)
            if not chunks_info:
                raise Exception("Failed to create audio chunks")

            logger.info(f"📦 Created {len(chunks_info)} chunks")

            # Store session metadata
            session_data = {
                "session_id": session_id,
                "status": "chunking_completed",
                "processing_strategy": "chunked",
                "original_filename": filename,
                "original_filepath": filepath,
                "file_size": file_size,
                "duration": duration,
                "total_chunks": len(chunks_info),
                "chunks_info": json.dumps(chunks_info),
                "uploaded_at": datetime.utcnow().isoformat(),
                "chunking_completed_at": datetime.utcnow().isoformat(),
            }

            # Set session status with longer expiry for chunked processing
            self.redis_client.set_session_status(
                session_id,
                session_data,
                expire_seconds=self.config.SESSION_EXPIRE_TIME,
            )

            # Queue chunks for parallel processing
            queued_chunks = self._queue_chunks_for_processing(session_id, chunks_info)
            logger.info(f"🚀 Queued {queued_chunks} chunks for parallel processing")

            # Update status to processing
            self.redis_client.update_session_status(
                session_id,
                {
                    "status": "processing",
                    "queued_chunks": queued_chunks,
                    "processing_started_at": datetime.utcnow().isoformat(),
                },
            )

            return {
                "session_id": session_id,
                "filename": filename,
                "filepath": filepath,
                "file_size": file_size,
                "timestamp": timestamp,
                "duration": duration,
                "processing_strategy": "chunked",
                "total_chunks": len(chunks_info),
                "queued_chunks": queued_chunks,
            }

        except Exception as e:
            logger.error(f"❌ Error in chunked processing: {e}")
            raise

    def _process_direct_audio(
        self, session_id, filename, filepath, file_size, timestamp, duration
    ):
        """Process small audio files directly (original method)"""
        # FIXED: Verify file exists before queuing
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Audio file not found for direct processing: {filepath}")
        try:
            # Queue for direct processing
            stream_id = self.queue_for_processing(
                session_id, filename, merged_file_path, file_size, 
                str(int(datetime.now().timestamp() * 1000))
            )

            # Add duration info
            self.redis_client.update_session_status(
                session_id, {"processing_strategy": "direct", "duration": duration}
            )

            return {
                "session_id": session_id,
                "filename": filename,
                "filepath": filepath,
                "file_size": file_size,
                "timestamp": timestamp,
                "duration": duration,
                "processing_strategy": "direct",
                "stream_id": stream_id,
            }

        except Exception as e:
            logger.error(f"❌ Error in direct processing: {e}")
            raise

    def _queue_chunks_for_processing(self, session_id, chunks_info):
        """Queue individual chunks for parallel processing"""
        try:
            queued_count = 0
            chunk_stream = self.config.AUDIO_CHUNK_STREAM

            for chunk_info in chunks_info:
                # Prepare chunk data for Redis stream
                chunk_data = {
                    "session_id": session_id,
                    "chunk_id": chunk_info["chunk_id"],
                    "chunk_index": chunk_info["chunk_index"],
                    "chunk_path": chunk_info["chunk_path"],
                    "start_time": chunk_info["start_time"],
                    "end_time": chunk_info["end_time"],
                    "duration": chunk_info["duration"],
                    "file_size": chunk_info["file_size"],
                    "queued_at": datetime.utcnow().isoformat(),
                    "type": "chunk_processing",
                }

                # Add to chunk processing stream
                stream_id = self.redis_client.add_to_stream(chunk_stream, chunk_data)

                # Store chunk status
                chunk_status_key = f"chunk_status:{chunk_info['chunk_id']}"
                self.redis_client.client.hset(
                    chunk_status_key,
                    mapping={
                        "status": "queued",
                        "stream_id": stream_id,
                        "session_id": session_id,
                        "queued_at": datetime.utcnow().isoformat(),
                    },
                )
                self.redis_client.client.expire(
                    chunk_status_key, self.config.SESSION_EXPIRE_TIME
                )

                queued_count += 1
                logger.debug(
                    f"📤 Queued chunk {chunk_info['chunk_index']} -> {stream_id}"
                )

            return queued_count

        except Exception as e:
            logger.error(f"❌ Error queuing chunks: {e}")
            return 0

    def queue_for_processing(
        self, session_id, filename, filepath, file_size, timestamp
    ):
        """Add audio file to processing queue (original method for direct processing)"""
        try:
            # Prepare data for Redis stream
            audio_data = {
                "session_id": session_id,
                "timestamp": timestamp,
                "filename": filename,
                "filepath": filepath,  # This should be the merged file path
                "file_size": file_size,
                "status": "uploaded",
                "uploaded_at": datetime.utcnow().isoformat(),
                "type": "direct_processing",  # Make sure this is "direct_processing"
            }

            # Add to Redis stream
            stream_name = self.config.AUDIO_INPUT_STREAM
            stream_id = self.redis_client.add_to_stream(stream_name, audio_data)

            # Set initial session status
            self.redis_client.set_session_status(
                session_id,
                {
                    "status": "queued",
                    "stream_id": stream_id,
                    "queued_at": datetime.utcnow().isoformat(),
                    "filename": filename,
                    "file_size": file_size,
                    "original_format": self.get_file_extension(filename).lstrip("."),
                },
                expire_seconds=self.config.SESSION_EXPIRE_TIME,
            )

            logger.info(f"📤 Queued for processing: {session_id} -> {stream_id}")
            return stream_id

        except Exception as e:
            logger.error(f"❌ Error queuing for processing: {e}")
            raise

    def get_session_status(self, session_id):
        """Get enhanced processing status for a session"""
        try:
            status_data = self.redis_client.get_session_status(session_id)
            if not status_data:
                return None

            # Add computed fields
            status_data["session_id"] = session_id

            # Add real-time progress for chunked processing
            if status_data.get("processing_strategy") == "chunked":
                progress_info = self._get_chunked_progress(session_id, status_data)
                status_data.update(progress_info)

            # Calculate processing time if completed
            if status_data.get("status") == "completed":
                started = status_data.get("processing_started_at")
                completed = status_data.get("processing_completed_at")
                if started and completed:
                    start_time = datetime.fromisoformat(started)
                    end_time = datetime.fromisoformat(completed)
                    duration = (end_time - start_time).total_seconds()
                    status_data["processing_duration"] = duration

            return status_data

        except Exception as e:
            logger.error(f"❌ Error getting session status: {e}")
            return None

    def _get_chunked_progress(self, session_id, status_data):
        """Get real-time progress for chunked processing"""
        try:
            total_chunks = status_data.get("total_chunks", 0)
            if total_chunks == 0:
                return {"progress_percent": 0, "completed_chunks": 0}

            # Count completed chunks
            completed_chunks = 0
            processing_chunks = 0
            failed_chunks = 0

            chunks_info_json = status_data.get("chunks_info", "[]")
            if isinstance(chunks_info_json, str):
                chunks_info = json.loads(chunks_info_json) if chunks_info_json else []
            elif isinstance(chunks_info_json, list):
                chunks_info = chunks_info_json
            else:
                chunks_info = []

            for chunk_info in chunks_info:
                chunk_id = chunk_info["chunk_id"]
                chunk_status_key = f"chunk_status:{chunk_id}"
                chunk_status = self.redis_client.client.hgetall(chunk_status_key)

                if chunk_status:
                    chunk_state = chunk_status.get("status", "queued")
                    if chunk_state == "completed":
                        completed_chunks += 1
                    elif chunk_state == "processing":
                        processing_chunks += 1
                    elif chunk_state == "error":
                        failed_chunks += 1

            progress_percent = int((completed_chunks / total_chunks) * 100)

            return {
                "progress_percent": progress_percent,
                "completed_chunks": completed_chunks,
                "processing_chunks": processing_chunks,
                "failed_chunks": failed_chunks,
                "pending_chunks": total_chunks
                - completed_chunks
                - processing_chunks
                - failed_chunks,
            }

        except Exception as e:
            logger.error(f"❌ Error getting chunked progress: {e}")
            return {"progress_percent": 0, "completed_chunks": 0}

    def check_chunked_completion(self, session_id):
        """Check if all chunks are completed and merge results"""
        try:
            status_data = self.get_session_status(session_id)
            if not status_data or status_data.get("processing_strategy") != "chunked":
                return False

            total_chunks = status_data.get("total_chunks", 0)
            completed_chunks = status_data.get("completed_chunks", 0)
            failed_chunks = status_data.get("failed_chunks", 0)

            # Check if all chunks are processed
            if completed_chunks + failed_chunks < total_chunks:
                return False  # Still processing

            if completed_chunks == 0:
                # All chunks failed
                self.redis_client.update_session_status(
                    session_id,
                    {
                        "status": "error",
                        "error": "All chunks failed to process",
                        "processing_completed_at": datetime.utcnow().isoformat(),
                    },
                )
                return True

            # Merge completed chunks
            logger.info(
                f"🧩 Merging {completed_chunks} completed chunks for session {session_id}"
            )
            merged_result = self._merge_chunk_results(session_id, status_data)

            if merged_result["status"] == "completed":
                # Save merged transcript
                transcript_path = self._save_merged_transcript(
                    session_id, merged_result
                )

                # Update session status
                final_status = {
                    "status": "completed",
                    "transcript_text": merged_result["text"],
                    "transcript_confidence": merged_result["confidence"],
                    "transcript_words": merged_result["words"],
                    "transcript_path": transcript_path,
                    "processing_completed_at": datetime.utcnow().isoformat(),
                    "chunks_processed": merged_result["chunks_processed"],
                }

                if failed_chunks > 0:
                    final_status["warning"] = (
                        f"{failed_chunks} chunks failed but transcript completed with available chunks"
                    )

                self.redis_client.update_session_status(session_id, final_status)

                # Cleanup chunks
                self._cleanup_session_chunks(session_id)

                logger.info(f"✅ Chunked processing completed for session {session_id}")
                return True
            else:
                # Merge failed
                self.redis_client.update_session_status(
                    session_id,
                    {
                        "status": "error",
                        "error": merged_result.get("error", "Failed to merge chunks"),
                        "processing_completed_at": datetime.utcnow().isoformat(),
                    },
                )
                return True

        except Exception as e:
            logger.error(f"❌ Error checking chunked completion: {e}")
            return False

    def _merge_chunk_results(self, session_id, status_data):
        """Merge results from completed chunks"""
        try:
            chunks_info_json = status_data.get("chunks_info", "[]")
            # FIXED: Handle both string and already-parsed list
            if isinstance(chunks_info_json, str):
                chunks_info = json.loads(chunks_info_json) if chunks_info_json else []
            elif isinstance(chunks_info_json, list):
                chunks_info = chunks_info_json
            else:
                chunks_info = []

            # Get completed chunk results
            chunk_results = []
            for chunk_info in chunks_info:
                chunk_id = chunk_info["chunk_id"]
                chunk_status_key = f"chunk_status:{chunk_id}"
                chunk_status = self.redis_client.client.hgetall(chunk_status_key)

                if chunk_status and chunk_status.get("status") == "completed":
                    chunk_result = {
                        "chunk_index": chunk_info["chunk_index"],
                        "transcript_text": chunk_status.get("transcript_text", ""),
                        "transcript_confidence": float(
                            chunk_status.get("transcript_confidence", 0)
                        ),
                        "duration": chunk_info["duration"],
                        "start_time": chunk_info["start_time"],
                        "end_time": chunk_info["end_time"],
                    }
                    chunk_results.append(chunk_result)

            if not chunk_results:
                return {
                    "status": "error",
                    "error": "No completed chunks found",
                    "text": "",
                    "confidence": 0.0,
                }

            # Use chunker to merge results
            return self.chunker.merge_transcripts(chunk_results)

        except Exception as e:
            logger.error(f"❌ Error merging chunk results: {e}")
            return {"status": "error", "error": str(e), "text": "", "confidence": 0.0}

    def _save_merged_transcript(self, session_id, merged_result):
        """Save merged transcript to file"""
        try:
            transcript_filename = f"{session_id}_merged_transcript.txt"
            transcript_path = (
                self.config.TRANSCRIPTS_FOLDER / transcript_filename
            )

            # Create enhanced medical transcript content
            content = f"Medical Transcript for Session: {session_id}\n"
            content += f"Generated: {datetime.utcnow().isoformat()}Z\n"
            content += f"Processing Method: Chunked Parallel Processing\n"
            content += f"Chunks Processed: {merged_result.get('chunks_processed', 0)}\n"
            content += (
                f"Overall Confidence Score: {merged_result.get('confidence', 0):.3f}\n"
            )
            content += f"Word Count: {merged_result.get('words', 0)}\n"
            content += (
                f"Total Duration: {merged_result.get('duration', 0):.2f} seconds\n"
            )
            content += "=" * 60 + "\n\n"
            content += merged_result.get("text", "No transcript available")
            content += "\n\n" + "=" * 60 + "\n"
            content += "Generated by MaiChart Medical Transcription System\n"
            content += "Enhanced with Parallel Chunk Processing\n"

            # Write to file
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"💾 Merged transcript saved to {transcript_path}")
            return str(transcript_path)

        except Exception as e:
            logger.error(f"❌ Error saving merged transcript: {e}")
            return ""

    def _cleanup_session_chunks(self, session_id):
        """Clean up chunk files and Redis data for a session"""
        try:
            # Cleanup chunk files
            cleaned_files = self.chunker.cleanup_chunks(session_id)

            # Cleanup chunk status keys
            chunk_keys = self.redis_client.client.keys(
                f"chunk_status:{session_id}_chunk_*"
            )
            if chunk_keys:
                self.redis_client.client.delete(*chunk_keys)
                logger.info(f"🧹 Cleaned up {len(chunk_keys)} chunk status keys")

            logger.info(
                f"🧹 Cleanup completed - {cleaned_files} files, {len(chunk_keys)} Redis keys"
            )

        except Exception as e:
            logger.warning(f"⚠️ Error during chunk cleanup: {e}")

    def get_transcript_data(self, session_id):
        """Get the transcript data for a session (enhanced for chunked processing)"""
        try:
            status_data = self.get_session_status(session_id)
            if not status_data or status_data.get("status") != "completed":
                return None

            transcript_text = status_data.get("transcript_text")
            if transcript_text:
                return {
                    "text": transcript_text,
                    "confidence": status_data.get("transcript_confidence", 0),
                    "words_count": status_data.get("transcript_words", 0),
                    "processing_duration": status_data.get("processing_duration", 0),
                    "processing_strategy": status_data.get(
                        "processing_strategy", "direct"
                    ),
                    "chunks_processed": status_data.get("chunks_processed", 1),
                }

            return None

        except Exception as e:
            logger.error(f"❌ Error getting transcript data: {e}")
            return None

    def cleanup_session_files(self, session_id):
        """Clean up uploaded files and chunks for a session"""
        try:
            status_data = self.get_session_status(session_id)
            if not status_data:
                return False

            files_to_clean = []

            # Add uploaded file
            if "filepath" in status_data:
                files_to_clean.append(status_data["filepath"])
            if "original_filepath" in status_data:
                files_to_clean.append(status_data["original_filepath"])

            # Add transcript file if exists
            if "transcript_path" in status_data:
                files_to_clean.append(status_data["transcript_path"])

            # Clean up chunks if it's a chunked session
            if status_data.get("processing_strategy") == "chunked":
                self._cleanup_session_chunks(session_id)

            # Remove main files
            cleaned_count = 0
            for file_path in files_to_clean:
                try:
                    if Path(file_path).exists():
                        Path(file_path).unlink()
                        cleaned_count += 1
                        logger.info(f"🗑️ Cleaned up file: {file_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not clean up {file_path}: {e}")

            logger.info(
                f"✅ Cleaned up {cleaned_count} main files for session {session_id}"
            )
            return cleaned_count > 0

        except Exception as e:
            logger.error(f"❌ Error cleaning up session files: {e}")
            return False

    @staticmethod
    def get_file_extension(filename):
        """Get file extension from filename"""
        if not filename:
            return ".webm"  # Default

        return Path(filename).suffix.lower() or ".webm"

    @staticmethod
    def is_allowed_file(filename, config):
        """Check if file extension is allowed"""
        if not filename:
            return False

        extension = Path(filename).suffix.lower().lstrip(".")
        return extension in config.ALLOWED_EXTENSIONS

    def get_system_stats(self):
        """Get enhanced system statistics"""
        try:
            stream_name = self.config.AUDIO_INPUT_STREAM
            chunk_stream_name = self.config.AUDIO_CHUNK_STREAM
            consumer_group = self.config.CONSUMER_GROUP
            chunk_consumer_group = self.config.CHUNK_CONSUMER_GROUP

            stats = {
                "redis_connected": self.redis_client.ping(),
                "stream_info": self.redis_client.get_stream_info(stream_name),
                "chunk_stream_info": self.redis_client.get_stream_info(
                    chunk_stream_name
                ),
                "pending_messages": len(
                    self.redis_client.get_pending_messages(stream_name, consumer_group)
                ),
                "pending_chunks": len(
                    self.redis_client.get_pending_messages(
                        chunk_stream_name, chunk_consumer_group
                    )
                ),
                "upload_folder_size": self._get_folder_size(
                    self.config.UPLOAD_FOLDER
                ),
                "chunks_folder_size": self._get_folder_size(
                    self.config.CHUNKS_FOLDER
                ),
            }

            return stats

        except Exception as e:
            logger.error(f"❌ Error getting system stats: {e}")
            return {"error": str(e)}

    @staticmethod
    def _get_folder_size(folder_path):
        """Get total size of files in a folder"""
        try:
            folder = Path(folder_path)
            if not folder.exists():
                return 0

            total_size = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
            return total_size

        except Exception:
            return 0

    def initialize_streaming_session(self, session_id: str) -> bool:
        """Initialize a new streaming session"""
        try:
            # Create streaming session directory
            streaming_dir = self.config.UPLOAD_FOLDER / f"streaming_{session_id}"
            streaming_dir.mkdir(exist_ok=True)
            
            # Initialize session status
            session_data = {
                "session_id": session_id,
                "status": "recording",
                "recording_mode": "streaming",
                "chunks_received": 0,
                "total_size": 0,
                "streaming_dir": str(streaming_dir),
                "created_at": datetime.utcnow().isoformat(),
                "last_chunk_received": False
            }
            
            # Set session status with longer expiry for streaming
            self.redis_client.set_session_status(
                session_id,
                session_data,
                expire_seconds=self.config.SESSION_EXPIRE_TIME * 2  # Double expiry for streaming
            )
            
            logger.info(f"✅ Streaming session initialized: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error initializing streaming session {session_id}: {e}")
            return False

    async def save_streaming_chunk(self, file: UploadFile, session_id: str, 
                                chunk_sequence: int, is_last_chunk: bool, 
                                timestamp: str = None) -> dict:
        """Save a streaming audio chunk and manage session state"""
        try:
            # Get session data
            session_data = self.get_session_status(session_id)
            if not session_data:
                raise ValueError(f"Streaming session not found: {session_id}")
            
            if session_data.get("recording_mode") != "streaming":
                raise ValueError(f"Session {session_id} is not a streaming session")
            
            # Validate chunk sequence
            expected_sequence = session_data.get("chunks_received", 0)
            if chunk_sequence != expected_sequence:
                logger.warning(f"⚠️ Unexpected chunk sequence for {session_id}: expected {expected_sequence}, got {chunk_sequence}")
            
            # Create chunk filename
            streaming_dir = Path(session_data["streaming_dir"])
            chunk_filename = f"chunk_{chunk_sequence:03d}.webm"
            chunk_filepath = streaming_dir / chunk_filename
            
            # Save chunk file
            if timestamp is None:
                timestamp = str(int(datetime.now().timestamp() * 1000))
            
            # Reset file pointer and save
            await file.seek(0)
            file_size = 0
            
            import aiofiles
            async with aiofiles.open(chunk_filepath, 'wb') as f:
                content = await file.read()
                if not content:
                    raise ValueError("Chunk file is empty")
                await f.write(content)
                file_size = len(content)
            
            # Verify file was saved
            if not chunk_filepath.exists():
                raise FileNotFoundError(f"Chunk file was not saved: {chunk_filepath}")
            
            # Update session status
            current_total_size = session_data.get("total_size", 0) + file_size
            update_data = {
                "chunks_received": chunk_sequence + 1,
                "total_size": current_total_size,
                "last_chunk_at": datetime.utcnow().isoformat(),
                "last_chunk_sequence": chunk_sequence,
                "last_chunk_received": is_last_chunk
            }
            
            self.redis_client.update_session_status(session_id, update_data)
            
            logger.info(f"📦 Streaming chunk saved: {session_id} chunk {chunk_sequence} ({file_size} bytes)")
            
            result = {
                "session_id": session_id,
                "filename": chunk_filename,
                "filepath": str(chunk_filepath),
                "file_size": file_size,
                "chunk_sequence": chunk_sequence,
                "is_last_chunk": is_last_chunk,
                "processing_triggered": False
            }
            
            # If this is the last chunk, trigger processing
            if is_last_chunk:
                success = self._finalize_streaming_session(session_id)
                result["processing_triggered"] = success
                logger.info(f"🏁 Last chunk received for {session_id}, processing {'triggered' if success else 'failed'}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error saving streaming chunk: {e}")
            raise

    def _finalize_streaming_session(self, session_id: str) -> bool:
        """Finalize streaming session and trigger processing"""
        try:
            session_data = self.get_session_status(session_id)
            if not session_data:
                logger.error(f"❌ Session not found for finalization: {session_id}")
                return False
            
            streaming_dir = Path(session_data["streaming_dir"])
            if not streaming_dir.exists():
                logger.error(f"❌ Streaming directory not found: {streaming_dir}")
                return False
            
            # Merge chunks into single file
            merged_file_path = self._merge_streaming_chunks(session_id, streaming_dir)
            if not merged_file_path:
                logger.error(f"❌ Failed to merge streaming chunks for {session_id}")
                return False
            
            # Get merged file info
            file_size = os.path.getsize(merged_file_path)
            duration = self.chunker.get_audio_duration(str(merged_file_path))
            
            # Update session status
            filename = Path(merged_file_path).name
            update_data = {
                "status": "processing",
                "step": "chunks_merged",
                "merged_file_path": str(merged_file_path),
                "filename": filename,
                "file_size": file_size,
                "audio_duration": duration,
                "processing_started_at": datetime.utcnow().isoformat(),
                "processing_strategy": "streaming_merged"
            }
            
            self.redis_client.update_session_status(session_id, update_data)
            
            # Queue for transcription processing
            stream_id = self.queue_for_processing(
                session_id, filename, merged_file_path, file_size, 
                str(int(datetime.now().timestamp() * 1000))
            )
            
            if stream_id:
                # Update session with stream info
                self.redis_client.update_session_status(session_id, {
                    "stream_id": stream_id,
                    "queued_for_transcription_at": datetime.utcnow().isoformat()
                })
                
                logger.info(f"✅ Streaming session finalized and queued: {session_id} -> {stream_id}")
                return True
            else:
                logger.error(f"❌ Failed to queue merged file for transcription: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error finalizing streaming session {session_id}: {e}")
            return False

    def _merge_streaming_chunks(self, session_id: str, streaming_dir: Path) -> str:
        """Merge streaming chunks into a single audio file"""
        try:
            # Find all chunk files
            chunk_files = sorted(streaming_dir.glob("chunk_*.webm"))
            if not chunk_files:
                logger.error(f"❌ No chunk files found in {streaming_dir}")
                return None
            
            logger.info(f"🔗 Merging {len(chunk_files)} streaming chunks for {session_id}")
            
            # Create output filename
            merged_filename = f"{session_id}_streaming_merged.webm"
            merged_filepath = self.config.UPLOAD_FOLDER / merged_filename
            
            # Use ffmpeg to concatenate chunks
            if self.chunker.ffmpeg_available:
                success = self._merge_chunks_with_ffmpeg(chunk_files, merged_filepath)
            else:
                # Fallback: simple binary concatenation
                success = self._merge_chunks_binary(chunk_files, merged_filepath)
            
            if success and merged_filepath.exists():
                # Cleanup chunk files and directory
                self._cleanup_streaming_chunks(streaming_dir)
                logger.info(f"✅ Streaming chunks merged successfully: {merged_filepath}")
                return str(merged_filepath)
            else:
                logger.error(f"❌ Failed to merge streaming chunks for {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error merging streaming chunks: {e}")
            return None

    def _merge_chunks_with_ffmpeg(self, chunk_files: List[Path], output_path: Path) -> bool:
        """Merge chunks using ffmpeg (preferred method)"""
        try:
            import subprocess
            import tempfile
            
            # Create temporary file list for ffmpeg
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for chunk_file in chunk_files:
                    f.write(f"file '{chunk_file.absolute()}'\n")
                filelist_path = f.name
            
            try:
                # FFmpeg concat command
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", filelist_path,
                    "-c", "copy",
                    str(output_path)
                ]
                
                result = subprocess.run(
                    cmd, capture_output=True, text=True, check=True
                )
                
                logger.info("✅ FFmpeg chunk merging completed")
                return True
                
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ FFmpeg merge failed: {e}")
                logger.error(f"FFmpeg stderr: {e.stderr}")
                return False
            finally:
                # Cleanup temp file
                try:
                    os.unlink(filelist_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"❌ Error in FFmpeg merge: {e}")
            return False

    def _merge_chunks_binary(self, chunk_files: List[Path], output_path: Path) -> bool:
        """Fallback: merge chunks using binary concatenation"""
        try:
            logger.info("📎 Using binary concatenation for chunk merging")
            
            with open(output_path, 'wb') as outfile:
                for chunk_file in chunk_files:
                    with open(chunk_file, 'rb') as infile:
                        outfile.write(infile.read())
            
            logger.info("✅ Binary chunk merging completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Binary merge failed: {e}")
            return False

    def _cleanup_streaming_chunks(self, streaming_dir: Path):
        """Clean up streaming chunk files and directory"""
        try:
            # Add a small delay to ensure file operations are complete
            import time
            time.sleep(1)
            
            # Remove all chunk files
            chunk_files = list(streaming_dir.glob("chunk_*.webm"))
            for chunk_file in chunk_files:
                try:
                    if chunk_file.exists():  # Add existence check
                        chunk_file.unlink()
                except Exception as e:
                    logger.warning(f"⚠️ Could not delete chunk file {chunk_file}: {e}")
            
            # Remove directory if empty
            try:
                if streaming_dir.exists() and not any(streaming_dir.iterdir()):  # Only if empty
                    streaming_dir.rmdir()
                    logger.info(f"🧹 Cleaned up streaming directory: {streaming_dir}")
            except OSError as e:
                logger.warning(f"⚠️ Could not remove streaming directory {streaming_dir}: {e}")
                
        except Exception as e:
            logger.warning(f"⚠️ Error cleaning up streaming chunks: {e}")

    def get_streaming_session_status(self, session_id: str) -> dict:
        """Get enhanced status for streaming sessions"""
        try:
            status_data = self.get_session_status(session_id)
            if not status_data:
                return None
            
            # Add streaming-specific information
            if status_data.get("recording_mode") == "streaming":
                chunks_received = status_data.get("chunks_received", 0)
                total_size = status_data.get("total_size", 0)
                is_recording = status_data.get("status") == "recording"
                
                status_data.update({
                    "streaming_info": {
                        "chunks_received": chunks_received,
                        "total_size_mb": round(total_size / (1024 * 1024), 2),
                        "is_recording": is_recording,
                        "estimated_duration": chunks_received * 5,  # 5 seconds per chunk
                        "last_chunk_received": status_data.get("last_chunk_received", False)
                    }
                })
            
            return status_data
            
        except Exception as e:
            logger.error(f"❌ Error getting streaming session status: {e}")
            return None

    def cleanup_streaming_session_files(self, session_id: str) -> bool:
        """Clean up all files for a streaming session"""
        try:
            session_data = self.get_session_status(session_id)
            if not session_data:
                return False
            
            files_cleaned = 0
            
            # Clean up streaming directory if exists
            streaming_dir = session_data.get("streaming_dir")
            if streaming_dir and Path(streaming_dir).exists():
                self._cleanup_streaming_chunks(Path(streaming_dir))
                files_cleaned += 1
            
            # Clean up merged file if exists
            merged_file = session_data.get("merged_file_path")
            if merged_file and Path(merged_file).exists():
                try:
                    Path(merged_file).unlink()
                    files_cleaned += 1
                    logger.info(f"🗑️ Deleted merged file: {merged_file}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not delete merged file {merged_file}: {e}")
            
            # Clean up other files using existing method
            if self.cleanup_session_files(session_id):
                files_cleaned += 1
            
            logger.info(f"✅ Cleaned up {files_cleaned} file groups for streaming session {session_id}")
            return files_cleaned > 0
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up streaming session: {e}")
            return False