import React, { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';

const MedicalSummariesSection = ({ onShowRecording, onShowNotes, onOpenTranscript }) => {
  const [summaries, setSummaries] = useState([]);
  const [filteredSummaries, setFilteredSummaries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentFilter, setCurrentFilter] = useState('all');
  const [expandedSummaries, setExpandedSummaries] = useState(new Set());

  // Load medical summaries from backend
  const loadSummaries = useCallback(async () => {
    try {
      setLoading(true);
      
      // Get all notes first
      const notesResponse = await apiService.getAllNotes();
      const notes = notesResponse.notes || [];
      
      // Get medical data for each note
      const summariesWithMedicalData = await Promise.all(
        notes.map(async (note) => {
          try {
            const medicalResponse = await apiService.getMedicalData(note.session_id);
            const alertsResponse = await apiService.getMedicalAlerts(note.session_id);
            
            if (medicalResponse && medicalResponse.medical_data) {
              return {
                ...note,
                medical_data: medicalResponse.medical_data,
                medical_alerts: alertsResponse?.alerts || [],
                has_medical_data: true
              };
            }
            return null;
          } catch (error) {
            console.error(`Error loading medical data for ${note.session_id}:`, error);
            return null;
          }
        })
      );
      
      // Filter out notes without medical data
      const validSummaries = summariesWithMedicalData.filter(summary => summary !== null);
      
      setSummaries(validSummaries);
      setFilteredSummaries(validSummaries);
    } catch (error) {
      console.error('Failed to load medical summaries:', error);
      setSummaries([]);
      setFilteredSummaries([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load summaries on component mount
  useEffect(() => {
    loadSummaries();
  }, [loadSummaries]);

  // Handle search
  const handleSearch = useCallback((query) => {
    setSearchQuery(query);
    if (!query.trim()) {
      setFilteredSummaries(summaries);
      return;
    }

    const filtered = summaries.filter(summary => {
      const searchText = query.toLowerCase();
      return (
        (summary.text && summary.text.toLowerCase().includes(searchText)) ||
        summary.session_id.toLowerCase().includes(searchText) ||
        (summary.medical_data.patient_details?.name && 
         summary.medical_data.patient_details.name.toLowerCase().includes(searchText)) ||
        (summary.medical_data.chief_complaints && 
         summary.medical_data.chief_complaints.some(complaint => 
           complaint.toLowerCase().includes(searchText))) ||
        (summary.medical_data.symptoms && 
         summary.medical_data.symptoms.some(symptom => 
           symptom.toLowerCase().includes(searchText)))
      );
    });
    
    setFilteredSummaries(filtered);
  }, [summaries]);

  // Handle filter
  const handleFilter = useCallback((filter) => {
    setCurrentFilter(filter);
    let filtered = [...summaries];

    switch (filter) {
      case 'critical':
        filtered = filtered.filter(summary => 
          summary.medical_alerts && summary.medical_alerts.some(alert => 
            alert.priority === 'critical' || alert.priority === 'high'
          )
        );
        break;
      case 'allergies':
        filtered = filtered.filter(summary => 
          summary.medical_data.allergies && summary.medical_data.allergies.length > 0
        );
        break;
      case 'medications':
        filtered = filtered.filter(summary => 
          summary.medical_data.drug_history && summary.medical_data.drug_history.length > 0
        );
        break;
      case 'chronic':
        filtered = filtered.filter(summary => 
          summary.medical_data.chronic_diseases && summary.medical_data.chronic_diseases.length > 0
        );
        break;
      default:
        // 'all' - no filtering
        break;
    }

    setFilteredSummaries(filtered);
  }, [summaries]);

  // Download medical summary
  const downloadSummary = useCallback(async (sessionId, event) => {
    event.stopPropagation();
    try {
      await apiService.downloadMedicalData(sessionId);
    } catch (error) {
      console.error('Error downloading medical summary:', error);
      alert('Failed to download medical summary');
    }
  }, []);

  // Toggle summary expansion
  const toggleExpand = useCallback((sessionId, event) => {
    event.stopPropagation();
    const newExpanded = new Set(expandedSummaries);
    if (newExpanded.has(sessionId)) {
      newExpanded.delete(sessionId);
    } else {
      newExpanded.add(sessionId);
    }
    setExpandedSummaries(newExpanded);
  }, [expandedSummaries]);

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

  // Get priority class for alerts
  const getPriorityClass = useCallback((priority) => {
    switch (priority) {
      case 'critical': return 'priority-critical';
      case 'high': return 'priority-high';
      case 'medium': return 'priority-medium';
      case 'low': return 'priority-low';
      default: return 'priority-medium';
    }
  }, []);

  // Get severity indicator
  const getSeverityIndicator = useCallback((summary) => {
    const alerts = summary.medical_alerts || [];
    const criticalCount = alerts.filter(a => a.priority === 'critical').length;
    const highCount = alerts.filter(a => a.priority === 'high').length;
    
    if (criticalCount > 0) return { level: 'critical', count: criticalCount, label: 'Critical' };
    if (highCount > 0) return { level: 'high', count: highCount, label: 'High Priority' };
    if (alerts.length > 0) return { level: 'medium', count: alerts.length, label: 'Medium' };
    return { level: 'low', count: 0, label: 'Normal' };
  }, []);

  // Create enhanced medical card
  const createEnhancedMedicalCard = useCallback((summary) => {
    const date = new Date(summary.created_at || summary.timestamp);
    const isExpanded = expandedSummaries.has(summary.session_id);
    const medicalData = summary.medical_data;
    const alerts = summary.medical_alerts || [];
    const severity = getSeverityIndicator(summary);
    
    // Extract key medical information
    const patientName = medicalData.patient_details?.name || 'Unknown Patient';
    const patientAge = medicalData.patient_details?.age || '';
    const patientGender = medicalData.patient_details?.gender || '';
    
    const complaintsCount = medicalData.chief_complaints?.length || 0;
    const symptomsCount = medicalData.symptoms?.length || 0;
    const medicationsCount = medicalData.drug_history?.length || 0;
    const allergiesCount = medicalData.allergies?.length || 0;
    const chronicCount = medicalData.chronic_diseases?.length || 0;
    const diagnosesCount = medicalData.possible_diseases?.length || 0;
    
    // Get primary chief complaint
    const primaryComplaint = medicalData.chief_complaints?.[0] || 'No chief complaint recorded';
    
    // Get critical alerts
    const criticalAlerts = alerts.filter(alert => 
      alert.priority === 'critical' || alert.priority === 'high'
    );

    return (
      <div 
        key={summary.session_id}
        className={`summary-card ${criticalAlerts.length > 0 ? 'has-alerts' : ''} ${severity.level === 'critical' ? 'critical-case' : ''}`}
        onClick={() => onOpenTranscript(summary)}
      >
        {/* Card Header with Patient Info */}
        <div className="summary-header">
          <div className="patient-info">
            <div className="patient-header">
              <h3 className="patient-name">{patientName}</h3>
              <div className="severity-indicator">
                <span className={`severity-badge ${severity.level}`}>
                  {severity.level === 'critical' && '🚨'}
                  {severity.level === 'high' && '⚠️'}
                  {severity.level === 'medium' && 'ℹ️'}
                  {severity.level === 'low' && '✅'}
                  {severity.label}
                </span>
              </div>
            </div>
            <div className="patient-meta">
              {patientAge && <span className="patient-age">Age: {patientAge}</span>}
              {patientGender && <span className="patient-gender">{patientGender}</span>}
              <span className="visit-date">{formatDate(date)}</span>
            </div>
          </div>
          <div className="summary-actions">
            <button 
              className="action-btn download" 
              onClick={(e) => downloadSummary(summary.session_id, e)} 
              title="Download Medical Summary"
            >
              📋
            </button>
            <button 
              className="action-btn expand" 
              onClick={(e) => toggleExpand(summary.session_id, e)} 
              title={isExpanded ? "Collapse Details" : "Expand Details"}
            >
              {isExpanded ? '📖' : '📄'}
            </button>
          </div>
        </div>

        {/* Primary Complaint */}
        <div className="primary-complaint">
          <div className="complaint-header">
            <span className="complaint-icon">🩺</span>
            <span className="complaint-label">Chief Complaint</span>
          </div>
          <p className="complaint-text">{primaryComplaint}</p>
        </div>

        {/* Critical Alerts Banner */}
        {criticalAlerts.length > 0 && (
          <div className="critical-alerts-banner">
            {criticalAlerts.slice(0, 2).map((alert, index) => (
              <div key={index} className={`critical-alert ${getPriorityClass(alert.priority)}`}>
                <span className="alert-icon">
                  {alert.priority === 'critical' ? '🚨' : '⚠️'}
                </span>
                <span className="alert-text">{alert.title.replace(/[🚨⚠️]/g, '').trim()}</span>
              </div>
            ))}
            {criticalAlerts.length > 2 && (
              <div className="more-alerts">
                +{criticalAlerts.length - 2} more alerts
              </div>
            )}
          </div>
        )}

        {/* Medical Overview Stats */}
        <div className="medical-overview">
          <div className="overview-grid">
            {symptomsCount > 0 && (
              <div className="overview-stat">
                <span className="overview-icon">🤒</span>
                <div className="overview-info">
                  <span className="overview-number">{symptomsCount}</span>
                  <span className="overview-label">Symptoms</span>
                </div>
              </div>
            )}
            
            {medicationsCount > 0 && (
              <div className="overview-stat">
                <span className="overview-icon">💊</span>
                <div className="overview-info">
                  <span className="overview-number">{medicationsCount}</span>
                  <span className="overview-label">Medications</span>
                </div>
              </div>
            )}
            
            {allergiesCount > 0 && (
              <div className="overview-stat critical">
                <span className="overview-icon">⚠️</span>
                <div className="overview-info">
                  <span className="overview-number">{allergiesCount}</span>
                  <span className="overview-label">Allergies</span>
                </div>
              </div>
            )}
            
            {chronicCount > 0 && (
              <div className="overview-stat">
                <span className="overview-icon">🏥</span>
                <div className="overview-info">
                  <span className="overview-number">{chronicCount}</span>
                  <span className="overview-label">Chronic</span>
                </div>
              </div>
            )}
            
            {diagnosesCount > 0 && (
              <div className="overview-stat">
                <span className="overview-icon">🔍</span>
                <div className="overview-info">
                  <span className="overview-number">{diagnosesCount}</span>
                  <span className="overview-label">Diagnoses</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Expanded Medical Details */}
        {isExpanded && (
          <div className="expanded-medical-details">
            {/* Key Symptoms Section */}
            {medicalData.symptoms && medicalData.symptoms.length > 0 && (
              <div className="medical-detail-section">
                <div className="section-header">
                  <h4 className="section-title">
                    <span className="section-icon">🤒</span>
                    Reported Symptoms
                  </h4>
                  <span className="section-count">{medicalData.symptoms.length}</span>
                </div>
                <div className="symptoms-display">
                  {medicalData.symptoms.slice(0, 8).map((symptom, index) => (
                    <span key={index} className="symptom-pill">{symptom}</span>
                  ))}
                  {medicalData.symptoms.length > 8 && (
                    <span className="symptom-pill more-symptoms">
                      +{medicalData.symptoms.length - 8} more
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Critical Allergies Section */}
            {medicalData.allergies && medicalData.allergies.length > 0 && (
              <div className="medical-detail-section critical-section">
                <div className="section-header">
                  <h4 className="section-title critical">
                    <span className="section-icon">⚠️</span>
                    ALLERGIES - CRITICAL
                  </h4>
                  <span className="section-count critical">{medicalData.allergies.length}</span>
                </div>
                <div className="allergies-display">
                  {medicalData.allergies.map((allergy, index) => (
                    <div key={index} className="allergy-item">
                      <span className="allergy-icon">⚠️</span>
                      <span className="allergy-name">{allergy}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Current Medications */}
            {medicalData.drug_history && medicalData.drug_history.length > 0 && (
              <div className="medical-detail-section">
                <div className="section-header">
                  <h4 className="section-title">
                    <span className="section-icon">💊</span>
                    Current Medications
                  </h4>
                  <span className="section-count">{medicalData.drug_history.length}</span>
                </div>
                <div className="medications-display">
                  {medicalData.drug_history.map((medication, index) => (
                    <div key={index} className="medication-item">
                      <span className="medication-icon">💊</span>
                      <span className="medication-name">{medication}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Chronic Conditions */}
            {medicalData.chronic_diseases && medicalData.chronic_diseases.length > 0 && (
              <div className="medical-detail-section">
                <div className="section-header">
                  <h4 className="section-title">
                    <span className="section-icon">🏥</span>
                    Chronic Conditions
                  </h4>
                  <span className="section-count">{medicalData.chronic_diseases.length}</span>
                </div>
                <div className="chronic-diseases-display">
                  {medicalData.chronic_diseases.map((disease, index) => (
                    <div key={index} className="chronic-disease-item">
                      <span className="disease-name">{disease}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Possible Diagnoses */}
            {medicalData.possible_diseases && medicalData.possible_diseases.length > 0 && (
              <div className="medical-detail-section">
                <div className="section-header">
                  <h4 className="section-title">
                    <span className="section-icon">🔍</span>
                    Possible Diagnoses
                  </h4>
                  <span className="section-count">{medicalData.possible_diseases.length}</span>
                </div>
                <div className="diagnoses-display">
                  {medicalData.possible_diseases.map((disease, index) => (
                    <div key={index} className="diagnosis-item">
                      <span className="diagnosis-icon">🔍</span>
                      <span className="diagnosis-name">{disease}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Chief Complaint Details */}
            {medicalData.chief_complaint_details && medicalData.chief_complaint_details.length > 0 && (
              <div className="medical-detail-section">
                <div className="section-header">
                  <h4 className="section-title">
                    <span className="section-icon">📋</span>
                    Complaint Details
                  </h4>
                </div>
                <div className="complaint-details-display">
                  {medicalData.chief_complaint_details.map((detail, index) => (
                    <div key={index} className="complaint-detail-item">
                      <div className="complaint-detail-header">
                        <span className="complaint-detail-name">{detail.complaint}</span>
                        {detail.severity && (
                          <span className={`severity-tag ${
                            detail.severity.toLowerCase().includes('high') || 
                            detail.severity.includes('8') || detail.severity.includes('9') || detail.severity.includes('10')
                            ? 'high-severity' : 'normal-severity'
                          }`}>
                            {detail.severity}
                          </span>
                        )}
                      </div>
                      <div className="complaint-detail-meta">
                        {detail.location && (
                          <span className="detail-meta">📍 {detail.location}</span>
                        )}
                        {detail.duration && (
                          <span className="detail-meta">⏱️ {detail.duration}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Family History */}
            {medicalData.family_history && medicalData.family_history.length > 0 && (
              <div className="medical-detail-section">
                <div className="section-header">
                  <h4 className="section-title">
                    <span className="section-icon">👨‍👩‍👧‍👦</span>
                    Family History
                  </h4>
                </div>
                <div className="family-history-display">
                  {medicalData.family_history.map((history, index) => (
                    <div key={index} className="family-history-item">
                      {history}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Card Footer */}
        <div className="summary-footer">
          <div className="footer-left">
            <span className="session-id">ID: {summary.session_id.substring(0, 8)}...</span>
            <span className="extraction-method">
              {medicalData.extraction_metadata?.method?.includes('OpenAI') ? '🤖 AI Extracted' : '🔧 Processed'}
            </span>
          </div>
          <div className="footer-right">
            {medicalData.extraction_metadata?.processing_time_seconds && (
              <span className="processing-time">
                ⚡ {medicalData.extraction_metadata.processing_time_seconds}s
              </span>
            )}
          </div>
        </div>
      </div>
    );
  }, [expandedSummaries, formatDate, getPriorityClass, getSeverityIndicator, onOpenTranscript, downloadSummary, toggleExpand]);

  // Calculate summary statistics
  const calculateStats = useCallback(() => {
    const totalSummaries = filteredSummaries.length;
    const criticalCases = filteredSummaries.filter(s => 
      s.medical_alerts?.some(a => a.priority === 'critical' || a.priority === 'high')
    ).length;
    const patientsWithAllergies = filteredSummaries.filter(s => 
      s.medical_data.allergies && s.medical_data.allergies.length > 0
    ).length;
    const patientsOnMedications = filteredSummaries.filter(s => 
      s.medical_data.drug_history && s.medical_data.drug_history.length > 0
    ).length;

    return {
      total: totalSummaries,
      critical: criticalCases,
      allergies: patientsWithAllergies,
      medications: patientsOnMedications
    };
  }, [filteredSummaries]);

  if (loading) {
    return (
      <section className="summaries-section">
        <div className="summaries-header">
          <h2 className="summaries-title">🏥 Medical Summaries</h2>
        </div>
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading medical summaries...</p>
        </div>
      </section>
    );
  }

  const stats = calculateStats();

  return (
    <section className="summaries-section">
      <div className="summaries-header">
        <h2 className="summaries-title">🏥 Medical Summaries</h2>
        <div className="summaries-controls">
          <input 
            type="text" 
            className="search-box" 
            placeholder="Search patients, symptoms, medications..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
          />
          <button className="btn btn-outline" onClick={loadSummaries}>
            🔄 Refresh
          </button>
          <button className="btn btn-outline" onClick={onShowNotes}>
            📝 Transcripts
          </button>
          <button className="btn btn-primary" onClick={onShowRecording}>
            ➕ New Recording
          </button>
        </div>
      </div>

      {/* Enhanced Filter Chips */}
      <div className="filter-chips">
        {[
          { key: 'all', label: 'All Patients', icon: '👥', count: stats.total },
          { key: 'critical', label: 'Critical Cases', icon: '🚨', count: stats.critical },
          { key: 'allergies', label: 'Has Allergies', icon: '⚠️', count: stats.allergies },
          { key: 'medications', label: 'On Medications', icon: '💊', count: stats.medications },
          { key: 'chronic', label: 'Chronic Conditions', icon: '🏥' }
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

      {/* Enhanced Summaries Grid */}
      {filteredSummaries.length > 0 ? (
        <>
          <div className="summaries-grid">
            {filteredSummaries.map(createEnhancedMedicalCard)}
          </div>

          {/* Enhanced Stats Footer */}
          <div className="summaries-stats">
            <div className="stats-grid">
              <div className="stat-card">
                <span className="stat-number">{stats.total}</span>
                <span className="stat-label">Total Patients</span>
              </div>
              <div className="stat-card">
                <span className="stat-number">{stats.critical}</span>
                <span className="stat-label">Critical Cases</span>
              </div>
              <div className="stat-card">
                <span className="stat-number">{stats.allergies}</span>
                <span className="stat-label">With Allergies</span>
              </div>
              <div className="stat-card">
                <span className="stat-number">{stats.medications}</span>
                <span className="stat-label">On Medications</span>
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="empty-state">
          <div className="empty-state-icon">🏥</div>
          <h3>No Medical Summaries Available</h3>
          <p>
            Medical summaries will appear here after audio recordings are transcribed 
            and processed by our AI medical extraction system. Start by recording a 
            patient consultation or uploading an existing audio file.
          </p>
          <div className="empty-state-actions">
            <button className="btn btn-primary btn-lg" onClick={onShowRecording}>
              🎤 Start Recording
            </button>
            <button className="btn btn-outline" onClick={onShowNotes}>
              📝 View Transcripts
            </button>
          </div>
        </div>
      )}
    </section>
  );
};

export default MedicalSummariesSection;