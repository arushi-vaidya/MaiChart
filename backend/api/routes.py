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


# Dependency to get config
def get_config_dep(request: Request):
    return request.app.state.config


@api_router.post("/upload_audio")
async def upload_audio(
    request: Request,
    audio: UploadFile = File(...),
    timestamp: Optional[str] = Form(None),
    config = Depends(get_config_dep)
):
    """Upload audio file for processing - FIXED"""
    try:
        logger.info(f"Audio upload request received - File: {audio.filename}, Size: {audio.size}")

        # FIXED: Enhanced validation with better error messages
        validation_result = await validate_upload_request(audio, config)
        if not validation_result["valid"]:
            logger.error(f"Validation failed: {validation_result['error']}")
            raise HTTPException(status_code=400, detail=validation_result["error"])

        # Use provided timestamp or current time
        if timestamp is None:
            timestamp = str(int(datetime.now().timestamp() * 1000))

        # Initialize audio handler
        audio_handler = AudioHandler(config)

        # FIXED: Better error handling and logging
        try:
            # Save file and queue for processing
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
                    "word_count": len(status_data.get("transcript_text", "").split()) if status_data.get("transcript_text") else 0
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


@api_router.get("/notes/search")
async def search_notes(q: str, request: Request, config = Depends(get_config_dep)):
    """Search notes by text content"""
    try:
        if not q:
            raise HTTPException(status_code=400, detail="Search query required")

        query = q.lower()
        audio_handler = AudioHandler(config)
        
        # Get all notes
        all_notes = []
        session_keys = audio_handler.redis_client.client.keys("session_status:*")
        
        for key in session_keys:
            session_id = key.split(":")[-1]
            status_data = audio_handler.get_session_status(session_id)
            
            if status_data and status_data.get("status") == "completed":
                transcript_text = status_data.get("transcript_text", "").lower()
                
                # Search in transcript text and session ID
                if query in transcript_text or query in session_id.lower():
                    note = {
                        "session_id": session_id,
                        "text": status_data.get("transcript_text", ""),
                        "confidence": float(status_data.get("transcript_confidence", 0)),
                        "created_at": status_data.get("processing_completed_at") or status_data.get("uploaded_at"),
                        "filename": status_data.get("filename", ""),
                        "duration": float(status_data.get("audio_duration", 0)),
                        "word_count": len(status_data.get("transcript_text", "").split()) if status_data.get("transcript_text") else 0
                    }
                    
                    all_notes.append(note)
        
        # Sort by relevance and creation date
        all_notes.sort(key=lambda x: x["created_at"] or "", reverse=True)
        
        return JSONResponse(content={
            "success": True,
            "query": q,
            "count": len(all_notes),
            "notes": all_notes
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching notes: {str(e)}")
        raise HTTPException(status_code=500, detail="Search failed")


@api_router.get("/notes/stats")
async def get_notes_stats(request: Request, config = Depends(get_config_dep)):
    """Get statistics about all notes"""
    try:
        audio_handler = AudioHandler(config)
        
        total_notes = 0
        total_words = 0
        total_duration = 0
        confidence_scores = []
        notes_today = 0
        notes_this_week = 0
        
        from datetime import datetime, timedelta
        today = datetime.now().date()
        week_ago = datetime.now() - timedelta(days=7)
        
        session_keys = audio_handler.redis_client.client.keys("session_status:*")
        
        for key in session_keys:
            session_id = key.split(":")[-1]
            status_data = audio_handler.get_session_status(session_id)
            
            if status_data and status_data.get("status") == "completed":
                total_notes += 1
                
                # Word count
                words = len(status_data.get("transcript_text", "").split())
                total_words += words
                
                # Duration
                duration = float(status_data.get("audio_duration", 0))
                total_duration += duration
                
                # Confidence
                confidence = float(status_data.get("transcript_confidence", 0))
                confidence_scores.append(confidence)
                
                # Date-based counts
                created_at = status_data.get("processing_completed_at") or status_data.get("uploaded_at")
                if created_at:
                    try:
                        note_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
                        if note_date == today:
                            notes_today += 1
                        if datetime.fromisoformat(created_at.replace('Z', '+00:00')) >= week_ago:
                            notes_this_week += 1
                    except:
                        pass
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        avg_words = total_words / total_notes if total_notes > 0 else 0
        avg_duration = total_duration / total_notes if total_notes > 0 else 0
        
        return JSONResponse(content={
            "success": True,
            "stats": {
                "total_notes": total_notes,
                "total_words": total_words,
                "total_duration": round(total_duration, 1),
                "average_confidence": round(avg_confidence, 3),
                "average_words": round(avg_words, 1),
                "average_duration": round(avg_duration, 1),
                "notes_today": notes_today,
                "notes_this_week": notes_this_week,
                "confidence_distribution": {
                    "high": len([c for c in confidence_scores if c >= 0.8]),
                    "medium": len([c for c in confidence_scores if 0.6 <= c < 0.8]),
                    "low": len([c for c in confidence_scores if c < 0.6])
                }
            }
        })

    except Exception as e:
        logger.error(f"Error getting notes stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Stats retrieval failed")


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


@api_router.get("/stats")
async def get_stats(request: Request, config = Depends(get_config_dep)):
    """Get system statistics"""
    try:
        audio_handler = AudioHandler(config)
        stats = audio_handler.get_system_stats()

        return JSONResponse(content={
            "timestamp": datetime.utcnow().isoformat(),
            "stats": stats
        })

    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Stats retrieval failed")


@api_router.get("/export/notes")
async def export_notes(request: Request, config = Depends(get_config_dep)):
    """Export all notes as a JSON file"""
    try:
        audio_handler = AudioHandler(config)
        
        # Get all completed notes
        all_notes = []
        session_keys = audio_handler.redis_client.client.keys("session_status:*")
        
        for key in session_keys:
            session_id = key.split(":")[-1]
            status_data = audio_handler.get_session_status(session_id)
            
            if status_data and status_data.get("status") == "completed":
                note = {
                    "session_id": session_id,
                    "text": status_data.get("transcript_text", ""),
                    "confidence": float(status_data.get("transcript_confidence", 0)),
                    "created_at": status_data.get("processing_completed_at") or status_data.get("uploaded_at"),
                    "filename": status_data.get("filename", ""),
                    "file_size": status_data.get("file_size", 0),
                    "duration": float(status_data.get("audio_duration", 0)),
                    "word_count": len(status_data.get("transcript_text", "").split()) if status_data.get("transcript_text") else 0
                }
                all_notes.append(note)
        
        # Sort by creation date
        all_notes.sort(key=lambda x: x["created_at"] or "", reverse=True)
        
        # Create export data
        export_data = {
            "export_date": datetime.utcnow().isoformat(),
            "total_notes": len(all_notes),
            "notes": all_notes
        }
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(export_data, f, indent=2)
            temp_path = f.name
        
        return FileResponse(
            path=temp_path,
            filename=f"medical_notes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            media_type="application/json"
        )

    except Exception as e:
        logger.error(f"Error exporting notes: {str(e)}")
        raise HTTPException(status_code=500, detail="Export failed")


# Error handlers would be handled by FastAPI's built-in exception handling