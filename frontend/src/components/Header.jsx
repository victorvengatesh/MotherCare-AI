import React from 'react';
import '../styles/Header.css';

const Header = () => {
  return (
    <header className="app-header">
      <div className="header-content">
        <div className="logo">
          <span className="logo-icon">➕</span>
          <h1>MotherCare AI</h1>
        </div>
        <nav>
          <p className="tagline">Smart Triage for Better Care</p>
        </nav>
      </div>
    </header>
  );
};

export default Header;
