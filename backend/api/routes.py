from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
import logging
from datetime import datetime
from pathlib import Path
import os
import glob

from core.audio_handler import AudioHandler
from .utils import validate_upload_request, handle_api_error

logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/upload_audio", methods=["POST"])
def upload_audio():
    """Upload audio file for processing"""
    try:
        logger.info("Audio upload request received")

        # Validate request
        validation_result = validate_upload_request(request)
        if not validation_result["valid"]:
            return jsonify({"error": validation_result["error"]}), 400

        file = request.files["audio"]
        timestamp = request.form.get("timestamp")

        # Initialize audio handler
        audio_handler = AudioHandler()

        # Save file and queue for processing
        result = audio_handler.save_uploaded_file(file, timestamp)

        return jsonify(
            {
                "success": True,
                "id": result["session_id"],
                "filename": result["filename"],
                "size": result["file_size"],
                "message": "Audio uploaded successfully and queued for transcription",
            }
        )

    except Exception as e:
        logger.error(f"Error uploading audio: {str(e)}")
        return handle_api_error(e, "Upload failed")


@api_bp.route("/status/<session_id>")
def get_status(session_id):
    """Get processing status for a session"""
    try:
        audio_handler = AudioHandler()
        status_data = audio_handler.get_session_status(session_id)

        if not status_data:
            return jsonify({"error": "Session not found"}), 404

        return jsonify(status_data)

    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return handle_api_error(e, "Status check failed")


@api_bp.route("/transcript/<session_id>")
def get_transcript(session_id):
    """Get the transcript for a session"""
    try:
        audio_handler = AudioHandler()
        transcript_data = audio_handler.get_transcript_data(session_id)

        if not transcript_data:
            return jsonify({"error": "Transcript not found or not ready"}), 404

        return jsonify(
            {"success": True, "session_id": session_id, "transcript": transcript_data}
        )

    except Exception as e:
        logger.error(f"Error getting transcript: {str(e)}")
        return handle_api_error(e, "Transcript retrieval failed")


@api_bp.route("/transcript/<session_id>/download")
def download_transcript(session_id):
    """Download transcript as a text file"""
    try:
        audio_handler = AudioHandler()
        status_data = audio_handler.get_session_status(session_id)
        
        if not status_data or status_data.get("status") != "completed":
            return jsonify({"error": "Transcript not found or not ready"}), 404

        transcript_path = status_data.get("transcript_path")
        if transcript_path and os.path.exists(transcript_path):
            return send_file(
                transcript_path,
                as_attachment=True,
                download_name=f"medical_note_{session_id[:8]}.txt",
                mimetype="text/plain"
            )
        else:
            return jsonify({"error": "Transcript file not found"}), 404

    except Exception as e:
        logger.error(f"Error downloading transcript: {str(e)}")
        return handle_api_error(e, "Download failed")


@api_bp.route("/notes")
def get_all_notes():
    """Get all transcribed notes"""
    try:
        audio_handler = AudioHandler()
        
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
        
        return jsonify({
            "success": True,
            "count": len(all_notes),
            "notes": all_notes
        })

    except Exception as e:
        logger.error(f"Error getting all notes: {str(e)}")
        return handle_api_error(e, "Failed to retrieve notes")


@api_bp.route("/notes/search")
def search_notes():
    """Search notes by text content"""
    try:
        query = request.args.get("q", "").lower()
        if not query:
            return jsonify({"error": "Search query required"}), 400

        audio_handler = AudioHandler()
        
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
        
        return jsonify({
            "success": True,
            "query": query,
            "count": len(all_notes),
            "notes": all_notes
        })

    except Exception as e:
        logger.error(f"Error searching notes: {str(e)}")
        return handle_api_error(e, "Search failed")


@api_bp.route("/notes/stats")
def get_notes_stats():
    """Get statistics about all notes"""
    try:
        audio_handler = AudioHandler()
        
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
        
        return jsonify({
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
        return handle_api_error(e, "Stats retrieval failed")


@api_bp.route("/health")
def health_check():
    """Health check endpoint"""
    try:
        audio_handler = AudioHandler()
        stats = audio_handler.get_system_stats()

        return jsonify(
            {
                "status": "healthy" if stats.get("redis_connected") else "degraded",
                "timestamp": datetime.utcnow().isoformat(),
                "stats": stats,
            }
        )

    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify(
            {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
        ), 500


@api_bp.route("/cleanup/<session_id>", methods=["DELETE"])
def cleanup_session(session_id):
    """Clean up files and data for a session"""
    try:
        audio_handler = AudioHandler()
        
        # Clean up files
        success = audio_handler.cleanup_session_files(session_id)
        
        # Also remove from Redis
        audio_handler.redis_client.client.delete(f"session_status:{session_id}")
        
        if success:
            return jsonify({"success": True, "message": "Session cleaned up successfully"})
        else:
            return jsonify({"success": True, "message": "Session data removed (no files to clean up)"})

    except Exception as e:
        logger.error(f"Error cleaning up session: {str(e)}")
        return handle_api_error(e, "Cleanup failed")


@api_bp.route("/stats")
def get_stats():
    """Get system statistics"""
    try:
        audio_handler = AudioHandler()
        stats = audio_handler.get_system_stats()

        return jsonify({"timestamp": datetime.utcnow().isoformat(), "stats": stats})

    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return handle_api_error(e, "Stats retrieval failed")


@api_bp.route("/export/notes")
def export_notes():
    """Export all notes as a JSON file"""
    try:
        audio_handler = AudioHandler()
        
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
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(export_data, f, indent=2)
            temp_path = f.name
        
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=f"medical_notes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error exporting notes: {str(e)}")
        return handle_api_error(e, "Export failed")


# Error handlers for the blueprint
@api_bp.errorhandler(413)
def file_too_large(error):
    """Handle file too large error"""
    return jsonify(
        {"error": "File too large", "max_size": current_app.config["MAX_FILE_SIZE"]}
    ), 413


@api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404


@api_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500