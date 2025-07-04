import os
import uuid
import time
from pathlib import Path
from datetime import datetime
from flask import current_app
import logging

from .redis_client import RedisClient

logger = logging.getLogger(__name__)


class AudioHandler:
    """Handle audio file operations and processing coordination"""

    def __init__(self):
        # Updated to include password
        self.redis_client = RedisClient(
            host=current_app.config["REDIS_HOST"],
            port=current_app.config["REDIS_PORT"],
            password=current_app.config["REDIS_PASSWORD"],
            db=current_app.config["REDIS_DB"],
        )

    def save_uploaded_file(self, file, timestamp=None):
        """Save uploaded audio file and queue for processing"""
        try:
            # Generate unique session ID
            session_id = str(uuid.uuid4())

            # Use provided timestamp or current time
            if timestamp is None:
                timestamp = str(int(time.time() * 1000))

            # Create filename with session ID and timestamp
            file_extension = self.get_file_extension(file.filename)
            filename = f"{session_id}_{timestamp}{file_extension}"
            filepath = current_app.config["UPLOAD_FOLDER"] / filename

            # Save file
            logger.info(f"Saving uploaded file: {filepath}")
            file.save(str(filepath))

            # Get file info
            file_size = filepath.stat().st_size
            logger.info(f"File saved successfully. Size: {file_size} bytes")

            # Queue for processing (direct processing, no conversion)
            self.queue_for_processing(
                session_id, filename, str(filepath), file_size, timestamp
            )

            return {
                "session_id": session_id,
                "filename": filename,
                "filepath": str(filepath),
                "file_size": file_size,
                "timestamp": timestamp,
            }

        except Exception as e:
            logger.error(f"Error saving uploaded file: {e}")
            raise

    def queue_for_processing(
        self, session_id, filename, filepath, file_size, timestamp
    ):
        """Add audio file to processing queue (direct processing)"""
        try:
            # Prepare data for Redis stream
            audio_data = {
                "session_id": session_id,
                "timestamp": timestamp,
                "filename": filename,
                "filepath": filepath,
                "file_size": file_size,
                "status": "uploaded",
                "uploaded_at": datetime.utcnow().isoformat(),
            }

            # Add to Redis stream
            stream_name = current_app.config["AUDIO_INPUT_STREAM"]
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
                expire_seconds=current_app.config["SESSION_EXPIRE_TIME"],
            )

            logger.info(f"Queued for processing: {session_id} -> {stream_id}")
            return stream_id

        except Exception as e:
            logger.error(f"Error queuing for processing: {e}")
            raise

    def get_session_status(self, session_id):
        """Get processing status for a session"""
        try:
            status_data = self.redis_client.get_session_status(session_id)
            if not status_data:
                return None

            # Add computed fields
            status_data["session_id"] = session_id

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
            logger.error(f"Error getting session status: {e}")
            return None

    def get_transcript_data(self, session_id):
        """Get the transcript data for a session"""
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
                }

            return None

        except Exception as e:
            logger.error(f"Error getting transcript data: {e}")
            return None

    def cleanup_session_files(self, session_id):
        """Clean up uploaded files for a session"""
        try:
            status_data = self.get_session_status(session_id)
            if not status_data:
                return False

            files_to_clean = []

            # Add uploaded file
            if "filepath" in status_data:
                files_to_clean.append(status_data["filepath"])

            # Add transcript file if exists
            if "transcript_path" in status_data:
                files_to_clean.append(status_data["transcript_path"])

            # Remove files
            cleaned_count = 0
            for file_path in files_to_clean:
                try:
                    if Path(file_path).exists():
                        Path(file_path).unlink()
                        cleaned_count += 1
                        logger.info(f"Cleaned up file: {file_path}")
                except Exception as e:
                    logger.warning(f"Could not clean up {file_path}: {e}")

            logger.info(f"Cleaned up {cleaned_count} files for session {session_id}")
            return cleaned_count > 0

        except Exception as e:
            logger.error(f"Error cleaning up session files: {e}")
            return False

    @staticmethod
    def get_file_extension(filename):
        """Get file extension from filename"""
        if not filename:
            return ".webm"  # Default

        return Path(filename).suffix.lower() or ".webm"

    @staticmethod
    def is_allowed_file(filename):
        """Check if file extension is allowed"""
        if not filename:
            return False

        extension = Path(filename).suffix.lower().lstrip(".")
        return extension in current_app.config["ALLOWED_EXTENSIONS"]

    def get_system_stats(self):
        """Get system statistics"""
        try:
            stream_name = current_app.config["AUDIO_INPUT_STREAM"]
            consumer_group = current_app.config["CONSUMER_GROUP"]

            stats = {
                "redis_connected": self.redis_client.ping(),
                "stream_info": self.redis_client.get_stream_info(stream_name),
                "pending_messages": len(
                    self.redis_client.get_pending_messages(stream_name, consumer_group)
                ),
                "upload_folder_size": self._get_folder_size(
                    current_app.config["UPLOAD_FOLDER"]
                ),
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
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
