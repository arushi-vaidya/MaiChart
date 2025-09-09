import React, { useEffect, useCallback, useState } from 'react';
import apiService from '../services/api';

const EnhancedTranscriptModal = ({ isOpen, note, onClose }) => {
  const [medicalData, setMedicalData] = useState(null);
  const [medicalAlerts, setMedicalAlerts] = useState(null);
  const [loadingMedical, setLoadingMedical] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  // Load medical data when modal opens
  useEffect(() => {
    if (isOpen && note && note.session_id) {
      setActiveTab('overview');
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

  if (!isOpen || !note) {
    return null;
  }

  const confidence = getConfidenceDisplay(note.confidence);
  const wordCount = note.text ? note.text.split(' ').length : 0;
  const hasMedicalData = medicalData && Object.keys(medicalData).length > 0;
  const hasAlerts = medicalAlerts && medicalAlerts.length > 0;

  const tabs = [
    { id: 'overview', label: 'Overview', icon: 'grid' },
    { id: 'transcript', label: 'Full Transcript', icon: 'document' },
    ...(hasMedicalData ? [{ id: 'medical', label: 'Medical Data', icon: 'heart' }] : []),
    ...(hasAlerts ? [{ id: 'alerts', label: `Alerts (${medicalAlerts.length})`, icon: 'alert' }] : [])
  ];

  const getTabIcon = (iconName) => {
    const iconProps = { style: { width: '16px', height: '16px' }, fill: 'none', stroke: 'currentColor', strokeWidth: '2' };
    
    switch (iconName) {
      case 'grid':
        return <svg viewBox="0 0 24 24" {...iconProps}><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>;
      case 'document':
        return <svg viewBox="0 0 24 24" {...iconProps}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>;
      case 'heart':
        return <svg viewBox="0 0 24 24" {...iconProps}><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>;
      case 'alert':
        return <svg viewBox="0 0 24 24" {...iconProps}><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>;
      default:
        return null;
    }
  };

  return (
    <div className="modal-overlay" onClick={handleBackdropClick}>
      <div className="modal">
        {/* Modal Header */}
        <div className="modal-header">
          <div>
            <h2 className="modal-title">Medical Record</h2>
            <p className="text-sm text-gray-500">{formatDate(new Date(note.created_at || note.timestamp))}</p>
          </div>
          <div className="flex items-center gap-4">
            {/* Confidence indicator */}
            <div className="flex items-center gap-2">
              <div className={`confidence-dot ${confidence.level}`}></div>
              <span className={`text-sm font-medium confidence-${confidence.level}`}>
                {confidence.percentage}% confidence
              </span>
            </div>
            <button className="modal-close" onClick={onClose}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{width: '20px', height: '20px'}}>
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div className="text-center">
                <div className="text-lg font-semibold text-gray-900">{wordCount.toLocaleString()}</div>
                <div className="text-xs text-gray-500">Words</div>
              </div>
              {note.duration && (
                <div className="text-center">
                  <div className="text-lg font-semibold text-gray-900">{Math.round(note.duration)}s</div>
                  <div className="text-xs text-gray-500">Duration</div>
                </div>
              )}
              <div className="text-center">
                <div className="text-lg font-semibold text-gray-900">{hasMedicalData ? 'Yes' : 'No'}</div>
                <div className="text-xs text-gray-500">Medical Data</div>
              </div>
              {hasAlerts && (
                <div className="text-center">
                  <div className="text-lg font-semibold text-red-600">{medicalAlerts.length}</div>
                  <div className="text-xs text-red-500">Alerts</div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-gray-200">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setActiveTab(tab.id)}
            >
              {getTabIcon(tab.icon)}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="modal-content">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Patient Information */}
              {hasMedicalData && medicalData.patient_details && (
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">Patient Information</h3>
                  </div>
                  <div className="card-content">
                    <div className="grid grid-cols-2 gap-4">
                      {Object.entries(medicalData.patient_details).map(([key, value]) => 
                        value && (
                          <div key={key}>
                            <div className="text-sm font-medium text-gray-900 capitalize">
                              {key.replace('_', ' ')}
                            </div>
                            <div className="text-sm text-gray-600">{value}</div>
                          </div>
                        )
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Medical Overview */}
              {hasMedicalData && (
                <div className="card">
                  <div className="card-header">
                    <h3 className="card-title">Medical Overview</h3>
                  </div>
                  <div className="card-content">
                    <div className="grid grid-cols-2 gap-4">
                      {medicalData.chief_complaints && medicalData.chief_complaints.length > 0 && (
                        <div>
                          <div className="text-sm font-medium text-gray-900">Chief Complaints</div>
                          <div className="text-sm text-gray-600">{medicalData.chief_complaints.length} recorded</div>
                        </div>
                      )}
                      {medicalData.symptoms && medicalData.symptoms.length > 0 && (
                        <div>
                          <div className="text-sm font-medium text-gray-900">Symptoms</div>
                          <div className="text-sm text-gray-600">{medicalData.symptoms.length} identified</div>
                        </div>
                      )}
                      {medicalData.drug_history && medicalData.drug_history.length > 0 && (
                        <div>
                          <div className="text-sm font-medium text-gray-900">Medications</div>
                          <div className="text-sm text-gray-600">{medicalData.drug_history.length} current</div>
                        </div>
                      )}
                      {medicalData.allergies && medicalData.allergies.length > 0 && (
                        <div>
                          <div className="text-sm font-medium text-red-900">Allergies</div>
                          <div className="text-sm text-red-600">{medicalData.allergies.length} critical</div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Transcript Preview */}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">Transcript Preview</h3>
                </div>
                <div className="card-content">
                  <div className="text-sm text-gray-600 line-clamp-4">
                    {note.text ? note.text.substring(0, 300) + (note.text.length > 300 ? '...' : '') : 'No transcript available'}
                  </div>
                  <button 
                    className="btn btn-outline btn-sm mt-4"
                    onClick={() => setActiveTab('transcript')}
                  >
                    Read Full Transcript
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'transcript' && (
            <div className="space-y-6">
              {/* Metadata */}
              <div className="grid grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg">
                <div>
                  <div className="text-sm font-medium text-gray-900">Session ID</div>
                  <div className="text-sm text-gray-600 font-mono">{note.session_id}</div>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-900">Word Count</div>
                  <div className="text-sm text-gray-600">{wordCount.toLocaleString()}</div>
                </div>
                {note.filename && (
                  <div>
                    <div className="text-sm font-medium text-gray-900">Original File</div>
                    <div className="text-sm text-gray-600">{note.filename}</div>
                  </div>
                )}
              </div>

              {/* Full Transcript */}
              <div className="card">
                <div className="card-header flex justify-between items-center">
                  <h3 className="card-title">Full Medical Transcript</h3>
                  <button 
                    className="btn btn-outline btn-sm"
                    onClick={() => navigator.clipboard.writeText(note.text || '')}
                  >
                    Copy Text
                  </button>
                </div>
                <div className="card-content">
                  <div className="whitespace-pre-wrap text-sm text-gray-700 leading-relaxed">
                    {note.text || 'No transcript available'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'medical' && hasMedicalData && (
            <div className="space-y-6">
              {/* Critical Allergies */}
              {medicalData.allergies && medicalData.allergies.length > 0 && (
                <div className="alert alert-critical">
                  <div className="alert-title">ALLERGIES - CRITICAL INFORMATION</div>
                  <div className="alert-description">
                    <div className="flex flex-wrap gap-2 mt-2">
                      {medicalData.allergies.map((allergy, index) => (
                        <span key={index} className="bg-red-100 text-red-800 text-xs px-2 py-1 rounded">
                          {allergy}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Medical Sections */}
              {[
                { key: 'chief_complaints', title: 'Chief Complaints', icon: 'stethoscope' },
                { key: 'symptoms', title: 'Symptoms', icon: 'thermometer' },
                { key: 'drug_history', title: 'Current Medications', icon: 'pill' },
                { key: 'chronic_diseases', title: 'Chronic Conditions', icon: 'hospital' },
                { key: 'possible_diseases', title: 'Possible Diagnoses', icon: 'search' },
                { key: 'family_history', title: 'Family History', icon: 'users' }
              ].map(section => (
                medicalData[section.key] && medicalData[section.key].length > 0 && (
                  <div key={section.key} className="card">
                    <div className="card-header">
                      <h3 className="card-title">{section.title}</h3>
                    </div>
                    <div className="card-content">
                      <div className="space-y-2">
                        {medicalData[section.key].map((item, index) => (
                          <div key={index} className="flex items-start gap-3 p-3 bg-gray-50 rounded">
                            <div className="text-sm text-gray-700">
                              {typeof item === 'object' ? JSON.stringify(item, null, 2) : item}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )
              ))}
            </div>
          )}

          {activeTab === 'alerts' && hasAlerts && (
            <div className="space-y-4">
              {medicalAlerts.map((alert, index) => (
                <div key={index} className={`alert alert-${alert.priority === 'critical' ? 'critical' : alert.priority === 'high' ? 'warning' : 'info'}`}>
                  <div className="alert-title">{alert.title}</div>
                  <div className="alert-description">{alert.message}</div>
                  {alert.details && alert.details.length > 0 && (
                    <ul className="mt-2 space-y-1">
                      {alert.details.map((detail, detailIndex) => (
                        <li key={detailIndex} className="text-sm">• {detail}</li>
                      ))}
                    </ul>
                  )}
                  {alert.action_required && (
                    <div className="mt-3 p-2 bg-white bg-opacity-50 rounded">
                      <strong>Action Required:</strong> {alert.action_required}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <div className="flex gap-3">
            <button 
              className="btn btn-secondary"
              onClick={() => navigator.clipboard.writeText(note.text || '')}
            >
              Copy Transcript
            </button>
            
            <button 
              className="btn btn-secondary"
              onClick={() => apiService.downloadTranscript(note.session_id)}
            >
              Download Transcript
            </button>
            
            {hasMedicalData && (
              <button 
                className="btn btn-success"
                onClick={handleDownloadMedical}
              >
                Download Medical Data
              </button>
            )}
            
            <button className="btn btn-primary" onClick={onClose}>
              Close
            </button>
          </div>
        </div>