import React, { useState, useEffect } from 'react';

const SymptomForm = ({ symptoms, onChange, language }) => {
  const [isListening, setIsListening] = useState(false);
  const isSpeechSupported = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  const recognitionRef = React.useRef(null);

  useEffect(() => {
    if (!isSpeechSupported) {
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = language === 'ta' ? 'ta-IN' : 'en-US';

    rec.onresult = (event) => {
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        }
      }
      if (finalTranscript) {
        const separator = symptoms.trim() ? ' ' : '';
        onChange(symptoms + separator + finalTranscript);
      }
    };

    rec.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      setIsListening(false);
    };

    rec.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = rec;
  }, [symptoms, onChange, language, isSpeechSupported]);

  const toggleListening = () => {
    if (isListening) {
      if (recognitionRef.current) recognitionRef.current.stop();
    } else {
      setIsListening(true);
      if (recognitionRef.current) recognitionRef.current.start();
    }
  };

  return (
    <div className="form-group">
      <div className="voice-controls">
        <label htmlFor="symptoms"><strong>{language === 'ta' ? 'உங்கள் அறிகுறிகளை விவரிக்கவும்:' : 'Describe your symptoms:'}</strong></label>
        {isSpeechSupported ? (
          <button 
            type="button"
            className={`voice-btn ${isListening ? 'listening' : ''}`}
            onClick={toggleListening}
            title={isListening ? (language === 'ta' ? 'கேட்பதை நிறுத்து' : 'Stop Listening') : (language === 'ta' ? 'குரல் உள்ளீட்டைத் தொடங்கு' : 'Start Voice Input')}
          >
            {isListening ? (language === 'ta' ? '🛑 கேட்பதை நிறுத்து' : '🛑 Stop Listening') : (language === 'ta' ? '🎤 குரல் உள்ளீட்டைத் தொடங்கு' : '🎤 Start Voice Input')}
          </button>
        ) : (
          <span className="unsupported-msg">{language === 'ta' ? 'இந்த உலாவியில் குரல் உள்ளீடு ஆதரிக்கப்படவில்லை.' : 'Voice input is not supported in this browser.'}</span>
        )}
      </div>

      <textarea
        id="symptoms"
        rows="4"
        placeholder={language === 'ta' ? 'எ.கா., நேற்று இடது கையில் தோன்றிய சிவப்பு அரிப்பு தடிப்பு...' : 'e.g., Red itchy rash on the left arm that appeared yesterday...'}
        value={symptoms}
        onChange={(e) => onChange(e.target.value)}
        required
      ></textarea>
      <p className="help-text">{language === 'ta' ? 'அமைவிடம், காலம் மற்றும் உணர்வு பற்றிய விவரங்களை முடிந்தவரை தெளிவாக வழங்கவும்.' : 'Please be as specific as possible about the location, duration, and feeling.'}</p>
    </div>
  );
};

export default SymptomForm;
