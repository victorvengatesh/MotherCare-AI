/**
 * NotificationBell — Phase 4 WebSocket upgrade
 *
 * Real-time notifications via WebSocket with HTTP polling fallback.
 * - Connects to ws://host/ws/notifications?token=<JWT>
 * - Auto-reconnects with exponential backoff (max 5 attempts)
 * - Falls back to 60s HTTP polling if WebSocket fails
 * - Heartbeat pong keeps connection alive through proxies
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { listNotifications, markNotificationRead, markAllNotificationsRead } from '../services/api';

const TYPE_ICONS = {
  instruction:                '📋',
  appointment_confirmed:      '✅',
  appointment_rescheduled:    '🔄',
  appointment_cancelled:      '❌',
  appointment_reminder:       '⏰',
  reminder:                   '💊',
  alert_review:               '⚠️',
  follow_up:                  '🩺',
};

const rawWsUrl = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000';
const WS_BASE_URL = rawWsUrl.endsWith('/') ? rawWsUrl.slice(0, -1) : rawWsUrl;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_BASE_DELAY_MS = 2000;

export default function NotificationBell() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount]     = useState(0);
  const [open, setOpen]                   = useState(false);
  const [loading, setLoading]             = useState(false);
  const [wsStatus, setWsStatus]           = useState('connecting'); // connecting | connected | polling | error

  const ref            = useRef(null);
  const wsRef          = useRef(null);
  const reconnectCount = useRef(0);
  const reconnectTimer = useRef(null);

  // ── Fetch notifications from HTTP API ──────────────────────────────────────
  const fetchNotifications = useCallback(async () => {
    try {
      const res = await listNotifications();
      setNotifications(res.notifications || []);
      setUnreadCount(res.unread_count ?? 0);
    } catch {
      // silent — bell is non-critical
    }
  }, []);

  // ── WebSocket connection ───────────────────────────────────────────────────
  const connectWebSocket = useCallback(() => {
    const token = localStorage.getItem('mc_token');
    if (!token) {
      setWsStatus('polling');
      return;
    }

    try {
      const url = `${WS_BASE_URL}/ws/notifications?token=${encodeURIComponent(token)}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsStatus('connected');
        reconnectCount.current = 0;
        // Initial load when WS connects
        fetchNotifications();
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === 'ping') {
            // Server heartbeat — keep alive (no pong needed for browser WebSocket)
            return;
          }

          if (msg.type === 'notification' && msg.data) {
            const notif = msg.data;
            // Prepend new notification and bump unread count
            setNotifications(prev => [notif, ...prev].slice(0, 50));
            setUnreadCount(prev => prev + 1);
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onerror = () => {
        setWsStatus('error');
      };

      ws.onclose = () => {
        wsRef.current = null;

        if (reconnectCount.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = RECONNECT_BASE_DELAY_MS * Math.pow(2, reconnectCount.current);
          reconnectCount.current += 1;
          setWsStatus('connecting');
          reconnectTimer.current = setTimeout(connectWebSocket, delay);
        } else {
          // Give up on WS — fall back to polling
          setWsStatus('polling');
        }
      };
    } catch {
      setWsStatus('polling');
    }
  }, [fetchNotifications]);

  // ── Lifecycle ──────────────────────────────────────────────────────────────
  useEffect(() => {
    fetchNotifications();       // immediate first load
    connectWebSocket();         // start WebSocket

    return () => {
      // Cleanup on unmount
      clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on intentional close
        wsRef.current.close();
      }
    };
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  // ── Polling fallback when WS is unavailable ────────────────────────────────
  useEffect(() => {
    if (wsStatus !== 'polling') return;
    const interval = setInterval(fetchNotifications, 60_000);
    return () => clearInterval(interval);
  }, [wsStatus, fetchNotifications]);

  // ── Close dropdown on outside click ───────────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // ── Mark read handlers ─────────────────────────────────────────────────────
  async function handleMarkRead(notifId) {
    try {
      await markNotificationRead(notifId);
      setNotifications(prev => prev.map(n => n.id === notifId ? { ...n, is_read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch {
      // silent
    }
  }

  async function handleMarkAllRead() {
    setLoading(true);
    try {
      await markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }

  // ── Styles ─────────────────────────────────────────────────────────────────
  const bellStyle = {
    position: 'relative',
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    fontSize: '1.35rem',
    padding: '0.4rem',
    borderRadius: '8px',
    transition: 'background 0.15s',
    display: 'flex',
    alignItems: 'center',
  };

  const badgeStyle = {
    position: 'absolute',
    top: '0px',
    right: '0px',
    background: '#ef4444',
    color: '#fff',
    fontSize: '0.6rem',
    fontWeight: 700,
    borderRadius: '9999px',
    minWidth: '16px',
    height: '16px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '0 3px',
    lineHeight: 1,
  };

  const dropdownStyle = {
    position: 'absolute',
    top: 'calc(100% + 8px)',
    right: 0,
    width: '340px',
    maxHeight: '420px',
    overflowY: 'auto',
    background: '#fff',
    borderRadius: '12px',
    boxShadow: '0 8px 30px rgba(0,0,0,0.14)',
    border: '1px solid #e2e8f0',
    zIndex: 1000,
  };

  // WS status indicator dot
  const wsIndicatorColor = {
    connected:  '#22c55e',
    connecting: '#f59e0b',
    polling:    '#94a3b8',
    error:      '#ef4444',
  }[wsStatus] || '#94a3b8';

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div ref={ref} style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={bellStyle}
        title={`Notifications (${wsStatus === 'connected' ? 'live' : 'polling'})`}
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
      >
        🔔
        {unreadCount > 0 && (
          <span style={badgeStyle}>{unreadCount > 99 ? '99+' : unreadCount}</span>
        )}
        {/* WebSocket status dot */}
        <span style={{
          position: 'absolute', bottom: '2px', right: '2px',
          width: '7px', height: '7px', borderRadius: '50%',
          background: wsIndicatorColor,
          border: '1.5px solid #fff',
        }} title={wsStatus} />
      </button>

      {open && (
        <div style={dropdownStyle}>
          {/* Header */}
          <div style={{
            padding: '0.75rem 1rem',
            borderBottom: '1px solid #f1f5f9',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span style={{ fontWeight: 700, color: '#1e293b', fontSize: '0.9rem' }}>
              Notifications {unreadCount > 0 && <span style={{ color: '#ef4444' }}>({unreadCount})</span>}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ fontSize: '0.68rem', color: wsIndicatorColor, fontWeight: 600 }}>
                {wsStatus === 'connected' ? '● Live' : wsStatus === 'polling' ? '○ Polling' : '◌ Connecting'}
              </span>
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  disabled={loading}
                  style={{
                    background: 'none', border: 'none', color: '#0ea5e9',
                    fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer', padding: 0,
                    opacity: loading ? 0.6 : 1,
                  }}
                >
                  Mark all read
                </button>
              )}
            </div>
          </div>

          {/* Notification list */}
          {notifications.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8', fontSize: '0.85rem' }}>
              🔔 No notifications
            </div>
          ) : (
            notifications.map(n => (
              <div
                key={n.id}
                onClick={() => !n.is_read && handleMarkRead(n.id)}
                style={{
                  padding: '0.75rem 1rem',
                  borderBottom: '1px solid #f8fafc',
                  cursor: n.is_read ? 'default' : 'pointer',
                  background: n.is_read ? '#fff' : '#f0f9ff',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => { if (!n.is_read) e.currentTarget.style.background = '#e0f2fe'; }}
                onMouseLeave={e => { if (!n.is_read) e.currentTarget.style.background = '#f0f9ff'; }}
              >
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
                  <span style={{ fontSize: '1rem', marginTop: '0.05rem' }}>
                    {TYPE_ICONS[n.notif_type] || TYPE_ICONS[n.type] || '🔔'}
                  </span>
                  <div style={{ flex: 1 }}>
                    <p style={{ margin: 0, fontSize: '0.83rem', color: '#1e293b', lineHeight: 1.4 }}>
                      {n.message}
                    </p>
                    <p style={{ margin: '0.2rem 0 0', fontSize: '0.72rem', color: '#94a3b8' }}>
                      {new Date(n.created_at).toLocaleString('en-GB', {
                        day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
                      })}
                    </p>
                  </div>
                  {!n.is_read && (
                    <span style={{
                      width: '8px', height: '8px', background: '#3b82f6',
                      borderRadius: '50%', flexShrink: 0, marginTop: '0.35rem',
                    }} />
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
