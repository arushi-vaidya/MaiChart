import React, { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';

const UnifiedNotesSection = ({ onShowRecording, onOpenTranscript }) => {
  const [notes, setNotes] = useState([]);
  const [filteredNotes, setFilteredNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentFilter, setCurrentFilter] = useState('all');
  const [expandedCards, setExpandedCards] = useState(new Set());

  // Load notes with medical data
  const loadNotes = useCallback(async () => {
    try {
      setLoading(true);
      
      // Get all notes first
      const notesResponse = await apiService.getAllNotes();
      const notesData = notesResponse.notes || [];
      
      // Get medical data for each note
      const enrichedNotes = await Promise.all(
        notesData.map(async (note) => {
          try {
            const [medicalResponse, alertsResponse] = await Promise.all([
              apiService.getMedicalData(note.session_id),
              apiService.getMedicalAlerts(note.session_id)
            ]);
            
            return {
              ...note,
              medical_data: medicalResponse?.medical_data || null,
              medical_alerts: alertsResponse?.alerts || [],
              has_medical_data: !!medicalResponse?.medical_data
            };
          } catch (error) {
            console.error(`Error loading medical data for ${note.session_id}:`, error);
            return {
              ...note,
              medical_data: null,
              medical_alerts: [],
              has_medical_data: false
            };
          }
        })
      );
      
      setNotes(enrichedNotes);
      setFilteredNotes(enrichedNotes);
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

    const filtered = notes.filter(note => {
      const searchText = query.toLowerCase();
      return (
        (note.text && note.text.toLowerCase().includes(searchText)) ||
        note.session_id.toLowerCase().includes(searchText) ||
        (note.medical_data?.patient_details?.name && 
         note.medical_data.patient_details.name.toLowerCase().includes(searchText)) ||
        (note.medical_data?.chief_complaints && 
         note.medical_data.chief_complaints.some(complaint => 
           complaint.toLowerCase().includes(searchText))) ||
        (note.medical_data?.symptoms && 
         note.medical_data.symptoms.some(symptom => 
           symptom.toLowerCase().includes(searchText)))
      );
    });
    setFilteredNotes(filtered);
  }, [notes]);

  // Handle filter
  const handleFilter = useCallback((filter) => {
    setCurrentFilter(filter);
    let filtered = [...notes];

    switch (filter) {
      case 'today':
        const today = new Date().toDateString();
        filtered = filtered.filter(note => {
          const noteDate = new Date(note.created_at || note.timestamp);
          return noteDate.toDateString() === today;
        });
        break;
      case 'critical':
        filtered = filtered.filter(note => 
          note.medical_alerts && note.medical_alerts.some(alert => 
            alert.priority === 'critical' || alert.priority === 'high'
          )
        );
        break;
      case 'with-medical':
        filtered = filtered.filter(note => note.has_medical_data);
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

  // Toggle card expansion
  const toggleExpand = useCallback((sessionId) => {
    const newExpanded = new Set(expandedCards);
    if (newExpanded.has(sessionId)) {
      newExpanded.delete(sessionId);
    } else {
      newExpanded.add(sessionId);
    }
    setExpandedCards(newExpanded);
  }, [expandedCards]);

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
  const getConfidenceLevel = useCallback((confidence) => {
    const conf = confidence || 0;
    if (conf >= 0.8) return 'high';
    if (conf >= 0.6) return 'medium';
    return 'low';
  }, []);

  // Get severity indicator
  const getSeverityIndicator = useCallback((note) => {
    const alerts = note.medical_alerts || [];
    const criticalCount = alerts.filter(a => a.priority === 'critical').length;
    const highCount = alerts.filter(a => a.priority === 'high').length;
    
    if (criticalCount > 0) return { level: 'critical', count: criticalCount, label: 'Critical' };
    if (highCount > 0) return { level: 'high', count: highCount, label: 'High Risk' };
    if (alerts.length > 0) return { level: 'medium', count: alerts.length, label: 'Attention' };
    return { level: 'normal', count: 0, label: 'Normal' };
  }, []);

  // Generate medical summary for card display
  const generateMedicalSummary = useCallback((medicalData) => {
    if (!medicalData) return null;

    const symptoms = medicalData.symptoms?.slice(0, 3) || [];
    const medications = medicalData.drug_history?.slice(0, 2) || [];
    const allergies = medicalData.allergies || [];
    const conditions = medicalData.chronic_diseases?.slice(0, 2) || [];
    
    return {
      symptoms,
      medications, 
      allergies,
      conditions,
      hasData: symptoms.length > 0 || medications.length > 0 || allergies.length > 0 || conditions.length > 0
    };
  }, []);

  // Calculate stats
  const calculateStats = useCallback(() => {
    const total = filteredNotes.length;
    const withMedical = filteredNotes.filter(note => note.has_medical_data).length;
    const critical = filteredNotes.filter(note => 
      note.medical_alerts?.some(a => a.priority === 'critical' || a.priority === 'high')
    ).length;
    const today = new Date().toDateString();
    const todayNotes = filteredNotes.filter(note => {
      const noteDate = new Date(note.created_at || note.timestamp);
      return noteDate.toDateString() === today;
    }).length;

    return { total, withMedical, critical, today: todayNotes };
  }, [filteredNotes]);

  const stats = calculateStats();

  if (loading) {
    return (
      <div className="unified-notes-section">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <h3>Loading Patient Notes...</h3>
          <p>Gathering transcripts and medical data</p>
        </div>
      </div>
    );
  }

  return (
    <div className="unified-notes-section">
      {/* Modern Header */}
      <div className="notes-header">
        <div className="header-content">
          <div className="header-title">
            <h1>Patient Notes</h1>
            <p>AI-powered medical insights and transcriptions</p>
          </div>
          <div className="header-actions">
            <button className="btn btn-outline" onClick={loadNotes}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
                <path d="M21 3v5h-5"/>
                <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
                <path d="M3 21v-5h5"/>
              </svg>
              Refresh
            </button>
            <button className="btn btn-primary" onClick={onShowRecording}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              </svg>
              New Recording
            </button>
          </div>
        </div>

        {/* Search and Stats Bar */}
        <div className="search-stats-bar">
          <div className="search-container">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="search-icon">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
            <input
              type="text"
              placeholder="Search by patient, symptoms, medications, conditions..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="search-input"
            />
          </div>
          <div className="quick-stats">
            <div className="stat-item">
              <span className="stat-number">{stats.total}</span>
              <span className="stat-label">Total Notes</span>
            </div>
            <div className="stat-item">
              <span className="stat-number">{stats.withMedical}</span>
              <span className="stat-label">AI Analyzed</span>
            </div>
            <div className="stat-item">
              <span className="stat-number critical">{stats.critical}</span>
              <span className="stat-label">Critical Cases</span>
            </div>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="filter-pills">
          {[
            { key: 'all', label: 'All Notes', count: stats.total },
            { key: 'today', label: 'Today', count: stats.today },
            { key: 'critical', label: 'Critical Cases', count: stats.critical },
            { key: 'with-medical', label: 'AI Analyzed', count: stats.withMedical },
            { key: 'high-confidence', label: 'High Quality' }
          ].map(filter => (
            <button
              key={filter.key}
              className={`filter-pill ${currentFilter === filter.key ? 'active' : ''}`}
              onClick={() => handleFilter(filter.key)}
            >
              <span>{filter.label}</span>
              {filter.count !== undefined && filter.count > 0 && (
                <span className="filter-count">{filter.count}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Enhanced Notes Grid */}
      {filteredNotes.length > 0 ? (
        <div className="notes-grid">
          {filteredNotes.map((note) => {
            const date = new Date(note.created_at || note.timestamp);
            const confidence = note.confidence || 0;
            const confidenceLevel = getConfidenceLevel(confidence);
            const severity = getSeverityIndicator(note);
            const isExpanded = expandedCards.has(note.session_id);
            const wordCount = note.text ? note.text.split(' ').length : 0;
            const preview = note.text ? note.text.substring(0, 150) + '...' : 'No transcript available';
            
            // Medical data extraction
            const medicalData = note.medical_data;
            const patientName = medicalData?.patient_details?.name || 'Unknown Patient';
            const patientAge = medicalData?.patient_details?.age || '';
            const primaryComplaint = medicalData?.chief_complaints?.[0] || '';
            const medicalSummary = generateMedicalSummary(medicalData);

            return (
              <div 
                key={note.session_id}
                className={`note-card ${severity.level} ${isExpanded ? 'expanded' : ''}`}
                onClick={() => onOpenTranscript(note)}
              >
                {/* Enhanced Card Header */}
                <div className="card-header">
                  <div className="patient-info">
                    <div className="patient-avatar">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                        <circle cx="12" cy="7" r="4"/>
                      </svg>
                    </div>
                    <div className="patient-details">
                      <h3 className="patient-name">{patientName}</h3>
                      <div className="patient-meta">
                        {patientAge && <span className="age">Age {patientAge}</span>}
                        <span className="visit-date">{formatDate(date)}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="card-indicators">
                    <div className={`confidence-badge ${confidenceLevel}`}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M9 12l2 2 4-4"/>
                        <circle cx="12" cy="12" r="9"/>
                      </svg>
                      {Math.round(confidence * 100)}%
                    </div>
                    <div className={`severity-badge ${severity.level}`}>
                      {severity.level === 'critical' && '🚨'}
                      {severity.level === 'high' && '⚠️'}
                      {severity.level === 'medium' && 'ℹ️'}
                      {severity.level === 'normal' && '✅'}
                      <span>{severity.label}</span>
                    </div>
                  </div>

                  <div className="card-actions">
                    <button 
                      className="action-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleExpand(note.session_id);
                      }}
                      title={isExpanded ? "Collapse" : "Expand Details"}
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        {isExpanded ? (
                          <path d="M18 15l-6-6-6 6"/>
                        ) : (
                          <path d="M6 9l6 6 6-6"/>
                        )}
                      </svg>
                    </button>
                    <button 
                      className="action-btn"
                      onClick={(e) => downloadNote(note.session_id, e)}
                      title="Download"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                      </svg>
                    </button>
                    <button 
                      className="action-btn danger"
                      onClick={(e) => deleteNote(note.session_id, e)}
                      title="Delete"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="m19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>
                      </svg>
                    </button>
                  </div>
                </div>

                {/* Primary Complaint */}
                {primaryComplaint && (
                  <div className="primary-complaint">
                    <div className="complaint-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                      </svg>
                    </div>
                    <div className="complaint-content">
                      <span className="complaint-label">Chief Complaint</span>
                      <p className="complaint-text">{primaryComplaint}</p>
                    </div>
                  </div>
                )}

                {/* NEW: Medical Summary Section */}
                {medicalSummary && medicalSummary.hasData && (
                  <div className="medical-summary">
                    <div className="summary-header">
                      <div className="summary-icon">🏥</div>
                      <div className="summary-title">Medical Overview</div>
                    </div>
                    
                    <div className="summary-grid">
                      {medicalSummary.symptoms.length > 0 && (
                        <div className="summary-item">
                          <div className="summary-item-icon">🤒</div>
                          <div className="summary-item-content">
                            <div className="summary-item-label">Key Symptoms</div>
                            <div className="summary-item-value">
                              {medicalSummary.symptoms.join(', ')}
                              {medicalData.symptoms?.length > 3 && ` +${medicalData.symptoms.length - 3} more`}
                            </div>
                          </div>
                        </div>
                      )}

                      {medicalSummary.conditions.length > 0 && (
                        <div className="summary-item">
                          <div className="summary-item-icon">🏥</div>
                          <div className="summary-item-content">
                            <div className="summary-item-label">Conditions</div>
                            <div className="summary-item-value">
                              {medicalSummary.conditions.join(', ')}
                              {medicalData.chronic_diseases?.length > 2 && ` +${medicalData.chronic_diseases.length - 2} more`}
                            </div>
                          </div>
                        </div>
                      )}

                      {medicalSummary.medications.length > 0 && (
                        <div className="summary-item">
                          <div className="summary-item-icon">💊</div>
                          <div className="summary-item-content">
                            <div className="summary-item-label">Medications</div>
                            <div className="summary-item-value">
                              {medicalSummary.medications.join(', ')}
                              {medicalData.drug_history?.length > 2 && ` +${medicalData.drug_history.length - 2} more`}
                            </div>
                          </div>
                        </div>
                      )}

                      {medicalSummary.allergies.length > 0 && (
                        <div className="summary-item critical">
                          <div className="summary-item-icon">⚠️</div>
                          <div className="summary-item-content">
                            <div className="summary-item-label">ALLERGIES</div>
                            <div className="summary-item-value">
                              {medicalSummary.allergies.slice(0, 2).join(', ')}
                              {medicalSummary.allergies.length > 2 && ` +${medicalSummary.allergies.length - 2} more`}
                            </div>
                          </div>
                        </div>
                      )}

                      {medicalData && (
                        <div className="summary-item">
                          <div className="summary-item-icon">🤖</div>
                          <div className="summary-item-content">
                            <div className="summary-item-label">AI Analysis</div>
                            <div className="summary-item-value">
                              {medicalData.extraction_metadata?.method || 'GPT-4 Medical'}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Transcript Preview */}
                <div className="transcript-preview">
                  <div className="transcript-header">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14,2 14,8 20,8"/>
                      <line x1="16" y1="13" x2="8" y2="13"/>
                      <line x1="16" y1="17" x2="8" y2="17"/>
                    </svg>
                    <span>Transcript Preview</span>
                    <div className="transcript-stats">
                      <span>{wordCount} words</span>
                      {note.duration && <span>{Math.round(note.duration)}s</span>}
                    </div>
                  </div>
                  <p className="transcript-text">{preview}</p>
                </div>

                {/* Enhanced Card Footer */}
                <div className="card-footer">
                  <div className="footer-left">
                    <span className="session-id">ID: {note.session_id.substring(0, 8)}...</span>
                    {note.has_medical_data && (
                      <span className="ai-badge">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="12" r="3"/>
                          <path d="M12 1v6m0 6v6m11-7h-6m-6 0H1"/>
                        </svg>
                        AI Analyzed
                      </span>
                    )}
                  </div>
                  <div className="footer-right">
                    <button className="view-details-btn" onClick={(e) => {
                      e.stopPropagation();
                      onOpenTranscript(note);
                    }}>
                      <span>View Full Details</span>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M9 18l6-6-6-6"/>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="empty-state">
          <div className="empty-state-illustration">
            <svg viewBox="0 0 200 150" fill="none">
              <defs>
                <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#e0f2fe" />
                  <stop offset="100%" stopColor="#f0f9ff" />
                </linearGradient>
                <linearGradient id="grad2" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#3b82f6" />
                  <stop offset="100%" stopColor="#8b5cf6" />
                </linearGradient>
              </defs>
              <rect width="200" height="150" rx="20" fill="url(#grad1)" />
              <circle cx="100" cy="60" r="30" fill="url(#grad2)" opacity="0.1" />
              <path d="M85 60h30M100 45v30" stroke="url(#grad2)" strokeWidth="4" strokeLinecap="round" />
              <rect x="60" y="90" width="80" height="6" rx="3" fill="url(#grad2)" opacity="0.3" />
              <rect x="70" y="105" width="60" height="6" rx="3" fill="url(#grad2)" opacity="0.2" />
              <rect x="80" y="120" width="40" height="6" rx="3" fill="url(#grad2)" opacity="0.1" />
            </svg>
          </div>
          <h3>No Patient Notes Found</h3>
          <p>
            Start by recording your first medical consultation or uploading an audio file. 
            Our AI will transcribe and extract comprehensive medical information automatically.
          </p>
          <div className="empty-state-actions">
            <button className="btn btn-primary btn-lg" onClick={onShowRecording}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              </svg>
              Start Recording
            </button>
            <button className="btn btn-outline btn-lg" onClick={loadNotes}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
                <path d="M21 3v5h-5"/>
              </svg>
              Refresh Data
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default UnifiedNotesSection;