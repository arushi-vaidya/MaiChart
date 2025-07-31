from fastapi import UploadFile, HTTPException
from werkzeug.utils import secure_filename
import logging
from pathlib import Path

from core.audio_handler import AudioHandler

logger = logging.getLogger(__name__)


async def validate_upload_request(file: UploadFile, config):
    """Validate audio upload request for FastAPI"""

    # Check if file is provided
    if not file:
        return {"valid": False, "error": "No audio file provided"}

    # Check if file has content
    if file.size == 0:
        return {"valid": False, "error": "Empty file uploaded"}

    # Check file size
    if file.size and file.size > config.MAX_FILE_SIZE:
        return {
            "valid": False,
            "error": f"File too large. Maximum size: {config.MAX_FILE_SIZE // (1024 * 1024)}MB",
        }

    # Check file extension
    if not AudioHandler.is_allowed_file(file.filename, config):
        return {
            "valid": False,
            "error": f"File type not allowed. Allowed types: {', '.join(config.ALLOWED_EXTENSIONS)}",
        }

    # Secure the filename
    filename = secure_filename(file.filename) if file.filename else "audio_file"
    if not filename:
        return {"valid": False, "error": "Invalid filename"}

    return {"valid": True, "filename": filename}


def handle_api_error(exception, message="An error occurred"):
    """Handle API errors consistently for FastAPI"""
    error_msg = f"{message}: {str(exception)}"
    logger.error(error_msg)
    raise HTTPException(status_code=500, detail=message)


def format_file_size(size_bytes):
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def get_audio_duration_estimate(file_size):
    """Estimate audio duration based on file size (rough estimate)"""
    # Rough estimate: WebM/Opus typically ~1KB per second of audio
    estimated_seconds = file_size / 1024

    minutes = int(estimated_seconds // 60)
    seconds = int(estimated_seconds % 60)

    if minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def validate_session_id(session_id):
    """Validate session ID format"""
    import uuid

    try:
        uuid.UUID(session_id)
        return True
    except ValueError:
        return False


def get_config(request):
    """Get config from FastAPI request"""
    return request.app.state.config