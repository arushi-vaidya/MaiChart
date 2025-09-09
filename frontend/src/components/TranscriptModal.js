import React, { useEffect, useCallback, useState } from 'react';
import apiService from '../services/api';

const TranscriptModal = ({ isOpen, note, onClose }) => {
  const [medicalData, setMedicalData] = useState(null);
  const [medicalAlerts, setMedicalAlerts] = useState(null);
  const [loadingMedical, setLoadingMedical] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [showRawMedicalJson, setShowRawMedicalJson] = useState(false);

  // Load medical data when modal opens
  useEffect(() => {
    if (isOpen && note && note.session_id) {
      loadMedicalData(note.session_id);
    }
  }, [isOpen, note]);

  const loadMedicalData = async (sessionId) => {
    try {
      setLoadingMedical(true);
      
      // Load medical data and alerts in parallel
      const [medicalResponse, alertsResponse] = await Promise.all([
        apiService.getMedicalData(sessionId),
        apiService.getMedicalAlerts(sessionId)
      ]);
      
      setMedicalData(medicalResponse?.medical_data || null);
      setMedicalAlerts(alertsResponse?.alerts || null);
      
    } catch (error) {
      console.error('Error loading medical data:', error);
      setMedicalData(null);
      setMedicalAlerts(null);
    } finally {
      setLoadingMedical(false);
    }
  };

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
      document.body.style.overflow = 'hidden';
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

  // Download medical data
  const handleDownloadMedical = async () => {
    try {
      await apiService.downloadMedicalData(note.session_id);
    } catch (error) {
      console.error('Error downloading medical data:', error);
      alert('Failed to download medical data');
    }
  };

  // Trigger medical extraction
  const handleTriggerExtraction = async () => {
    try {
      setLoadingMedical(true);
      await apiService.triggerMedicalExtraction(note.session_id);
      // Wait a moment then reload medical data
      setTimeout(() => loadMedicalData(note.session_id), 3000);
    } catch (error) {
      console.error('Error triggering medical extraction:', error);
      alert('Failed to trigger medical extraction');
      setLoadingMedical(false);
    }
  };

  // Get confidence display
  const getConfidenceDisplay = useCallback((confidence) => {
    const conf = confidence || 0;
    const percentage = Math.round(conf * 100);
    
    let level = 'low';
    let color = 'var(--danger-red)';
    let icon = '🔴';
    
    if (conf >= 0.8) {
      level = 'high';
      color = 'var(--success-green)';
      icon = '🟢';
    } else if (conf >= 0.6) {
      level = 'medium';
      color = 'var(--warning-orange)';
      icon = '🟡';
    }
    
    return { level, percentage, color, icon };
  }, []);

  if (!isOpen || !note) {
    return null;
  }

  const confidence = getConfidenceDisplay(note.confidence);
  const wordCount = note.text ? note.text.split(' ').length : 0;
  const hasMedicalData = medicalData && Object.keys(medicalData).length > 0;
  const hasAlerts = medicalAlerts && medicalAlerts.length > 0;

  return (
    <div className="modal" onClick={handleBackdropClick}>
      <div className="modal-content enhanced-modal">
        {/* Enhanced Modal Header */}
        <div className="modal-header">
          <div className="modal-title-section">
            <h3 className="modal-title">
              🏥 Medical Record
            </h3>
            <div className="modal-subtitle">
              {formatDate(new Date(note.created_at || note.timestamp))}
            </div>
          </div>
          <div className="modal-header-actions">
            {/* Quality indicator */}
            <div className="quality-indicator">
              <span className="quality-icon">{confidence.icon}</span>
              <span className="quality-text" style={{ color: confidence.color }}>
                {confidence.percentage}%
              </span>
            </div>
            <button className="close-btn" onClick={onClose}>
              ✕
            </button>
          </div>
        </div>

        {/* Enhanced Quick Stats Bar */}
        <div className="modal-quick-stats">
          <div className="quick-stat">
            <span className="quick-stat-icon">📝</span>
            <div className="quick-stat-info">
              <span className="quick-stat-value">{wordCount.toLocaleString()}</span>
              <span className="quick-stat-label">Words</span>
            </div>
          </div>
          {note.duration && (
            <div className="quick-stat">
              <span className="quick-stat-icon">⏱️</span>
              <div className="quick-stat-info">
                <span className="quick-stat-value">{Math.round(note.duration)}s</span>
                <span className="quick-stat-label">Duration</span>
              </div>
            </div>
          )}
          <div className="quick-stat">
            <span className="quick-stat-icon">🏥</span>
            <div className="quick-stat-info">
              <span className="quick-stat-value">{hasMedicalData ? 'Yes' : 'No'}</span>
              <span className="quick-stat-label">Medical Data</span>
            </div>
          </div>
          {hasAlerts && (
            <div className="quick-stat critical">
              <span className="quick-stat-icon">🚨</span>
              <div className="quick-stat-info">
                <span className="quick-stat-value">{medicalAlerts.length}</span>
                <span className="quick-stat-label">Alerts</span>
              </div>
            </div>
          )}
        </div>
        
        {/* Enhanced Tab Navigation */}
        <div className="modal-tabs">
          <button 
            className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <span className="tab-icon">📋</span>
            Overview
          </button>
          <button 
            className={`tab-btn ${activeTab === 'transcript' ? 'active' : ''}`}
            onClick={() => setActiveTab('transcript')}
          >
            <span className="tab-icon">📝</span>
            Full Transcript
          </button>
          {hasMedicalData && (
            <button 
              className={`tab-btn ${activeTab === 'medical' ? 'active' : ''}`}
              onClick={() => setActiveTab('medical')}
            >
              <span className="tab-icon">🏥</span>
              Medical Data
            </button>
          )}
          {hasAlerts && (
            <button 
              className={`tab-btn ${activeTab === 'alerts' ? 'active' : ''}`}
              onClick={() => setActiveTab('alerts')}
            >
              <span className="tab-icon">🚨</span>
              Alerts ({medicalAlerts.length})
            </button>
          )}
        </div>

        {/* Enhanced Tab Content */}
        <div className="tab-content">
          {activeTab === 'overview' && (
            <div className="overview-tab">
              {/* Patient Summary */}
              {hasMedicalData && medicalData.patient_details && (
                <div className="patient-summary-card">
                  <h4 className="summary-card-title">
                    <span className="summary-icon">👤</span>
                    Patient Information
                  </h4>
                  <div className="patient-summary-grid">
                    {Object.entries(medicalData.patient_details).map(([key, value]) => 
                      value && (
                        <div key={key} className="patient-summary-item">
                          <span className="summary-label">{key.replace('_', ' ').toUpperCase()}</span>
                          <span className="summary-value">{value}</span>
                        </div>
                      )
                    )}
                  </div>
                </div>
              )}

              {/* Quick Medical Overview */}
              {hasMedicalData && (
                <div className="medical-overview-card">
                  <h4 className="summary-card-title">
                    <span className="summary-icon">🩺</span>
                    Medical Overview
                  </h4>
                  <div className="medical-overview-grid">
                    {medicalData.chief_complaints && medicalData.chief_complaints.length > 0 && (
                      <div className="overview-item">
                        <span className="overview-label">Chief Complaints</span>
                        <span className="overview-count">{medicalData.chief_complaints.length}</span>
                      </div>
                    )}
                    {medicalData.symptoms && medicalData.symptoms.length > 0 && (
                      <div className="overview-item">
                        <span className="overview-label">Symptoms</span>
                        <span className="overview-count">{medicalData.symptoms.length}</span>
                      </div>
                    )}
                    {medicalData.drug_history && medicalData.drug_history.length > 0 && (
                      <div className="overview-item">
                        <span className="overview-label">Medications</span>
                        <span className="overview-count">{medicalData.drug_history.length}</span>
                      </div>
                    )}
                    {medicalData.allergies && medicalData.allergies.length > 0 && (
                      <div className="overview-item critical">
                        <span className="overview-label">Allergies</span>
                        <span className="overview-count">{medicalData.allergies.length}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Transcript Preview */}
              <div className="transcript-preview-card">
                <h4 className="summary-card-title">
                  <span className="summary-icon">📝</span>
                  Transcript Preview
                </h4>
                <div className="transcript-preview">
                  {note.text ? note.text.substring(0, 300) + (note.text.length > 300 ? '...' : '') : 'No transcript available'}
                </div>
                <button 
                  className="btn btn-outline btn-sm"
                  onClick={() => setActiveTab('transcript')}
                >
                  📖 Read Full Transcript
                </button>
              </div>
            </div>
          )}

          {activeTab === 'transcript' && (
            <div className="transcript-tab">
              {/* Enhanced Metadata */}
              <div className="transcript-metadata">
                <div className="metadata-grid">
                  <div className="metadata-item">
                    <span className="metadata-label">Session ID</span>
                    <span className="metadata-value">{note.session_id}</span>
                  </div>
                  <div className="metadata-item">
                    <span className="metadata-label">Confidence Score</span>
                    <span className="metadata-value" style={{ color: confidence.color }}>
                      {confidence.icon} {confidence.percentage}%
                    </span>
                  </div>
                  <div className="metadata-item">
                    <span className="metadata-label">Word Count</span>
                    <span className="metadata-value">{wordCount.toLocaleString()}</span>
                  </div>
                  {note.duration && (
                    <div className="metadata-item">
                      <span className="metadata-label">Audio Duration</span>
                      <span className="metadata-value">{Math.round(note.duration)} seconds</span>
                    </div>
                  )}
                  {note.filename && (
                    <div className="metadata-item">
                      <span className="metadata-label">Original File</span>
                      <span className="metadata-value">{note.filename}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Enhanced Transcript Display */}
              <div className="modal-transcript-enhanced">
                <div className="transcript-header">
                  <h4>📝 Full Medical Transcript</h4>
                  <button 
                    className="btn btn-outline btn-sm"
                    onClick={() => navigator.clipboard.writeText(note.text || '')}
                  >
                    📋 Copy
                  </button>
                </div>
                <div className="transcript-content">
                  {note.text || 'No transcript available'}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'medical' && hasMedicalData && (
            <div className="medical-tab">
              {/* Medical Data Controls */}
              <div className="medical-controls">
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => setShowRawMedicalJson(v => !v)}
                >
                  {showRawMedicalJson ? '📊 Show Structured' : '🔧 Show Raw JSON'}
                </button>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleDownloadMedical}
                >
                  💾 Download Medical Data
                </button>
              </div>

              {showRawMedicalJson ? (
                <div className="raw-json-container">
                  <pre className="medical-raw-json">
                    {JSON.stringify(medicalData, null, 2)}
                  </pre>
                </div>
              ) : (
                <div className="structured-medical-data">
                  {/* Patient Details */}
                  {medicalData.patient_details && Object.values(medicalData.patient_details).some(v => v) && (
                    <div className="medical-data-section">
                      <h4 className="medical-section-title">
                        <span className="section-icon">👤</span>
                        Patient Details
                      </h4>
                      <div className="medical-data-grid">
                        {Object.entries(medicalData.patient_details).map(([key, value]) => 
                          value && (
                            <div key={key} className="medical-data-item">
                              <span className="data-label">{key.replace('_', ' ').toUpperCase()}</span>
                              <span className="data-value">{value}</span>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  )}

                  {/* Critical Allergies First */}
                  {medicalData.allergies && medicalData.allergies.length > 0 && (
                    <div className="medical-data-section critical-section">
                      <h4 className="medical-section-title critical">
                        <span className="section-icon">⚠️</span>
                        ALLERGIES - CRITICAL INFORMATION
                      </h4>
                      <div className="allergies-critical-display">
                        {medicalData.allergies.map((allergy, index) => (
                          <div key={index} className="critical-allergy-item">
                            <span className="allergy-icon">⚠️</span>
                            <span className="allergy-text">{allergy}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Chief Complaints */}
                  {medicalData.chief_complaints && medicalData.chief_complaints.length > 0 && (
                    <div className="medical-data-section">
                      <h4 className="medical-section-title">
                        <span className="section-icon">🩺</span>
                        Chief Complaints
                      </h4>
                      <div className="complaints-list">
                        {medicalData.chief_complaints.map((complaint, index) => (
                          <div key={index} className="complaint-item">
                            {complaint}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Other Medical Sections */}
                  {[
                    { key: 'symptoms', title: 'Symptoms', icon: '🤒' },
                    { key: 'drug_history', title: 'Current Medications', icon: '💊' },
                    { key: 'chronic_diseases', title: 'Chronic Conditions', icon: '🏥' },
                    { key: 'possible_diseases', title: 'Possible Diagnoses', icon: '🔍' },
                    { key: 'family_history', title: 'Family History', icon: '👨‍👩‍👧‍👦' }
                  ].map(section => (
                    medicalData[section.key] && medicalData[section.key].length > 0 && (
                      <div key={section.key} className="medical-data-section">
                        <h4 className="medical-section-title">
                          <span className="section-icon">{section.icon}</span>
                          {section.title}
                        </h4>
                        <div className="medical-items-list">
                          {medicalData[section.key].map((item, index) => (
                            <div key={index} className="medical-list-item">
                              {typeof item === 'object' ? JSON.stringify(item) : item}
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'alerts' && hasAlerts && (
            <div className="alerts-tab">
              <div className="alerts-container">
                {medicalAlerts.map((alert, index) => (
                  <div key={index} className={`alert-card alert-${alert.priority}`}>
                    <div className="alert-header">
                      <h4 className="alert-title">{alert.title}</h4>
                      <span className={`alert-priority priority-${alert.priority}`}>
                        {alert.priority.toUpperCase()}
                      </span>
                    </div>
                    <p className="alert-message">{alert.message}</p>
                    {alert.details && alert.details.length > 0 && (
                      <div className="alert-details">
                        {alert.details.map((detail, detailIndex) => (
                          <div key={detailIndex} className="alert-detail-item">
                            {detail}
                          </div>
                        ))}
                      </div>
                    )}
                    {alert.action_required && (
                      <div className="alert-action">
                        <strong>Action Required:</strong> {alert.action_required}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No Medical Data State */}
          {activeTab === 'medical' && !hasMedicalData && (
            <div className="no-medical-data">
              <div className="no-data-icon">🏥</div>
              <h4>No Medical Data Available</h4>
              <p>Medical information extraction has not been completed for this transcript.</p>
              <button 
                className="btn btn-primary"
                onClick={handleTriggerExtraction}
                disabled={loadingMedical}
              >
                {loadingMedical ? (
                  <>
                    <div className="loading-spinner small"></div>
                    Extracting...
                  </>
                ) : (
                  <>
                    🤖 Extract Medical Information
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        {/* Enhanced Modal Actions */}
        <div className="modal-actions">
          <div className="action-group-left">
            <button 
              className="btn btn-outline"
              onClick={() => navigator.clipboard.writeText(note.text || '')}
            >
              📋 Copy Transcript
            </button>
            
            <button 
              className="btn btn-outline"
              onClick={() => apiService.downloadTranscript(note.session_id)}
            >
              📄 Download Transcript
            </button>
          </div>
          
          <div className="action-group-right">
            {hasMedicalData && (
              <button 
                className="btn btn-success"
                onClick={handleDownloadMedical}
              >
                💾 Download Medical Data
              </button>
            )}
            
            <button className="btn btn-primary" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TranscriptModal;