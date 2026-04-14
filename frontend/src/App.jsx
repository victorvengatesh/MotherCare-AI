import React from 'react';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import './styles/global.css';

function App() {
  return (
    <div className="app">
      <Header />
      <Dashboard />
      <footer style={{ 
        textAlign: 'center', 
        padding: '2rem', 
        color: 'var(--text-muted)',
        fontSize: '0.8rem'
      }}>
        &copy; {new Date().getFullYear()} MotherCare AI. All rights reserved.
      </footer>
    </div>
  );
}

export default App;
