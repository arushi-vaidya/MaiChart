import React, { useState } from 'react';
import AudioRecorder from './components/AudioRecorder';
import NotesSection from './components/NotesSection';
import MedicalSummariesSection from './components/MedicalSummariesSection';
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

  const showSummariesSection = () => {
    setCurrentSection('summaries');
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
      title: 'Record',
      description: 'Create new voice note',
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
      title: 'Transcripts',
      description: 'View all transcriptions',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="nav-icon">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14,2 14,8 20,8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
          <polyline points="10,9 9,9 8,9"/>
        </svg>
      )
    },
    {
      key: 'summaries',
      title: 'Medical Data',
      description: 'AI-extracted insights',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="nav-icon">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
        </svg>
      )
    }
  ];

  return (
    <div className="app">
      {/* Left Navigation Sidebar */}
      <nav className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="logo-icon">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
            <span className="logo-text">MaiChart</span>
          </div>
          <p className="logo-subtitle">Medical Voice Notes</p>
        </div>

        <div className="nav-items">
          {navigationItems.map((item) => (
            <button
              key={item.key}
              className={`nav-item ${currentSection === item.key ? 'active' : ''}`}
              onClick={() => {
                if (item.key === 'recording') showRecordingSection();
                else if (item.key === 'notes') showNotesSection();
                else if (item.key === 'summaries') showSummariesSection();
              }}
            >
              <div className="nav-item-icon">
                {item.icon}
              </div>
              <div className="nav-item-content">
                <h3 className="nav-item-title">{item.title}</h3>
                <p className="nav-item-description">{item.description}</p>
              </div>
            </button>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="status-indicator">
            <div className="status-dot"></div>
            <span>System Active</span>
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="main-content">
        {currentSection === 'recording' && (
          <AudioRecorder 
            onShowNotes={showNotesSection} 
            onShowSummaries={showSummariesSection}
          />
        )}
        
        {currentSection === 'notes' && (
          <NotesSection 
            onShowRecording={showRecordingSection}
            onOpenTranscript={openTranscriptModal}
            onShowSummaries={showSummariesSection}
          />
        )}

        {currentSection === 'summaries' && (
          <MedicalSummariesSection 
            onShowRecording={showRecordingSection}
            onShowNotes={showNotesSection}
            onOpenTranscript={openTranscriptModal}
          />
        )}
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