// Enhanced UnifiedNotesSection.js with Medical Information Display
import React, { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';

const UnifiedNotesSection = ({ refreshTrigger }) => {
  const [notes, setNotes] = useState([]);
  const [filteredNotes, setFilteredNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNote, setSelectedNote] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [activeTab, setActiveTab] = useState('transcript');
  const [generatingActions, setGeneratingActions] = useState(false);
  const [followUpActions, setFollowUpActions] = useState([]);

  // Load notes with medical data
  const loadNotes = useCallback(async () => {
    try {
      setLoading(true);
      const notesResponse = await apiService.getAllNotes();
      const notesData = notesResponse.notes || [];
      
      // Enrich with medical data
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

  useEffect(() => {
    loadNotes();
  }, [loadNotes, refreshTrigger]);

  // Handle search
  const handleSearch = useCallback((query) => {
    setSearchQuery(query);
    if (!query.trim()) {
      setFilteredNotes(notes);
      return;
    }

    const filtered = notes.filter(note => {
      const searchText = query.toLowerCase();
      const patientName = note.medical_data?.patient_details?.name?.toLowerCase() || '';
      const symptoms = note.medical_data?.symptoms?.join(' ').toLowerCase() || '';
      const conditions = note.medical_data?.possible_diseases?.join(' ').toLowerCase() || '';
      
      return (
        (note.text && note.text.toLowerCase().includes(searchText)) ||
        patientName.includes(searchText) ||
        symptoms.includes(searchText) ||
        conditions.includes(searchText) ||
        note.session_id.toLowerCase().includes(searchText)
      );
    });
    setFilteredNotes(filtered);
  }, [notes]);

  // Generate follow-up actions using AI
  const generateFollowUpActions = async (transcript, medicalData) => {
    try {
      setGeneratingActions(true);
      
      // Simulate AI generation - in real implementation, this would call your backend
      // For now, generate based on medical data
      const actions = [];
      
      if (medicalData?.allergies && medicalData.allergies.length > 0) {
        actions.push({
          priority: 'critical',
          action: 'Update allergy information in patient chart',
          details: `Ensure allergies (${medicalData.allergies.join(', ')}) are prominently displayed in EHR`,
          category: 'Safety'
        });
      }
      
      if (medicalData?.symptoms && medicalData.symptoms.length > 0) {
        actions.push({
          priority: 'high',
          action: 'Schedule diagnostic tests',
          details: `Based on symptoms: ${medicalData.symptoms.slice(0, 3).join(', ')}`,
          category: 'Diagnostics'
        });
      }
      
      if (medicalData?.drug_history && medicalData.drug_history.length > 0) {
        actions.push({
          priority: 'medium',
          action: 'Review current medications',
          details: 'Check for drug interactions and dosage optimization',
          category: 'Medication Management'
        });
      }
      
      if (medicalData?.possible_diseases && medicalData.possible_diseases.length > 0) {
        actions.push({
          priority: 'high',
          action: 'Consider differential diagnosis',
          details: `Evaluate: ${medicalData.possible_diseases.slice(0, 2).join(', ')}`,
          category: 'Clinical Assessment'
        });
      }
      
      actions.push({
        priority: 'medium',
        action: 'Schedule follow-up appointment',
        details: 'Monitor progress and treatment response in 2-4 weeks',
        category: 'Care Coordination'
      });
      
      setFollowUpActions(actions);
    } catch (error) {
      console.error('Error generating follow-up actions:', error);
      setFollowUpActions([]);
    } finally {
      setGeneratingActions(false);
    }
  };

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

  // Get confidence level
  const getConfidenceLevel = useCallback((confidence) => {
    const conf = confidence || 0;
    if (conf >= 0.8) return 'high';
    if (conf >= 0.6) return 'medium';
    return 'low';
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

  // Open modal with full details
  const openNoteModal = (note) => {
    setSelectedNote(note);
    setShowModal(true);
    setActiveTab('transcript');
    setFollowUpActions([]);
    
    // Generate follow-up actions if medical data is available
    if (note.medical_data) {
      generateFollowUpActions(note.text, note.medical_data);
    }
  };

  // Download medical summary
  const downloadMedicalSummary = (note) => {
    const ehrSummary = generateEHRSummary(note);
    const blob = new Blob([ehrSummary], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `medical_summary_${note.session_id.substring(0, 8)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Generate EHR-formatted summary
  const generateEHRSummary = (note) => {
    const medicalData = note.medical_data;
    const date = new Date(note.created_at || note.timestamp);
    
    return `
ELECTRONIC HEALTH RECORD SUMMARY
=====================================

PATIENT ENCOUNTER SUMMARY
Date of Service: ${formatDate(date)}
Session ID: ${note.session_id}
Provider: AI Medical Transcription System
Documentation Type: Voice Note Transcription

PATIENT DEMOGRAPHICS
${medicalData?.patient_details ? `
Name: ${medicalData.patient_details.name || 'Not specified'}
Age: ${medicalData.patient_details.age || 'Not specified'}
Gender: ${medicalData.patient_details.gender || 'Not specified'}
Marital Status: ${medicalData.patient_details.marital_status || 'Not specified'}
Address: ${medicalData.patient_details.residence || 'Not specified'}
` : 'Patient demographics not extracted from transcript'}

CHIEF COMPLAINT(S)
${medicalData?.chief_complaints && medicalData.chief_complaints.length > 0 
  ? medicalData.chief_complaints.map((complaint, index) => `${index + 1}. ${complaint}`).join('\n')
  : 'No chief complaints documented'}

HISTORY OF PRESENT ILLNESS
${medicalData?.chief_complaint_details && medicalData.chief_complaint_details.length > 0
  ? medicalData.chief_complaint_details.map(detail => 
    `• ${detail.complaint || 'Complaint'}: ${detail.location ? `Located at ${detail.location}, ` : ''}${detail.severity ? `Severity ${detail.severity}, ` : ''}${detail.duration ? `Duration ${detail.duration}` : ''}`
  ).join('\n')
  : 'Detailed complaint information not available'}

REVIEW OF SYSTEMS
Current Symptoms:
${medicalData?.symptoms && medicalData.symptoms.length > 0
  ? medicalData.symptoms.map((symptom, index) => `${index + 1}. ${symptom}`).join('\n')
  : 'No specific symptoms documented'}

PAST MEDICAL HISTORY
${medicalData?.past_history && medicalData.past_history.length > 0
  ? medicalData.past_history.map((history, index) => `${index + 1}. ${history}`).join('\n')
  : 'No significant past medical history documented'}

CHRONIC CONDITIONS
${medicalData?.chronic_diseases && medicalData.chronic_diseases.length > 0
  ? medicalData.chronic_diseases.map((disease, index) => `${index + 1}. ${disease}`).join('\n')
  : 'No chronic conditions documented'}

CURRENT MEDICATIONS
${medicalData?.drug_history && medicalData.drug_history.length > 0
  ? medicalData.drug_history.map((medication, index) => `${index + 1}. ${medication}`).join('\n')
  : 'No current medications documented'}

ALLERGIES AND ADVERSE REACTIONS
${medicalData?.allergies && medicalData.allergies.length > 0
  ? '*** CRITICAL ALERT *** \n' + medicalData.allergies.map((allergy, index) => `${index + 1}. ${allergy}`).join('\n')
  : 'No known allergies (NKDA)'}

FAMILY HISTORY
${medicalData?.family_history && medicalData.family_history.length > 0
  ? medicalData.family_history.map((history, index) => `${index + 1}. ${history}`).join('\n')
  : 'Family history not documented'}

SOCIAL HISTORY
${medicalData?.lifestyle && medicalData.lifestyle.length > 0
  ? medicalData.lifestyle.map(lifestyle => 
    `• ${lifestyle.habit || 'Habit'}: ${lifestyle.frequency || 'Frequency not specified'}${lifestyle.duration ? ` for ${lifestyle.duration}` : ''}`
  ).join('\n')
  : 'Social history not documented'}

ASSESSMENT AND PLAN
Possible Diagnoses for Consideration:
${medicalData?.possible_diseases && medicalData.possible_diseases.length > 0
  ? medicalData.possible_diseases.map((disease, index) => `${index + 1}. ${disease}`).join('\n')
  : 'Differential diagnosis pending further evaluation'}

COMPLETE TRANSCRIPT
=====================================
${note.text || 'Transcript not available'}

QUALITY METRICS
=====================================
Transcription Confidence: ${Math.round((note.confidence || 0) * 100)}%
Word Count: ${note.text ? note.text.split(' ').length : 0}
Audio Duration: ${note.duration ? `${Math.round(note.duration)} seconds` : 'Not available'}
Processing Strategy: ${note.processing_strategy || 'Standard'}

AI EXTRACTION METADATA
${medicalData?.extraction_metadata ? `
Method: ${medicalData.extraction_metadata.method || 'Not specified'}
Processing Time: ${medicalData.extraction_metadata.processing_time_seconds || 'Not specified'} seconds
Timestamp: ${medicalData.extraction_metadata.timestamp || 'Not specified'}
` : 'Extraction metadata not available'}

=====================================
Document generated by MaiChart Medical AI System
This summary is generated from AI analysis and should be reviewed by qualified medical personnel.
All medical decisions should be made by licensed healthcare providers.
=====================================
`;
  };

  if (loading) {
    return (
      <div className="notes-section">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <h3>Loading Patient Notes...</h3>
          <p>Gathering transcripts and medical data</p>
        </div>
      </div>
    );
  }

  return (
    <div className="notes-section">
      {/* Header */}
      <div className="notes-header">
        <div className="header-content">
          <div className="header-left">
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
          </div>
        </div>

        {/* Search Bar */}
        <div className="search-bar">
          <div className="search-container">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="search-icon">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
            <input
              type="text"
              placeholder="Search by patient name, symptoms, conditions..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="search-input"
            />
          </div>
          <div className="notes-stats">
            <span className="stat">{filteredNotes.length} Notes</span>
            <span className="stat">{notes.filter(n => n.has_medical_data).length} AI Analyzed</span>
          </div>
        </div>
      </div>

      {/* Enhanced Medical Notes Grid */}
      {filteredNotes.length > 0 ? (
        <div className="medical-notes-grid">
          {filteredNotes.map((note) => {
            const date = new Date(note.created_at || note.timestamp);
            const confidence = note.confidence || 0;
            const confidenceLevel = getConfidenceLevel(confidence);
            const medicalData = note.medical_data;
            const patientDetails = medicalData?.patient_details || {};
            const hasAlerts = note.medical_alerts && note.medical_alerts.some(alert => 
              alert.priority === 'critical' || alert.priority === 'high'
            );
            
            return (
              <div 
                key={note.session_id}
                className={`medical-note-card ${hasAlerts ? 'has-alerts' : ''}`}
              >
                {/* Patient Header */}
                <div className="patient-header">
                  <div className="patient-info">
                    <div className="patient-avatar">
                      {patientDetails.name ? patientDetails.name.charAt(0).toUpperCase() : 'P'}
                    </div>
                    <div className="patient-details">
                      <h3 className="patient-name">
                        {patientDetails.name || 'Unknown Patient'}
                      </h3>
                      <div className="patient-meta">
                        {patientDetails.age && <span className="age">{patientDetails.age} years</span>}
                        {patientDetails.gender && <span className="gender">{patientDetails.gender}</span>}
                        {patientDetails.marital_status && <span className="marital">{patientDetails.marital_status}</span>}
                      </div>
                      <div className="visit-date">{formatDate(date)}</div>
                    </div>
                  </div>
                  
                  <div className="card-actions">
                    <button 
                      className="action-btn view-btn"
                      onClick={() => openNoteModal(note)}
                      title="View Full Medical Record"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                        <circle cx="12" cy="12" r="3"/>
                      </svg>
                    </button>
                    <button 
                      className="action-btn delete-btn"
                      onClick={(e) => deleteNote(note.session_id, e)}
                      title="Delete Note"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="m19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>
                      </svg>
                    </button>
                  </div>
                </div>

                {/* Medical Information */}
                <div className="medical-content">
                  {/* Chief Complaints */}
                  {medicalData?.chief_complaints && medicalData.chief_complaints.length > 0 && (
                    <div className="medical-section">
                      <h4>Chief Complaints</h4>
                      <ul className="medical-list">
                        {medicalData.chief_complaints.slice(0, 2).map((complaint, index) => (
                          <li key={index}>{complaint}</li>
                        ))}
                        {medicalData.chief_complaints.length > 2 && (
                          <li className="more-items">+{medicalData.chief_complaints.length - 2} more</li>
                        )}
                      </ul>
                    </div>
                  )}

                  {/* Allergies - Critical */}
                  {medicalData?.allergies && medicalData.allergies.length > 0 && (
                    <div className="medical-section critical">
                      <h4>⚠️ Allergies</h4>
                      <ul className="medical-list">
                        {medicalData.allergies.slice(0, 3).map((allergy, index) => (
                          <li key={index} className="allergy-item">{allergy}</li>
                        ))}
                        {medicalData.allergies.length > 3 && (
                          <li className="more-items">+{medicalData.allergies.length - 3} more</li>
                        )}
                      </ul>
                    </div>
                  )}

                  {/* Symptoms */}
                  {medicalData?.symptoms && medicalData.symptoms.length > 0 && (
                    <div className="medical-section">
                      <h4>Current Symptoms</h4>
                      <ul className="medical-list">
                        {medicalData.symptoms.slice(0, 3).map((symptom, index) => (
                          <li key={index}>{symptom}</li>
                        ))}
                        {medicalData.symptoms.length > 3 && (
                          <li className="more-items">+{medicalData.symptoms.length - 3} more</li>
                        )}
                      </ul>
                    </div>
                  )}

                  {/* Possible Conditions */}
                  {medicalData?.possible_diseases && medicalData.possible_diseases.length > 0 && (
                    <div className="medical-section">
                      <h4>Possible Conditions</h4>
                      <ul className="medical-list">
                        {medicalData.possible_diseases.slice(0, 2).map((condition, index) => (
                          <li key={index}>{condition}</li>
                        ))}
                        {medicalData.possible_diseases.length > 2 && (
                          <li className="more-items">+{medicalData.possible_diseases.length - 2} more</li>
                        )}
                      </ul>
                    </div>
                  )}

                  {!medicalData && (
                    <div className="no-medical-data">
                      <p>Medical analysis pending or unavailable</p>
                    </div>
                  )}
                </div>

                {/* Card Footer */}
                <div className="card-footer">
                  <div className="confidence-badge">
                    <span className={`confidence ${confidenceLevel}`}>
                      {Math.round(confidence * 100)}% confidence
                    </span>
                  </div>
                  {note.has_medical_data && (
                    <div className="ai-badge">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="3"/>
                        <path d="M12 1v6m0 6v6m11-7h-6m-6 0H1"/>
                      </svg>
                      AI Analyzed
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="empty-state">
          <div className="empty-icon">
            <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v56a2 2 0 0 0 2 2h52a2 2 0 0 0 2-2V16z"/>
              <polyline points="14,2 14,16 28,16"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <line x1="16" y1="21" x2="8" y2="21"/>
            </svg>
          </div>
          <h3>No Medical Notes Found</h3>
          <p>Start by recording your first medical consultation or uploading an audio file.</p>
        </div>
      )}

      {/* Enhanced Medical Modal */}
      {showModal && selectedNote && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="enhanced-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="header-title">
                <h2>Medical Record</h2>
                <p>{selectedNote.medical_data?.patient_details?.name || 'Unknown Patient'} - {formatDate(new Date(selectedNote.created_at || selectedNote.timestamp))}</p>
              </div>
              <button className="close-btn" onClick={() => setShowModal(false)}>×</button>
            </div>
            
            {/* Modal Tabs */}
            <div className="modal-tabs">
              <button 
                className={`tab-btn ${activeTab === 'transcript' ? 'active' : ''}`}
                onClick={() => setActiveTab('transcript')}
              >
                Complete Transcript
              </button>
              <button 
                className={`tab-btn ${activeTab === 'medical' ? 'active' : ''}`}
                onClick={() => setActiveTab('medical')}
              >
                EHR Summary
              </button>
              <button 
                className={`tab-btn ${activeTab === 'actions' ? 'active' : ''}`}
                onClick={() => setActiveTab('actions')}
              >
                Follow-up Actions
              </button>
            </div>

            <div className="modal-body">
              {activeTab === 'transcript' && (
                <div className="transcript-tab">
                  <div className="transcript-full">
                    {selectedNote.text || 'No transcript available'}
                  </div>
                </div>
              )}

              {activeTab === 'medical' && (
                <div className="medical-tab">
                  <div className="ehr-summary">
                    <pre className="ehr-content">{generateEHRSummary(selectedNote)}</pre>
                  </div>
                </div>
              )}

              {activeTab === 'actions' && (
                <div className="actions-tab">
                  {generatingActions ? (
                    <div className="loading-actions">
                      <div className="loading-spinner"></div>
                      <p>Generating AI follow-up recommendations...</p>
                    </div>
                  ) : (
                    <div className="follow-up-actions">
                      {followUpActions.map((action, index) => (
                        <div key={index} className={`action-item ${action.priority}`}>
                          <div className="action-header">
                            <span className={`priority-badge ${action.priority}`}>
                              {action.priority.toUpperCase()}
                            </span>
                            <span className="category-badge">{action.category}</span>
                          </div>
                          <h4>{action.action}</h4>
                          <p>{action.details}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            
            <div className="modal-footer">
              <button 
                className="btn btn-outline"
                onClick={() => downloadMedicalSummary(selectedNote)}
              >
                Download EHR Summary
              </button>
              <button 
                className="btn btn-outline"
                onClick={() => apiService.downloadTranscript(selectedNote.session_id)}
              >
                Download Transcript
              </button>
              <button className="btn btn-primary" onClick={() => setShowModal(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UnifiedNotesSection;