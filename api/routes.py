from flask import Blueprint, request, jsonify, render_template, send_file, current_app
from werkzeug.utils import secure_filename
import logging
from datetime import datetime
from pathlib import Path

from core.audio_handler import AudioHandler
from .utils import validate_upload_request, handle_api_error

logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__)

@api_bp.route('/')
def index():
    """Serve the main audio recorder page"""
    return render_template('index.html')

@api_bp.route('/api/upload_audio', methods=['POST'])
def upload_audio():
    """Upload audio file for processing"""
    try:
        logger.info("Audio upload request received")
        
        # Validate request
        validation_result = validate_upload_request(request)
        if not validation_result['valid']:
            return jsonify({'error': validation_result['error']}), 400
        
        file = request.files['audio']
        timestamp = request.form.get('timestamp')
        
        # Initialize audio handler
        audio_handler = AudioHandler()
        
        # Save file and queue for processing
        result = audio_handler.save_uploaded_file(file, timestamp)
        
        return jsonify({
            'success': True,
            'id': result['session_id'],
            'filename': result['filename'],
            'size': result['file_size'],
            'message': 'Audio uploaded successfully and queued for processing'
        })
        
    except Exception as e:
        logger.error(f"Error uploading audio: {str(e)}")
        return handle_api_error(e, "Upload failed")

@api_bp.route('/api/status/<session_id>')
def get_status(session_id):
    """Get processing status for a session"""
    try:
        audio_handler = AudioHandler()
        status_data = audio_handler.get_session_status(session_id)
        
        if not status_data:
            return jsonify({'error': 'Session not found'}), 404
            
        return jsonify(status_data)
        
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return handle_api_error(e, "Status check failed")

@api_bp.route('/api/download/<session_id>')
def download_file(session_id):
    """Download the processed WAV file"""
    try:
        audio_handler = AudioHandler()
        file_path = audio_handler.get_processed_file_path(session_id)
        
        if not file_path:
            return jsonify({'error': 'File not found or not ready'}), 404
        
        # Send file
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"recording_{session_id}.wav",
            mimetype='audio/wav'
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return handle_api_error(e, "Download failed")

@api_bp.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        audio_handler = AudioHandler()
        stats = audio_handler.get_system_stats()
        
        return jsonify({
            'status': 'healthy' if stats.get('redis_connected') else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@api_bp.route('/api/cleanup/<session_id>', methods=['DELETE'])
def cleanup_session(session_id):
    """Clean up files for a session"""
    try:
        audio_handler = AudioHandler()
        success = audio_handler.cleanup_session_files(session_id)
        
        if success:
            return jsonify({'message': 'Session files cleaned up successfully'})
        else:
            return jsonify({'message': 'No files to clean up or cleanup failed'}), 404
            
    except Exception as e:
        logger.error(f"Error cleaning up session: {str(e)}")
        return handle_api_error(e, "Cleanup failed")

@api_bp.route('/api/stats')
def get_stats():
    """Get system statistics"""
    try:
        audio_handler = AudioHandler()
        stats = audio_handler.get_system_stats()
        
        return jsonify({
            'timestamp': datetime.utcnow().isoformat(),
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return handle_api_error(e, "Stats retrieval failed")

# Error handlers for the blueprint
@api_bp.errorhandler(413)
def file_too_large(error):
    """Handle file too large error"""
    return jsonify({
        'error': 'File too large',
        'max_size': current_app.config['MAX_FILE_SIZE']
    }), 413

@api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@api_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500