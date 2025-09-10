// components/Sidebar.js - Fixed White Theme with Proper Toggle
import React from 'react';

const Sidebar = ({ isOpen, onToggle }) => {
  const navigationItems = [
    { key: 'find-care', icon: '🔍', label: 'Find Care' },
    { key: 'appointment', icon: '📅', label: 'Appointment' },
    { key: 'messages', icon: '💬', label: 'Messages', badge: 3 },
    { key: 'test-results', icon: '🧪', label: 'Test Results' },
    { key: 'medication', icon: '💊', label: 'Medication' },
    { key: 'immunizations', icon: '💉', label: 'Immunizations' },
    { key: 'maichart', icon: '🎤', label: 'MaiChart', active: true }, // Only this one active
    { key: 'payments', icon: '💳', label: 'Payments' },
    { key: 'medical-records', icon: '📋', label: 'Medical Records' }
  ];

  return (
    <div className={`sidebar ${isOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
      <div className="sidebar-content">
        <div className="patient-menu-header">
          <button 
            className="sidebar-toggle-btn"
            onClick={() => onToggle(!isOpen)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d={isOpen ? "m15 18-6-6 6-6" : "m9 18 6-6-6-6"}/>
            </svg>
          </button>
          {isOpen && (
            <div className="patient-menu-title">
              <span>Patient Menu</span>
            </div>
          )}
        </div>
        
        <nav className="sidebar-nav">
          {navigationItems.map((item) => (
            <a 
              key={item.key} 
              href="#" 
              className={`nav-item ${item.active ? 'nav-item-active' : ''}`}
              onClick={(e) => {
                e.preventDefault();
                if (item.key !== 'maichart') {
                  // Only MaiChart is operational, others do nothing
                }
              }}
            >
              <div className="nav-item-content">
                <span className="nav-icon">{item.icon}</span>
                {isOpen && (
                  <>
                    <span className="nav-label">{item.label}</span>
                    {item.badge && <span className="nav-badge">{item.badge}</span>}
                  </>
                )}
              </div>
            </a>
          ))}
        </nav>
      </div>
    </div>
  );
};

export default Sidebar;