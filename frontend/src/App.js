import React, { useState } from 'react';
import AudioRecorder from './components/AudioRecorder';
import UnifiedNotesSection from './components/UnifiedNotesSection';
import EnhancedTranscriptModal from './components/EnhancedTranscriptModal';
import './styles/App.css';

function App() {
  const [currentSection, setCurrentSection] = useState('recording');
  const [modalData, setModalData] = useState({ isOpen: false, note: null });

  const showRecordingSection = () => {
    setCurrentSection('recording');
  };

  const showNotesSection = () => {
    setCurrentSection('notes');
  };

  const openTranscriptModal = (note) => {
    setModalData({ isOpen: true, note });
  };

  const closeTranscriptModal = () => {
    setModalData({ isOpen: false, note: null });
  };

  const navigationItems = [
    {
      key: 'recording',
      title: 'Voice Notes',
      description: 'Record medical consultations',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="nav-icon">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <path d="M12 19v4"/>
          <path d="M8 23h8"/>
        </svg>
      )
    },
    {
      key: 'notes',
      title: 'Patient Records',
      description: 'View transcripts & medical data',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="nav-icon">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14,2 14,8 20,8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
      )
    }
  ];

  return (
    <div className="app">
      {/* Top Header Bar - Medical Dashboard Style */}
      <header className="top-header">
        <div className="header-left">
          <div className="logo-container">
            <img 
              src="/logo-icon.png" 
              alt="MaiChart Logo" 
              className="logo-image"
              onError={(e) => {
                // Fallback to SVG if image doesn't exist
                e.target.style.display = 'none';
                e.target.nextSibling.style.display = 'block';
              }}
            />
            <div className="logo-fallback" style={{display: 'none'}}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="logo-svg">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
              </svg>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="header-nav">
          <div className="nav-tabs">
            {navigationItems.map((item) => (
              <button
                key={item.key}
                className={`nav-tab ${currentSection === item.key ? 'active' : ''}`}
                onClick={() => {
                  if (item.key === 'recording') showRecordingSection();
                  else if (item.key === 'notes') showNotesSection();
                }}
              >
                <div className="nav-tab-icon">
                  {item.icon}
                </div>
                <div className="nav-tab-content">
                  <span className="nav-tab-title">{item.title}</span>
                  <span className="nav-tab-description">{item.description}</span>
                </div>
              </button>
            ))}
          </div>
        </nav>
      </header>

      {/* Main Content Area */}
      <main className="main-content">
        <div className="content-container">
          {currentSection === 'recording' && (
            <AudioRecorder 
              onShowNotes={showNotesSection}
            />
          )}
          
          {currentSection === 'notes' && (
            <UnifiedNotesSection 
              onShowRecording={showRecordingSection}
              onOpenTranscript={openTranscriptModal}
            />
          )}
        </div>
      </main>

      {/* Modal for transcript viewing */}
      <EnhancedTranscriptModal
        isOpen={modalData.isOpen}
        note={modalData.note}
        onClose={closeTranscriptModal}
      />
    </div>
  );
}

export default App;