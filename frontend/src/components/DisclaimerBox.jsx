import React from 'react';

const DisclaimerBox = ({ text }) => {
  if (!text) return null;

  return (
    <div className="disclaimer-box" style={{
      marginTop: '2rem',
      padding: '1rem',
      backgroundColor: '#fff5f5',
      border: '1px solid #feb2b2',
      borderRadius: '8px',
      color: '#c53030',
      fontSize: '0.85rem'
    }}>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
        <span style={{ fontSize: '1.2rem' }}>⚠️</span>
        <div>
          <strong style={{ display: 'block', marginBottom: '0.25rem' }}>Important Disclaimer:</strong>
          <p>{text}</p>
        </div>
      </div>
    </div>
  );
};

export default DisclaimerBox;
