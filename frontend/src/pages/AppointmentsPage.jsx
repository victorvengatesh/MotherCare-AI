import React, { useState, useEffect } from 'react';
import { listAppointments, requestAppointment, updateAppointmentStatus } from '../services/api';

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

  const [form, setForm] = useState({
    doctor_id: doctorId || '',
    appointment_datetime: '',
    appointment_type: 'checkup',
    reason: '',
  });

  useEffect(() => {
    fetchAppointments();
  }, [filterStatus]);

  async function fetchAppointments() {
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
  }

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

  async function handleCancel(apptId) {
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

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ margin: 0, color: '#1e293b', fontSize: '1.5rem', fontWeight: 700 }}>📅 Appointments</h2>
          <p style={{ margin: '0.25rem 0 0', color: '#64748b', fontSize: '0.9rem' }}>
            {role === 'patient' ? 'Your scheduled appointments' : 'Patient appointments'}
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
                background: showForm ? '#e2e8f0' : 'linear-gradient(135deg, #0ea5e9, #0369a1)',
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
        <div style={{ ...card, border: '2px solid #0ea5e9', marginBottom: '1.5rem' }}>
          <h3 style={{ margin: '0 0 1rem', color: '#0369a1', fontSize: '1rem' }}>New Appointment Request</h3>
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
                  background: 'linear-gradient(135deg, #0ea5e9, #0369a1)',
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
        const style = STATUS_COLORS[appt.status] || { bg: '#f3f4f6', color: '#374151' };
        const dt = new Date(appt.appointment_datetime);
        const isPast = dt < new Date();

        return (
          <div key={appt.id} style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.25rem', flexWrap: 'wrap' }}>
                  <span style={{
                    fontSize: '0.75rem', fontWeight: 700,
                    padding: '0.15rem 0.5rem', borderRadius: '4px',
                    backgroundColor: style.bg, color: style.color,
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
                {appt.patient_instructions && (
                  <div style={{
                    marginTop: '0.5rem', padding: '0.5rem 0.75rem',
                    backgroundColor: '#f0fdf4', borderRadius: '6px',
                    fontSize: '0.85rem', color: '#166534', borderLeft: '3px solid #4ade80',
                  }}>
                    📋 <strong>Instructions:</strong> {appt.patient_instructions}
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
                {role === 'patient' && appt.status === 'requested' && (
                  <button
                    onClick={() => handleCancel(appt.id)}
                    disabled={actionLoading === appt.id}
                    style={{
                      padding: '0.4rem 0.85rem',
                      background: '#fee2e2',
                      color: '#991b1b',
                      border: '1px solid #fca5a5',
                      borderRadius: '6px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      fontSize: '0.8rem',
                    }}
                  >
                    {actionLoading === appt.id ? '…' : 'Cancel'}
                  </button>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
