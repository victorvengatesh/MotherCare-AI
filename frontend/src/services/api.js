/**
 * Service for communicating with the MotherCare AI Backend API
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

// ─── Token helpers ────────────────────────────────────────────────────────────

export const getToken = () => localStorage.getItem('mc_token');
export const setToken = (token) => localStorage.setItem('mc_token', token);
export const removeToken = () => localStorage.removeItem('mc_token');

// ─── Interceptors ─────────────────────────────────────────────────────────────

apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    // Backend now returns StandardResponse: { status, message, data }
    return response.data;
  },
  (error) => {
    if (error.response?.status === 401) {
      removeToken();
      // Only reload if we are not on the login page to prevent loops
      // window.location.reload(); 
    }
    const message = error.response?.data?.message || error.response?.data?.detail || error.message;
    return Promise.reject(new Error(message));
  }
);

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const registerUser = async (username, email, password, role = 'patient') => {
  const body = new URLSearchParams();
  body.append('username', username);
  body.append('email', email);
  body.append('password', password);
  if (role) {
    body.append('role', role);
  }

  const response = await apiClient.post('/auth/register', body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return response;
};

export const loginUser = async (username, password) => {
  const body = new URLSearchParams();
  body.append('username', username);
  body.append('password', password);

  const response = await apiClient.post('/auth/login', body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  // Return the entire data payload which contains { access_token, user: { role } }
  return response.data;
};

// ─── Analysis ─────────────────────────────────────────────────────────────────

export const analyzeSymptoms = async (symptoms, image) => {
  const formData = new FormData();
  formData.append('symptoms', symptoms);
  if (image) {
    formData.append('file', image);
  }

  const response = await apiClient.post('/analyze', formData);
  return response.data;
};

// ─── Health ───────────────────────────────────────────────────────────────────

export const checkHealth = async () => {
  try {
    const response = await apiClient.get('/health');
    return response;
  } catch {
    return { status: 'error', data: { status: 'offline' } };
  }
};

// ─── Doctor ───────────────────────────────────────────────────────────────────

export const getPatients = async () => {
  const response = await apiClient.get('/doctor/patients');
  return response.data;
};

export const getPatientTwin = async (patientId) => {
  const response = await apiClient.get(`/doctor/patient/${patientId}/twin`);
  return response.data;
};

export const getAlerts = async (params = {}) => {
  const response = await apiClient.get('/doctor/alerts', { params });
  return response.data;
};

export const getAlert = async (alertId) => {
  const response = await apiClient.get(`/doctor/alert/${alertId}`);
  return response.data;
};

export const startReview = async (alertId) => {
  const response = await apiClient.post(`/doctor/alert/${alertId}/review`);
  return response.data;
};

export const addNotes = async (alertId, notes) => {
  const response = await apiClient.post(`/doctor/alert/${alertId}/notes`, { notes });
  return response.data;
};

export const escalateAlert = async (alertId, reason = '') => {
  const response = await apiClient.post(`/doctor/alert/${alertId}/escalate`, { reason });
  return response.data;
};

export const resolveAlert = async (alertId, reason) => {
  const response = await apiClient.post(`/doctor/alert/${alertId}/resolve`, { reason });
  return response.data;
};

export const dismissAlert = async (alertId, reason) => {
  const response = await apiClient.post(`/doctor/alert/${alertId}/dismiss`, { reason });
  return response.data;
};

export const getPatientTrends = async (patientId) => {
  const response = await apiClient.get(`/doctor/patient/${patientId}/trends`);
  return response.data;
};

export const getUserTrends = async () => {
  const response = await apiClient.get('/ai/trends');
  return response.data;
};

// ─── Patient Instructions ─────────────────────────────────────────────────────

export const getPatientInstructions = async () => {
  const response = await apiClient.get('/ai/instructions');
  return response.data;
};

export const markInstructionRead = async (instId) => {
  const response = await apiClient.post(`/ai/instruction/${instId}/read`);
  return response.data;
};

export const sendInstruction = async (payload) => {
  const response = await apiClient.post('/doctor/instruction', payload);
  return response.data;
};

export const listDoctorInstructions = async (patientId = null) => {
  const params = {};
  if (patientId) params.patient_id = patientId;
  const response = await apiClient.get('/doctor/instructions', { params });
  return response.data;
};

export const updateInstruction = async (instId, payload) => {
  const response = await apiClient.put(`/doctor/instruction/${instId}`, payload);
  return response.data;
};

export const withdrawInstruction = async (instId) => {
  const response = await apiClient.post(`/doctor/instruction/${instId}/withdraw`);
  return response.data;
};


// ─── Appointments ─────────────────────────────────────────────────────────────

export const requestAppointment = async (payload) => {
  const response = await apiClient.post('/appointments', payload);
  return response.data;
};

export const listAppointments = async (patientId = null, apptStatus = null) => {
  const params = {};
  if (patientId) params.patient_id = patientId;
  if (apptStatus) params.appt_status = apptStatus;
  const response = await apiClient.get('/appointments', { params });
  return response.data;
};

export const updateAppointmentStatus = async (apptId, payload) => {
  const response = await apiClient.put(`/appointments/${apptId}/status`, payload);
  return response.data;
};

// ─── Medicine Reminders ───────────────────────────────────────────────────────

export const createDoctorReminder = async (payload) => {
  const response = await apiClient.post('/reminders/doctor', payload);
  return response.data;
};

export const createSelfReminder = async (payload) => {
  const response = await apiClient.post('/reminders/self', payload);
  return response.data;
};

export const listReminders = async (patientId = null, activeOnly = true) => {
  const params = { active_only: activeOnly };
  if (patientId) params.patient_id = patientId;
  const response = await apiClient.get('/reminders', { params });
  return response.data;
};

export const recordAdherence = async (reminderId, payload) => {
  const response = await apiClient.post(`/reminders/${reminderId}/adherence`, payload);
  return response.data;
};

// ─── Notifications ────────────────────────────────────────────────────────────

export const listNotifications = async (unreadOnly = false) => {
  const response = await apiClient.get('/notifications', { params: { unread_only: unreadOnly } });
  return response.data;
};

export const markNotificationRead = async (notifId) => {
  const response = await apiClient.post(`/notifications/${notifId}/read`);
  return response.data;
};

export const markAllNotificationsRead = async () => {
  const response = await apiClient.post('/notifications/read-all');
  return response.data;
};

// ─── Medical Summary PDF ──────────────────────────────────────────────────────

export const downloadMedicalSummaryPdf = async (patientId = null) => {
  const params = {};
  if (patientId) params.patient_id = patientId;
  const response = await apiClient.get('/reports/summary/pdf', {
    params,
    responseType: 'blob',
  });
  return response; // caller handles blob download
};
