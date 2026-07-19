import React from 'react';
import '../styles/Header.css';

const Header = ({ username, onLogout }) => {
  return (
    <header className="app-header">
      <div className="header-content">
        <div className="logo">
          <span className="logo-icon">➕</span>
          <h1>MotherCare AI</h1>
        </div>
        <nav style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {username && (
            <p className="tagline" style={{ margin: 0 }}>
              👤 {username}
            </p>
          )}
          {onLogout && (
            <button
              onClick={onLogout}
              style={{
                padding: '0.4rem 1rem',
                backgroundColor: 'transparent',
                color: 'var(--text-muted)',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                fontWeight: '600',
                fontSize: '0.8rem',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.target.style.backgroundColor = '#fef2f2';
                e.target.style.borderColor = '#fca5a5';
                e.target.style.color = '#dc2626';
              }}
              onMouseLeave={(e) => {
                e.target.style.backgroundColor = 'transparent';
                e.target.style.borderColor = '#e2e8f0';
                e.target.style.color = 'var(--text-muted)';
              }}
            >
              Sign Out
            </button>
          )}
          {!username && (
            <p className="tagline">Smart Triage for Better Care</p>
          )}
        </nav>
      </div>
    </header>
  );
};

export default Header;
