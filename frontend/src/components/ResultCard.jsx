import React, { useState } from 'react';
import '../styles/ResultCard.css';

const ResultCard = ({ result, language }) => {
  const [isSpeaking, setIsSpeaking] = useState(false);

  if (!result) return null;

  const handleSpeak = () => {
    if (!window.speechSynthesis) {
      alert("Text-to-speech is not supported in this browser.");
      return;
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    const textToRead = `
      AI Analysis Result. 
      Condition: ${result.condition}. 
      Urgency Level: ${result.urgency}. 
      Recommended Actions: ${result.advice}.
    `;

    const utterance = new SpeechSynthesisUtterance(textToRead);
    
    // Set locale based on selected language
    const locale = language === 'ta' ? 'ta-IN' : 'en-US';
    utterance.lang = locale;
    
    // Try to find a matching voice
    const voices = window.speechSynthesis.getVoices();
    const matchingVoice = voices.find(voice => voice.lang.includes(locale));
    if (matchingVoice) {
      utterance.voice = matchingVoice;
    }

    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    
    setIsSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  const getUrgencyClass = (urgency) => {
    const lower = urgency.toLowerCase();
    if (lower.includes('high') || lower.includes('severe')) return 'urgency-high';
    if (lower.includes('moderate')) return 'urgency-moderate';
    return 'urgency-low';
  };

  return (
    <div className="result-card">
      <div className="result-header">
        <div className="header-top">
          <span className="analysis-badge">AI Analysis</span>
          <p className={`urgency-badge ${getUrgencyClass(result.urgency)}`}>
            {result.urgency} Priority
          </p>
        </div>
        <h2>{result.condition}</h2>
      </div>

      <div className="result-body">
        {result.history_note && (
          <div className="history-note">
            <span className="info-icon">ℹ️</span> 
            <div>
              <strong>History Match:</strong> {result.history_note}
            </div>
          </div>
        )}

        <div className="result-item">
          <h3>{language === 'ta' ? 'பரிந்துரைக்கப்பட்ட நடவடிக்கைகள்' : 'Recommended Actions'}</h3>
          <div className="advice-text">{result.advice}</div>
        </div>

        <button 
          onClick={handleSpeak}
          className="speak-btn"
          title={isSpeaking ? (language === 'ta' ? 'வாசிப்பதை நிறுத்து' : 'Stop Speaking') : (language === 'ta' ? 'முடிவைப் பேசு' : 'Speak Result')}
        >
          {isSpeaking ? (language === 'ta' ? '🛑 வாசிப்பதை நிறுத்து' : '🛑 Stop Reading') : (language === 'ta' ? '🔊 முடிவைப் பேசு' : '🔊 Speak Result')}
        </button>

        <div className="result-disclaimer">
          <strong>{language === 'ta' ? 'முக்கியமானது:' : 'Important:'}</strong> {result.disclaimer}
        </div>
      </div>
    </div>
  );
};

export default ResultCard;
