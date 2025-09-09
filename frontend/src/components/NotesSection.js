import React, { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';

const NotesSection = ({ onShowRecording, onOpenTranscript, onShowSummaries }) => {
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

  // Get confidence class and display
  const getConfidenceDisplay = useCallback((confidence) => {
    const conf = confidence || 0;
    const percentage = Math.round(conf * 100);
    
    let level = 'low';
    let icon = '🔴';
    if (conf >= 0.8) {
      level = 'high';
      icon = '🟢';
    } else if (conf >= 0.6) {
      level = 'medium';
      icon = '🟡';
    }
    
    return { level, percentage, icon };
  }, []);

  // Create enhanced note card
  const createEnhancedNoteCard = useCallback((note) => {
    const date = new Date(note.created_at || note.timestamp);
    const confidence = getConfidenceDisplay(note.confidence);
    const preview = note.text ? note.text.substring(0, 200) : 'No transcript available';
    const wordCount = note.text ? note.text.split(' ').length : 0;
    const isExpanded = expandedNotes.has(note.session_id);
    const displayText = isExpanded ? note.text : preview;

    return (
      <div 
        key={note.session_id}
        className={`note-card ${confidence.level === 'high' ? 'high-quality' : ''}`} 
        onClick={() => onOpenTranscript(note)}
      >
        {/* Note Header */}
        <div className="note-header">
          <div className="note-primary-info">
            <div className="note-title">
              <span className="note-icon">📝</span>
              <span>Medical Transcript</span>
            </div>
            <div className="note-date">{formatDate(date)}</div>
          </div>
          <div className="note-actions">
            <button 
              className="action-btn download" 
              onClick={(e) => downloadNote(note.session_id, e)} 
              title="Download Transcript"
            >
              💾
            </button>
            <button 
              className="action-btn expand" 
              onClick={(e) => toggleExpand(note.session_id, e)} 
              title={isExpanded ? "Collapse" : "Expand"}
            >
              {isExpanded ? '📖' : '📄'}
            </button>
            <button 
              className="action-btn delete" 
              onClick={(e) => deleteNote(note.session_id, e)} 
              title="Delete Note"
            >
              🗑️
            </button>
          </div>
        </div>
        
        {/* Note Quality Indicators */}
        <div className="note-quality-bar">
          <div className="quality-item">
            <span className="quality-icon">{confidence.icon}</span>
            <span className="quality-label">Confidence</span>
            <span className={`quality-value confidence-${confidence.level}`}>
              {confidence.percentage}%
            </span>
          </div>
          <div className="quality-item">
            <span className="quality-icon">📊</span>
            <span className="quality-label">Words</span>
            <span className="quality-value">{wordCount.toLocaleString()}</span>
          </div>
          {note.duration && (
            <div className="quality-item">
              <span className="quality-icon">⏱️</span>
              <span className="quality-label">Duration</span>
              <span className="quality-value">{Math.round(note.duration)}s</span>
            </div>
          )}
        </div>
        
        {/* Transcript Preview */}
        <div className="note-content">
          <div className={`note-text ${isExpanded ? 'expanded' : ''}`}>
            {displayText}
            {!isExpanded && note.text && note.text.length > 200 && (
              <span className="text-truncation">...</span>
            )}
          </div>
          
          {note.text && note.text.length > 200 && (
            <button 
              className="expand-text-btn" 
              onClick={(e) => toggleExpand(note.session_id, e)}
            >
              {isExpanded ? (
                <>
                  <span>📄</span>
                  Show preview
                </>
              ) : (
                <>
                  <span>📖</span>
                  Read full transcript
                </>
              )}
            </button>
          )}
        </div>

        {/* Note Footer */}
        <div className="note-footer">
          <div className="footer-left">
            <span className="session-id">ID: {note.session_id.substring(0, 8)}...</span>
            {note.filename && (
              <span className="original-file">📁 {note.filename}</span>
            )}
          </div>
          <div className="footer-right">
            <span className="processing-indicator">
              ✅ Processed
            </span>
          </div>
        </div>
      </div>
    );
  }, [expandedNotes, formatDate, getConfidenceDisplay, onOpenTranscript, downloadNote, deleteNote, toggleExpand]);

  // Calculate notes statistics
  const calculateNotesStats = useCallback(() => {
    const total = filteredNotes.length;
    const highConfidence = filteredNotes.filter(note => (note.confidence || 0) >= 0.8).length;
    const today = new Date().toDateString();
    const todayNotes = filteredNotes.filter(note => {
      const noteDate = new Date(note.created_at || note.timestamp);
      return noteDate.toDateString() === today;
    }).length;
    const totalWords = filteredNotes.reduce((sum, note) => {
      return sum + (note.text ? note.text.split(' ').length : 0);
    }, 0);

    return { total, highConfidence, today: todayNotes, totalWords };
  }, [filteredNotes]);

  if (loading) {
    return (
      <section className="notes-section">
        <div className="notes-header">
          <h2 className="notes-title">📝 Medical Transcripts</h2>
        </div>
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading transcripts...</p>
        </div>
      </section>
    );
  }

  const stats = calculateNotesStats();

  return (
    <section className="notes-section">
      <div className="notes-header">
        <h2 className="notes-title">📝 Medical Transcripts</h2>
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
          <button className="btn btn-outline" onClick={onShowSummaries}>
            🏥 Medical View
          </button>
          <button className="btn btn-primary" onClick={onShowRecording}>
            ➕ New Recording
          </button>
        </div>
      </div>

      {/* Enhanced Filter Chips */}
      <div className="filter-chips">
        {[
          { key: 'all', label: 'All Transcripts', icon: '📋', count: stats.total },
          { key: 'today', label: 'Today', icon: '📅', count: stats.today },
          { key: 'week', label: 'This Week', icon: '📆' },
          { key: 'high-confidence', label: 'High Quality', icon: '🎯', count: stats.highConfidence }
        ].map(filter => (
          <div 
            key={filter.key}
            className={`filter-chip ${currentFilter === filter.key ? 'active' : ''}`}
            onClick={() => handleFilter(filter.key)}
          >
            <span className="filter-icon">{filter.icon}</span>
            <span>{filter.label}</span>
            {filter.count !== undefined && (
              <span className="filter-count">{filter.count}</span>
            )}
          </div>
        ))}
      </div>

      {/* Enhanced Notes Grid */}
      {filteredNotes.length > 0 ? (
        <>
          <div className="notes-grid">
            {filteredNotes.map(createEnhancedNoteCard)}
          </div>

          {/* Enhanced Stats Footer */}
          <div className="notes-stats">
            <div className="stats-grid">
              <div className="stat-card">
                <span className="stat-number">{stats.total}</span>
                <span className="stat-label">Total Transcripts</span>
              </div>
              <div className="stat-card">
                <span className="stat-number">{stats.highConfidence}</span>
                <span className="stat-label">High Quality</span>
              </div>
              <div className="stat-card">
                <span className="stat-number">{stats.today}</span>
                <span className="stat-label">Today</span>
              </div>
              <div className="stat-card">
                <span className="stat-number">{stats.totalWords.toLocaleString()}</span>
                <span className="stat-label">Total Words</span>
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="empty-state">
          <div className="empty-state-icon">📝</div>
          <h3>No Transcripts Available</h3>
          <p>
            Start by recording your first medical consultation or uploading an audio file. 
            Our AI will transcribe and extract medical information automatically.
          </p>
          <div className="empty-state-actions">
            <button className="btn btn-primary btn-lg" onClick={onShowRecording}>
              🎤 Start Recording
            </button>
            <button className="btn btn-outline" onClick={onShowSummaries}>
              🏥 View Medical Summaries
            </button>
          </div>
        </div>
      )}
    </section>
  );
};

export default NotesSection;