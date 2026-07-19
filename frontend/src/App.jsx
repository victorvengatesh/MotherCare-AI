import React, { useState } from 'react';
import Header from './components/Header';
import ErrorBoundary from './components/ErrorBoundary';
import Dashboard from './pages/Dashboard';
import ChatPage from './pages/ChatPage';
import RiskDashboard from './pages/RiskDashboard';
import LoginPage from './pages/LoginPage';
import { getToken, setToken, removeToken } from './services/api';
import './styles/global.css';

const TABS = [
  { id: 'dashboard', label: '🩺 Symptom Analysis' },
  { id: 'chat',      label: '🤖 AI Consultation' },
  { id: 'risk',      label: '🧬 Digital Twin' },
];

function App() {
  const [token, setTokenState] = useState(() => getToken());
  const [username, setUsername] = useState(() => localStorage.getItem('mc_username') || '');
  const [activeTab, setActiveTab] = useState('dashboard');
  const [language, setLanguage] = useState('English');

  const handleLoginSuccess = (newToken, user) => {
    setToken(newToken);
    localStorage.setItem('mc_username', user);
    setTokenState(newToken);
    setUsername(user);
  };

  const handleLogout = () => {
    removeToken();
    localStorage.removeItem('mc_username');
    setTokenState(null);
    setUsername('');
  };

  if (!token) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <ErrorBoundary>
      <div className="app">
        <Header username={username} onLogout={handleLogout} />

        {/* Tab navigation */}
        <nav style={{
          backgroundColor: '#fff',
          borderBottom: '1px solid #e2e8f0',
          padding: '0 1.5rem',
          display: 'flex',
          gap: '0',
        }}>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '0.85rem 1.5rem',
                border: 'none',
                borderBottom: activeTab === tab.id ? '3px solid #247576' : '3px solid transparent',
                backgroundColor: 'transparent',
                color: activeTab === tab.id ? '#247576' : '#64748b',
                fontWeight: activeTab === tab.id ? 700 : 500,
                fontSize: '0.9rem',
                cursor: 'pointer',
                transition: 'all 0.2s',
                whiteSpace: 'nowrap',
              }}
              onMouseEnter={(e) => { if (activeTab !== tab.id) e.target.style.color = '#247576'; }}
              onMouseLeave={(e) => { if (activeTab !== tab.id) e.target.style.color = '#64748b'; }}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Page content */}
        <main style={{ minHeight: 'calc(100vh - 180px)', backgroundColor: '#f8fafc', padding: '1.5rem' }}>
          {activeTab === 'dashboard' && <Dashboard />}
          {activeTab === 'chat'      && <ChatPage language={language} setLanguage={setLanguage} />}
          {activeTab === 'risk'      && <RiskDashboard language={language} />}
        </main>

        <footer style={{
          textAlign: 'center', padding: '1.25rem',
          color: '#94a3b8', fontSize: '0.78rem',
          borderTop: '1px solid #e2e8f0', backgroundColor: '#fff',
        }}>
          &copy; {new Date().getFullYear()} MotherCare AI — For informational purposes only. Not a substitute for professional medical advice.
        </footer>
      </div>
    </ErrorBoundary>
  );
}

export default App;
