import React, { useState, useEffect } from 'react';
import api from '../api/axios';

const RISK_COLOR = (score) => {
  if (score >= 0.65) return { bg: '#fef2f2', border: '#fecaca', text: '#dc2626', label: 'High' };
  if (score >= 0.30) return { bg: '#fffbeb', border: '#fde68a', text: '#d97706', label: 'Moderate' };
  return { bg: '#f0fdf4', border: '#bbf7d0', text: '#16a34a', label: 'Low' };
};

const VitalCard = ({ icon, label, value, unit, normal }) => (
  <div style={{
    backgroundColor: '#fff', borderRadius: 12, padding: '1.25rem',
    border: '1px solid #e2e8f0', boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  }}>
    <div style={{ fontSize: '1.5rem', marginBottom: '0.4rem' }}>{icon}</div>
    <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600, marginBottom: 4 }}>{label}</div>
    <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#1e293b' }}>
      {value ?? '—'} <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 500 }}>{unit}</span>
    </div>
    {normal && <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: 2 }}>Normal: {normal}</div>}
  </div>
);

const RiskBar = ({ label, score }) => {
  const c = RISK_COLOR(score);
  const pct = Math.round(score * 100);
  return (
    <div style={{ marginBottom: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#1e293b' }}>{label}</span>
        <span style={{ fontSize: '0.85rem', fontWeight: 700, color: c.text }}>{c.label} ({pct}%)</span>
      </div>
      <div style={{ height: 10, backgroundColor: '#f1f5f9', borderRadius: 99, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${pct}%`, borderRadius: 99,
          backgroundColor: c.text, transition: 'width 0.8s ease',
        }} />
      </div>
    </div>
  );
};

const RiskDashboard = ({ language }) => {
  const [twin, setTwin]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState(null);
  const [form, setForm]       = useState({});
  const [editMode, setEditMode] = useState(false);
  const [saved, setSaved]     = useState(false);

  const fetchTwin = async () => {
    setLoading(true);
    setError(null);
    try {
      // Add timeout protection
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Request timeout')), 15000)
      );
      
      const fetchPromise = api.get('/ai/twin');
      const res = await Promise.race([fetchPromise, timeoutPromise]);
      
      const twinData = res.data?.data;
      if (!twinData) {
        throw new Error('Invalid response from server');
      }
      
      setTwin(twinData);
      setForm({
        current_week:  twinData.current_week  ?? '',
        systolic_bp:   twinData.systolic_bp   ?? '',
        diastolic_bp:  twinData.diastolic_bp  ?? '',
        heart_rate:    twinData.heart_rate     ?? '',
        body_temp:     twinData.body_temp      ?? '',
        glucose_level: twinData.glucose_level ?? '',
        hemoglobin:    twinData.hemoglobin     ?? '',
        bmi:           twinData.bmi            ?? '',
      });
    } catch (e) {
      let errorMsg = 'Failed to load Digital Twin data. ';
      if (e.message?.includes('timeout') || e.isTimeout) {
        errorMsg += 'Request timed out. Please check your connection.';
      } else if (e.isServiceUnavailable) {
        errorMsg += 'Service temporarily unavailable. Please try again later.';
      } else if (e.isNetworkError) {
        errorMsg += 'Network error. Please check your connection.';
      } else {
        errorMsg += 'Please try again.';
      }
      setError(errorMsg);
      console.error('Fetch twin error:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTwin(); }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    const payload = {};
    Object.entries(form).forEach(([k, v]) => { if (v !== '') payload[k] = parseFloat(v) || v; });
    try {
      // Add timeout protection
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Request timeout')), 15000)
      );
      
      const savePromise = api.put('/ai/twin', payload);
      const res = await Promise.race([savePromise, timeoutPromise]);
      
      const updatedData = res.data?.data;
      if (!updatedData) {
        throw new Error('Invalid response from server');
      }
      
      setTwin(updatedData);
      setSaved(true);
      setEditMode(false);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      let errorMsg = 'Save failed. ';
      if (e.message?.includes('timeout') || e.isTimeout) {
        errorMsg += 'Request timed out.';
      } else if (e.isNetworkError) {
        errorMsg += 'Network error.';
      } else {
        errorMsg += 'Please try again.';
      }
      setError(errorMsg);
      console.error('Save error:', e);
    } finally {
      setSaving(false);
    }
  };

  const inp = (key, label, unit) => (
    <div key={key} style={{ marginBottom: '0.75rem' }}>
      <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#64748b', marginBottom: 3 }}>
        {label} {unit && <span style={{ color: '#94a3b8' }}>({unit})</span>}
      </label>
      <input type="number" step="any" value={form[key] ?? ''}
        onChange={(e) => setForm(p => ({ ...p, [key]: e.target.value }))}
        style={{ width: '100%', padding: '0.5rem 0.75rem', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: '0.9rem', outline: 'none' }}
        onFocus={(e) => e.target.style.borderColor = '#247576'}
        onBlur={(e) => e.target.style.borderColor = '#e2e8f0'}
      />
    </div>
  );

  if (loading) return (
    <div style={{ textAlign: 'center', padding: '4rem', color: '#64748b' }}>
      <div style={{ fontSize: '2rem', marginBottom: '1rem', animation: 'spin 1s linear infinite', display: 'inline-block' }}>⟳</div>
      <p>Loading your Digital Twin...</p>
    </div>
  );

  if (error) return (
    <div style={{ maxWidth: 600, margin: '3rem auto', padding: '1.5rem', backgroundColor: '#fef2f2', borderRadius: 12, color: '#dc2626', textAlign: 'center' }}>
      ❌ {error} <button onClick={fetchTwin} style={{ marginLeft: 8, color: '#247576', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }}>Retry</button>
    </div>
  );

  const risks = twin?.risk_analysis?.risk_scores || {};
  const insights = twin?.risk_analysis?.insights || [];
  const overall = twin?.risk_analysis?.overall_risk || 'Low';
  const overallColor = RISK_COLOR(overall === 'High' ? 0.8 : overall === 'Moderate' ? 0.4 : 0.1);

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '1.5rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ margin: 0, color: '#1e293b', fontWeight: 800 }}>🧬 Digital Twin — Risk Analytics</h2>
          <p style={{ margin: '0.25rem 0 0', color: '#64748b', fontSize: '0.85rem' }}>
            Week {twin?.current_week ?? '?'} · Last updated: {twin?.last_updated ? new Date(twin.last_updated).toLocaleString() : '—'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {saved && <span style={{ color: '#16a34a', fontWeight: 600, fontSize: '0.85rem', alignSelf: 'center' }}>✓ Saved</span>}
          <button onClick={() => setEditMode(e => !e)} style={{
            padding: '0.5rem 1.25rem', borderRadius: 8, border: '1px solid #e2e8f0',
            backgroundColor: editMode ? '#f1f5f9' : '#247576', color: editMode ? '#1e293b' : '#fff',
            fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer',
          }}>
            {editMode ? 'Cancel' : '✏️ Update Vitals'}
          </button>
          {editMode && (
            <button onClick={handleSave} disabled={saving} style={{
              padding: '0.5rem 1.25rem', borderRadius: 8, border: 'none',
              backgroundColor: saving ? '#94a3b8' : '#247576', color: '#fff',
              fontWeight: 600, fontSize: '0.85rem', cursor: saving ? 'not-allowed' : 'pointer',
            }}>
              {saving ? 'Saving...' : '💾 Save'}
            </button>
          )}
        </div>
      </div>

      {/* Overall risk badge */}
      <div style={{ backgroundColor: overallColor.bg, border: `1px solid ${overallColor.border}`, borderRadius: 12, padding: '1rem 1.5rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <span style={{ fontSize: '2rem' }}>{overall === 'High' ? '🔴' : overall === 'Moderate' ? '🟡' : '🟢'}</span>
        <div>
          <div style={{ fontWeight: 800, fontSize: '1.1rem', color: overallColor.text }}>Overall Risk: {overall}</div>
          <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Based on current biomarker readings</div>
        </div>
      </div>

      {/* Vitals grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <VitalCard icon="🫀" label="Systolic BP"   value={twin?.systolic_bp}    unit="mmHg"  normal="<120" />
        <VitalCard icon="🩸" label="Diastolic BP"  value={twin?.diastolic_bp}   unit="mmHg"  normal="<80" />
        <VitalCard icon="💓" label="Heart Rate"    value={twin?.heart_rate}     unit="bpm"   normal="60–100" />
        <VitalCard icon="🌡️"  label="Body Temp"    value={twin?.body_temp}      unit="°F"    normal="97–99" />
        <VitalCard icon="🍬" label="Glucose"       value={twin?.glucose_level}  unit="mg/dL" normal="<110" />
        <VitalCard icon="💉" label="Haemoglobin"   value={twin?.hemoglobin}     unit="g/dL"  normal="≥11" />
        <VitalCard icon="⚖️"  label="BMI"           value={twin?.bmi}            unit=""      normal="18.5–24.9" />
        <VitalCard icon="🤰" label="Pregnancy Week" value={twin?.current_week}  unit="wks"   normal="" />
      </div>

      {/* Edit form */}
      {editMode && (
        <div style={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '1.5rem', marginBottom: '1.5rem' }}>
          <h3 style={{ margin: '0 0 1rem', color: '#1e293b', fontSize: '1rem' }}>Update Biomarkers</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0 1.5rem' }}>
            {inp('current_week', 'Pregnancy Week', 'wks')}
            {inp('systolic_bp',  'Systolic BP', 'mmHg')}
            {inp('diastolic_bp', 'Diastolic BP', 'mmHg')}
            {inp('heart_rate',   'Heart Rate', 'bpm')}
            {inp('body_temp',    'Body Temp', '°F')}
            {inp('glucose_level','Glucose', 'mg/dL')}
            {inp('hemoglobin',   'Haemoglobin', 'g/dL')}
            {inp('bmi',          'BMI', '')}
          </div>
        </div>
      )}

      {/* Risk scores */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        <div style={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '1.5rem' }}>
          <h3 style={{ margin: '0 0 1rem', color: '#1e293b', fontSize: '1rem' }}>📊 Risk Scores</h3>
          <RiskBar label="Pre-eclampsia"          score={risks.pre_eclampsia        ?? 0} />
          <RiskBar label="Gestational Diabetes"   score={risks.gestational_diabetes ?? 0} />
          <RiskBar label="Anaemia"                score={risks.anemia               ?? 0} />
        </div>
        <div style={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '1.5rem' }}>
          <h3 style={{ margin: '0 0 1rem', color: '#1e293b', fontSize: '1rem' }}>💡 Clinical Insights</h3>
          {insights.length === 0
            ? <p style={{ color: '#64748b', fontSize: '0.85rem' }}>No insights available yet.</p>
            : insights.map((ins, i) => (
              <div key={i} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <span style={{ color: '#247576', fontWeight: 700, flexShrink: 0 }}>→</span>
                <span style={{ fontSize: '0.85rem', color: '#1e293b', lineHeight: 1.5 }}>{ins}</span>
              </div>
            ))
          }
        </div>
      </div>

      <p style={{ textAlign: 'center', color: '#94a3b8', fontSize: '0.72rem', marginTop: '1.5rem' }}>
        Risk scores are indicative only. Always consult a qualified healthcare professional.
      </p>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default RiskDashboard;
