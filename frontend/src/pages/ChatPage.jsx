import React, { useState, useRef, useEffect } from 'react';
import api from '../api/axios';

const AGENT_META = {
  obgyn:         { label: 'OB-GYN Agent',         emoji: '🩺', color: '#3b82f6' },
  nutritionist:  { label: 'Nutritionist Agent',    emoji: '🥗', color: '#22c55e' },
  mental_health: { label: 'Mental Health Agent',   emoji: '🧠', color: '#a855f7' },
  emergency:     { label: 'Emergency Specialist',  emoji: '🚨', color: '#ef4444' },
};

const EMERGENCY_KEYWORDS = ['bleeding', 'severe pain', 'no movement', 'chest pain', 'seizure', 'unconscious'];

const ChatPage = ({ language, setLanguage }) => {
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      agent: 'obgyn',
      text: language === 'Tamil'
        ? 'வணக்கம்! நான் உங்கள் MotherCare AI உதவியாளர். உங்கள் கேள்வியை கேளுங்கள்.'
        : 'Hello! I am your MotherCare AI assistant. I will connect you with the right specialist. How can I help you today?',
    },
  ]);
  const [input, setInput]       = useState('');
  const [loading, setLoading]   = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const bottomRef = useRef(null);
  const fileRef   = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const isEmergency = (text) =>
    EMERGENCY_KEYWORDS.some((kw) => text.toLowerCase().includes(kw));

  const sendMessage = async () => {
    const query = input.trim();
    if (!query || loading) return;

    const userMsg = { role: 'user', text: query };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    // Show emergency banner immediately if needed
    if (isEmergency(query)) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'system',
          text: '🚨 Emergency keywords detected. Connecting to Emergency Specialist and contacting help immediately.',
        },
      ]);
    }

    try {
      // Add timeout protection
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Request timeout after 30 seconds')), 30000)
      );

      const chatPromise = api.post('/ai/chat', { query, language });
      const res = await Promise.race([chatPromise, timeoutPromise]);
      
      const data = res.data?.data;
      
      if (!data) {
        throw new Error('Invalid response format from server');
      }
      
      if (!data.response || typeof data.response !== 'string') {
        throw new Error('Received empty or invalid response from AI service');
      }
      
      setMessages((prev) => [
        ...prev,
        { role: 'bot', agent: data.agent || 'obgyn', text: data.response, rag: data.rag_context_used },
      ]);
    } catch (err) {
      // Handle different error types gracefully
      let errorMsg = 'Sorry, I could not process your request. Please try again.';
      
      if (err.message?.includes('timeout') || err.isTimeout) {
        errorMsg = '⏱️ Request timed out (took too long). Please try a shorter question or check your internet connection.';
      } else if (err.isServiceUnavailable) {
        errorMsg = '⚠️ The medical service is temporarily unavailable due to high load. Our circuit breaker is protecting the system. Please try again in 30 seconds.';
      } else if (err.isServerError) {
        errorMsg = '⚠️ A server error occurred. Please try again shortly or contact support.';
      } else if (err.isNetworkError) {
        errorMsg = '📡 Network connection error. Please check your internet and try again.';
      } else if (err.userMessage) {
        errorMsg = err.userMessage;
      } else if (err.message) {
        errorMsg = `Error: ${err.message}`;
      }
      
      setMessages((prev) => [
        ...prev,
        { role: 'bot', agent: 'emergency', text: errorMsg },
      ]);
      
      console.error('Chat error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handlePdfUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadResult({ success: false, error: 'Only PDF files are supported' });
      fileRef.current.value = '';
      return;
    }
    
    setUploading(true);
    setUploadResult(null);
    const form = new FormData();
    form.append('file', file);
    
    try {
      // Add timeout protection
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Upload timeout after 60 seconds')), 60000)
      );

      const uploadPromise = api.post('/ai/upload-report', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      
      const res = await Promise.race([uploadPromise, timeoutPromise]);
      const data = res.data?.data;
      
      if (!data) {
        throw new Error('Invalid response from upload');
      }
      
      if (!data.filename || !data.summary) {
        throw new Error('Incomplete response from upload');
      }
      
      setUploadResult({ success: true, filename: data.filename, summary: data.summary });
      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          agent: 'obgyn',
          text: `📄 Report "${data.filename}" uploaded and indexed.\n\n${data.summary}`,
        },
      ]);
    } catch (err) {
      let errorMsg = 'Upload failed.';
      
      if (err.message?.includes('timeout')) {
        errorMsg = 'Upload timed out. The file may be too large or your connection is slow.';
      } else if (err.isServiceUnavailable) {
        errorMsg = 'Upload service temporarily unavailable. Please try again shortly.';
      } else if (err.isNetworkError) {
        errorMsg = 'Network error during upload. Please check your connection.';
      } else if (err.userMessage) {
        errorMsg = err.userMessage;
      } else if (err.message) {
        errorMsg = err.message;
      }
      
      setUploadResult({ success: false, error: errorMsg });
      setMessages((prev) => [
        ...prev,
        { role: 'bot', agent: 'emergency', text: `❌ Upload failed: ${errorMsg}` },
      ]);
      
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
      fileRef.current.value = '';
    }
  };

  const agentBadge = (agentKey) => {
    const meta = AGENT_META[agentKey] || AGENT_META.obgyn;
    return (
      <span style={{
        fontSize: '0.7rem', fontWeight: 700,
        color: meta.color, marginBottom: '0.25rem',
        display: 'block',
      }}>
        {meta.emoji} {meta.label}
      </span>
    );
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 140px)' }}>

      {/* Header bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h2 style={{ margin: 0, color: '#1e293b', fontSize: '1.25rem', fontWeight: 700 }}>
            🤖 Multi-Agent Consultation
          </h2>
          <p style={{ margin: 0, color: '#64748b', fontSize: '0.8rem' }}>
            CMO routes your query to the right specialist · RAG-powered
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {/* Language toggle */}
          <div style={{ display: 'flex', backgroundColor: '#f1f5f9', borderRadius: 8, padding: 2 }}>
            {['English', 'Tamil'].map((lang) => (
              <button key={lang} onClick={() => setLanguage(lang)} style={{
                padding: '0.3rem 0.75rem', borderRadius: 6, border: 'none', cursor: 'pointer',
                fontSize: '0.8rem', fontWeight: 600,
                backgroundColor: language === lang ? '#fff' : 'transparent',
                color: language === lang ? '#247576' : '#64748b',
                boxShadow: language === lang ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              }}>
                {lang === 'Tamil' ? 'தமிழ்' : lang}
              </button>
            ))}
          </div>

          {/* PDF upload */}
          <label style={{
            padding: '0.4rem 0.9rem', backgroundColor: '#247576', color: '#fff',
            borderRadius: 8, fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
            opacity: uploading ? 0.6 : 1,
          }}>
            {uploading ? '⏳ Uploading...' : '📄 Upload PDF'}
            <input ref={fileRef} type="file" accept=".pdf" onChange={handlePdfUpload}
              style={{ display: 'none' }} disabled={uploading} />
          </label>
        </div>
      </div>

      {/* Agent legend */}
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        {Object.entries(AGENT_META).map(([key, meta]) => (
          <span key={key} style={{
            fontSize: '0.7rem', fontWeight: 600, padding: '0.2rem 0.6rem',
            borderRadius: 20, backgroundColor: `${meta.color}15`, color: meta.color,
            border: `1px solid ${meta.color}30`,
          }}>
            {meta.emoji} {meta.label}
          </span>
        ))}
      </div>

      {/* Chat window */}
      <div style={{
        flex: 1, overflowY: 'auto', backgroundColor: '#f8fafc',
        borderRadius: 12, padding: '1rem', border: '1px solid #e2e8f0',
        display: 'flex', flexDirection: 'column', gap: '0.75rem',
      }}>
        {messages.map((msg, i) => {
          if (msg.role === 'system') {
            return (
              <div key={i} style={{
                backgroundColor: '#fef2f2', border: '1px solid #fecaca',
                borderRadius: 8, padding: '0.6rem 1rem',
                color: '#dc2626', fontSize: '0.85rem', fontWeight: 600, textAlign: 'center',
              }}>
                {msg.text}
              </div>
            );
          }

          const isUser = msg.role === 'user';
          return (
            <div key={i} style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
              <div style={{ maxWidth: '75%' }}>
                {!isUser && msg.agent && agentBadge(msg.agent)}
                <div style={{
                  padding: '0.75rem 1rem',
                  borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                  backgroundColor: isUser ? '#247576' : '#fff',
                  color: isUser ? '#fff' : '#1e293b',
                  fontSize: '0.9rem', lineHeight: 1.6,
                  boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                  border: isUser ? 'none' : '1px solid #e2e8f0',
                  whiteSpace: 'pre-wrap',
                }}>
                  {msg.text}
                </div>
                {!isUser && msg.rag && (
                  <span style={{ fontSize: '0.65rem', color: '#94a3b8', marginTop: 2, display: 'block' }}>
                    📚 RAG context used
                  </span>
                )}
              </div>
            </div>
          );
        })}

        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              backgroundColor: '#fff', border: '1px solid #e2e8f0',
              borderRadius: '16px 16px 16px 4px', padding: '0.75rem 1.25rem',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }}>
              <span style={{ display: 'flex', gap: 4 }}>
                {[0, 1, 2].map((d) => (
                  <span key={d} style={{
                    width: 7, height: 7, borderRadius: '50%', backgroundColor: '#247576',
                    display: 'inline-block',
                    animation: `bounce 1s ease-in-out ${d * 0.15}s infinite`,
                  }} />
                ))}
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={language === 'Tamil' ? 'உங்கள் கேள்வியை இங்கே கேளுங்கள்...' : 'Ask about symptoms, diet, mental health, or upload a report...'}
          rows={2}
          style={{
            flex: 1, padding: '0.75rem 1rem', border: '1px solid #e2e8f0',
            borderRadius: 10, fontFamily: 'inherit', fontSize: '0.9rem',
            resize: 'none', outline: 'none',
            transition: 'border-color 0.2s',
          }}
          onFocus={(e) => e.target.style.borderColor = '#247576'}
          onBlur={(e) => e.target.style.borderColor = '#e2e8f0'}
        />
        <button onClick={sendMessage} disabled={loading || !input.trim()} style={{
          padding: '0 1.5rem', backgroundColor: (loading || !input.trim()) ? '#94a3b8' : '#247576',
          color: '#fff', borderRadius: 10, border: 'none', fontWeight: 700,
          fontSize: '1.1rem', cursor: (loading || !input.trim()) ? 'not-allowed' : 'pointer',
          transition: 'background-color 0.2s', minWidth: 54,
        }}>
          ➤
        </button>
      </div>

      <p style={{ textAlign: 'center', color: '#94a3b8', fontSize: '0.72rem', marginTop: '0.4rem' }}>
        Enter to send · Shift+Enter for new line · Not a substitute for professional medical advice
      </p>

      <style>{`
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-5px); }
        }
      `}</style>
    </div>
  );
};

export default ChatPage;
