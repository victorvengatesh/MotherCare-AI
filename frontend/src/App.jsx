import React, { useState, lazy, Suspense } from 'react';
import Header from './components/Header';
import ErrorBoundary from './components/ErrorBoundary';
import { getToken, setToken, removeToken } from './services/api';
import './styles/global.css';

// Lazy load route pages for optimal chunk size and performance
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ChatPage = lazy(() => import('./pages/ChatPage'));
const RiskDashboard = lazy(() => import('./pages/RiskDashboard'));
const DoctorDashboard = lazy(() => import('./pages/DoctorDashboard'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const AppointmentsPage = lazy(() => import('./pages/AppointmentsPage'));

const PATIENT_TABS = [
  { id: 'dashboard',    label: '🩺 Symptom Analysis' },
  { id: 'chat',         label: '🤖 AI Consultation' },
  { id: 'risk',         label: '🧬 Digital Twin' },
  { id: 'appointments', label: '📅 Appointments' },
];

const DOCTOR_TABS = [
  { id: 'patients',     label: '👩‍⚕️ Patient Directory' },
  { id: 'appointments', label: '📅 Appointments' },
];

const ADMIN_TABS = [
  { id: 'admin',        label: '🛡️ Admin Panel' },
  { id: 'appointments', label: '📅 Appointments' },
];

function App() {
  const [token, setTokenState] = useState(() => getToken());
  const [username, setUsername] = useState(() => localStorage.getItem('mc_username') || '');
  const [role, setRole] = useState(() => localStorage.getItem('mc_role') || 'patient');
  
  const TABS = role === 'admin' ? ADMIN_TABS : (role === 'doctor' ? DOCTOR_TABS : PATIENT_TABS);
  const initialTab = role === 'admin' ? 'admin' : (role === 'doctor' ? 'patients' : 'dashboard');
  
  const [activeTab, setActiveTab] = useState(initialTab);
  const [language, setLanguage] = useState('English');

  const handleLoginSuccess = (newToken, user, userRole) => {
    setToken(newToken);
    localStorage.setItem('mc_username', user);
    if (userRole) localStorage.setItem('mc_role', userRole);
    setTokenState(newToken);
    setUsername(user);
    if (userRole) {
        setRole(userRole);
        setActiveTab(userRole === 'admin' ? 'admin' : (userRole === 'doctor' ? 'patients' : 'dashboard'));
    }
  };

  const handleLogout = () => {
    removeToken();
    localStorage.removeItem('mc_username');
    localStorage.removeItem('mc_role');
    setTokenState(null);
    setUsername('');
    setRole('patient');
    setActiveTab('dashboard');
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
          <Suspense fallback={
            <div style={{ padding: '4rem', textAlign: 'center', color: '#247576', fontSize: '1.1rem', fontWeight: 600 }}>
              <div style={{
                display: 'inline-block', width: '30px', height: '30px',
                border: '3px solid rgba(36, 117, 118, 0.15)', borderTopColor: '#247576',
                borderRadius: '50%', animation: 'spin 1s infinite linear', marginBottom: '1rem'
              }} />
              <div>Loading diagnostics...</div>
            </div>
          }>
            {activeTab === 'dashboard'    && <Dashboard />}
            {activeTab === 'chat'         && <ChatPage language={language} setLanguage={setLanguage} />}
            {activeTab === 'risk'         && <RiskDashboard language={language} />}
            {activeTab === 'appointments' && <AppointmentsPage role={role} />}
            {activeTab === 'patients'     && <DoctorDashboard />}
            {activeTab === 'admin'        && <AdminDashboard />}
          </Suspense>
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
