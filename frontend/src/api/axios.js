import axios from 'axios';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000',
});

/**
 * Request Interceptor: Attach JWT Token
 * 
 * Automatically includes the JWT token in Authorization header
 * for all outgoing requests.
 */
api.interceptors.request.use(
  (config) => {
    // Print the real endpoint being called during development
    console.log(`[API Call] Requesting endpoint: ${config.method.toUpperCase()} ${config.baseURL || ''}${config.url}`);
    const token = localStorage.getItem('mc_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    console.error('Request interceptor error:', error);
    return Promise.reject(error);
  }
);

/**
 * Response Interceptor: Handle Standardized Response Format
 * 
 * All backend responses follow:
 * {
 *   success: boolean,
 *   data: any,
 *   message: string,
 *   status_code: number
 * }
 * 
 * This interceptor:
 * 1. Validates response structure
 * 2. Handles 401 (unauthorized) — clears token and redirects to login
 * 3. Handles 503 (service unavailable) — shows fallback message
 * 4. Handles 500 (server error) — logs and shows user-friendly message
 * 5. Logs detailed errors for debugging
 */
api.interceptors.response.use(
  (response) => {
    // Validate standardized response format
    const { data } = response;
    
    if (data && typeof data === 'object') {
      // Response follows standardized format
      if (!data.success && data.status_code >= 400) {
        // Backend returned a business logic error (e.g., 400, 403)
        const error = new Error(data.message || 'Request failed');
        error.response = response;
        error.data = data;
        return Promise.reject(error);
      }
    }
    
    return response;
  },
  (error) => {
    const status = error.response?.status;
    const data = error.response?.data;

    // 401 Unauthorized — Clear token and redirect to login
    if (status === 401) {
      console.warn('Session expired (401). Redirecting to login.');
      localStorage.removeItem('mc_token');
      localStorage.removeItem('mc_username');
      localStorage.removeItem('mc_language');
      window.location.href = '/login';
      return Promise.reject(error);
    }

    // 403 Forbidden
    if (status === 403) {
      console.error('Access denied (403):', data?.message || 'Forbidden');
      error.userMessage = 'You do not have permission to access this resource.';
      return Promise.reject(error);
    }

    // 400 Bad Request
    if (status === 400) {
      console.error('Bad request (400):', data?.message || error.message);
      error.userMessage = data?.message || 'Invalid request. Please check your input.';
      return Promise.reject(error);
    }

    // 503 Service Unavailable — Circuit breaker likely OPEN
    if (status === 503) {
      console.error('Service unavailable (503). Backend circuit breaker is likely OPEN.');
      error.userMessage = data?.message || 'The medical service is temporarily unavailable. Please try again in a moment.';
      error.isServiceUnavailable = true;
      return Promise.reject(error);
    }

    // 500 Server Error
    if (status === 500) {
      console.error('Server error (500):', data?.message || error.message);
      error.userMessage = 'An unexpected server error occurred. Please try again or contact support.';
      error.isServerError = true;
      return Promise.reject(error);
    }

    // Network error (no response)
    if (!error.response) {
      console.error('Network error:', error.message);
      error.userMessage = 'Network error. Please check your connection and try again.';
      error.isNetworkError = true;
      return Promise.reject(error);
    }

    // Timeout
    if (error.code === 'ECONNABORTED') {
      console.error('Request timeout');
      error.userMessage = 'Request timed out. Please try again.';
      error.isTimeout = true;
      return Promise.reject(error);
    }

    // Unknown error
    console.error('Unknown error:', error);
    error.userMessage = 'An unexpected error occurred. Please try again.';
    
    return Promise.reject(error);
  }
);

export default api;
