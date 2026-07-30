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

const RiskDashboard = () => {
  const [twin, setTwin]       = useState(null);
  const [trends, setTrends]   = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [instructions, setInstructions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState(null);
  const [form, setForm]       = useState({});
  const [editMode, setEditMode] = useState(false);
  const [saved, setSaved]     = useState(false);

  const fetchTwinAndTrends = async () => {
    setLoading(true);
    setError(null);
    try {
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

      // Fetch patient trends
      const trendsRes = await api.get('/ai/trends');
      setTrends(trendsRes.data?.data?.trends || []);
      setTimeline(trendsRes.data?.data?.alert_timeline || []);

      // Fetch instructions
      const instRes = await api.get('/ai/instructions');
      setInstructions(instRes.data?.data?.instructions || []);
    } catch (e) {
      let errorMsg = 'Failed to load Digital Twin data. ';
      if (e.message?.includes('timeout') || e.isTimeout) {
        errorMsg += 'Request timed out.';
      } else {
        errorMsg += 'Please try again.';
      }
      setError(errorMsg);
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkRead = async (instId) => {
    try {
      await api.post(`/ai/instruction/${instId}/read`);
      setInstructions(prev => prev.map(inst =>
        inst.id === instId ? { ...inst, read_at: new Date().toISOString() } : inst
      ));
    } catch (e) {
      console.error("Failed to mark instruction as read:", e);
    }
  };

  useEffect(() => { fetchTwinAndTrends(); }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    const payload = {};
    Object.entries(form).forEach(([k, v]) => { if (v !== '') payload[k] = parseFloat(v) || v; });
    try {
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
      
      // Refresh trends
      const trendsRes = await api.get('/ai/trends');
      setTrends(trendsRes.data?.data?.trends || []);
      setTimeline(trendsRes.data?.data?.alert_timeline || []);
    } catch (e) {
      setError('Save failed. Please try again.');
      console.error(e);
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
      ❌ {error} <button onClick={fetchTwinAndTrends} style={{ marginLeft: 8, color: '#247576', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }}>Retry</button>
    </div>
  );

  const risks = twin?.risk_analysis?.risk_scores || {};
  const insights = twin?.risk_analysis?.insights || [];
  const overall = twin?.risk_analysis?.overall_risk || 'Low';
  const overallColor = RISK_COLOR(overall === 'High' ? 0.8 : overall === 'Moderate' ? 0.4 : 0.1);

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '1.5rem', fontFamily: 'Inter, sans-serif' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ margin: 0, color: '#1e293b', fontWeight: 800 }}>🧬 Digital Twin — Maternal Analytics</h2>
          <p style={{ margin: '0.25rem 0 0', color: '#64748b', fontSize: '0.85rem' }}>
            User: <strong>{twin?.username}</strong> · Gestational Week {twin?.current_week ?? '?'} · Last updated: {twin?.last_updated ? new Date(twin.last_updated).toLocaleString() : '—'}
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

      {/* Awaiting clinical review banner */}
      {twin?.awaiting_review && (
        <div style={{
          backgroundColor: '#fff7ed', border: '1px solid #ffedd5',
          borderRadius: 12, padding: '1rem 1.5rem', marginBottom: '1.5rem',
          display: 'flex', alignItems: 'center', gap: '1rem'
        }}>
          <span style={{ fontSize: '1.5rem' }}>⏳</span>
          <div>
            <div style={{ fontWeight: 800, color: '#c2410c' }}>Case Awaiting Clinician Review</div>
            <div style={{ fontSize: '0.8rem', color: '#ea580c' }}>
              Your latest biomarkers or symptom reports have triggered a clinical review request. A qualified doctor is reviewing your case now.
            </div>
          </div>
        </div>
      )}

      {/* Overall risk badge */}
      <div style={{ backgroundColor: overallColor.bg, border: `1px solid ${overallColor.border}`, borderRadius: 12, padding: '1rem 1.5rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <span style={{ fontSize: '2rem' }}>{overall === 'High' ? '🔴' : overall === 'Moderate' ? '🟡' : '🟢'}</span>
        <div>
          <div style={{ fontWeight: 800, fontSize: '1.1rem', color: overallColor.text }}>Overall Status: {overall} Risk</div>
          <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Computed from ML models and vital thresholds</div>
        </div>
      </div>

      {/* Clinical Care Instructions Panel */}
      {instructions.length > 0 && (
        <div style={{
          backgroundColor: '#fff',
          border: '1px solid #e2e8f0',
          borderRadius: 12,
          padding: '1.5rem',
          marginBottom: '1.5rem',
          boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)'
        }}>
          <h3 style={{ margin: '0 0 1rem', color: '#1e293b', fontSize: '1.1rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>🩺</span> Doctor's Care Guidelines ({instructions.filter(i => !i.read_at).length} Unread)
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {instructions.map((inst) => {
              const isHigh = inst.priority === 'High';
              const isRead = !!inst.read_at;
              return (
                <div key={inst.id} style={{
                  padding: '1rem',
                  borderRadius: 8,
                  border: isHigh ? '1px solid #fca5a5' : '1px solid #cbd5e1',
                  backgroundColor: isRead ? '#f8fafc' : (isHigh ? '#fff5f5' : '#f0fdfa'),
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: '1rem'
                }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                      <span style={{
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        padding: '0.15rem 0.4rem',
                        borderRadius: 4,
                        backgroundColor: isHigh ? '#ef4444' : '#0f766e',
                        color: '#fff'
                      }}>
                        {inst.priority}
                      </span>
                      <strong style={{ fontSize: '0.85rem', color: '#334155' }}>
                        From: Dr. {inst.doctor_name}
                      </strong>
                      <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                        {new Date(inst.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p style={{
                      margin: 0,
                      fontSize: '0.9rem',
                      color: isRead ? '#64748b' : '#1e293b',
                      textDecoration: isRead ? 'line-through' : 'none',
                      lineHeight: 1.4
                    }}>
                      {inst.message}
                    </p>
                  </div>
                  {!isRead && (
                    <button
                      onClick={() => handleMarkRead(inst.id)}
                      style={{
                        padding: '0.5rem 1rem',
                        backgroundColor: '#247576',
                        color: '#fff',
                        border: 'none',
                        borderRadius: 6,
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        whiteSpace: 'nowrap'
                      }}
                    >
                      ✓ Mark as Read
                    </button>
                  )}
                  {isRead && (
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8', fontStyle: 'italic' }}>
                      ✓ Read {new Date(inst.read_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

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
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '1.5rem' }}>
          <h3 style={{ margin: '0 0 1rem', color: '#1e293b', fontSize: '1rem' }}>📊 Risk Scores</h3>
          <RiskBar label="Pre-eclampsia"          score={risks.pre_eclampsia        ?? 0} />
          <RiskBar label="Gestational Diabetes"   score={risks.gestational_diabetes ?? 0} />
          <RiskBar label="Anaemia"                score={risks.anemia               ?? 0} />
        </div>
        <div style={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '1.5rem' }}>
          <h3 style={{ margin: '0 0 1rem', color: '#1e293b', fontSize: '1rem' }}>💡 Diagnostic Insights</h3>
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

      {/* Vitals and Risk History Trends (For Patients) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '1.5rem' }}>
        {/* Left Card: Screening Trend Logs with Interactive SVG Chart */}
        <div style={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '1.5rem' }}>
          <h3 style={{ margin: '0 0 1rem', color: '#1e293b', fontSize: '1rem', fontWeight: 800 }}>
            📈 Screening Urgency Trend
          </h3>
          
          {trends.length === 0 ? (
            <p style={{ color: '#64748b', fontSize: '0.85rem', textAlign: 'center', padding: '2rem' }}>
              No screening entries found to display trends.
            </p>
          ) : (
            <div>
              {/* Interactive SVG Chart */}
              <div style={{ marginBottom: '1.5rem', background: '#f8fafc', padding: '1rem', borderRadius: '8px', border: '1px solid #f1f5f9' }}>
                <svg width="100%" height="200" viewBox="0 0 500 200" preserveAspectRatio="none">
                  {/* Grid Lines */}
                  <line x1="40" y1="30" x2="480" y2="30" stroke="#fee2e2" strokeDasharray="3,3" />
                  <text x="35" y="34" fontSize="9" textAnchor="end" fill="#dc2626" fontWeight="700">High</text>
                  
                  <line x1="40" y1="95" x2="480" y2="95" stroke="#fffbeb" strokeDasharray="3,3" />
                  <text x="35" y="99" fontSize="9" textAnchor="end" fill="#d97706" fontWeight="700">Mod</text>
                  
                  <line x1="40" y1="160" x2="480" y2="160" stroke="#f0fdf4" strokeDasharray="3,3" />
                  <text x="35" y="164" fontSize="9" textAnchor="end" fill="#16a34a" fontWeight="700">Low</text>

                  {/* Draw area & line */}
                  {(() => {
                    const points = trends.map((t, idx) => {
                      const val = t.urgency === 'High' ? 30 : t.urgency === 'Moderate' ? 95 : 160;
                      const x = 40 + (idx / Math.max(1, trends.length - 1)) * 440;
                      return { x, y: val, label: new Date(t.timestamp).toLocaleDateString(), t };
                    });

                    let lineD = '';
                    let areaD = 'M 40 160';
                    
                    points.forEach((p, idx) => {
                      if (idx === 0) {
                        lineD = `M ${p.x} ${p.y}`;
                        areaD = `M ${p.x} 160 L ${p.x} ${p.y}`;
                      } else {
                        lineD += ` L ${p.x} ${p.y}`;
                        areaD += ` L ${p.x} ${p.y}`;
                      }
                    });
                    if (points.length > 0) {
                      areaD += ` L ${points[points.length - 1].x} 160 Z`;
                    }

                    return (
                      <g>
                        {/* Area */}
                        {points.length > 1 && <path d={areaD} fill="url(#chart-grad)" opacity="0.15" />}
                        {/* Line */}
                        {points.length > 1 && <path d={lineD} fill="none" stroke="#247576" strokeWidth="2.5" />}
                        {/* Points */}
                        {points.map((p, idx) => (
                          <g key={idx}>
                            <circle
                              cx={p.x}
                              cy={p.y}
                              r="4"
                              fill="#fff"
                              stroke="#247576"
                              strokeWidth="2"
                              style={{ cursor: 'pointer' }}
                            />
                            <title>{`${p.label}\nUrgency: ${p.t.urgency}\nSymptoms: ${p.t.symptoms}`}</title>
                          </g>
                        ))}
                      </g>
                    );
                  })()}

                  <defs>
                    <linearGradient id="chart-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#247576" />
                      <stop offset="100%" stopColor="#247576" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>

              {/* Raw Entry Logs */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '200px', overflowY: 'auto' }}>
                {trends.slice().reverse().map((t, i) => (
                  <div key={i} style={{ padding: '0.75rem', borderRadius: '8px', border: '1px solid #f1f5f9', backgroundColor: '#fafafb', fontSize: '0.85rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', marginBottom: '0.25rem' }}>
                      <span>{new Date(t.timestamp).toLocaleDateString()}</span>
                      <strong style={{ color: t.urgency === 'High' ? '#dc2626' : (t.urgency === 'Moderate' ? '#d97706' : '#16a34a') }}>
                        {t.urgency} Urgency
                      </strong>
                    </div>
                    <p style={{ margin: 0, color: '#334155' }}><strong>Symptoms Reported:</strong> {t.symptoms}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Card: Alerts Timeline & Status Distribution */}
        <div style={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '1.5rem' }}>
          <h3 style={{ margin: '0 0 1rem', color: '#1e293b', fontSize: '1rem', fontWeight: 800 }}>
            🔔 Alert Status Distribution
          </h3>
          
          {timeline.length === 0 ? (
            <p style={{ color: '#64748b', fontSize: '0.85rem', textAlign: 'center', padding: '2rem' }}>
              All systems normal. No active or historical risk alerts raised.
            </p>
          ) : (
            <div>
              {/* Alert Gauges */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', marginBottom: '1.5rem', background: '#f8fafc', padding: '1rem', borderRadius: '8px' }}>
                {(() => {
                  const counts = { new: 0, resolved: 0, escalated: 0 };
                  timeline.forEach(a => {
                    if (counts[a.status] !== undefined) counts[a.status]++;
                  });
                  const total = timeline.length;
                  const pct = (val) => Math.round((val / total) * 100);

                  return (
                    <>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', fontWeight: 600, color: '#475569', marginBottom: 2 }}>
                          <span>New Alerts</span>
                          <span>{counts.new} ({pct(counts.new)}%)</span>
                        </div>
                        <div style={{ height: 6, backgroundColor: '#e2e8f0', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct(counts.new)}%`, backgroundColor: '#ef4444' }} />
                        </div>
                      </div>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', fontWeight: 600, color: '#475569', marginBottom: 2 }}>
                          <span>Escalated Alerts</span>
                          <span>{counts.escalated} ({pct(counts.escalated)}%)</span>
                        </div>
                        <div style={{ height: 6, backgroundColor: '#e2e8f0', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct(counts.escalated)}%`, backgroundColor: '#a855f7' }} />
                        </div>
                      </div>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', fontWeight: 600, color: '#475569', marginBottom: 2 }}>
                          <span>Resolved Alerts</span>
                          <span>{counts.resolved} ({pct(counts.resolved)}%)</span>
                        </div>
                        <div style={{ height: 6, backgroundColor: '#e2e8f0', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct(counts.resolved)}%`, backgroundColor: '#22c55e' }} />
                        </div>
                      </div>
                    </>
                  );
                })()}
              </div>

              {/* Raw Timeline Events */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '200px', overflowY: 'auto' }}>
                {timeline.slice().reverse().map((item, i) => (
                  <div key={i} style={{ padding: '0.75rem', borderRadius: '8px', border: '1px solid #cbd5e1', backgroundColor: '#fff', fontSize: '0.8rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                      <strong>{item.alert_source.toUpperCase()} Alert ({item.risk_level})</strong>
                      <span>{new Date(item.created_at).toLocaleDateString()}</span>
                    </div>
                    <p style={{ margin: '0 0 0.5rem', color: '#475569' }}>{item.warning_signs}</p>
                    <div>
                      Status: <strong style={{ color: item.status === 'resolved' ? '#16a34a' : (item.status === 'escalated' ? '#a855f7' : '#ea580c') }}>
                        {item.status.toUpperCase()}
                      </strong>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <p style={{ textAlign: 'center', color: '#94a3b8', fontSize: '0.72rem', marginTop: '1.5rem' }}>
        <strong>Medical Disclaimer:</strong> MotherCare AI is designed for informational purposes and decision support only. It is not a clinical diagnosis platform. Always seek professional advice from your doctor or local health coordinator for actual medical treatment or diagnosis.
      </p>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default RiskDashboard;
