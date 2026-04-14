import React, { useState } from 'react';
import SymptomForm from '../components/SymptomForm';
import ImageUploader from '../components/ImageUploader';
import ResultCard from '../components/ResultCard';
import DisclaimerBox from '../components/DisclaimerBox';
import { analyzeSymptoms } from '../services/api';

const Dashboard = () => {
  const [symptoms, setSymptoms] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [language, setLanguage] = useState('en'); // 'en' or 'ta'

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!symptoms.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await analyzeSymptoms(symptoms, file);
      setResult(data);
    } catch (err) {
      setError(err.message || 'Failed to connect to backend');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="container">
      <section className="input-section" style={{
        backgroundColor: 'var(--white)',
        padding: '2rem',
        borderRadius: 'var(--border-radius)',
        boxShadow: 'var(--shadow-md)',
        marginBottom: '3rem'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2>{language === 'ta' ? 'உங்கள் நிலையை விவரிக்கவும்' : 'Describe Your Condition'}</h2>
          
          <div className="language-selector">
            <button 
              className={`lang-btn ${language === 'en' ? 'active' : ''}`}
              onClick={() => setLanguage('en')}
            >
              English
            </button>
            <button 
              className={`lang-btn ${language === 'ta' ? 'active' : ''}`}
              onClick={() => setLanguage('ta')}
            >
              தமிழ் (Tamil)
            </button>
          </div>
        </div>

        <p className="description" style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>
          {language === 'ta' 
            ? 'உங்கள் அறிகுறிகளைப் பற்றிய விவரங்களை வழங்கவும் மற்றும் விருப்பப்பட்டால் ஒரு புகைப்படத்தைப் பதிவேற்றவும். எங்கள் AI உதவியாளர் ஆரம்ப வழிகாட்டலை வழங்குவார்.' 
            : 'Please provide details about your symptoms and optionally upload a photo. Our AI assistant will provide preliminary guidance.'}
        </p>

        <form onSubmit={handleSubmit} className="analysis-form">
          <SymptomForm symptoms={symptoms} onChange={setSymptoms} language={language} />
          <ImageUploader onImageChange={setFile} />
          
          <button 
            type="submit" 
            className="submit-btn" 
            disabled={loading || !symptoms.trim()}
            style={{
              marginTop: '1rem',
              backgroundColor: (loading || !symptoms.trim()) ? 'var(--text-muted)' : 'var(--primary-color)',
              color: 'var(--white)',
              padding: '1rem 2rem',
              borderRadius: 'var(--border-radius)',
              fontWeight: '600',
              fontSize: '1rem',
              width: '100%',
              boxShadow: (loading || !symptoms.trim()) ? 'none' : '0 4px 6px -1px rgba(36, 117, 118, 0.2)'
            }}
          >
            {loading ? (language === 'ta' ? 'பகுப்பாய்வு செய்கிறது...' : 'Analyzing...') : (language === 'ta' ? 'அறிகுறிகளை பகுப்பாய்வு செய்யவும்' : 'Analyze Symptoms')}
          </button>
        </form>
      </section>

      {error && (
        <div className="error-message" style={{
          marginBottom: '2rem',
          padding: '1rem',
          backgroundColor: '#fef2f2',
          border: '1px solid #fee2e2',
          borderRadius: 'var(--border-radius)',
          color: 'var(--danger-color)',
          fontWeight: '500',
          textAlign: 'center'
        }}>
          ❌ {error}
        </div>
      )}

      {loading && !result && (
        <div style={{ textAlign: 'center', margin: '3rem 0' }}>
          <div className="loader" style={{ 
            border: '3px solid var(--secondary-color)', 
            borderTop: '3px solid var(--primary-color)',
            borderRadius: '50%',
            width: '40px',
            height: '40px',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 1rem'
          }}></div>
          <p style={{ color: 'var(--text-muted)', fontWeight: '500' }}>Processing your report...</p>
        </div>
      )}

      {result && (
        <div className="result-container" style={{ animation: 'fadeIn 0.6s ease-out' }}>
          <ResultCard result={result} language={language} />
        </div>
      )}
      
      {!result && !loading && (
        <DisclaimerBox text="This system is for informational purposes only. In case of emergency, please contact your local emergency services immediately." />
      )}

      <style>{`
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </main>
  );
};

export default Dashboard;
