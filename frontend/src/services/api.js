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

export const registerUser = async (username, email, password) => {
  const body = new URLSearchParams();
  body.append('username', username);
  body.append('email', email);
  body.append('password', password);

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
  return response.data.access_token;
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

