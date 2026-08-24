import React, { useCallback, useEffect, useState } from 'react';
import {
  listAppointments,
  requestAppointment,
  updateAppointmentStatus,
  getPatients,
  getAdminUsers
} from '../services/api';

const STATUS_COLORS = {
  requested:   { bg: '#fef3c7', color: '#92400e' },
  confirmed:   { bg: '#d1fae5', color: '#065f46' },
  rescheduled: { bg: '#dbeafe', color: '#1e40af' },
  completed:   { bg: '#f3f4f6', color: '#374151' },
  cancelled:   { bg: '#fee2e2', color: '#991b1b' },
  no_show:     { bg: '#fce7f3', color: '#831843' },
};

const APPOINTMENT_TYPES = ['checkup', 'emergency', 'follow_up', 'scan', 'consultation', 'other'];

export default function AppointmentsPage({ role = 'patient', doctorId = null }) {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [filterStatus, setFilterStatus] = useState('');
  const [actionLoading, setActionLoading] = useState(null);
  const [usersMap, setUsersMap] = useState({});

  // Form states for requested appointments
  const [form, setForm] = useState({
    doctor_id: doctorId || '',
    appointment_datetime: '',
    appointment_type: 'checkup',
    reason: '',
  });

  // Action states for doctors
  const [activeActionId, setActiveActionId] = useState(null); // ID of appointment currently being edited
  const [actionType, setActionType] = useState(''); // reschedule | complete | cancel | no_show
  const [actionFields, setActionFields] = useState({
    reason: '',
    doctor_notes: '',
    patient_instructions: '',
    new_datetime: ''
  });

  useEffect(() => {
    // Resolve user IDs to readable usernames
    if (role === 'doctor') {
      getPatients().then(res => {
        const mapping = {};
        (res.patients || []).forEach(p => {
          mapping[p.id] = p.username;
        });
        setUsersMap(mapping);
      }).catch(() => {});
    } else if (role === 'admin') {
      getAdminUsers().then(res => {
        const mapping = {};
        (res.users || []).forEach(u => {
          mapping[u.id] = `${u.username} (${u.role})`;
        });
        setUsersMap(mapping);
      }).catch(() => {});
    }
  }, [role]);

  const fetchAppointments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listAppointments(null, filterStatus || null);
      setAppointments(res.appointments || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  useEffect(() => {
    fetchAppointments();
  }, [fetchAppointments]);

  async function handleRequestAppointment(e) {
    e.preventDefault();
    setActionLoading('form');
    try {
      await requestAppointment({
        ...form,
        appointment_datetime: new Date(form.appointment_datetime).toISOString(),
      });
      setShowForm(false);
      setForm({ doctor_id: doctorId || '', appointment_datetime: '', appointment_type: 'checkup', reason: '' });
      await fetchAppointments();
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setActionLoading(null);
    }
  }

  // Handle clinical appointment actions
  async function handleUpdateStatus(apptId, newStatus) {
    setActionLoading(apptId);
    try {
      const payload = { new_status: newStatus };
      if (newStatus === 'cancelled' || newStatus === 'no_show') {
        if (!actionFields.reason) {
          alert('A reason is required.');
          setActionLoading(null);
          return;
        }
        payload.reason = actionFields.reason;
      } else if (newStatus === 'rescheduled') {
        if (!actionFields.new_datetime || !actionFields.reason) {
          alert('New Date/Time and Reason are required.');
          setActionLoading(null);
          return;
        }
        payload.new_datetime = new Date(actionFields.new_datetime).toISOString();
        payload.reason = actionFields.reason;
      } else if (newStatus === 'completed') {
        payload.doctor_notes = actionFields.doctor_notes;
        payload.patient_instructions = actionFields.patient_instructions;
      }

      await updateAppointmentStatus(apptId, payload);
      setActiveActionId(null);
      setActionType('');
      setActionFields({ reason: '', doctor_notes: '', patient_instructions: '', new_datetime: '' });
      await fetchAppointments();
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setActionLoading(null);
    }
  }

  async function handlePatientCancel(apptId) {
    const reason = window.prompt('Please provide a cancellation reason:');
    if (!reason) return;
    setActionLoading(apptId);
    try {
      await updateAppointmentStatus(apptId, { new_status: 'cancelled', reason });
      await fetchAppointments();
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setActionLoading(null);
    }
  }

  const card = {
    background: '#fff',
    borderRadius: '12px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.07)',
    padding: '1.25rem',
    marginBottom: '0.75rem',
    border: '1px solid #e2e8f0',
  };

  const actionButtonStyle = {
    padding: '0.35rem 0.75rem',
    borderRadius: '6px',
    fontSize: '0.78rem',
    fontWeight: 600,
    cursor: 'pointer',
    border: 'none',
  };

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ margin: 0, color: '#1e293b', fontSize: '1.5rem', fontWeight: 700 }}>📅 Appointments</h2>
          <p style={{ margin: '0.25rem 0 0', color: '#64748b', fontSize: '0.9rem' }}>
            {role === 'patient' ? 'Your scheduled appointments' : 'Manage patient appointment requests'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            style={{ padding: '0.45rem 0.75rem', borderRadius: '8px', border: '1px solid #d1d5db', fontSize: '0.85rem', color: '#374151' }}
          >
            <option value="">All statuses</option>
            {Object.keys(STATUS_COLORS).map(s => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
          {role === 'patient' && (
            <button
              onClick={() => setShowForm(f => !f)}
              style={{
                padding: '0.5rem 1.1rem',
                background: showForm ? '#e2e8f0' : 'linear-gradient(135deg, #247576, #1b5a5b)',
                color: showForm ? '#374151' : '#fff',
                border: 'none',
                borderRadius: '8px',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: '0.85rem',
              }}
            >
              {showForm ? '✕ Cancel' : '+ Request Appointment'}
            </button>
          )}
        </div>
      </div>

      {/* Request Form */}
      {showForm && role === 'patient' && (
        <div style={{ ...card, border: '2px solid #247576', marginBottom: '1.5rem' }}>
          <h3 style={{ margin: '0 0 1rem', color: '#247576', fontSize: '1rem' }}>New Appointment Request</h3>
          <form onSubmit={handleRequestAppointment}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '0.25rem' }}>
                  Doctor ID *
                </label>
                <input
                  type="text"
                  value={form.doctor_id}
                  onChange={e => setForm(f => ({ ...f, doctor_id: e.target.value }))}
                  required
                  placeholder="Enter your doctor's ID"
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #d1d5db', fontSize: '0.9rem', boxSizing: 'border-box' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '0.25rem' }}>
                  Date & Time *
                </label>
                <input
                  type="datetime-local"
                  value={form.appointment_datetime}
                  onChange={e => setForm(f => ({ ...f, appointment_datetime: e.target.value }))}
                  required
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #d1d5db', fontSize: '0.9rem', boxSizing: 'border-box' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '0.25rem' }}>
                  Appointment Type *
                </label>
                <select
                  value={form.appointment_type}
                  onChange={e => setForm(f => ({ ...f, appointment_type: e.target.value }))}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #d1d5db', fontSize: '0.9rem', boxSizing: 'border-box' }}
                >
                  {APPOINTMENT_TYPES.map(t => (
                    <option key={t} value={t}>{t.replace('_', ' ').toUpperCase()}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151', display: 'block', marginBottom: '0.25rem' }}>
                  Reason *
                </label>
                <input
                  type="text"
                  value={form.reason}
                  onChange={e => setForm(f => ({ ...f, reason: e.target.value }))}
                  required
                  minLength={3}
                  placeholder="Brief reason for appointment"
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', border: '1px solid #d1d5db', fontSize: '0.9rem', boxSizing: 'border-box' }}
                />
              </div>
            </div>
            <div style={{ marginTop: '1rem' }}>
              <button
                type="submit"
                disabled={actionLoading === 'form'}
                style={{
                  padding: '0.55rem 1.5rem',
                  background: 'linear-gradient(135deg, #247576, #1b5a5b)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '8px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  opacity: actionLoading === 'form' ? 0.7 : 1,
                }}
              >
                {actionLoading === 'form' ? 'Sending…' : 'Submit Request'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Appointments List */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
          Loading appointments…
        </div>
      )}
      {error && (
        <div style={{ ...card, backgroundColor: '#fee2e2', border: '1px solid #fca5a5', color: '#991b1b' }}>
          ⚠ {error}
        </div>
      )}
      {!loading && !error && appointments.length === 0 && (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>📅</div>
          <p style={{ margin: 0, fontWeight: 500 }}>No appointments found</p>
          {role === 'patient' && (
            <p style={{ margin: '0.5rem 0 0', fontSize: '0.85rem' }}>
              Click "Request Appointment" to schedule one with your doctor.
            </p>
          )}
        </div>
      )}

      {appointments.map(appt => {
        const statusDec = STATUS_COLORS[appt.status] || { bg: '#f3f4f6', color: '#374151' };
        const dt = new Date(appt.appointment_datetime);
        const isPast = dt < new Date();
        const isClinician = role === 'doctor' || role === 'admin';
        const clientName = usersMap[appt.patient_id] || appt.patient_id;

        return (
          <div key={appt.id} style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div style={{ flex: 1, minWidth: '280px' }}>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.25rem', flexWrap: 'wrap' }}>
                  <span style={{
                    fontSize: '0.75rem', fontWeight: 700,
                    padding: '0.15rem 0.5rem', borderRadius: '4px',
                    backgroundColor: statusDec.bg, color: statusDec.color,
                  }}>
                    {appt.status.toUpperCase()}
                  </span>
                  <span style={{
                    fontSize: '0.75rem', fontWeight: 600,
                    padding: '0.15rem 0.5rem', borderRadius: '4px',
                    backgroundColor: '#e0f2fe', color: '#0369a1',
                  }}>
                    {appt.appointment_type.replace('_', ' ').toUpperCase()}
                  </span>
                  {isPast && appt.status === 'confirmed' && (
                    <span style={{ fontSize: '0.7rem', color: '#dc2626', fontWeight: 600 }}>⚠ Past date</span>
                  )}
                </div>

                {isClinician && (
                  <div style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: '0.2rem' }}>
                    Patient: <strong>{clientName}</strong>
                  </div>
                )}

                <div style={{ fontSize: '1rem', fontWeight: 700, color: '#1e293b' }}>
                  {dt.toLocaleDateString('en-GB', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                </div>
                <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                  🕐 {dt.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                </div>
                {appt.reason && (
                  <div style={{ fontSize: '0.85rem', color: '#475569', marginTop: '0.25rem' }}>
                    <strong>Reason:</strong> {appt.reason}
                  </div>
                )}

                {/* Show clinical notes to doctor or admin */}
                {isClinician && appt.doctor_notes && (
                  <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.25rem', fontStyle: 'italic' }}>
                    <strong>Doctor Notes (Internal):</strong> {appt.doctor_notes}
                  </div>
                )}

                {appt.patient_instructions && (
                  <div style={{
                    marginTop: '0.5rem', padding: '0.5rem 0.75rem',
                    backgroundColor: '#f0fdf4', borderRadius: '6px',
                    fontSize: '0.85rem', color: '#166534', borderLeft: '3px solid #4ade80',
                  }}>
                    📋 <strong>Instructions:</strong> {appt.patient_instructions}
                  </div>
                )}

                {appt.cancellation_reason && (
                  <div style={{ fontSize: '0.8rem', color: '#b91c1c', marginTop: '0.25rem' }}>
                    <strong>Cancellation Reason:</strong> {appt.cancellation_reason}
                  </div>
                )}
                {appt.reschedule_reason && (
                  <div style={{ fontSize: '0.8rem', color: '#1e3a8a', marginTop: '0.25rem' }}>
                    <strong>Reschedule Reason:</strong> {appt.reschedule_reason}
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'flex-start', justifyContent: 'flex-end' }}>
                {role === 'patient' && appt.status === 'requested' && (
                  <button
                    onClick={() => handlePatientCancel(appt.id)}
                    disabled={actionLoading === appt.id}
                    style={{
                      ...actionButtonStyle,
                      backgroundColor: '#fee2e2',
                      color: '#991b1b',
                      border: '1px solid #fca5a5',
                    }}
                  >
                    {actionLoading === appt.id ? '…' : 'Cancel Request'}
                  </button>
                )}

                {isClinician && activeActionId !== appt.id && (
                  <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                    {(appt.status === 'requested') && (
                      <button
                        onClick={() => handleUpdateStatus(appt.id, 'confirmed')}
                        disabled={actionLoading === appt.id}
                        style={{ ...actionButtonStyle, backgroundColor: '#d1fae5', color: '#065f46' }}
                      >
                        ✓ Confirm
                      </button>
                    )}
                    {(appt.status === 'confirmed' || appt.status === 'rescheduled') && (
                      <button
                        onClick={() => { setActiveActionId(appt.id); setActionType('complete'); }}
                        style={{ ...actionButtonStyle, backgroundColor: '#e0f2fe', color: '#0369a1' }}
                      >
                        🩺 Complete
                      </button>
                    )}
                    {(appt.status === 'requested' || appt.status === 'confirmed') && (
                      <button
                        onClick={() => { setActiveActionId(appt.id); setActionType('reschedule'); }}
                        style={{ ...actionButtonStyle, backgroundColor: '#fef3c7', color: '#92400e' }}
                      >
                        🔄 Reschedule
                      </button>
                    )}
                    {(appt.status === 'confirmed') && (
                      <button
                        onClick={() => { setActiveActionId(appt.id); setActionType('no_show'); }}
                        style={{ ...actionButtonStyle, backgroundColor: '#fce7f3', color: '#831843' }}
                      >
                        No Show
                      </button>
                    )}
                    {(appt.status === 'requested' || appt.status === 'confirmed' || appt.status === 'rescheduled') && (
                      <button
                        onClick={() => { setActiveActionId(appt.id); setActionType('cancel'); }}
                        style={{ ...actionButtonStyle, backgroundColor: '#fee2e2', color: '#991b1b' }}
                      >
                        ✕ Cancel
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Action Form Inputs under selected appointment */}
            {isClinician && activeActionId === appt.id && (
              <div style={{
                marginTop: '1rem', padding: '1rem', borderTop: '1px solid #e2e8f0',
                backgroundColor: '#f8fafc', borderRadius: '8px'
              }}>
                <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.85rem', color: '#1e293b', textTransform: 'capitalize' }}>
                  {actionType} Appointment
                </h4>

                {actionType === 'reschedule' && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <div>
                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>New Date & Time *</label>
                      <input
                        type="datetime-local"
                        required
                        value={actionFields.new_datetime}
                        onChange={e => setActionFields(f => ({ ...f, new_datetime: e.target.value }))}
                        style={{ padding: '0.4rem', fontSize: '0.8rem', width: '100%', boxSizing: 'border-box' }}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>Reason for Rescheduling *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Schedule conflict"
                        value={actionFields.reason}
                        onChange={e => setActionFields(f => ({ ...f, reason: e.target.value }))}
                        style={{ padding: '0.4rem', fontSize: '0.8rem', width: '100%', boxSizing: 'border-box' }}
                      />
                    </div>
                  </div>
                )}

                {actionType === 'complete' && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <div>
                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>Internal Doctor Notes</label>
                      <textarea
                        rows={2}
                        placeholder="Diagnosis details, clinical comments..."
                        value={actionFields.doctor_notes}
                        onChange={e => setActionFields(f => ({ ...f, doctor_notes: e.target.value }))}
                        style={{ padding: '0.4rem', fontSize: '0.8rem', width: '100%', boxSizing: 'border-box', resize: 'none' }}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>Patient Care Instructions</label>
                      <textarea
                        rows={2}
                        placeholder="Take prescribed vitamins, call coordinate clinic..."
                        value={actionFields.patient_instructions}
                        onChange={e => setActionFields(f => ({ ...f, patient_instructions: e.target.value }))}
                        style={{ padding: '0.4rem', fontSize: '0.8rem', width: '100%', boxSizing: 'border-box', resize: 'none' }}
                      />
                    </div>
                  </div>
                )}

                {(actionType === 'cancel' || actionType === 'no_show') && (
                  <div style={{ marginBottom: '0.5rem' }}>
                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>Reason *</label>
                    <input
                      type="text"
                      required
                      placeholder={`Provide a reason for ${actionType === 'cancel' ? 'cancellation' : 'no-show'}`}
                      value={actionFields.reason}
                      onChange={e => setActionFields(f => ({ ...f, reason: e.target.value }))}
                      style={{ padding: '0.4rem', fontSize: '0.8rem', width: '100%', boxSizing: 'border-box' }}
                    />
                  </div>
                )}

                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', justifyContent: 'flex-end' }}>
                  <button
                    onClick={() => { setActiveActionId(null); setActionType(''); }}
                    style={{ ...actionButtonStyle, backgroundColor: '#cbd5e1', color: '#334155' }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleUpdateStatus(appt.id, {
                      reschedule: 'rescheduled',
                      complete: 'completed',
                      cancel: 'cancelled',
                      no_show: 'no_show'
                    }[actionType])}
                    disabled={actionLoading === appt.id}
                    style={{
                      ...actionButtonStyle,
                      backgroundColor: '#247576',
                      color: '#fff',
                      opacity: actionLoading === appt.id ? 0.7 : 1
                    }}
                  >
                    {actionLoading === appt.id ? 'Saving…' : 'Submit'}
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
