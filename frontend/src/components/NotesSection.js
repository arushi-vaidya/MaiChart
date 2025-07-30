import React, { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';

const NotesSection = ({ onShowRecording, onOpenTranscript }) => {
  const [notes, setNotes] = useState([]);
  const [filteredNotes, setFilteredNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentFilter, setCurrentFilter] = useState('all');
  const [expandedNotes, setExpandedNotes] = useState(new Set());

  // Load notes from backend
  const loadNotes = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiService.getAllNotes();
      const notesData = response.notes || [];
      setNotes(notesData);
      setFilteredNotes(notesData);
    } catch (error) {
      console.error('Failed to load notes:', error);
      setNotes([]);
      setFilteredNotes([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load notes on component mount
  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  // Handle search
  const handleSearch = useCallback((query) => {
    setSearchQuery(query);
    if (!query.trim()) {
      setFilteredNotes(notes);
      return;
    }

    const filtered = notes.filter(note =>
      (note.text && note.text.toLowerCase().includes(query.toLowerCase())) ||
      note.session_id.toLowerCase().includes(query.toLowerCase())
    );
    setFilteredNotes(filtered);
  }, [notes]);

  // Handle filter
  const handleFilter = useCallback((filter) => {
    setCurrentFilter(filter);
    let filtered = [...notes];
    const now = new Date();

    switch (filter) {
      case 'today':
        filtered = filtered.filter(note => {
          const noteDate = new Date(note.created_at || note.timestamp);
          return noteDate.toDateString() === now.toDateString();
        });
        break;
      case 'week':
        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        filtered = filtered.filter(note => {
          const noteDate = new Date(note.created_at || note.timestamp);
          return noteDate >= weekAgo;
        });
        break;
      case 'high-confidence':
        filtered = filtered.filter(note => (note.confidence || 0) >= 0.8);
        break;
      default:
        // 'all' - no filtering
        break;
    }

    setFilteredNotes(filtered);
  }, [notes]);

  // Download note
  const downloadNote = useCallback(async (sessionId, event) => {
    event.stopPropagation();
    try {
      await apiService.downloadTranscript(sessionId);
    } catch (error) {
      console.error('Error downloading note:', error);
    }
  }, []);

  // Delete note
  const deleteNote = useCallback(async (sessionId, event) => {
    event.stopPropagation();
    
    if (!window.confirm('Are you sure you want to delete this medical note?')) {
      return;
    }

    try {
      await apiService.deleteSession(sessionId);
      // Remove from current notes array
      const updatedNotes = notes.filter(note => note.session_id !== sessionId);
      setNotes(updatedNotes);
      setFilteredNotes(updatedNotes);
    } catch (error) {
      console.error('Error deleting note:', error);
      alert('Failed to delete note');
    }
  }, [notes]);

  // Toggle note expansion
  const toggleExpand = useCallback((sessionId, event) => {
    event.stopPropagation();
    const newExpanded = new Set(expandedNotes);
    if (newExpanded.has(sessionId)) {
      newExpanded.delete(sessionId);
    } else {
      newExpanded.add(sessionId);
    }
    setExpandedNotes(newExpanded);
  }, [expandedNotes]);

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

  // Get confidence class
  const getConfidenceClass = useCallback((confidence) => {
    if (confidence >= 0.8) return 'confidence-high';
    if (confidence >= 0.6) return 'confidence-medium';
    return 'confidence-low';
  }, []);

  // Create note card
  const createNoteCard = useCallback((note) => {
    const date = new Date(note.created_at || note.timestamp);
    const confidence = note.confidence || 0;
    const confidenceClass = getConfidenceClass(confidence);
    const preview = note.text ? note.text.substring(0, 200) : 'No transcript available';
    const wordCount = note.text ? note.text.split(' ').length : 0;
    const isExpanded = expandedNotes.has(note.session_id);
    const displayText = isExpanded ? note.text : preview;

    return (
      <div 
        key={note.session_id}
        className="note-card" 
        onClick={() => onOpenTranscript(note)}
      >
        <div className="note-header">
          <div className="note-metadata">
            <div className="note-date">{formatDate(date)}</div>
            <div className="note-session">ID: {note.session_id.substring(0, 8)}...</div>
          </div>
          <div className="note-actions">
            <button 
              className="action-btn" 
              onClick={(e) => downloadNote(note.session_id, e)} 
              title="Download"
            >
              💾
            </button>
            <button 
              className="action-btn delete" 
              onClick={(e) => deleteNote(note.session_id, e)} 
              title="Delete"
            >
              🗑️
            </button>
          </div>
        </div>
        
        <div className="note-stats">
          <div className="stat-item">
            <span>🎯</span>
            <span className={confidenceClass}>{Math.round(confidence * 100)}%</span>
          </div>
          <div className="stat-item">
            <span>📝</span>
            <span>{wordCount} words</span>
          </div>
          {note.duration && (
            <div className="stat-item">
              <span>⏱️</span>
              <span>{Math.round(note.duration)}s</span>
            </div>
          )}
        </div>
        
        <div className={`note-text ${isExpanded ? 'expanded' : ''}`}>
          {displayText}
          {!isExpanded && note.text && note.text.length > 200 && '...'}
        </div>
        
        {note.text && note.text.length > 200 && (
          <div 
            className="expand-btn" 
            onClick={(e) => toggleExpand(note.session_id, e)}
          >
            {isExpanded ? 'Show less' : 'Click to read full transcript'}
          </div>
        )}
      </div>
    );
  }, [expandedNotes, formatDate, getConfidenceClass, onOpenTranscript, downloadNote, deleteNote, toggleExpand]);

  if (loading) {
    return (
      <section className="notes-section">
        <div className="notes-header">
          <h2 className="notes-title">📋 Medical Notes</h2>
        </div>
        <div className="loading-state">Loading notes...</div>
      </section>
    );
  }

  return (
    <section className="notes-section">
      <div className="notes-header">
        <h2 className="notes-title">📋 Medical Notes</h2>
        <div className="notes-controls">
          <input 
            type="text" 
            className="search-box" 
            placeholder="Search transcripts..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
          />
          <button className="btn btn-outline" onClick={loadNotes}>
            🔄 Refresh
          </button>
          <button className="btn btn-primary" onClick={onShowRecording}>
            ➕ New Note
          </button>
        </div>
      </div>

      {/* Filter Chips */}
      <div className="filter-chips">
        {[
          { key: 'all', label: 'All Notes' },
          { key: 'today', label: 'Today' },
          { key: 'week', label: 'This Week' },
          { key: 'high-confidence', label: 'High Confidence' }
        ].map(filter => (
          <div 
            key={filter.key}
            className={`filter-chip ${currentFilter === filter.key ? 'active' : ''}`}
            onClick={() => handleFilter(filter.key)}
          >
            {filter.label}
          </div>
        ))}
      </div>

      {/* Notes Grid */}
      {filteredNotes.length > 0 ? (
        <div className="notes-grid">
          {filteredNotes.map(createNoteCard)}
        </div>
      ) : (
        <div className="empty-state">
          <div className="empty-state-icon">📝</div>
          <h3>No Medical Notes Yet</h3>
          <p>Start by recording your first voice note or uploading an audio file.</p>
          <button className="btn btn-primary" onClick={onShowRecording}>
            🎤 Start Recording
          </button>
        </div>
      )}
    </section>
  );
};

export default NotesSection;