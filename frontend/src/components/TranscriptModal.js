import React, { useEffect, useCallback } from 'react';

const TranscriptModal = ({ isOpen, note, onClose }) => {
  // Handle escape key to close modal
  const handleKeyDown = useCallback((event) => {
    if (event.key === 'Escape') {
      onClose();
    }
  }, [onClose]);

  // Add/remove event listeners
  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden'; // Prevent background scrolling
    } else {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, handleKeyDown]);

  // Handle backdrop click
  const handleBackdropClick = useCallback((event) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  }, [onClose]);

  // Format date for display
  const formatDate = useCallback((date) => {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }, []);

  if (!isOpen || !note) {
    return null;
  }

  const confidence = note.confidence || 0;
  const wordCount = note.text ? note.text.split(' ').length : 0;

  return (
    <div className="modal" onClick={handleBackdropClick}>
      <div className="modal-content">
        <div className="modal-header">
          <h3 className="modal-title">
            Medical Note - {formatDate(new Date(note.created_at || note.timestamp))}
          </h3>
          <span className="close-btn" onClick={onClose}>
            &times;
          </span>
        </div>
        
        {/* Note Metadata */}
        <div className="modal-metadata">
          <div className="metadata-grid">
            <div className="metadata-item">
              <span className="metadata-label">Session ID:</span>
              <span className="metadata-value">{note.session_id}</span>
            </div>
            <div className="metadata-item">
              <span className="metadata-label">Confidence:</span>
              <span className={`metadata-value ${
                confidence >= 0.8 ? 'confidence-high' : 
                confidence >= 0.6 ? 'confidence-medium' : 'confidence-low'
              }`}>
                {Math.round(confidence * 100)}%
              </span>
            </div>
            <div className="metadata-item">
              <span className="metadata-label">Word Count:</span>
              <span className="metadata-value">{wordCount} words</span>
            </div>
            {note.duration && (
              <div className="metadata-item">
                <span className="metadata-label">Duration:</span>
                <span className="metadata-value">{Math.round(note.duration)}s</span>
              </div>
            )}
            {note.filename && (
              <div className="metadata-item">
                <span className="metadata-label">Original File:</span>
                <span className="metadata-value">{note.filename}</span>
              </div>
            )}
          </div>
        </div>

        {/* Transcript Text */}
        <div className="modal-transcript">
          {note.text || 'No transcript available'}
        </div>

        {/* Modal Actions */}
        <div className="modal-actions">
          <button 
            className="btn btn-outline"
            onClick={() => {
              // Copy transcript to clipboard
              navigator.clipboard.writeText(note.text || '');
              // You could add a toast notification here
            }}
          >
            📋 Copy Text
          </button>
          <button className="btn btn-primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default TranscriptModal;