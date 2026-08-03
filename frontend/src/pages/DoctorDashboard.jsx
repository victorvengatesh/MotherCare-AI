import React, { useState, useEffect } from 'react';
import { 
  getPatients, 
  getAlerts, 
  getPatientTwin, 
  getPatientTrends, 
  startReview, 
  addNotes, 
  escalateAlert, 
  resolveAlert, 
  dismissAlert,
  sendInstruction,
  listDoctorInstructions,
  updateInstruction,
  withdrawInstruction,
  applyOverride
} from '../services/api';

const ALERT_STATUS_DECORATION = {
  new: { label: 'New Alert', color: '#dc2626', bg: '#fef2f2', border: '#fecaca', icon: '🔔' },
  under_review: { label: 'Under Review', color: '#ea580c', bg: '#fff7ed', border: '#ffedd5', icon: '🩺' },
  escalated: { label: 'Escalated', color: '#7c3aed', bg: '#f5f3ff', border: '#e0e7ff', icon: '⚠️' },
  resolved: { label: 'Resolved', color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0', icon: '✅' },
  dismissed_as_false_positive: { label: 'Dismissed', color: '#64748b', bg: '#f8fafc', border: '#e2e8f0', icon: '🔇' },
};

const RISK_LEVEL_DECORATION = {
  Emergency: { label: 'Emergency (Critical)', color: '#dc2626', bg: '#fef2f2', border: '#fecaca' },
  High: { label: 'High Risk', color: '#b91c1c', bg: '#fff5f5', border: '#fed7d7' },
  Moderate: { label: 'Moderate Risk', color: '#d97706', bg: '#fffbeb', border: '#fde68a' },
  Low: { label: 'Low Risk', color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' },
};

const DoctorDashboard = () => {
  // State variables
  const [patients, setPatients] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [selectedPatientId, setSelectedPatientId] = useState(null);
  const [selectedPatientTwin, setSelectedPatientTwin] = useState(null);
  const [selectedPatientTrends, setSelectedPatientTrends] = useState(null);
  const [selectedAlert, setSelectedAlert] = useState(null);
  
  // Loading and Error states
  const [loadingPatients, setLoadingPatients] = useState(true);
  const [loadingAlerts, setLoadingAlerts] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [error, setError] = useState(null);

  // Filter States
  const [statusFilter, setStatusFilter] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalAlerts, setTotalAlerts] = useState(0);

  // Action Inputs
  const [noteText, setNoteText] = useState('');
  const [actionReason, setActionReason] = useState('');
  const [showReasonModal, setShowReasonModal] = useState(null); // 'resolve' | 'dismiss' | 'escalate'
  const [overrideRiskLvl, setOverrideRiskLvl] = useState('Low');
  const [overrideReason, setOverrideReason] = useState('');
  const [showOverrideForm, setShowOverrideForm] = useState(false);

  // Instruction panel states
  const [patientInstructions, setPatientInstructions] = useState([]);
  const [loadingInstructions, setLoadingInstructions] = useState(false);
  const [instructionMessage, setInstructionMessage] = useState('');
  const [instructionPriority, setInstructionPriority] = useState('Normal');
  const [instructionExpiry, setInstructionExpiry] = useState('');
  const [instructionVisible, setInstructionVisible] = useState(true);
  const [instructionAlertId, setInstructionAlertId] = useState('');
  const [editingInstructionId, setEditingInstructionId] = useState(null);
  const [instructionError, setInstructionError] = useState(null);
  const [instructionSuccess, setInstructionSuccess] = useState(null);

  // Metric counts
  const [metrics, setMetrics] = useState({
    new: 0,
    emergency: 0,
    high: 0,
    underReview: 0
  });

  useEffect(() => {
    fetchPatients();
    fetchAlerts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, riskFilter, currentPage]);

  const fetchPatients = async () => {
    setLoadingPatients(true);
    try {
      const res = await getPatients();
      setPatients(res.patients || []);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch assigned patients.');
    } finally {
      setLoadingPatients(false);
    }
  };

  const fetchAlerts = async () => {
    setLoadingAlerts(true);
    try {
      const params = {
        page: currentPage,
        limit: 10,
      };
      if (statusFilter) params.status = statusFilter;
      if (riskFilter) params.risk_level = riskFilter;
      
      const res = await getAlerts(params);
      setAlerts(res.alerts || []);
      setTotalAlerts(res.total_count || 0);

      // Compute metrics locally from recent alerts
      const allAlertsRes = await getAlerts({ limit: 50 });
      const list = allAlertsRes.alerts || [];
      setMetrics({
        new: list.filter(a => a.status === 'new').length,
        emergency: list.filter(a => a.risk_level === 'Emergency').length,
        high: list.filter(a => a.risk_level === 'High').length,
        underReview: list.filter(a => a.status === 'under_review').length,
      });
    } catch (err) {
      console.error(err);
      setError('Failed to fetch alert directory.');
    } finally {
      setLoadingAlerts(false);
    }
  };

  const handleSelectPatient = async (patientId, alertItem = null) => {
    setSelectedPatientId(patientId);
    setSelectedAlert(alertItem);
    setLoadingDetails(true);
    setNoteText(alertItem?.doctor_notes || '');
    setActionReason('');
    
    setInstructionMessage('');
    setInstructionPriority('Normal');
    setInstructionExpiry('');
    setInstructionVisible(true);
    setInstructionAlertId(alertItem?.id || '');
    setEditingInstructionId(null);
    setInstructionError(null);
    setInstructionSuccess(null);

    setLoadingInstructions(true);
    
    try {
      const twinRes = await getPatientTwin(patientId);
      setSelectedPatientTwin(twinRes.twin);
      
      const trendRes = await getPatientTrends(patientId);
      setSelectedPatientTrends(trendRes);

      const instRes = await listDoctorInstructions(patientId);
      setPatientInstructions(instRes.instructions || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingDetails(false);
      setLoadingInstructions(false);
    }
  };

  const triggerStartReview = async (alertId) => {
    try {
      await startReview(alertId);
      fetchAlerts();
      if (selectedAlert && selectedAlert.id === alertId) {
        setSelectedAlert(prev => ({ ...prev, status: 'under_review' }));
      }
    } catch (err) {
      alert(err.message || 'Failed to start review.');
    }
  };

  const triggerAddNotes = async () => {
    if (!noteText.trim()) return;
    try {
      await addNotes(selectedAlert.id, noteText);
      alert('Clinical note successfully added.');
      fetchAlerts();
    } catch (err) {
      alert(err.message || 'Failed to save notes.');
    }
  };

  const triggerEscalate = async () => {
    try {
      await escalateAlert(selectedAlert.id, actionReason);
      setShowReasonModal(null);
      setActionReason('');
      fetchAlerts();
      handleSelectPatient(selectedPatientId, { ...selectedAlert, status: 'escalated' });
    } catch (err) {
      alert(err.message || 'Failed to escalate alert.');
    }
  };

  const triggerResolve = async () => {
    if (!actionReason.trim()) {
      alert('A resolution reason is mandatory.');
      return;
    }
    try {
      await resolveAlert(selectedAlert.id, actionReason);
      setShowReasonModal(null);
      setActionReason('');
      fetchAlerts();
      handleSelectPatient(selectedPatientId, { ...selectedAlert, status: 'resolved', resolution_reason: actionReason });
    } catch (err) {
      alert(err.message || 'Failed to resolve alert.');
    }
  };

  const triggerDismiss = async () => {
    if (!actionReason.trim()) {
      alert('A dismissal reason is mandatory.');
      return;
    }
    try {
      await dismissAlert(selectedAlert.id, actionReason);
      setShowReasonModal(null);
      setActionReason('');
      fetchAlerts();
      handleSelectPatient(selectedPatientId, { ...selectedAlert, status: 'dismissed_as_false_positive', resolution_reason: actionReason });
    } catch (err) {
      alert(err.message || 'Failed to dismiss alert.');
    }
  };

  const handleApplyOverride = async () => {
    if (!overrideReason.trim()) {
      alert("Please specify a reason for the clinical override.");
      return;
    }
    try {
      await applyOverride(selectedAlert.id, overrideRiskLvl, overrideReason);
      alert("Clinical override applied successfully!");
      setShowOverrideForm(false);
      setOverrideReason('');
      
      // Update local state
      setSelectedAlert(prev => ({
        ...prev,
        risk_level: overrideRiskLvl,
        doctor_notes: prev.doctor_notes 
          ? `${prev.doctor_notes}\n[Clinical Override] Changed to ${overrideRiskLvl}. Reason: ${overrideReason}`
          : `[Clinical Override] Changed to ${overrideRiskLvl}. Reason: ${overrideReason}`
      }));
      fetchAlerts();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to apply override.");
    }
  };

  const handlePublishInstruction = async (e) => {
    e.preventDefault();
    if (!instructionMessage.trim()) {
      setInstructionError("Instruction message is required.");
      return;
    }
    
    setInstructionError(null);
    setInstructionSuccess(null);
    
    const payload = {
      patient_id: selectedPatientId,
      message: instructionMessage,
      priority: instructionPriority,
      patient_visible: instructionVisible,
      alert_id: instructionAlertId || null,
      expiry_date: instructionExpiry ? new Date(instructionExpiry).toISOString() : null
    };
    
    try {
      if (editingInstructionId) {
        await updateInstruction(editingInstructionId, {
          message: payload.message,
          priority: payload.priority,
          patient_visible: payload.patient_visible,
          expiry_date: payload.expiry_date
        });
        setInstructionSuccess("Instruction updated successfully!");
      } else {
        await sendInstruction(payload);
        setInstructionSuccess("Instruction published successfully!");
      }
      
      // Refresh list
      const instRes = await listDoctorInstructions(selectedPatientId);
      setPatientInstructions(instRes.instructions || []);
      
      // Reset form
      setInstructionMessage('');
      setInstructionPriority('Normal');
      setInstructionExpiry('');
      setInstructionVisible(true);
      setInstructionAlertId(selectedAlert?.id || '');
      setEditingInstructionId(null);
      
      setTimeout(() => setInstructionSuccess(null), 3000);
    } catch (err) {
      setInstructionError(err.message || "Failed to publish instruction.");
    }
  };

  const handleEditInstruction = (inst) => {
    setEditingInstructionId(inst.id);
    setInstructionMessage(inst.message);
    setInstructionPriority(inst.priority);
    setInstructionVisible(inst.patient_visible !== false);
    setInstructionExpiry(inst.expiry_date ? new Date(inst.expiry_date).toISOString().substring(0, 16) : '');
    setInstructionAlertId(inst.alert_id || '');
    setInstructionSuccess(null);
    setInstructionError(null);
  };

  const handleWithdrawInstruction = async (instId) => {
    if (!window.confirm("Are you sure you want to withdraw this instruction? This will deactivate it for the patient.")) {
      return;
    }
    
    setInstructionError(null);
    setInstructionSuccess(null);
    
    try {
      await withdrawInstruction(instId);
      setInstructionSuccess("Instruction withdrawn successfully.");
      
      // Refresh list
      const instRes = await listDoctorInstructions(selectedPatientId);
      setPatientInstructions(instRes.instructions || []);
      
      setTimeout(() => setInstructionSuccess(null), 3000);
    } catch (err) {
      setInstructionError(err.message || "Failed to withdraw instruction.");
    }
  };

  // Filter lists based on search query
  const filteredAlerts = alerts.filter(a => 
    a.patient?.username?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.warning_signs?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredPatients = patients.filter(p => 
    p.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Rendering Helper Methods
  const getBiomarkerClass = (value, minVal, maxVal) => {
    if (value < minVal || value > maxVal) {
      return { border: '2px solid #ef4444', background: '#fef2f2', text: '#dc2626', label: '⚠️ Out of Range' };
    }
    return { border: '1px solid #e2e8f0', background: '#fff', text: '#0f172a', label: '✅ Normal' };
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', fontFamily: 'Inter, sans-serif' }}>
      
      {/* Upper Metrics Section */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        <div style={{ backgroundColor: '#fff', borderRadius: '16px', padding: '1.5rem', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)', borderLeft: '6px solid #ef4444' }}>
          <h4 style={{ margin: '0 0 0.5rem', color: '#64748b', fontSize: '0.9rem', fontWeight: 600 }}>Emergency Alerts</h4>
          <span style={{ fontSize: '2rem', fontWeight: 800, color: '#ef4444' }}>{metrics.emergency}</span>
        </div>
        <div style={{ backgroundColor: '#fff', borderRadius: '16px', padding: '1.5rem', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)', borderLeft: '6px solid #b91c1c' }}>
          <h4 style={{ margin: '0 0 0.5rem', color: '#64748b', fontSize: '0.9rem', fontWeight: 600 }}>High Risk Patients</h4>
          <span style={{ fontSize: '2rem', fontWeight: 800, color: '#b91c1c' }}>{metrics.high}</span>
        </div>
        <div style={{ backgroundColor: '#fff', borderRadius: '16px', padding: '1.5rem', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)', borderLeft: '6px solid #dc2626' }}>
          <h4 style={{ margin: '0 0 0.5rem', color: '#64748b', fontSize: '0.9rem', fontWeight: 600 }}>New Alerts</h4>
          <span style={{ fontSize: '2rem', fontWeight: 800, color: '#dc2626' }}>{metrics.new}</span>
        </div>
        <div style={{ backgroundColor: '#fff', borderRadius: '16px', padding: '1.5rem', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)', borderLeft: '6px solid #ea580c' }}>
          <h4 style={{ margin: '0 0 0.5rem', color: '#64748b', fontSize: '0.9rem', fontWeight: 600 }}>Under Review</h4>
          <span style={{ fontSize: '2rem', fontWeight: 800, color: '#ea580c' }}>{metrics.underReview}</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '2rem', alignItems: 'start' }}>
        
        {/* Left Side: Alert Queue and assigned patients list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Search bar */}
          <div style={{ backgroundColor: '#fff', borderRadius: '16px', padding: '1.5rem', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}>
            <h3 style={{ margin: '0 0 1rem', fontSize: '1.1rem', fontWeight: 700, color: '#1e293b' }}>Search assigned directory</h3>
            <input 
              type="text" 
              placeholder="🔍 Search patients by name or email..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '0.6rem 0.8rem',
                borderRadius: '8px',
                border: '1px solid #cbd5e1',
                outline: 'none',
                fontSize: '0.85rem'
              }}
            />
          </div>

          {/* Filters card */}
          <div style={{ backgroundColor: '#fff', borderRadius: '16px', padding: '1.5rem', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}>
            <h3 style={{ margin: '0 0 1rem', fontSize: '1.1rem', fontWeight: 700, color: '#1e293b' }}>Queue Filters</h3>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <select 
                value={statusFilter} 
                onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
                style={{ flex: 1, padding: '0.6rem 0.8rem', borderRadius: '8px', border: '1px solid #cbd5e1', outline: 'none', fontSize: '0.85rem' }}
              >
                <option value="">All Statuses</option>
                <option value="new">New Alerts</option>
                <option value="under_review">Under Review</option>
                <option value="escalated">Escalated</option>
                <option value="resolved">Resolved</option>
                <option value="dismissed_as_false_positive">Dismissed</option>
              </select>

              <select 
                value={riskFilter} 
                onChange={(e) => { setRiskFilter(e.target.value); setCurrentPage(1); }}
                style={{ flex: 1, padding: '0.6rem 0.8rem', borderRadius: '8px', border: '1px solid #cbd5e1', outline: 'none', fontSize: '0.85rem' }}
              >
                <option value="">All Risks</option>
                <option value="Emergency">Emergency</option>
                <option value="High">High</option>
                <option value="Moderate">Moderate</option>
                <option value="Low">Low</option>
              </select>
            </div>
          </div>

          {/* Prioritized Alert Queue */}
          <div style={{ backgroundColor: '#fff', borderRadius: '16px', padding: '1.5rem', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800, color: '#1e293b' }}>Alert Triage Queue</h3>
              <span style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Total: {totalAlerts}</span>
            </div>

            {loadingAlerts ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>Loading alert queue...</div>
            ) : filteredAlerts.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8', fontSize: '0.9rem' }}>No alerts matching filters.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {filteredAlerts.map((a) => {
                  const statusDecor = ALERT_STATUS_DECORATION[a.status] || {};
                  const riskDecor = RISK_LEVEL_DECORATION[a.risk_level] || {};
                  const isSelected = selectedAlert?.id === a.id;
                  
                  return (
                    <div 
                      key={a.id}
                      onClick={() => handleSelectPatient(a.patient.id, a)}
                      style={{
                        padding: '1rem',
                        borderRadius: '12px',
                        border: isSelected ? '2px solid #247576' : '1px solid #e2e8f0',
                        backgroundColor: isSelected ? '#f2f9f9' : '#fff',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                        <strong style={{ fontSize: '0.95rem', color: '#0f172a' }}>{a.patient?.username}</strong>
                        <span style={{ fontSize: '0.75rem', color: '#64748b' }}>{new Date(a.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                      </div>
                      
                      <p style={{ margin: '0 0 0.75rem', fontSize: '0.85rem', color: '#475569', fontWeight: 500 }}>
                        {a.warning_signs}
                      </p>

                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <span style={{ 
                          fontSize: '0.75rem', 
                          fontWeight: 700, 
                          padding: '0.2rem 0.5rem', 
                          borderRadius: '4px',
                          backgroundColor: riskDecor.bg,
                          color: riskDecor.color,
                          border: `1px solid ${riskDecor.border}`
                        }}>
                          {riskDecor.label}
                        </span>
                        <span style={{ 
                          fontSize: '0.75rem', 
                          fontWeight: 700, 
                          padding: '0.2rem 0.5rem', 
                          borderRadius: '4px',
                          backgroundColor: statusDecor.bg,
                          color: statusDecor.color,
                          border: `1px solid ${statusDecor.border}`
                        }}>
                          {statusDecor.icon} {statusDecor.label}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Assigned Patients Directory Section */}
          <div style={{ backgroundColor: '#fff', borderRadius: '16px', padding: '1.5rem', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}>
            <h3 style={{ margin: '0 0 1rem', fontSize: '1.2rem', fontWeight: 800, color: '#1e293b' }}>Assigned Patients</h3>
            {loadingPatients ? (
              <div style={{ textAlign: 'center', padding: '1rem', color: '#64748b' }}>Loading assigned directory...</div>
            ) : filteredPatients.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '1rem', color: '#94a3b8', fontSize: '0.85rem' }}>No patients found.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {filteredPatients.map(p => (
                  <div 
                    key={p.id}
                    onClick={() => handleSelectPatient(p.id)}
                    style={{
                      padding: '0.75rem 1rem',
                      borderRadius: '8px',
                      border: selectedPatientId === p.id ? '2px solid #247576' : '1px solid #e2e8f0',
                      backgroundColor: selectedPatientId === p.id ? '#f2f9f9' : '#fff',
                      cursor: 'pointer',
                      fontSize: '0.85rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                  >
                    <div>
                      <strong>{p.username}</strong>
                      <span style={{ display: 'block', fontSize: '0.75rem', color: '#64748b' }}>{p.email}</span>
                    </div>
                    {p.twin_summary?.overall_risk && (
                      <span style={{ 
                        fontSize: '0.75rem', 
                        fontWeight: 700, 
                        padding: '0.15rem 0.4rem', 
                        borderRadius: '4px',
                        backgroundColor: p.twin_summary.overall_risk === 'High' ? '#fef2f2' : '#f0fdf4',
                        color: p.twin_summary.overall_risk === 'High' ? '#dc2626' : '#16a34a'
                      }}>
                        {p.twin_summary.overall_risk} Risk
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>

        {/* Right Side: Patient Clinical Details */}
        <div style={{ backgroundColor: '#fff', borderRadius: '16px', padding: '2rem', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)', minHeight: '400px' }}>
          {!selectedPatientId ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '300px', color: '#94a3b8' }}>
              <span style={{ fontSize: '3rem', marginBottom: '1rem' }}>🩺</span>
              <h3>No Patient Selected</h3>
              <p style={{ fontSize: '0.9rem', textAlign: 'center', maxWidth: '300px' }}>
                Select an alert from the triage queue on the left to review maternal biomarkers, ML risk outputs, and write clinical notes.
              </p>
            </div>
          ) : loadingDetails ? (
            <div style={{ textAlign: 'center', padding: '5rem', color: '#64748b' }}>
              <div style={{ fontSize: '2.5rem', animation: 'spin 1s linear infinite', display: 'inline-block' }}>⟳</div>
              <p style={{ marginTop: '1rem' }}>Loading clinical files & vital trends...</p>
            </div>
          ) : (
            <div>
              {error && (
                <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fee2e2', color: '#dc2626', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.85rem' }}>
                  ❌ {error}
                </div>
              )}
              {/* Patient header */}
              <div style={{ borderBottom: '1px solid #f1f5f9', paddingBottom: '1.25rem', marginBottom: '1.5rem' }}>
                <h2 style={{ margin: '0 0 0.5rem', color: '#0f172a', fontWeight: 800 }}>
                  {selectedPatientTrends?.trends?.[0]?.username || 'Maternal Profile'}
                </h2>
                <div style={{ display: 'flex', gap: '1rem', fontSize: '0.85rem', color: '#64748b' }}>
                  <span><strong>ID:</strong> {selectedPatientId.substring(0, 8)}...</span>
                  {selectedPatientTwin && (
                    <span><strong>Gestational Week:</strong> Week {selectedPatientTwin.current_week}</span>
                  )}
                </div>
              </div>

              {/* Deterministic emergency section */}
              {selectedAlert?.alert_source === 'deterministic' && (
                <div style={{ 
                  backgroundColor: '#fef2f2', 
                  border: '1px solid #fee2e2', 
                  borderRadius: '12px', 
                  padding: '1.25rem', 
                  marginBottom: '1.5rem',
                }}>
                  <h4 style={{ margin: '0 0 0.5rem', color: '#991b1b', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    🚨 Critical Emergency Red Flags (Deterministic Screening)
                  </h4>
                  <p style={{ margin: 0, fontSize: '0.9rem', color: '#b91c1c', fontWeight: 600 }}>
                    Warning signs: {selectedAlert.warning_signs}
                  </p>
                  <p style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: '#7f1d1d' }}>
                    *This was identified deterministically via raw symptom analysis. Original triage override requires clinical validation.
                  </p>
                </div>
              )}

              {/* Vitals biomarkers */}
              {selectedPatientTwin && (
                <div style={{ marginBottom: '2rem' }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 800, color: '#1e293b', marginBottom: '1rem' }}>Live Biomarker Twin State</h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem' }}>
                    
                    {/* Systolic BP */}
                    {(() => {
                      const dec = getBiomarkerClass(selectedPatientTwin.systolic_bp, 90, 139);
                      return (
                        <div style={{ padding: '0.75rem', borderRadius: '8px', border: dec.border, backgroundColor: dec.background }}>
                          <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block', fontWeight: 600 }}>Systolic BP</span>
                          <span style={{ fontSize: '1.2rem', fontWeight: 800, color: '#0f172a' }}>{selectedPatientTwin.systolic_bp} <span style={{ fontSize: '0.7rem' }}>mmHg</span></span>
                        </div>
                      );
                    })()}

                    {/* Diastolic BP */}
                    {(() => {
                      const dec = getBiomarkerClass(selectedPatientTwin.diastolic_bp, 60, 89);
                      return (
                        <div style={{ padding: '0.75rem', borderRadius: '8px', border: dec.border, backgroundColor: dec.background }}>
                          <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block', fontWeight: 600 }}>Diastolic BP</span>
                          <span style={{ fontSize: '1.2rem', fontWeight: 800, color: '#0f172a' }}>{selectedPatientTwin.diastolic_bp} <span style={{ fontSize: '0.7rem' }}>mmHg</span></span>
                        </div>
                      );
                    })()}

                    {/* Glucose */}
                    {(() => {
                      const dec = getBiomarkerClass(selectedPatientTwin.glucose_level, 70, 139);
                      return (
                        <div style={{ padding: '0.75rem', borderRadius: '8px', border: dec.border, backgroundColor: dec.background }}>
                          <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block', fontWeight: 600 }}>Fasting Glucose</span>
                          <span style={{ fontSize: '1.2rem', fontWeight: 800, color: '#0f172a' }}>{selectedPatientTwin.glucose_level} <span style={{ fontSize: '0.7rem' }}>mg/dL</span></span>
                        </div>
                      );
                    })()}

                    {/* Hemoglobin */}
                    {(() => {
                      const dec = getBiomarkerClass(selectedPatientTwin.hemoglobin, 11, 15);
                      return (
                        <div style={{ padding: '0.75rem', borderRadius: '8px', border: dec.border, backgroundColor: dec.background }}>
                          <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block', fontWeight: 600 }}>Hemoglobin</span>
                          <span style={{ fontSize: '1.2rem', fontWeight: 800, color: '#0f172a' }}>{selectedPatientTwin.hemoglobin} <span style={{ fontSize: '0.7rem' }}>g/dL</span></span>
                        </div>
                      );
                    })()}
                  </div>
                </div>
              )}

              {/* Machine learning models details */}
              {selectedPatientTwin && (
                <div style={{ backgroundColor: '#f8fafc', borderRadius: '12px', padding: '1.25rem', marginBottom: '2rem', border: '1px solid #e2e8f0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <h4 style={{ margin: 0, fontWeight: 800, color: '#334155', fontSize: '0.9rem' }}>🔮 ML Diagnostic Risk Engine</h4>
                    <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>Version: v1.0.0-rf</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.85rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Pre-eclampsia Probability:</span>
                      <strong style={{ color: selectedPatientTwin.risk_preeclampsia >= 0.7 ? '#ef4444' : '#0f172a' }}>
                        {parseInt(selectedPatientTwin.risk_preeclampsia * 100)}%
                      </strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Gestational Diabetes Probability:</span>
                      <strong style={{ color: selectedPatientTwin.risk_gestational_diabetes >= 0.7 ? '#ef4444' : '#0f172a' }}>
                        {parseInt(selectedPatientTwin.risk_gestational_diabetes * 100)}%
                      </strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Anaemia Probability:</span>
                      <strong style={{ color: selectedPatientTwin.risk_anemia >= 0.7 ? '#ef4444' : '#0f172a' }}>
                        {parseInt(selectedPatientTwin.risk_anemia * 100)}%
                      </strong>
                    </div>
                  </div>
                </div>
              )}

              {/* Clinical notes and actions workflow */}
              {selectedAlert && (
                <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '1.5rem', marginBottom: '2rem' }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 800, color: '#1e293b', marginBottom: '1rem' }}>Clinical Workflow Review</h3>
                  
                  {/* Show Current status details */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', fontSize: '0.85rem' }}>
                    <span><strong>Current Status:</strong></span>
                    <span style={{ 
                      fontWeight: 700, 
                      padding: '0.2rem 0.6rem', 
                      borderRadius: '4px',
                      backgroundColor: (ALERT_STATUS_DECORATION[selectedAlert.status] || {}).bg,
                      color: (ALERT_STATUS_DECORATION[selectedAlert.status] || {}).color,
                    }}>
                      {selectedAlert.status.toUpperCase()}
                    </span>
                  </div>

                  {selectedAlert.status === 'new' && (
                    <button 
                      onClick={() => triggerStartReview(selectedAlert.id)}
                      style={{
                        width: '100%',
                        padding: '0.8rem',
                        backgroundColor: '#247576',
                        color: '#fff',
                        border: 'none',
                        borderRadius: '8px',
                        fontWeight: 700,
                        cursor: 'pointer',
                        marginBottom: '1rem'
                      }}
                    >
                      🩺 Start Review / Lock Case
                    </button>
                  )}

                  {(selectedAlert.status === 'new' || selectedAlert.status === 'under_review' || selectedAlert.status === 'escalated') && (
                    <div>
                      {/* Doctor Notes Form */}
                      <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#475569', marginBottom: '0.4rem' }}>
                        Clinical Notes
                      </label>
                      <textarea
                        value={noteText}
                        onChange={(e) => setNoteText(e.target.value)}
                        placeholder="Write triage review summary, medical guidelines, or notes for the clinical coordinator..."
                        rows={3}
                        style={{
                          width: '100%',
                          padding: '0.75rem',
                          borderRadius: '8px',
                          border: '1px solid #cbd5e1',
                          outline: 'none',
                          fontSize: '0.85rem',
                          fontFamily: 'inherit',
                          marginBottom: '0.75rem'
                        }}
                      />
                      <button 
                        onClick={triggerAddNotes}
                        disabled={!noteText.trim()}
                        style={{
                          padding: '0.5rem 1rem',
                          backgroundColor: '#f1f5f9',
                          border: '1px solid #cbd5e1',
                          borderRadius: '6px',
                          color: '#475569',
                          fontWeight: 700,
                          cursor: 'pointer',
                          fontSize: '0.8rem',
                          marginBottom: '1.5rem'
                        }}
                      >
                        💾 Save Clinical Notes
                      </button>

                      {/* Clinical Override UI Section */}
                      <div style={{ marginBottom: '1.25rem', border: '1px dashed #cbd5e1', padding: '0.75rem', borderRadius: '8px', backgroundColor: '#f8fafc' }}>
                        {!showOverrideForm ? (
                          <button
                            onClick={() => setShowOverrideForm(true)}
                            style={{ width: '100%', padding: '0.5rem', backgroundColor: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: '6px', color: '#0f766e', fontWeight: 700, fontSize: '0.8rem', cursor: 'pointer' }}
                          >
                            ⚖️ Override AI Risk Assessment
                          </button>
                        ) : (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#1e293b' }}>New Override Risk Level:</span>
                              <select 
                                value={overrideRiskLvl}
                                onChange={(e) => setOverrideRiskLvl(e.target.value)}
                                style={{ padding: '0.25rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.8rem' }}
                              >
                                <option value="Low">Low (Home Care) 🟢</option>
                                <option value="Moderate">Moderate (Routine) 🟡</option>
                                <option value="High">High (Urgent) 🟠</option>
                                <option value="Emergency">Emergency 🔴</option>
                              </select>
                            </div>
                            <textarea
                              value={overrideReason}
                              onChange={(e) => setOverrideReason(e.target.value)}
                              placeholder="Reason for overriding AI risk level..."
                              rows={2}
                              style={{ width: '100%', padding: '0.4rem', border: '1px solid #cbd5e1', borderRadius: '4px', fontSize: '0.8rem', resize: 'none' }}
                            />
                            <div style={{ display: 'flex', gap: '0.35rem', justifyContent: 'flex-end' }}>
                              <button onClick={handleApplyOverride} style={{ padding: '0.3rem 0.75rem', backgroundColor: '#0d9488', color: '#fff', border: 'none', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer' }}>
                                Confirm Override
                              </button>
                              <button onClick={() => setShowOverrideForm(false)} style={{ padding: '0.3rem 0.75rem', backgroundColor: '#94a3b8', color: '#fff', border: 'none', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer' }}>
                                Cancel
                              </button>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Action buttons */}
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button 
                          onClick={() => setShowReasonModal('escalate')}
                          style={{ flex: 1, padding: '0.6rem', border: '1px solid #d8b4fe', color: '#7c3aed', backgroundColor: '#f5f3ff', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer' }}
                        >
                          ⚠️ Escalate Alert
                        </button>
                        <button 
                          onClick={() => setShowReasonModal('resolve')}
                          style={{ flex: 1, padding: '0.6rem', border: '1px solid #86efac', color: '#16a34a', backgroundColor: '#f0fdf4', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer' }}
                        >
                          ✅ Resolve Case
                        </button>
                        <button 
                          onClick={() => setShowReasonModal('dismiss')}
                          style={{ flex: 1, padding: '0.6rem', border: '1px solid #cbd5e1', color: '#64748b', backgroundColor: '#f8fafc', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer' }}
                        >
                          🔇 Dismiss Alert
                        </button>
                      </div>
                    </div>
                  )}

                  {selectedAlert.resolution_reason && (
                    <div style={{ marginTop: '1rem', padding: '0.75rem', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '0.85rem' }}>
                      <strong>Resolution/Dismissal Reason:</strong> {selectedAlert.resolution_reason}
                    </div>
                  )}
                </div>
              )}

              {/* Doctor-Patient Secure Care Instructions Section */}
              <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '1.5rem', marginTop: '1.5rem', marginBottom: '2rem' }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#1e293b', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span>📢</span> Secure Patient Care Guidelines
                </h3>

                {/* Create/Edit Instruction Form */}
                <form onSubmit={handlePublishInstruction} style={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '1.25rem', marginBottom: '1.5rem' }}>
                  <h4 style={{ margin: '0 0 0.75rem', color: '#334155', fontWeight: 700 }}>
                    {editingInstructionId ? "✏️ Edit Patient Guideline" : "➕ Publish New Guideline"}
                  </h4>
                  
                  {instructionSuccess && (
                    <div style={{ color: '#16a34a', backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', padding: '0.5rem 0.75rem', borderRadius: '6px', fontSize: '0.8rem', marginBottom: '0.75rem', fontWeight: 600 }}>
                      ✓ {instructionSuccess}
                    </div>
                  )}
                  {instructionError && (
                    <div style={{ color: '#dc2626', backgroundColor: '#fef2f2', border: '1px solid #fecaca', padding: '0.5rem 0.75rem', borderRadius: '6px', fontSize: '0.8rem', marginBottom: '0.75rem', fontWeight: 600 }}>
                      ❌ {instructionError}
                    </div>
                  )}

                  <div style={{ marginBottom: '0.75rem' }}>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>
                      Care Instruction Message *
                    </label>
                    <textarea
                      value={instructionMessage}
                      onChange={(e) => setInstructionMessage(e.target.value)}
                      placeholder="Enter specific clinical guidance, medication instructions, or follow-up directions..."
                      rows={3}
                      required
                      style={{ width: '100%', padding: '0.5rem 0.75rem', border: '1px solid #cbd5e1', borderRadius: '6px', fontSize: '0.85rem', outline: 'none', fontFamily: 'inherit' }}
                    />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '0.75rem' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>
                        Priority
                      </label>
                      <select
                        value={instructionPriority}
                        onChange={(e) => setInstructionPriority(e.target.value)}
                        style={{ width: '100%', padding: '0.4rem 0.6rem', border: '1px solid #cbd5e1', borderRadius: '6px', fontSize: '0.85rem' }}
                      >
                        <option value="Normal">Normal</option>
                        <option value="High">High</option>
                      </select>
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>
                        Expiry Date (Optional)
                      </label>
                      <input
                        type="datetime-local"
                        value={instructionExpiry}
                        onChange={(e) => setInstructionExpiry(e.target.value)}
                        style={{ width: '100%', padding: '0.4rem 0.6rem', border: '1px solid #cbd5e1', borderRadius: '6px', fontSize: '0.85rem' }}
                      />
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>
                        Patient Visible
                      </label>
                      <select
                        value={instructionVisible ? "yes" : "no"}
                        onChange={(e) => setInstructionVisible(e.target.value === "yes")}
                        style={{ width: '100%', padding: '0.4rem 0.6rem', border: '1px solid #cbd5e1', borderRadius: '6px', fontSize: '0.85rem' }}
                      >
                        <option value="yes">Yes (Visible to Patient)</option>
                        <option value="no">No (Internal Medical Note)</option>
                      </select>
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>
                        Link to Maternal Alert
                      </label>
                      <select
                        value={instructionAlertId}
                        onChange={(e) => setInstructionAlertId(e.target.value)}
                        style={{ width: '100%', padding: '0.4rem 0.6rem', border: '1px solid #cbd5e1', borderRadius: '6px', fontSize: '0.85rem' }}
                      >
                        <option value="">None (General Guideline)</option>
                        {selectedAlert && (
                          <option value={selectedAlert.id}>
                            Current Alert ({selectedAlert.risk_level} - {selectedAlert.warning_signs.substring(0, 20)}...)
                          </option>
                        )}
                        {selectedPatientTrends?.alert_timeline?.filter(a => a.id !== selectedAlert?.id).map(a => (
                          <option key={a.id} value={a.id}>
                            Alert ({a.risk_level} - {new Date(a.created_at).toLocaleDateString()})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                    {editingInstructionId && (
                      <button
                        type="button"
                        onClick={() => {
                          setEditingInstructionId(null);
                          setInstructionMessage('');
                          setInstructionPriority('Normal');
                          setInstructionExpiry('');
                          setInstructionVisible(true);
                          setInstructionAlertId(selectedAlert?.id || '');
                        }}
                        style={{ padding: '0.4rem 1rem', border: '1px solid #cbd5e1', backgroundColor: '#fff', borderRadius: '6px', color: '#475569', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600 }}
                      >
                        Cancel
                      </button>
                    )}
                    <button
                      type="submit"
                      style={{ padding: '0.4rem 1.25rem', border: 'none', backgroundColor: '#247576', color: '#fff', borderRadius: '6px', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 700 }}
                    >
                      {editingInstructionId ? "💾 Save Changes" : "📤 Publish Guideline"}
                    </button>
                  </div>
                </form>

                {/* Published Instructions History */}
                <h4 style={{ margin: '1.5rem 0 0.75rem', color: '#475569', fontWeight: 700, fontSize: '0.9rem' }}>
                  📜 Guideline History ({patientInstructions.length})
                </h4>

                {loadingInstructions ? (
                  <div style={{ textAlign: 'center', padding: '1rem', color: '#94a3b8', fontSize: '0.85rem' }}>Loading instruction history...</div>
                ) : patientInstructions.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '1.5rem', border: '1px dashed #cbd5e1', borderRadius: '8px', color: '#94a3b8', fontSize: '0.85rem' }}>
                    No care guidelines published for this patient yet.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {patientInstructions.map((inst) => {
                      const isHigh = inst.priority === 'High';
                      const isWithdrawn = inst.status === 'withdrawn';
                      const isRead = !!inst.read_at;
                      
                      return (
                        <div key={inst.id} style={{
                          padding: '0.85rem',
                          borderRadius: '8px',
                          border: isWithdrawn ? '1px dashed #cbd5e1' : (isHigh ? '1px solid #fca5a5' : '1px solid #e2e8f0'),
                          backgroundColor: isWithdrawn ? '#f8fafc' : (isHigh ? '#fff5f5' : '#fff'),
                          opacity: isWithdrawn ? 0.6 : 1,
                          fontSize: '0.85rem'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', flexWrap: 'wrap', gap: '0.4rem' }}>
                            <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                              <span style={{
                                fontSize: '0.7rem',
                                fontWeight: 700,
                                padding: '0.15rem 0.4rem',
                                borderRadius: '4px',
                                backgroundColor: isHigh ? '#dc2626' : '#1e293b',
                                color: '#fff'
                              }}>
                                {inst.priority}
                              </span>
                              <span style={{
                                fontSize: '0.7rem',
                                fontWeight: 700,
                                padding: '0.1rem 0.3rem',
                                borderRadius: '4px',
                                backgroundColor: inst.patient_visible ? '#dcfce7' : '#f1f5f9',
                                color: inst.patient_visible ? '#166534' : '#475569'
                              }}>
                                {inst.patient_visible ? "Patient-Facing" : "Internal Notes"}
                              </span>
                              {isWithdrawn && (
                                <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '0.1rem 0.3rem', borderRadius: '4px', backgroundColor: '#f3f4f6', color: '#1f2937' }}>
                                  WITHDRAWN
                                </span>
                              )}
                            </div>
                            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                              {new Date(inst.created_at).toLocaleString()}
                            </span>
                          </div>

                          <p style={{ margin: '0 0 0.5rem', color: '#1e293b', lineHeight: 1.4 }}>
                            {inst.message}
                          </p>

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.78rem' }}>
                            <div>
                              {inst.expiry_date && (
                                <span style={{ color: '#64748b' }}>
                                  ⌛ Expires: {new Date(inst.expiry_date).toLocaleDateString()}
                                </span>
                              )}
                              {inst.patient_visible && (
                                <span style={{ marginLeft: inst.expiry_date ? 12 : 0, color: isRead ? '#16a34a' : '#ea580c', fontWeight: 600 }}>
                                  {isRead ? `✓ Read at ${new Date(inst.read_at).toLocaleDateString()}` : "⏳ Unread by patient"}
                                </span>
                              )}
                            </div>
                            
                            {!isWithdrawn && (
                              <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <button
                                  onClick={() => handleEditInstruction(inst)}
                                  style={{ border: 'none', background: 'none', color: '#247576', cursor: 'pointer', fontWeight: 700 }}
                                >
                                  ✏️ Edit
                                </button>
                                <button
                                  onClick={() => handleWithdrawInstruction(inst.id)}
                                  style={{ border: 'none', background: 'none', color: '#dc2626', cursor: 'pointer', fontWeight: 700 }}
                                >
                                  🚫 Withdraw
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Patient trends timeline */}
              {selectedPatientTrends && selectedPatientTrends.trends && (
                <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '1.5rem' }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 800, color: '#1e293b', marginBottom: '1rem' }}>Maternal Screening History</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {selectedPatientTrends.trends.map((t, idx) => (
                      <div key={idx} style={{ padding: '0.75rem', borderRadius: '8px', border: '1px solid #f1f5f9', backgroundColor: '#fafafb', fontSize: '0.8rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', marginBottom: '0.25rem' }}>
                          <span>{new Date(t.timestamp).toLocaleDateString()}</span>
                          <strong>{t.urgency}</strong>
                        </div>
                        <p style={{ margin: 0, color: '#334155' }}><strong>Symptom:</strong> {t.symptoms}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </div>
          )}
        </div>
      </div>

      {/* Mandatory Reason Modal Overlay */}
      {showReasonModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.6)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div style={{ backgroundColor: '#fff', padding: '2rem', borderRadius: '16px', width: '90%', maxWidth: '400px', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)' }}>
            <h3 style={{ margin: '0 0 1rem', color: '#1e293b' }}>
              {showReasonModal === 'resolve' ? 'Resolve Alert' : showReasonModal === 'escalate' ? 'Escalate Alert' : 'Dismiss Alert'}
            </h3>
            
            <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '1rem' }}>
              {showReasonModal === 'escalate' 
                ? 'State the reason/details for escalating this patient case.'
                : 'A formal reason is mandatory to change this maternal safety alert status.'}
            </p>

            <textarea
              value={actionReason}
              onChange={(e) => setActionReason(e.target.value)}
              placeholder="Provide clinical details or review reason..."
              rows={3}
              style={{
                width: '100%',
                padding: '0.75rem',
                borderRadius: '8px',
                border: '1px solid #cbd5e1',
                outline: 'none',
                fontSize: '0.85rem',
                fontFamily: 'inherit',
                marginBottom: '1rem'
              }}
            />

            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
              <button 
                onClick={() => setShowReasonModal(null)}
                style={{ padding: '0.5rem 1rem', border: '1px solid #cbd5e1', backgroundColor: '#fff', borderRadius: '6px', color: '#475569', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600 }}
              >
                Cancel
              </button>
              
              <button 
                onClick={
                  showReasonModal === 'resolve' 
                    ? triggerResolve 
                    : showReasonModal === 'escalate' 
                      ? triggerEscalate 
                      : triggerDismiss
                }
                disabled={showReasonModal !== 'escalate' && !actionReason.trim()}
                style={{
                  padding: '0.5rem 1rem',
                  border: 'none',
                  backgroundColor: '#247576',
                  color: '#fff',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  opacity: (showReasonModal !== 'escalate' && !actionReason.trim()) ? 0.6 : 1
                }}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default DoctorDashboard;
