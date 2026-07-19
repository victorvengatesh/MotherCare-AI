import React, { useState } from 'react';
import { loginUser, registerUser } from '../services/api';
import { 
  validateLoginRequest, 
  validateRegistrationRequest,
  calculatePasswordStrength 
} from '../utils/validation';

const LoginPage = ({ onLoginSuccess }) => {
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [form, setForm] = useState({ username: '', email: '', password: '', passwordConfirm: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [validationErrors, setValidationErrors] = useState({});
  const [passwordStrength, setPasswordStrength] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setError(null);
    
    // Update password strength indicator
    if (name === 'password' && mode === 'register') {
      setPasswordStrength(calculatePasswordStrength(value));
    }
    
    // Clear validation error for this field
    if (validationErrors[name]) {
      setValidationErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setValidationErrors({});

    try {
      if (mode === 'register') {
        // Validate registration
        const validation = validateRegistrationRequest(
          form.username,
          form.email,
          form.password
        );
        
        if (!validation.valid) {
          setValidationErrors({
            general: validation.errors
          });
          return;
        }
        
        // Check password confirmation
        if (form.password !== form.passwordConfirm) {
          setValidationErrors({ passwordConfirm: ['Passwords do not match'] });
          return;
        }
        
        setLoading(true);
        await registerUser(validation.username, validation.email, form.password);
        
        // Auto-login after successful registration
        const token = await loginUser(validation.username, form.password);
        onLoginSuccess(token, validation.username);
      } else {
        // Validate login
        const validation = validateLoginRequest(form.username, form.password);
        
        if (!validation.valid) {
          setValidationErrors({
            general: validation.errors
          });
          return;
        }
        
        setLoading(true);
        const token = await loginUser(validation.username, form.password);
        onLoginSuccess(token, validation.username);
      }
    } catch (err) {
      setError(err.message || 'An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getPasswordStrengthColor = () => {
    switch (passwordStrength) {
      case 'weak': return '#dc2626';
      case 'fair': return '#ea580c';
      case 'good': return '#eab308';
      case 'strong': return '#22c55e';
      case 'very strong': return '#16a34a';
      default: return '#e5e7eb';
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '0.875rem 1rem',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    fontFamily: 'inherit',
    fontSize: '1rem',
    backgroundColor: '#fff',
    marginBottom: '1rem',
    outline: 'none',
    transition: 'border-color 0.2s, box-shadow 0.2s',
  };

  const labelStyle = {
    display: 'block',
    fontSize: '0.875rem',
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: '0.4rem',
  };

  const errorLabelStyle = {
    display: 'block',
    fontSize: '0.75rem',
    fontWeight: '500',
    color: '#dc2626',
    marginTop: '-0.75rem',
    marginBottom: '0.5rem',
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: '#f8fafc',
      padding: '1.5rem',
    }}>
      <div style={{
        width: '100%',
        maxWidth: '420px',
        backgroundColor: '#fff',
        borderRadius: '16px',
        boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1), 0 4px 10px -5px rgba(0,0,0,0.05)',
        padding: '2.5rem',
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            marginBottom: '0.5rem',
          }}>
            <span style={{ fontSize: '1.75rem' }}>➕</span>
            <h1 style={{
              fontSize: '1.5rem',
              fontWeight: '700',
              color: '#247576',
              margin: 0,
            }}>MotherCare AI</h1>
          </div>
          <p style={{ color: '#64748b', fontSize: '0.875rem', margin: 0 }}>
            Smart Triage for Better Care
          </p>
        </div>

        {/* Mode Toggle */}
        <div style={{
          display: 'flex',
          backgroundColor: '#f1f5f9',
          borderRadius: '10px',
          padding: '0.25rem',
          marginBottom: '1.75rem',
          gap: '0.25rem',
        }}>
          {['login', 'register'].map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(null); setValidationErrors({}); }}
              style={{
                flex: 1,
                padding: '0.6rem',
                borderRadius: '8px',
                fontWeight: '600',
                fontSize: '0.875rem',
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.2s',
                backgroundColor: mode === m ? '#fff' : 'transparent',
                color: mode === m ? '#247576' : '#64748b',
                boxShadow: mode === m ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              }}
            >
              {m === 'login' ? 'Sign In' : 'Register'}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit}>
          {/* General Validation Errors */}
          {validationErrors.general && (
            <div style={{
              backgroundColor: '#fef2f2',
              border: '1px solid #fee2e2',
              borderRadius: '8px',
              padding: '0.75rem 1rem',
              color: '#dc2626',
              fontSize: '0.875rem',
              marginBottom: '1rem',
            }}>
              <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>⚠️ Validation Errors:</div>
              <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
                {validationErrors.general.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Username */}
          <div>
            <label style={labelStyle} htmlFor="username">Username</label>
            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              required
              placeholder="Enter your username"
              value={form.username}
              onChange={handleChange}
              style={{
                ...inputStyle,
                borderColor: validationErrors.username ? '#dc2626' : '#e2e8f0'
              }}
              onFocus={(e) => {
                e.target.style.borderColor = '#247576';
                e.target.style.boxShadow = '0 0 0 3px #e6f6f6';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = validationErrors.username ? '#dc2626' : '#e2e8f0';
                e.target.style.boxShadow = 'none';
              }}
            />
            {validationErrors.username && (
              <div style={errorLabelStyle}>{validationErrors.username[0]}</div>
            )}
          </div>

          {/* Email (register only) */}
          {mode === 'register' && (
            <div>
              <label style={labelStyle} htmlFor="email">Email</label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                placeholder="Enter your email"
                value={form.email}
                onChange={handleChange}
                style={{
                  ...inputStyle,
                  borderColor: validationErrors.email ? '#dc2626' : '#e2e8f0'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = '#247576';
                  e.target.style.boxShadow = '0 0 0 3px #e6f6f6';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = validationErrors.email ? '#dc2626' : '#e2e8f0';
                  e.target.style.boxShadow = 'none';
                }}
              />
              {validationErrors.email && (
                <div style={errorLabelStyle}>{validationErrors.email[0]}</div>
              )}
            </div>
          )}

          {/* Password */}
          <div>
            <label style={labelStyle} htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              required
              placeholder="Enter your password"
              value={form.password}
              onChange={handleChange}
              style={{
                ...inputStyle,
                borderColor: validationErrors.password ? '#dc2626' : '#e2e8f0'
              }}
              onFocus={(e) => {
                e.target.style.borderColor = '#247576';
                e.target.style.boxShadow = '0 0 0 3px #e6f6f6';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = validationErrors.password ? '#dc2626' : '#e2e8f0';
                e.target.style.boxShadow = 'none';
              }}
            />
            {validationErrors.password && (
              <div style={errorLabelStyle}>{validationErrors.password[0]}</div>
            )}
            
            {/* Password Strength Indicator (register only) */}
            {mode === 'register' && form.password && (
              <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '0.5rem', alignItems: 'center' }}>
                <div style={{ flex: 1, height: '4px', backgroundColor: '#e5e7eb', borderRadius: '2px', overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${(passwordStrength === 'weak' ? 20 : passwordStrength === 'fair' ? 40 : passwordStrength === 'good' ? 60 : passwordStrength === 'strong' ? 80 : 100)}%`,
                      backgroundColor: getPasswordStrengthColor(),
                      transition: 'width 0.3s'
                    }}
                  />
                </div>
                <span style={{ fontSize: '0.75rem', fontWeight: '600', color: getPasswordStrengthColor() }}>
                  {passwordStrength}
                </span>
              </div>
            )}
          </div>

          {/* Password Confirmation (register only) */}
          {mode === 'register' && (
            <div>
              <label style={labelStyle} htmlFor="passwordConfirm">Confirm Password</label>
              <input
                id="passwordConfirm"
                name="passwordConfirm"
                type="password"
                autoComplete="new-password"
                required
                placeholder="Confirm your password"
                value={form.passwordConfirm}
                onChange={handleChange}
                style={{
                  ...inputStyle,
                  borderColor: validationErrors.passwordConfirm ? '#dc2626' : '#e2e8f0'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = '#247576';
                  e.target.style.boxShadow = '0 0 0 3px #e6f6f6';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = validationErrors.passwordConfirm ? '#dc2626' : '#e2e8f0';
                  e.target.style.boxShadow = 'none';
                }}
              />
              {validationErrors.passwordConfirm && (
                <div style={errorLabelStyle}>{validationErrors.passwordConfirm[0]}</div>
              )}
            </div>
          )}

          {/* Error */}
          {error && (
            <div style={{
              backgroundColor: '#fef2f2',
              border: '1px solid #fee2e2',
              borderRadius: '8px',
              padding: '0.75rem 1rem',
              color: '#dc2626',
              fontSize: '0.875rem',
              marginBottom: '1rem',
            }}>
              ❌ {error}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '0.875rem',
              backgroundColor: loading ? '#94a3b8' : '#247576',
              color: '#fff',
              borderRadius: '10px',
              fontWeight: '600',
              fontSize: '1rem',
              border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s',
              boxShadow: loading ? 'none' : '0 4px 6px -1px rgba(36,117,118,0.25)',
              marginTop: '0.25rem',
            }}
            onMouseEnter={(e) => { if (!loading) e.target.style.backgroundColor = '#1b5a5b'; }}
            onMouseLeave={(e) => { if (!loading) e.target.style.backgroundColor = '#247576'; }}
          >
            {loading
              ? (mode === 'login' ? 'Signing in...' : 'Creating account...')
              : (mode === 'login' ? 'Sign In' : 'Create Account')}
          </button>
        </form>

        <p style={{
          textAlign: 'center',
          marginTop: '1.5rem',
          fontSize: '0.8rem',
          color: '#94a3b8',
        }}>
          For informational purposes only. Not a substitute for medical advice.
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
