// App.js - Main Dashboard Component with Fixed Sidebar Toggle
import React, { useState } from 'react';
import AudioRecorder from './components/AudioRecorder';
import UnifiedNotesSection from './components/UnifiedNotesSection';
import Sidebar from './components/Sidebar';
import TopHeader from './components/TopHeader';
import './styles/App.css';
// In your main App.js or wherever you want the recorder
import StreamingRecorder from './components/StreamingRecorder';


const App = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false); // Start closed on mobile, open on desktop
  const [currentUser] = useState({ name: 'Arushi Vaidya', initials: 'AV' });
  const [refreshNotes, setRefreshNotes] = useState(0);

  const triggerNotesRefresh = () => {
    setRefreshNotes(prev => prev + 1);
  };

  // Handle sidebar toggle
  const handleSidebarToggle = (isOpen) => {
    setSidebarOpen(isOpen);
  };

  return (
    <div className="dashboard">
      <Sidebar isOpen={sidebarOpen} onToggle={handleSidebarToggle} />
      
      <div className={`main-container ${sidebarOpen ? 'sidebar-expanded' : ''}`}>
        <TopHeader 
          currentUser={currentUser}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        />
        
        <div className="content">
          <AudioRecorder onRecordingComplete={triggerNotesRefresh} />
          <StreamingRecorder />
          <UnifiedNotesSection refreshTrigger={refreshNotes} />
        </div>
      </div>
    </div>
  );
};

export default App;