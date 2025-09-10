// components/TopHeader.js - Fixed to Match Image Exactly
import React from 'react';

const TopHeader = ({ currentUser, onToggleSidebar }) => {
  return (
    <header className="top-header">
      <div className="header-left">
        <div className="logo-section">
          <img 
            src="/logo-icon.png" 
            alt="Logo" 
            className="logo-image"
            onError={(e) => {
              // Fallback to text if image doesn't exist
              e.target.style.display = 'none';
              e.target.nextSibling.style.display = 'flex';
            }}
          />
          <div className="logo-fallback" style={{display: 'none'}}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="logo-svg">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
          </div>
        </div>
      </div>

      {/* Center Navigation - Exactly like the image */}
      <nav className="center-nav">
        <div className="nav-tabs">
          <button className="nav-tab">
            <div className="nav-tab-content">
              <span className="nav-tab-title">Maichart</span>
              <span className="nav-tab-description">View lab results</span>
            </div>
          </button>
          
        </div>
      </nav>
      
    </header>
  );
};

export default TopHeader;