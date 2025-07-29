import React, { useState } from 'react';
import AudioRecorder from './components/AudioRecorder';
import NotesSection from './components/NotesSection';
import TranscriptModal from './components/TranscriptModal';
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
            Record
          </a>
          <a 
            href="#notes" 
            className={`nav-link ${currentSection === 'notes' ? 'active' : ''}`}
            onClick={(e) => {
              e.preventDefault();
              showNotesSection();
            }}
          >
            Notes
          </a>
        </nav>
      </header>

      {/* Main Container */}
      <div className="container">
        {currentSection === 'recording' && (
          <AudioRecorder onShowNotes={showNotesSection} />
        )}
        
        {currentSection === 'notes' && (
          <NotesSection 
            onShowRecording={showRecordingSection}
            onOpenTranscript={openTranscriptModal}
          />
        )}
      </div>

      {/* Modal for transcript viewing */}
      <TranscriptModal 
        isOpen={modalData.isOpen}
        note={modalData.note}
        onClose={closeTranscriptModal}
      />
    </div>
  );
}

export default App;