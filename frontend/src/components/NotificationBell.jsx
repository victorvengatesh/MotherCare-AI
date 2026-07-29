import React, { useState, useEffect, useRef } from 'react';
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

export default function NotificationBell() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 60_000); // poll every minute
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  async function fetchNotifications() {
    try {
      const res = await listNotifications();
      setNotifications(res.notifications || []);
      setUnreadCount(res.unread_count || 0);
    } catch {
      // silent fail — notification bell is non-critical
    }
  }

  async function handleMarkRead(notifId) {
    try {
      await markNotificationRead(notifId);
      setNotifications(prev =>
        prev.map(n => n.id === notifId ? { ...n, is_read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch {
      // silent fail
    }
  }

  async function handleMarkAllRead() {
    setLoading(true);
    try {
      await markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // silent fail
    } finally {
      setLoading(false);
    }
  }

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

  return (
    <div ref={ref} style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={bellStyle}
        title="Notifications"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
      >
        🔔
        {unreadCount > 0 && (
          <span style={badgeStyle}>{unreadCount > 99 ? '99+' : unreadCount}</span>
        )}
      </button>

      {open && (
        <div style={dropdownStyle}>
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
                    {TYPE_ICONS[n.type] || '🔔'}
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
