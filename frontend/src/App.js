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

  return (
    <div className="App">
      {/* Header */}
      <header className="header">
        <div className="logo">MaiChart</div>
        <nav className="nav">
          <a 
            href="#recording" 
            className={`nav-link ${currentSection === 'recording' ? 'active' : ''}`}
            onClick={(e) => {
              e.preventDefault();
              showRecordingSection();
            }}
          >
            🎤 Record
          </a>
          <a 
            href="#notes" 
            className={`nav-link ${currentSection === 'notes' ? 'active' : ''}`}
            onClick={(e) => {
              e.preventDefault();
              showNotesSection();
            }}
          >
            📝 Transcripts
          </a>
          <a 
            href="#summaries" 
            className={`nav-link ${currentSection === 'summaries' ? 'active' : ''}`}
            onClick={(e) => {
              e.preventDefault();
              showSummariesSection();
            }}
          >
            🏥 Medical Summaries
          </a>
        </nav>
      </header>

      {/* Main Container */}
      <div className="container">
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
      </div>

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