# backend/api/routes.py - FIXED: File size limits and upload handling
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional, List
import logging
from datetime import datetime
from pathlib import Path
import os
import json
import tempfile

from core.audio_handler import AudioHandler
from .utils import validate_upload_request, handle_api_error, get_config

logger = logging.getLogger(__name__)

# Create router
api_router = APIRouter()

# FIXED: Increase file size limits
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB

# Dependency to get config
def get_config_dep(request: Request):
    return request.app.state.config


@api_router.post("/initialize_streaming_session")
async def initialize_streaming_session(
    request: Request,
    config = Depends(get_config_dep)
):
    """Initialize a new streaming session"""
    try:
        # Get session_id from request body
        body = await request.json()
        session_id = body.get("session_id")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        
        audio_handler = AudioHandler(config)
        success = audio_handler.initialize_streaming_session(session_id)
        
        if success:
            return JSONResponse(content={
                "success": True,
                "session_id": session_id,
                "message": "Streaming session initialized"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to initialize streaming session")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing streaming session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")


@api_router.post("/upload_audio")
async def upload_audio(
    request: Request,
    audio: UploadFile = File(...),
    timestamp: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    chunk_sequence: Optional[int] = Form(None),
    is_streaming: Optional[bool] = Form(False),
    is_last_chunk: Optional[bool] = Form(False),
    config = Depends(get_config_dep)
):
    """Upload audio file for processing - Enhanced for streaming with FIXED file size handling"""
    try:
        logger.info(f"Audio upload request - File: {audio.filename}, Size: {audio.size}, Streaming: {is_streaming}")

        # FIXED: Check file size early
        if audio.size and audio.size > MAX_UPLOAD_SIZE:
            logger.error(f"File too large: {audio.size} bytes (max: {MAX_UPLOAD_SIZE})")
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE // (1024 * 1024)}MB. Your file: {audio.size // (1024 * 1024)}MB"
            )

        # Enhanced validation with streaming support
        validation_result = await validate_upload_request(audio, config)
        if not validation_result["valid"]:
            logger.error(f"Validation failed: {validation_result['error']}")
            raise HTTPException(status_code=400, detail=validation_result["error"])

        # Use provided timestamp or current time
        if timestamp is None:
            timestamp = str(int(datetime.now().timestamp() * 1000))

        # Initialize audio handler
        audio_handler = AudioHandler(config)

        # Handle streaming vs regular upload
        if is_streaming:
            # Streaming chunk upload
            if not session_id:
                raise HTTPException(status_code=400, detail="session_id required for streaming uploads")
            if chunk_sequence is None:
                raise HTTPException(status_code=400, detail="chunk_sequence required for streaming uploads")
                
            result = await audio_handler.save_streaming_chunk(
                audio, session_id, chunk_sequence, is_last_chunk, timestamp
            )
            
            logger.info(f"✅ Streaming chunk uploaded - Session: {session_id}, Chunk: {chunk_sequence}")
            
            return JSONResponse(content={
                "success": True,
                "session_id": session_id,
                "chunk_sequence": chunk_sequence,
                "is_last_chunk": is_last_chunk,
                "filename": result["filename"],
                "size": result["file_size"],
                "message": "Streaming chunk uploaded successfully",
                "processing_triggered": result.get("processing_triggered", False)
            })
        else:
            # Regular file upload (existing logic)
            try:
                result = await audio_handler.save_uploaded_file(audio, timestamp)
                
                logger.info(f"✅ Upload successful - Session: {result['session_id']}")
                
                return JSONResponse(content={
                    "success": True,
                    "id": result["session_id"],
                    "filename": result["filename"],
                    "size": result["file_size"],
                    "duration": result.get("duration", 0),
                    "processing_strategy": result.get("processing_strategy", "direct"),
                    "message": "Audio uploaded successfully and queued for transcription",
                })
                
            except FileNotFoundError as e:
                logger.error(f"File not found after upload: {e}")
                raise HTTPException(status_code=500, detail="File upload failed - file not found after saving")
            except ValueError as e:
                logger.error(f"File validation error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                logger.error(f"Unexpected upload error: {e}")
                raise HTTPException(status_code=500, detail=f"Upload processing failed: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@api_router.get("/status/{session_id}")
async def get_status(session_id: str, request: Request, config = Depends(get_config_dep)):
    """Get processing status for a session"""
    try:
        audio_handler = AudioHandler(config)
        status_data = audio_handler.get_session_status(session_id)

        if not status_data:
            raise HTTPException(status_code=404, detail="Session not found")

        return JSONResponse(content=status_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(status_code=500, detail="Status check failed")


@api_router.get("/transcript/{session_id}")
async def get_transcript(session_id: str, request: Request, config = Depends(get_config_dep)):
    """Get the transcript for a session"""
    try:
        audio_handler = AudioHandler(config)
        transcript_data = audio_handler.get_transcript_data(session_id)

        if not transcript_data:
            raise HTTPException(status_code=404, detail="Transcript not found or not ready")

        return JSONResponse(content={
            "success": True,
            "session_id": session_id,
            "transcript": transcript_data
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transcript: {str(e)}")
        raise HTTPException(status_code=500, detail="Transcript retrieval failed")


@api_router.get("/transcript/{session_id}/download")
async def download_transcript(session_id: str, request: Request, config = Depends(get_config_dep)):
    """Download transcript as a text file"""
    try:
        audio_handler = AudioHandler(config)
        status_data = audio_handler.get_session_status(session_id)
        
        if not status_data or status_data.get("status") != "completed":
            raise HTTPException(status_code=404, detail="Transcript not found or not ready")

        transcript_path = status_data.get("transcript_path")
        if transcript_path and os.path.exists(transcript_path):
            return FileResponse(
                path=transcript_path,
                filename=f"medical_note_{session_id[:8]}.txt",
                media_type="text/plain"
            )
        else:
            raise HTTPException(status_code=404, detail="Transcript file not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading transcript: {str(e)}")
        raise HTTPException(status_code=500, detail="Download failed")


@api_router.get("/notes")
async def get_all_notes(request: Request, config = Depends(get_config_dep)):
    """Get all transcribed notes"""
    try:
        audio_handler = AudioHandler(config)
        
        # Get all completed sessions from Redis
        all_notes = []
        
        # Search for all session status keys
        session_keys = audio_handler.redis_client.client.keys("session_status:*")
        
        for key in session_keys:
            session_id = key.split(":")[-1]
            status_data = audio_handler.get_session_status(session_id)
            
            if status_data and status_data.get("status") == "completed":
                # Extract note information
                note = {
                    "session_id": session_id,
                    "text": status_data.get("transcript_text", ""),
                    "confidence": float(status_data.get("transcript_confidence", 0)),
                    "created_at": status_data.get("processing_completed_at") or status_data.get("uploaded_at"),
                    "filename": status_data.get("filename", ""),
                    "file_size": status_data.get("file_size", 0),
                    "duration": float(status_data.get("audio_duration", 0)),
                    "word_count": len(status_data.get("transcript_text", "").split()) if status_data.get("transcript_text") else 0,
                    "recording_mode": status_data.get("recording_mode", "upload")
                }
                
                all_notes.append(note)
        
        # Sort by creation date (newest first)
        all_notes.sort(key=lambda x: x["created_at"] or "", reverse=True)
        
        logger.info(f"Retrieved {len(all_notes)} completed notes")
        
        return JSONResponse(content={
            "success": True,
            "count": len(all_notes),
            "notes": all_notes
        })

    except Exception as e:
        logger.error(f"Error getting all notes: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notes")


@api_router.delete("/cleanup/{session_id}")
async def cleanup_session(session_id: str, request: Request, config = Depends(get_config_dep)):
    """Clean up files and data for a session"""
    try:
        audio_handler = AudioHandler(config)
        
        # Clean up files
        success = audio_handler.cleanup_session_files(session_id)
        
        # Also remove from Redis
        audio_handler.redis_client.client.delete(f"session_status:{session_id}")
        
        if success:
            message = "Session cleaned up successfully"
        else:
            message = "Session data removed (no files to clean up)"
            
        return JSONResponse(content={"success": True, "message": message})

    except Exception as e:
        logger.error(f"Error cleaning up session: {str(e)}")
        raise HTTPException(status_code=500, detail="Cleanup failed")

@api_router.get("/queue_status")
async def get_queue_status(request: Request, config = Depends(get_config_dep)):
    """Get queue status for debugging"""
    try:
        audio_handler = AudioHandler(config)
        
        # Get stream info for both streams
        direct_stream_info = audio_handler.redis_client.get_stream_info(config.AUDIO_INPUT_STREAM)
        chunk_stream_info = audio_handler.redis_client.get_stream_info(config.AUDIO_CHUNK_STREAM)
        
        # Get pending messages for consumer groups
        direct_pending = audio_handler.redis_client.get_pending_messages(
            config.AUDIO_INPUT_STREAM, config.CONSUMER_GROUP
        )
        chunk_pending = audio_handler.redis_client.get_pending_messages(
            config.AUDIO_CHUNK_STREAM, config.CHUNK_CONSUMER_GROUP
        )
        
        return JSONResponse(content={
            "success": True,
            "queues": {
                "direct_transcription": {
                    "stream_length": direct_stream_info.get("length", 0),
                    "pending_messages": len(direct_pending),
                    "consumer_groups": direct_stream_info.get("groups", 0)
                },
                "chunk_transcription": {
                    "stream_length": chunk_stream_info.get("length", 0),
                    "pending_messages": len(chunk_pending), 
                    "consumer_groups": chunk_stream_info.get("groups", 0)
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting queue status: {str(e)}")
        raise HTTPException(status_code=500, detail="Queue status check failed")
    
@api_router.get("/health")
async def health_check(request: Request, config = Depends(get_config_dep)):
    """Health check endpoint"""
    try:
        audio_handler = AudioHandler(config)
        stats = audio_handler.get_system_stats()

        return JSONResponse(content={
            "status": "healthy" if stats.get("redis_connected") else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "stats": stats,
        })

    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )