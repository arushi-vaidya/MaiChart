import React, { useEffect, useCallback, useState } from 'react';
import apiService from '../services/api';

const EnhancedTranscriptModal = ({ isOpen, note, onClose }) => {
  const [medicalData, setMedicalData] = useState(null);
  const [medicalAlerts, setMedicalAlerts] = useState(null);
  const [loadingMedical, setLoadingMedical] = useState(false);
  const [activeTab, setActiveTab] = useState('transcript');
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

  if (!isOpen || !note) {
    return null;
  }

  const confidence = note.confidence || 0;
  const wordCount = note.text ? note.text.split(' ').length : 0;
  const hasMedicalData = medicalData && Object.keys(medicalData).length > 0;

  return (
    <div className="modal" onClick={handleBackdropClick}>
      <div className="modal-content enhanced-modal">
        <div className="modal-header">
          <h3 className="modal-title">
            🏥 Medical Note - {formatDate(new Date(note.created_at || note.timestamp))}
          </h3>
          <span className="close-btn" onClick={onClose}>
            &times;
          </span>
        </div>
        
        {/* Tab Navigation */}
        <div className="modal-tabs">
          <button 
            className={`tab-btn ${activeTab === 'transcript' ? 'active' : ''}`}
            onClick={() => setActiveTab('transcript')}
          >
            📝 Transcript
          </button>
          <button 
            className={`tab-btn ${activeTab === 'medical' ? 'active' : ''}`}
            onClick={() => setActiveTab('medical')}
          >
            🏥 Medical Data
          </button>
          {medicalAlerts && medicalAlerts.length > 0 && (
            <button 
              className={`tab-btn ${activeTab === 'alerts' ? 'active' : ''}`}
              onClick={() => setActiveTab('alerts')}
            >
              🚨 Alerts
            </button>
          )}
        </div>

        {/* Tab Content */}
        <div className="tab-content">
          {activeTab === 'transcript' && (
            <div className="transcript-tab">
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
            </div>
          )}

          {activeTab === 'medical' && (
            <div className="medical-tab">
              <button
                className="btn btn-outline btn-sm"
                style={{ marginBottom: '10px' }}
                onClick={() => setShowRawMedicalJson(v => !v)}
                disabled={!hasMedicalData}
              >
                {showRawMedicalJson ? 'Hide Raw JSON' : 'Show Raw JSON'}
              </button>
              {showRawMedicalJson && hasMedicalData && (
                <pre className="medical-raw-json" style={{ maxHeight: 300, overflow: 'auto', background: '#f6f8fa', border: '1px solid #eee', borderRadius: 4, padding: 12, marginBottom: 16 }}>
                  {JSON.stringify(medicalData, null, 2)}
                </pre>
              )}
              {loadingMedical ? (
                <div className="loading-medical">
                  <div className="loading-spinner"></div>
                  <p>Loading medical data...</p>
                </div>
              ) : hasMedicalData ? (
                <div className="medical-data-display">
                  {/* Patient Details */}
                  {medicalData.patient_details && Object.values(medicalData.patient_details).some(v => v) && (
                    <div className="medical-section">
                      <h4>👤 Patient Details</h4>
                      <div className="medical-grid">
                        {Object.entries(medicalData.patient_details).map(([key, value]) => 
                          value && (
                            <div key={key} className="medical-item">
                              <span className="medical-label">{key.replace('_', ' ').toUpperCase()}:</span>
                              <span className="medical-value">{value}</span>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  )}

                  {/* Chief Complaints */}
                  {medicalData.chief_complaints && medicalData.chief_complaints.length > 0 && (
                    <div className="medical-section">
                      <h4>🩺 Chief Complaints</h4>
                      <ul className="medical-list">
                        {medicalData.chief_complaints.map((complaint, index) => (
                          <li key={index}>{complaint}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Symptoms */}
                  {medicalData.symptoms && medicalData.symptoms.length > 0 && (
                    <div className="medical-section">
                      <h4>🤒 Symptoms</h4>
                      <ul className="medical-list">
                        {medicalData.symptoms.map((symptom, index) => (
                          <li key={index}>{symptom}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Medications */}
                  {medicalData.drug_history && medicalData.drug_history.length > 0 && (
                    <div className="medical-section">
                      <h4>💊 Current Medications</h4>
                      <ul className="medical-list">
                        {medicalData.drug_history.map((med, index) => (
                          <li key={index}>{med}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Allergies - Critical Information */}
                  {medicalData.allergies && medicalData.allergies.length > 0 && (
                    <div className="medical-section critical">
                      <h4>⚠️ ALLERGIES (Critical)</h4>
                      <ul className="medical-list critical-list">
                        {medicalData.allergies.map((allergy, index) => (
                          <li key={index} className="critical-item">{allergy}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Chronic Diseases */}
                  {medicalData.chronic_diseases && medicalData.chronic_diseases.length > 0 && (
                    <div className="medical-section">
                      <h4>🏥 Chronic Conditions</h4>
                      <ul className="medical-list">
                        {medicalData.chronic_diseases.map((disease, index) => (
                          <li key={index}>{disease}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Possible Diseases */}
                  {medicalData.possible_diseases && medicalData.possible_diseases.length > 0 && (
                    <div className="medical-section">
                      <h4>🔍 Possible Diagnoses</h4>
                      <ul className="medical-list">
                        {medicalData.possible_diseases.map((disease, index) => (
                          <li key={index}>{disease}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Family History */}
                  {medicalData.family_history && medicalData.family_history.length > 0 && (
                    <div className="medical-section">
                      <h4>👨‍👩‍👧‍👦 Family History</h4>
                      <ul className="medical-list">
                        {medicalData.family_history.map((history, index) => (
                          <li key={index}>{history}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Lifestyle Factors */}
                  {medicalData.lifestyle && medicalData.lifestyle.length > 0 && (
                    <div className="medical-section">
                      <h4>🚭 Lifestyle Factors</h4>
                      <ul className="medical-list">
                        {medicalData.lifestyle.map((lifestyle, index) => (
                          <li key={index}>
                            {lifestyle.habit} 
                            {lifestyle.frequency && ` - ${lifestyle.frequency}`}
                            {lifestyle.duration && ` (${lifestyle.duration})`}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="no-medical-data">
                  <div className="no-data-icon">🏥</div>
                  <h4>No Medical Data Available</h4>
                  <p>Medical information extraction has not been completed for this transcript.</p>
                  <button 
                    className="btn btn-primary"
                    onClick={handleTriggerExtraction}
                    disabled={loadingMedical}
                  >
                    🤖 Extract Medical Information
                  </button>
                </div>
              )}
            </div>
          )}

          {activeTab === 'alerts' && medicalAlerts && (
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
                      <ul className="alert-details">
                        {alert.details.map((detail, detailIndex) => (
                          <li key={detailIndex}>{detail}</li>
                        ))}
                      </ul>
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
        </div>

        {/* Modal Actions */}
        <div className="modal-actions">
          <button 
            className="btn btn-outline"
            onClick={() => {
              navigator.clipboard.writeText(note.text || '');
            }}
          >
            📋 Copy Transcript
          </button>
          
          {hasMedicalData && (
            <button 
              className="btn btn-outline"
              onClick={handleDownloadMedical}
            >
              💾 Download Medical Data
            </button>
          )}
          
          <button 
            className="btn btn-outline"
            onClick={() => apiService.downloadTranscript(note.session_id)}
          >
            📄 Download Transcript
          </button>
          
          <button className="btn btn-primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default EnhancedTranscriptModal;