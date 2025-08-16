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

  // Create summary card
  const createSummaryCard = useCallback((summary) => {
    const date = new Date(summary.created_at || summary.timestamp);
    const isExpanded = expandedSummaries.has(summary.session_id);
    const medicalData = summary.medical_data;
    const alerts = summary.medical_alerts || [];
    
    // Count important medical information
    const patientName = medicalData.patient_details?.name || 'Unknown Patient';
    const patientAge = medicalData.patient_details?.age || '';
    const complaintsCount = medicalData.chief_complaints?.length || 0;
    const symptomsCount = medicalData.symptoms?.length || 0;
    const medicationsCount = medicalData.drug_history?.length || 0;
    const allergiesCount = medicalData.allergies?.length || 0;
    const diseasesCount = medicalData.possible_diseases?.length || 0;
    
    // Get highest priority alert
    const criticalAlerts = alerts.filter(alert => 
      alert.priority === 'critical' || alert.priority === 'high'
    );

    return (
      <div 
        key={summary.session_id}
        className={`summary-card ${criticalAlerts.length > 0 ? 'has-alerts' : ''}`}
        onClick={() => onOpenTranscript(summary)}
      >
        <div className="summary-header">
          <div className="summary-patient">
            <h3 className="patient-name">{patientName}</h3>
            {patientAge && <span className="patient-age">Age: {patientAge}</span>}
            <div className="summary-date">{formatDate(date)}</div>
          </div>
          <div className="summary-actions">
            <button 
              className="action-btn" 
              onClick={(e) => downloadSummary(summary.session_id, e)} 
              title="Download Medical Summary"
            >
              📋
            </button>
            <button 
              className="action-btn" 
              onClick={(e) => toggleExpand(summary.session_id, e)} 
              title={isExpanded ? "Collapse" : "Expand"}
            >
              {isExpanded ? '📖' : '📄'}
            </button>
          </div>
        </div>

        {/* Critical Alerts Banner */}
        {criticalAlerts.length > 0 && (
          <div className="alerts-banner">
            {criticalAlerts.map((alert, index) => (
              <div key={index} className={`alert-badge ${getPriorityClass(alert.priority)}`}>
                {alert.title}
              </div>
            ))}
          </div>
        )}

        {/* Medical Stats */}
        <div className="medical-stats">
          {complaintsCount > 0 && (
            <div className="stat-item">
              <span className="stat-icon">🩺</span>
              <span>{complaintsCount} Complaints</span>
            </div>
          )}
          {symptomsCount > 0 && (
            <div className="stat-item">
              <span className="stat-icon">🤒</span>
              <span>{symptomsCount} Symptoms</span>
            </div>
          )}
          {medicationsCount > 0 && (
            <div className="stat-item">
              <span className="stat-icon">💊</span>
              <span>{medicationsCount} Medications</span>
            </div>
          )}
          {allergiesCount > 0 && (
            <div className="stat-item critical">
              <span className="stat-icon">⚠️</span>
              <span>{allergiesCount} Allergies</span>
            </div>
          )}
          {diseasesCount > 0 && (
            <div className="stat-item">
              <span className="stat-icon">🔍</span>
              <span>{diseasesCount} Diagnoses</span>
            </div>
          )}
        </div>

        {/* Expanded Details */}
        {isExpanded && (
          <div className="summary-details">
            {/* Chief Complaints */}
            {medicalData.chief_complaints && medicalData.chief_complaints.length > 0 && (
              <div className="detail-section">
                <h4>Chief Complaints</h4>
                <ul className="detail-list">
                  {medicalData.chief_complaints.map((complaint, index) => (
                    <li key={index}>{complaint}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Key Symptoms */}
            {medicalData.symptoms && medicalData.symptoms.length > 0 && (
              <div className="detail-section">
                <h4>Key Symptoms</h4>
                <div className="symptoms-grid">
                  {medicalData.symptoms.slice(0, 6).map((symptom, index) => (
                    <span key={index} className="symptom-tag">{symptom}</span>
                  ))}
                  {medicalData.symptoms.length > 6 && (
                    <span className="symptom-tag more">+{medicalData.symptoms.length - 6} more</span>
                  )}
                </div>
              </div>
            )}

            {/* Critical: Allergies */}
            {medicalData.allergies && medicalData.allergies.length > 0 && (
              <div className="detail-section critical">
                <h4>⚠️ ALLERGIES</h4>
                <ul className="detail-list critical-list">
                  {medicalData.allergies.map((allergy, index) => (
                    <li key={index} className="critical-item">{allergy}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Current Medications */}
            {medicalData.drug_history && medicalData.drug_history.length > 0 && (
              <div className="detail-section">
                <h4>Current Medications</h4>
                <div className="medications-grid">
                  {medicalData.drug_history.map((medication, index) => (
                    <span key={index} className="medication-tag">{medication}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Possible Diagnoses */}
            {medicalData.possible_diseases && medicalData.possible_diseases.length > 0 && (
              <div className="detail-section">
                <h4>Possible Diagnoses</h4>
                <ul className="detail-list">
                  {medicalData.possible_diseases.map((disease, index) => (
                    <li key={index}>{disease}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <div className="summary-footer">
          <span className="session-id">ID: {summary.session_id.substring(0, 8)}...</span>
          <span className="extraction-method">
            {medicalData.extraction_metadata?.method || 'AI Extracted'}
          </span>
        </div>
      </div>
    );
  }, [expandedSummaries, formatDate, getPriorityClass, onOpenTranscript, downloadSummary, toggleExpand]);

  if (loading) {
    return (
      <section className="summaries-section">
        <div className="summaries-header">
          <h2 className="summaries-title">🏥 Medical Summaries</h2>
        </div>
        <div className="loading-state">Loading medical summaries...</div>
      </section>
    );
  }

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
            📝 View Transcripts
          </button>
          <button className="btn btn-primary" onClick={onShowRecording}>
            ➕ New Recording
          </button>
        </div>
      </div>

      {/* Filter Chips */}
      <div className="filter-chips">
        {[
          { key: 'all', label: 'All Summaries', icon: '📋' },
          { key: 'critical', label: 'Critical Alerts', icon: '🚨' },
          { key: 'allergies', label: 'Has Allergies', icon: '⚠️' },
          { key: 'medications', label: 'On Medications', icon: '💊' },
          { key: 'chronic', label: 'Chronic Conditions', icon: '🏥' }
        ].map(filter => (
          <div 
            key={filter.key}
            className={`filter-chip ${currentFilter === filter.key ? 'active' : ''}`}
            onClick={() => handleFilter(filter.key)}
          >
            <span className="filter-icon">{filter.icon}</span>
            {filter.label}
          </div>
        ))}
      </div>

      {/* Summaries Grid */}
      {filteredSummaries.length > 0 ? (
        <div className="summaries-grid">
          {filteredSummaries.map(createSummaryCard)}
        </div>
      ) : (
        <div className="empty-state">
          <div className="empty-state-icon">🏥</div>
          <h3>No Medical Summaries Available</h3>
          <p>
            Medical summaries will appear here after audio recordings are transcribed 
            and processed by our AI medical extraction system.
          </p>
          <div className="empty-state-actions">
            <button className="btn btn-primary" onClick={onShowRecording}>
              🎤 Start Recording
            </button>
            <button className="btn btn-outline" onClick={onShowNotes}>
              📝 View Transcripts
            </button>
          </div>
        </div>
      )}

      {/* Stats Footer */}
      {filteredSummaries.length > 0 && (
        <div className="summaries-stats">
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-number">{filteredSummaries.length}</span>
              <span className="stat-label">Medical Summaries</span>
            </div>
            <div className="stat-card">
              <span className="stat-number">
                {filteredSummaries.filter(s => s.medical_alerts?.some(a => 
                  a.priority === 'critical' || a.priority === 'high'
                )).length}
              </span>
              <span className="stat-label">Critical Cases</span>
            </div>
            <div className="stat-card">
              <span className="stat-number">
                {filteredSummaries.filter(s => 
                  s.medical_data.allergies && s.medical_data.allergies.length > 0
                ).length}
              </span>
              <span className="stat-label">Patients with Allergies</span>
            </div>
            <div className="stat-card">
              <span className="stat-number">
                {filteredSummaries.filter(s => 
                  s.medical_data.drug_history && s.medical_data.drug_history.length > 0
                ).length}
              </span>
              <span className="stat-label">On Medications</span>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default MedicalSummariesSection;