import React, { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';

const NotesSection = ({ onShowRecording, onOpenTranscript, onShowSummaries }) => {
  const [notes, setNotes] = useState([]);
  const [filteredNotes, setFilteredNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentFilter, setCurrentFilter] = useState('all');

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

  // Get confidence display
  const getConfidenceDisplay = useCallback((confidence) => {
    const conf = confidence || 0;
    const percentage = Math.round(conf * 100);
    
    let level = 'low';
    if (conf >= 0.8) {
      level = 'high';
    } else if (conf >= 0.6) {
      level = 'medium';
    }
    
    return { level, percentage };
  }, []);

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

  const stats = calculateNotesStats();

  if (loading) {
    return (
      <div className="section notes-section">
        <div className="section-header">
          <h1 className="section-title">Transcripts</h1>
          <p className="section-subtitle">All medical transcriptions</p>
        </div>
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading transcripts...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="section notes-section">
      <div className="section-header">
        <h1 className="section-title">Transcripts</h1>
        <p className="section-subtitle">View and manage all medical transcriptions</p>
      </div>

      {/* Controls */}
      <div className="section-controls">
        <input 
          type="text" 
          className="input search-input" 
          placeholder="Search transcripts..."
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
        />
        <button className="btn btn-secondary" onClick={loadNotes}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{width: '16px', height: '16px'}}>
            <polyline points="23 4 23 10 17 10"/>
            <polyline points="1 20 1 14 7 14"/>
            <path d="m3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          Refresh
        </button>
        <button className="btn btn-outline" onClick={onShowSummaries}>
          Medical Data
        </button>
        <button className="btn btn-primary" onClick={onShowRecording}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{width: '16px', height: '16px'}}>
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          New Recording
        </button>
      </div>

      {/* Filter Chips */}
      <div className="filter-chips">
        {[
          { key: 'all', label: 'All Transcripts', count: stats.total },
          { key: 'today', label: 'Today', count: stats.today },
          { key: 'week', label: 'This Week' },
          { key: 'high-confidence', label: 'High Quality', count: stats.highConfidence }
        ].map(filter => (
          <button
            key={filter.key}
            className={`filter-chip ${currentFilter === filter.key ? 'active' : ''}`}
            onClick={() => handleFilter(filter.key)}
          >
            <span>{filter.label}</span>
            {filter.count !== undefined && (
              <span className="filter-chip-count">{filter.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Notes Grid */}
      {filteredNotes.length > 0 ? (
        <>
          <div className="cards-grid">
            {filteredNotes.map((note) => {
              const date = new Date(note.created_at || note.timestamp);
              const confidence = getConfidenceDisplay(note.confidence);
              const wordCount = note.text ? note.text.split(' ').length : 0;
              const preview = note.text ? note.text.substring(0, 150) + '...' : 'No transcript available';

              return (
                <div 
                  key={note.session_id}
                  className="note-card" 
                  onClick={() => onOpenTranscript(note)}
                >
                  <div className="card-header">
                    <div>
                      <h3 className="card-title">Medical Transcript</h3>
                      <div className="card-meta">{formatDate(date)}</div>
                    </div>
                    <div className="card-actions">
                      <button 
                        className="card-action-btn" 
                        onClick={(e) => downloadNote(note.session_id, e)} 
                        title="Download"
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{width: '16px', height: '16px'}}>
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                          <polyline points="7 10 12 15 17 10"/>
                          <line x1="12" y1="15" x2="12" y2="3"/>
                        </svg>
                      </button>
                      <button 
                        className="card-action-btn" 
                        onClick={(e) => deleteNote(note.session_id, e)} 
                        title="Delete"
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{width: '16px', height: '16px'}}>
                          <polyline points="3 6 5 6 21 6"/>
                          <path d="m19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                      </button>
                    </div>
                  </div>
                  
                  <div className="card-content">
                    <div className="flex items-center gap-4 mb-4">
                      <div className="flex items-center gap-2">
                        <div className={`confidence-dot ${confidence.level}`}></div>
                        <span className={`confidence-indicator confidence-${confidence.level}`}>
                          {confidence.percentage}%
                        </span>
                      </div>
                      <div className="text-sm text-gray-500">
                        {wordCount.toLocaleString()} words
                      </div>
                      {note.duration && (
                        <div className="text-sm text-gray-500">
                          {Math.round(note.duration)}s
                        </div>
                      )}
                    </div>
                    
                    <div className="card-text truncated">
                      {preview}
                    </div>
                  </div>

                  <div className="card-footer">
                    <div className="text-xs text-gray-400">
                      ID: {note.session_id.substring(0, 8)}...
                    </div>
                    <div className="status status-success">
                      Processed
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Stats */}
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-number">{stats.total}</div>
              <div className="stat-label">Total Transcripts</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">{stats.highConfidence}</div>
              <div className="stat-label">High Quality</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">{stats.today}</div>
              <div className="stat-label">Today</div>
            </div>
            <div className="stat-card">
              <div className="stat-number">{stats.totalWords.toLocaleString()}</div>
              <div className="stat-label">Total Words</div>
            </div>
          </div>
        </>
      ) : (
        <div className="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" style={{width: '64px', height: '64px', margin: '0 auto 1.5rem', color: 'var(--gray-400)'}}>
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14,2 14,8 20,8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          <h3>No Transcripts Available</h3>
          <p>
            Start by recording your first medical consultation or uploading an audio file. 
            Our AI will transcribe and extract medical information automatically.
          </p>
          <div className="flex gap-4 justify-center mt-6">
            <button className="btn btn-primary btn-lg" onClick={onShowRecording}>
              Start Recording
            </button>
            <button className="btn btn-outline" onClick={onShowSummaries}>
              View Medical Data
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotesSection;