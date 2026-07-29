/**
 * Frontend Input Validation & Sanitization Utilities
 * 
 * Provides:
 * - Email validation
 * - Password strength checking
 * - XSS prevention (HTML escaping)
 * - SQL injection-like pattern detection
 * - File upload validation
 * - Medical query validation
 */

import DOMPurify from 'dompurify';

// ──────────────────────────────────────────────────────────────────
// Email Validation
// ──────────────────────────────────────────────────────────────────

export const validateEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

export const isValidEmail = (email) => {
  if (!email || typeof email !== 'string') return false;
  if (email.length > 254) return false;
  return validateEmail(email.trim());
};

// ──────────────────────────────────────────────────────────────────
// Password Validation
// ──────────────────────────────────────────────────────────────────

export const validatePassword = (password) => {
  const errors = [];
  
  if (!password || typeof password !== 'string') {
    return { valid: false, errors: ['Password is required'] };
  }
  
  if (password.length < 8) {
    errors.push('Password must be at least 8 characters');
  }
  
  if (!/[A-Z]/.test(password)) {
    errors.push('Password must contain uppercase letter');
  }
  
  if (!/[a-z]/.test(password)) {
    errors.push('Password must contain lowercase letter');
  }
  
  if (!/[0-9]/.test(password)) {
    errors.push('Password must contain digit');
  }
  
  if (!/[!@#$%^&*]/.test(password)) {
    errors.push('Password must contain special character (!@#$%^&*)');
  }
  
  return {
    valid: errors.length === 0,
    errors,
    strength: calculatePasswordStrength(password)
  };
};

export const calculatePasswordStrength = (password) => {
  let strength = 0;
  
  if (!password) return 'weak';
  if (password.length >= 12) strength++;
  if (password.length >= 16) strength++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) strength++;
  if (/[0-9]/.test(password)) strength++;
  if (/[!@#$%^&*]/.test(password)) strength++;
  
  if (strength <= 1) return 'weak';
  if (strength <= 2) return 'fair';
  if (strength <= 3) return 'good';
  if (strength <= 4) return 'strong';
  return 'very strong';
};

// ──────────────────────────────────────────────────────────────────
// Username Validation
// ──────────────────────────────────────────────────────────────────

export const validateUsername = (username) => {
  const errors = [];
  
  if (!username || typeof username !== 'string') {
    return { valid: false, errors: ['Username is required'] };
  }
  
  const trimmed = username.trim();
  
  if (trimmed.length < 3) {
    errors.push('Username must be at least 3 characters');
  }
  
  if (trimmed.length > 30) {
    errors.push('Username must not exceed 30 characters');
  }
  
  if (!/^[a-zA-Z0-9_-]+$/.test(trimmed)) {
    errors.push('Username can only contain letters, numbers, underscores, and hyphens');
  }
  
  // Prevent common injection patterns
  if (containsSuspiciousPatterns(trimmed)) {
    errors.push('Username contains invalid characters');
  }
  
  return {
    valid: errors.length === 0,
    errors,
    sanitized: trimmed
  };
};

// ──────────────────────────────────────────────────────────────────
// Medical Query Validation
// ──────────────────────────────────────────────────────────────────

export const validateMedicalQuery = (query) => {
  const errors = [];
  
  if (!query || typeof query !== 'string') {
    return { valid: false, errors: ['Query is required'] };
  }
  
  const trimmed = query.trim();
  
  if (trimmed.length < 3) {
    errors.push('Query must be at least 3 characters');
  }
  
  if (trimmed.length > 5000) {
    errors.push('Query must not exceed 5000 characters');
  }
  
  // Check for code injection patterns
  if (containsCodePatterns(trimmed)) {
    errors.push('Query contains invalid characters');
  }
  
  return {
    valid: errors.length === 0,
    errors,
    sanitized: sanitizeText(trimmed),
    wordCount: trimmed.split(/\s+/).length
  };
};

// ──────────────────────────────────────────────────────────────────
// XSS Prevention - HTML Escaping
// ──────────────────────────────────────────────────────────────────

export const sanitizeText = (text) => {
  if (!text || typeof text !== 'string') return '';
  
  // Use DOMPurify for safe HTML sanitization
  return DOMPurify.sanitize(text, { 
    ALLOWED_TAGS: [],
    ALLOWED_ATTR: [],
    KEEP_CONTENT: true
  }).trim();
};

export const escapeHtml = (text) => {
  if (!text || typeof text !== 'string') return '';
  
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
};

// ──────────────────────────────────────────────────────────────────
// Injection Pattern Detection
// ──────────────────────────────────────────────────────────────────

export const containsSuspiciousPatterns = (input) => {
  if (!input || typeof input !== 'string') return false;
  
  // SQL injection patterns
  const sqlPatterns = [
    /(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)/i,
    /(--|#|\/\*|\*\/)/,
    /[;'"]/
  ];
  
  // XSS patterns
  const xssPatterns = [
    /<script\b/i,
    /javascript:/i,
    /on\w+\s*=/i,
    /<iframe/i,
    /<img.*on/i
  ];
  
  const allPatterns = [...sqlPatterns, ...xssPatterns];
  return allPatterns.some(pattern => pattern.test(input));
};

export const containsCodePatterns = (input) => {
  if (!input || typeof input !== 'string') return false;
  
  const codePatterns = [
    /<script/i,
    /javascript:/i,
    /on\w+\s*=/i,
    /eval\(/i,
    /document\./i,
    /window\./i,
    /function\s*\(/i
  ];
  
  return codePatterns.some(pattern => pattern.test(input));
};

// ──────────────────────────────────────────────────────────────────
// File Upload Validation
// ──────────────────────────────────────────────────────────────────

export const validateFileUpload = (file, options = {}) => {
  const {
    maxSize = 10 * 1024 * 1024, // 10MB default
    allowedTypes = ['application/pdf'],
    allowedExtensions = ['.pdf']
  } = options;
  
  const errors = [];
  
  if (!file || !(file instanceof File)) {
    return { valid: false, errors: ['No file provided'] };
  }
  
  // Check file size
  if (file.size > maxSize) {
    errors.push(`File size exceeds ${maxSize / 1024 / 1024}MB limit`);
  }
  
  // Check file type
  if (!allowedTypes.includes(file.type)) {
    errors.push(`File type ${file.type} not allowed`);
  }
  
  // Check file extension
  const extension = '.' + file.name.split('.').pop().toLowerCase();
  if (!allowedExtensions.includes(extension)) {
    errors.push(`File extension ${extension} not allowed`);
  }
  
  // Check file name for suspicious patterns
  if (containsSuspiciousPatterns(file.name)) {
    errors.push('File name contains invalid characters');
  }
  
  return {
    valid: errors.length === 0,
    errors,
    fileName: sanitizeFileName(file.name),
    size: file.size,
    type: file.type
  };
};

export const sanitizeFileName = (fileName) => {
  if (!fileName || typeof fileName !== 'string') return 'file';
  
  // Remove path separators and suspicious characters
  return fileName
    .replace(/[/\\]/g, '')
    .replace(/[<>:"|?*]/g, '')
    .replace(/\s+/g, '_')
    .substring(0, 255);
};

// ──────────────────────────────────────────────────────────────────
// Language Validation
// ──────────────────────────────────────────────────────────────────

export const validateLanguage = (language) => {
  const allowedLanguages = ['English', 'Tamil'];
  
  if (!language || typeof language !== 'string') {
    return { valid: false, language: 'English' };
  }
  
  const validated = language.trim();
  const isValid = allowedLanguages.includes(validated);
  
  return {
    valid: isValid,
    language: isValid ? validated : 'English',
    errors: isValid ? [] : [`Language must be one of: ${allowedLanguages.join(', ')}`]
  };
};

// ──────────────────────────────────────────────────────────────────
// Comprehensive Request Validation
// ──────────────────────────────────────────────────────────────────

export const validateChatRequest = (query, language) => {
  const queryValidation = validateMedicalQuery(query);
  const languageValidation = validateLanguage(language);
  
  const errors = [
    ...queryValidation.errors,
    ...languageValidation.errors
  ];
  
  return {
    valid: queryValidation.valid && languageValidation.valid,
    errors,
    query: queryValidation.sanitized,
    language: languageValidation.language
  };
};

export const validateRegistrationRequest = (username, email, password) => {
  const usernameValidation = validateUsername(username);
  const emailValidation = { valid: isValidEmail(email), errors: [] };
  const passwordValidation = validatePassword(password);
  
  if (!emailValidation.valid) {
    emailValidation.errors = ['Invalid email format'];
  }
  
  const errors = [
    ...usernameValidation.errors,
    ...emailValidation.errors,
    ...passwordValidation.errors
  ];
  
  return {
    valid: usernameValidation.valid && emailValidation.valid && passwordValidation.valid,
    errors,
    username: usernameValidation.sanitized,
    email: email.trim().toLowerCase(),
    passwordStrength: passwordValidation.strength
  };
};

export const validateLoginRequest = (username, password) => {
  const errors = [];
  
  if (!username || typeof username !== 'string' || username.trim().length === 0) {
    errors.push('Username is required');
  }
  
  if (!password || typeof password !== 'string' || password.length === 0) {
    errors.push('Password is required');
  }
  
  return {
    valid: errors.length === 0,
    errors,
    username: username?.trim() || '',
    password
  };
};

// ──────────────────────────────────────────────────────────────────
// Rate Limiting Detection
// ──────────────────────────────────────────────────────────────────

export class ClientRateLimiter {
  constructor(maxRequests = 10, windowMs = 60000) {
    this.maxRequests = maxRequests;
    this.windowMs = windowMs;
    this.requests = [];
  }
  
  isAllowed() {
    const now = Date.now();
    
    // Remove old requests outside the window
    this.requests = this.requests.filter(time => now - time < this.windowMs);
    
    // Check if under limit
    if (this.requests.length < this.maxRequests) {
      this.requests.push(now);
      return true;
    }
    
    return false;
  }
  
  getRemainingRequests() {
    const now = Date.now();
    this.requests = this.requests.filter(time => now - time < this.windowMs);
    return Math.max(0, this.maxRequests - this.requests.length);
  }
  
  reset() {
    this.requests = [];
  }
}

export default {
  validateEmail,
  isValidEmail,
  validatePassword,
  calculatePasswordStrength,
  validateUsername,
  validateMedicalQuery,
  sanitizeText,
  escapeHtml,
  containsSuspiciousPatterns,
  containsCodePatterns,
  validateFileUpload,
  sanitizeFileName,
  validateLanguage,
  validateChatRequest,
  validateRegistrationRequest,
  validateLoginRequest,
  ClientRateLimiter
};
