import React, { useState, useRef, useEffect } from 'react';
import api from '../api/axios';
import { getHealthRecords } from '../services/api';

const AGENT_META = {
  obgyn:         { label: 'OB-GYN Specialist',    emoji: '🩺', color: '#0d9488' },
  nutritionist:  { label: 'Nutritionist Specialist', emoji: '🥗', color: '#16a34a' },
  mental_health: { label: 'Mental Health Advisor',  emoji: '🧠', color: '#7c3aed' },
  emergency:     { label: 'Emergency Specialist',  emoji: '🚨', color: '#dc2626' },
};

const ChatPage = ({ language, setLanguage }) => {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  
  // Stateful Guided Interview session parameters
  const [completed, setCompleted] = useState(true);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [stepNumber, setStepNumber] = useState(0);
  const [totalSteps, setTotalSteps] = useState(0);
  const [collectedSymptoms, setCollectedSymptoms] = useState([]);
  const [answers, setAnswers] = useState({});
  const [riskLevel, setRiskLevel] = useState('Home Care 🟢');
  const [lastResponse, setLastResponse] = useState('');

  // Editing state for previous answers
  const [editingQuestion, setEditingQuestion] = useState(null);
  const [editValue, setEditValue] = useState('');

  // Historical records panel
  const [pastRecords, setPastRecords] = useState([]);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState(null);

  const fileRef = useRef(null);

  // Fetch past health records
  const fetchRecords = async () => {
    setLoadingRecords(true);
    try {
      const data = await getHealthRecords();
      setPastRecords(data || []);
    } catch (e) {
      console.error('Failed to load past records:', e);
    } finally {
      setLoadingRecords(false);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, []);

  // Post action to AI chat API
  const handleAction = async (actionType, queryText = '', extraParams = {}) => {
    setLoading(true);
    try {
      const payload = {
        query: queryText,
        language: language,
        action: actionType,
        ...extraParams
      };
      
      const res = await api.post('/ai/chat', payload);
      const data = res.data?.data;
      
      if (data) {
        setCompleted(data.completed ?? false);
        setCurrentQuestion(data.completed ? '' : (data.response || ''));
        setStepNumber(data.step_number || 0);
        setTotalSteps(data.total_steps || 0);
        setCollectedSymptoms(data.collected_symptoms || []);
        setAnswers(data.answers || {});
        setRiskLevel(data.risk_level || 'Home Care 🟢');
        
        if (data.completed) {
          setLastResponse(data.response);
          fetchRecords(); // Refresh history logs
        }
      }
    } catch (err) {
      console.error('Consultation action error:', err);
      alert(err.response?.data?.detail || 'Could not process interview action. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartInterview = () => {
    const query = input.trim();
    if (!query) return;
    setInput('');
    handleAction('submit', query);
  };

  const handleSubmitAnswer = () => {
    const query = input.trim();
    if (!query) return;
    setInput('');
    handleAction('submit', query);
  };

  const handleEditAnswer = (qText) => {
    setEditingQuestion(qText);
    setEditValue(answers[qText] || '');
  };

  const handleSaveEdit = async () => {
    if (!editingQuestion) return;
    const q = editingQuestion;
    const val = editValue.trim();
    
    setEditingQuestion(null);
    setEditValue('');
    
    await handleAction('edit', '', {
      question_to_edit: q,
      new_value: val
    });
  };

  const handleReset = () => {
    setCompleted(true);
    setCurrentQuestion('');
    setStepNumber(0);
    setTotalSteps(0);
    setCollectedSymptoms([]);
    setAnswers({});
    setRiskLevel('Home Care 🟢');
    setLastResponse('');
    handleAction('reset', 'reset');
  };

  const handlePdfUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Only PDF documents are supported.');
      fileRef.current.value = '';
      return;
    }
    
    setUploading(true);
    const form = new FormData();
    form.append('file', file);
    
    try {
      const res = await api.post('/ai/upload-report', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const data = res.data?.data;
      if (data) {
        setLastResponse(`📄 Report "${data.filename}" uploaded and indexed.\n\n${data.summary}`);
        setCompleted(true);
        fetchRecords();
      }
    } catch (err) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
      fileRef.current.value = '';
    }
  };

  // Resolve color token based on active risk category
  const getRiskColor = (lvl) => {
    const risk = String(lvl).toLowerCase();
    if (risk.includes('emergency') || risk.includes('red') || risk.includes('🔴')) return '#dc2626';
    if (risk.includes('urgent') || risk.includes('orange') || risk.includes('🟠')) return '#ea580c';
    if (risk.includes('routine') || risk.includes('yellow') || risk.includes('🟡')) return '#ca8a04';
    return '#16a34a'; // Home Care 🟢
  };

  return (
    <div style={{
      maxWidth: 1200, margin: '0 auto', padding: '1rem', display: 'flex', gap: '1.5rem', height: 'calc(100vh - 140px)', flexWrap: 'wrap'
    }}>
      {/* Left Column: History Panel */}
      <div style={{
        flex: '1 1 300px', display: 'flex', flexDirection: 'column', backgroundColor: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '1rem', height: '100%', overflowY: 'hidden'
      }}>
        <h3 style={{ margin: '0 0 0.5rem', color: '#1e293b', fontSize: '1rem', fontWeight: 800 }}>
          📜 Consultation History
        </h3>
        <p style={{ margin: '0 0 1rem', color: '#64748b', fontSize: '0.75rem' }}>
          Review previous clinical screening queries and uploaded PDFs.
        </p>

        {loadingRecords ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8', fontSize: '0.85rem' }}>Loading logs...</div>
        ) : (
          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {pastRecords.map((rec) => {
              const isChat = rec.type === 'chat' || rec.type === 'symptom';
              return (
                <div
                  key={rec.id}
                  onClick={() => {
                    setSelectedRecord(rec);
                    setLastResponse(rec.summary);
                    setCompleted(true);
                  }}
                  style={{
                    padding: '0.65rem 0.85rem', borderRadius: 8, border: '1px solid #e2e8f0', cursor: 'pointer',
                    backgroundColor: selectedRecord?.id === rec.id ? '#f0fdfa' : '#fafbfe',
                    transition: 'all 0.15s'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#94a3b8', marginBottom: '0.2rem' }}>
                    <span>{isChat ? '🩺 Clinical Screening' : '📄 Report PDF'}</span>
                    <span>{new Date(rec.timestamp).toLocaleDateString()}</span>
                  </div>
                  <div style={{
                    fontSize: '0.82rem', fontWeight: 700, color: '#1e293b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'
                  }}>
                    {isChat ? rec.content : rec.filename}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                    {rec.summary}
                  </div>
                </div>
              );
            })}
            {pastRecords.length === 0 && (
              <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8', fontSize: '0.85rem' }}>No history logged yet.</div>
            )}
          </div>
        )}

        {/* Selected Record Detail Popup Modal/Overlay */}
        {selectedRecord && (
          <div style={{
            marginTop: '1rem', padding: '0.75rem', borderTop: '2px solid #0d9488', backgroundColor: '#f8fafc', borderRadius: 8, fontSize: '0.8rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <strong>History Detail</strong>
              <button onClick={() => setSelectedRecord(null)} style={{ background: 'none', border: 'none', color: '#ef4444', fontWeight: 'bold', cursor: 'pointer' }}>Close</button>
            </div>
            <div style={{ color: '#1e293b', fontWeight: 600, marginBottom: '0.25rem' }}>
              Query/File: {selectedRecord.type === 'chat' ? selectedRecord.content : selectedRecord.filename}
            </div>
            <p style={{ margin: 0, color: '#475569', lineHeight: 1.4 }}>
              <strong>AI Diagnostic Summary:</strong> {selectedRecord.summary}
            </p>
          </div>
        )}
      </div>

      {/* Right Column: Stateful Guided Interview Panel */}
      <div style={{
        flex: '2 1 600px', display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'hidden'
      }}>
        {/* Header bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <div>
            <h2 style={{ margin: 0, color: '#1e293b', fontSize: '1.25rem', fontWeight: 700 }}>
              🩺 Guided Clinical Interview
            </h2>
            <p style={{ margin: 0, color: '#64748b', fontSize: '0.8rem' }}>
              Structured maternal healthcare decision support assistant
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <div style={{ display: 'flex', backgroundColor: '#f1f5f9', borderRadius: 8, padding: 2 }}>
              {['English', 'Tamil'].map((lang) => (
                <button key={lang} onClick={() => setLanguage(lang)} style={{
                  padding: '0.3rem 0.75rem', borderRadius: 6, border: 'none', cursor: 'pointer',
                  fontSize: '0.8rem', fontWeight: 600,
                  backgroundColor: language === lang ? '#fff' : 'transparent',
                  color: language === lang ? '#0d9488' : '#64748b',
                  boxShadow: language === lang ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                }}>
                  {lang === 'Tamil' ? 'தமிழ்' : lang}
                </button>
              ))}
            </div>

            <label style={{
              padding: '0.4rem 0.9rem', backgroundColor: '#0d9488', color: '#fff',
              borderRadius: 8, fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
              opacity: uploading ? 0.6 : 1,
            }}>
              {uploading ? '⏳ Uploading...' : '📄 Upload PDF'}
              <input ref={fileRef} type="file" accept=".pdf" onChange={handlePdfUpload}
                style={{ display: 'none' }} disabled={uploading} />
            </label>
          </div>
        </div>

        {/* Diagnostic Status Banner if interview active */}
        {!completed && (
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '0.75rem 1rem', backgroundColor: '#f0fdfa', border: '1px solid #ccfbf1',
            borderRadius: 12, marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem'
          }}>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0d9488' }}>
                📋 Question {stepNumber} of {totalSteps}
              </span>
              <div style={{
                width: 100, height: 8, backgroundColor: '#e2e8f0', borderRadius: 4, overflow: 'hidden'
              }}>
                <div style={{
                  width: `${(stepNumber / totalSteps) * 100}%`, height: '100%',
                  backgroundColor: '#0d9488', transition: 'width 0.3s'
                }} />
              </div>
            </div>

            {/* Risk Gauge Progress bar */}
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#334155' }}>
                Risk Progress:
              </span>
              <span style={{
                fontSize: '0.78rem', fontWeight: 700, color: getRiskColor(riskLevel),
                padding: '0.15rem 0.5rem', borderRadius: 6, backgroundColor: `${getRiskColor(riskLevel)}15`
              }}>
                {riskLevel}
              </span>
            </div>

            <button onClick={handleReset} style={{
              padding: '0.25rem 0.6rem', border: '1px solid #dc2626', color: '#dc2626',
              backgroundColor: 'transparent', borderRadius: 6, fontSize: '0.75rem',
              fontWeight: 700, cursor: 'pointer', transition: 'all 0.15s'
            }}>
              Reset
            </button>
          </div>
        )}

        {/* Display matched symptom tags */}
        {collectedSymptoms.length > 0 && (
          <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b' }}>Extracted Symptoms:</span>
            {collectedSymptoms.map((sym, i) => (
              <span key={i} style={{
                fontSize: '0.72rem', fontWeight: 700, padding: '0.1rem 0.45rem',
                borderRadius: 12, backgroundColor: '#e0f2fe', color: '#0369a1'
              }}>
                🔍 {sym}
              </span>
            ))}
          </div>
        )}

        {/* Consultation Viewer Area */}
        <div style={{
          flex: 1, overflowY: 'auto', backgroundColor: '#f8fafc',
          borderRadius: 12, padding: '1rem', border: '1px solid #e2e8f0',
          display: 'flex', flexDirection: 'column', gap: '1rem',
        }}>
          {completed ? (
            // Completed Assessment Layout
            lastResponse ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{
                  padding: '1rem', backgroundColor: '#fff', border: '1px solid #e2e8f0',
                  borderRadius: 10, boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                  lineHeight: 1.6, fontSize: '0.9rem', color: '#1e293b', whiteSpace: 'pre-wrap'
                }}>
                  {lastResponse}
                </div>
                
                {/* Reset Trigger to start again */}
                <div style={{ textAlign: 'center' }}>
                  <button onClick={handleReset} style={{
                    padding: '0.5rem 1.5rem', backgroundColor: '#0d9488', color: '#fff',
                    border: 'none', borderRadius: 8, fontWeight: 700, cursor: 'pointer',
                    boxShadow: '0 2px 4px rgba(13, 148, 136, 0.2)'
                  }}>
                    Start New Assessment
                  </button>
                </div>
              </div>
            ) : (
              // Empty initial state
              <div style={{
                flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
                justifyContent: 'center', textAlign: 'center', padding: '2rem'
              }}>
                <span style={{ fontSize: '3rem', marginBottom: '1rem' }}>🤰</span>
                <h4 style={{ color: '#1e293b', margin: '0 0 0.5rem', fontSize: '1.1rem', fontWeight: 700 }}>
                  Begin Clinical Screening
                </h4>
                <p style={{ color: '#64748b', fontSize: '0.85rem', maxWidth: 400, margin: '0 auto 1.5rem' }}>
                  Describe your symptoms (in English or Tamil) to launch the guided medical interview flow.
                </p>
              </div>
            )
          ) : (
            // Active Triage Interview Flow
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Main active question card */}
              <div style={{
                backgroundColor: '#fff', border: '1px solid #ccfbf1',
                borderRadius: 12, padding: '1.25rem', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
                borderLeft: '4px solid #0d9488'
              }}>
                <span style={{
                  fontSize: '0.72rem', fontWeight: 800, color: '#0d9488',
                  textTransform: 'uppercase', tracking: '0.05em', display: 'block', marginBottom: '0.35rem'
                }}>
                  Obstetric Clinician Question
                </span>
                <p style={{
                  margin: 0, fontSize: '0.98rem', fontWeight: 600, color: '#1e293b',
                  lineHeight: 1.5
                }}>
                  {currentQuestion.replace('To better understand your symptoms, could you please answer this follow-up question:\n\n💬 **', '').replace('**', '')}
                </p>
              </div>

              {/* Questionnaire History Log */}
              {Object.keys(answers).length > 0 && (
                <div style={{
                  display: 'flex', flexDirection: 'column', gap: '0.5rem',
                  backgroundColor: '#f1f5f9', padding: '0.75rem', borderRadius: 10
                }}>
                  <h4 style={{ margin: '0 0 0.35rem', color: '#475569', fontSize: '0.8rem', fontWeight: 700 }}>
                    Collected Answers (Allow editing):
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                    {Object.entries(answers).map(([q, val]) => (
                      <div key={q} style={{
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        padding: '0.45rem 0.65rem', backgroundColor: '#fff', borderRadius: 8,
                        border: '1px solid #cbd5e1', fontSize: '0.8rem'
                      }}>
                        <div style={{ flex: 1, paddingRight: '0.5rem' }}>
                          <span style={{ color: '#64748b', display: 'block', fontSize: '0.72rem' }}>Q: {q.replace('?', '')}?</span>
                          <span style={{ color: '#1e293b', fontWeight: 600 }}>A: {val}</span>
                        </div>
                        
                        {editingQuestion === q ? (
                          <div style={{ display: 'flex', gap: '0.25rem' }}>
                            <input
                              type="text"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              style={{
                                padding: '0.2rem 0.4rem', border: '1px solid #0d9488',
                                borderRadius: 4, fontSize: '0.8rem'
                              }}
                            />
                            <button onClick={handleSaveEdit} style={{
                              padding: '0.2rem 0.4rem', backgroundColor: '#0d9488',
                              color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer'
                            }}>
                              Save
                            </button>
                            <button onClick={() => setEditingQuestion(null)} style={{
                              padding: '0.2rem 0.4rem', backgroundColor: '#94a3b8',
                              color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer'
                            }}>
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button onClick={() => handleEditAnswer(q)} style={{
                            padding: '0.25rem 0.5rem', backgroundColor: '#f1f5f9',
                            color: '#0d9488', border: 'none', borderRadius: 4,
                            fontWeight: 700, cursor: 'pointer', fontSize: '0.75rem'
                          }}>
                            Edit
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {loading && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '1rem' }}>
              <span style={{ display: 'flex', gap: 4 }}>
                {[0, 1, 2].map((d) => (
                  <span key={d} style={{
                    width: 7, height: 7, borderRadius: '50%', backgroundColor: '#0d9488',
                    display: 'inline-block',
                    animation: `bounce 1s ease-in-out ${d * 0.15}s infinite`,
                  }} />
                ))}
              </span>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                completed ? handleStartInterview() : handleSubmitAnswer();
              }
            }}
            placeholder={
              completed
                ? (language === 'Tamil' ? 'உங்கள் கர்ப்ப கால அறிகுறிகளை இங்கே விவரிக்கவும்...' : 'Describe your pregnancy symptoms to begin clinical assessment...')
                : (language === 'Tamil' ? 'உங்கள் பதிலை இங்கே தட்டச்சு செய்யவும்...' : 'Type your answer to the active question...')
            }
            rows={2}
            style={{
              flex: 1, padding: '0.75rem 1rem', border: '1px solid #e2e8f0',
              borderRadius: 10, fontFamily: 'inherit', fontSize: '0.9rem',
              resize: 'none', outline: 'none',
              transition: 'border-color 0.2s',
              marginBottom: 0
            }}
            onFocus={(e) => e.target.style.borderColor = '#0d9488'}
            onBlur={(e) => e.target.style.borderColor = '#e2e8f0'}
          />
          <button
            onClick={completed ? handleStartInterview : handleSubmitAnswer}
            disabled={loading || !input.trim()}
            style={{
              padding: '0 1.5rem', backgroundColor: (loading || !input.trim()) ? '#94a3b8' : '#0d9488',
              color: '#fff', borderRadius: 10, border: 'none', fontWeight: 700,
              fontSize: '1.1rem', cursor: (loading || !input.trim()) ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s', minWidth: 54,
            }}
          >
            ➤
          </button>
        </div>

        <p style={{ textAlign: 'center', color: '#94a3b8', fontSize: '0.7rem', marginTop: '0.4rem' }}>
          Press Enter to submit response · Not a substitute for a licensed doctor's diagnosis
        </p>
      </div>

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
