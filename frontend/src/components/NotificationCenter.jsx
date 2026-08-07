import React, { useState } from 'react';

const NOTIFICATIONS = [
  { id: 1, type: 'info', icon: '📋', title: 'New case assigned', message: 'DISP-2026-00133 has been assigned to you.', time: '2 min ago', read: false },
  { id: 2, type: 'warning', icon: '⚠️', title: 'SLA approaching', message: 'DISP-2026-00127 will breach SLA in 4 hours.', time: '15 min ago', read: false },
  { id: 3, type: 'success', icon: '✅', title: 'Case resolved', message: 'DISP-2026-00132 financial resolution completed successfully.', time: '1 hour ago', read: false },
  { id: 4, type: 'info', icon: '💬', title: 'Communication sent', message: 'Final response email dispatched for DISP-2026-00125.', time: '2 hours ago', read: true },
  { id: 5, type: 'info', icon: '🔍', title: 'Manual review queued', message: 'DISP-2026-00126 requires human investigation.', time: '3 hours ago', read: true },
  { id: 6, type: 'warning', icon: '🔐', title: 'Security alert', message: 'New login detected from Windows / Chrome — Kuala Lumpur.', time: '5 hours ago', read: true },
  { id: 7, type: 'success', icon: '💰', title: 'Provisional credit applied', message: 'RM 8,500 credited for DISP-2026-00124.', time: '1 day ago', read: true },
  { id: 8, type: 'info', icon: '📊', title: 'Weekly digest ready', message: 'Your weekly case summary is available. 12 cases processed.', time: '2 days ago', read: true },
];

const TYPE_STYLES = {
  info: 'bg-blue-50 border-blue-100 text-blue-700',
  warning: 'bg-amber-50 border-amber-100 text-amber-700',
  success: 'bg-green-50 border-green-100 text-green-700',
};

export default function NotificationCenter() {
  const [filter, setFilter] = useState('all'); // all | unread | info | warning | success
  const [notifications, setNotifications] = useState(NOTIFICATIONS);
  const [expandedId, setExpandedId] = useState(null); // expanded notification ID or null

  const unreadCount = notifications.filter((n) => !n.read).length;

  const filtered = notifications.filter((n) => {
    if (filter === 'unread') return !n.read;
    if (filter === 'all') return true;
    return n.type === filter;
  });

  const handleMarkRead = (id) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
  };

  const handleMarkAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const handleDismiss = (id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    setExpandedId((cur) => (cur === id ? null : cur));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Notifications</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}
            {' · '}
            {notifications.length} total
          </p>
        </div>
        {unreadCount > 0 && (
          <button onClick={handleMarkAllRead} className="text-xs text-blue-600 hover:text-blue-700 font-semibold">
            Mark all as read
          </button>
        )}
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2">
        {[
          { id: 'all', label: 'All', count: notifications.length },
          { id: 'unread', label: 'Unread', count: unreadCount },
          { id: 'info', label: 'Info', count: notifications.filter((n) => n.type === 'info').length },
          { id: 'warning', label: 'Warnings', count: notifications.filter((n) => n.type === 'warning').length },
          { id: 'success', label: 'Resolved', count: notifications.filter((n) => n.type === 'success').length },
        ].map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${
              filter === f.id
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-white text-slate-600 border border-slate-200 hover:border-slate-300 hover:bg-slate-50'
            }`}
          >
            {f.label}
            <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${
              filter === f.id ? 'bg-blue-500/30 text-blue-100' : 'bg-slate-100 text-slate-500'
            }`}>
              {f.count}
            </span>
          </button>
        ))}
      </div>

      {/* Notification list */}
      <div className="space-y-2">
        {filtered.map((notif) => (
          <NotificationItem
            key={notif.id}
            notif={notif}
            isExpanded={expandedId === notif.id}
            onExpand={() => setExpandedId(expandedId === notif.id ? null : notif.id)}
            onMarkRead={() => handleMarkRead(notif.id)}
            onDismiss={() => handleDismiss(notif.id)}
          />
        ))}
        {filtered.length === 0 && (
          <div className="text-center py-16">
            <p className="text-3xl mb-2">✨</p>
            <p className="text-sm font-medium text-slate-600">No notifications</p>
            <p className="text-xs text-slate-400 mt-0.5">You're all caught up.</p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Notification card ─── */

function NotificationItem({ notif, isExpanded, onExpand, onMarkRead, onDismiss }) {
  const badgeClass = TYPE_STYLES[notif.type] || TYPE_STYLES.info;

  return (
    <div
      className={`rounded-xl border transition-all duration-200 ${
        notif.read
          ? 'bg-white border-slate-100'
          : 'bg-white border-blue-200 shadow-soft'
      } ${isExpanded ? 'ring-1 ring-blue-500/10' : 'hover:border-slate-200 hover:shadow-card'}`}
    >
      <button onClick={onExpand} className="w-full flex items-start gap-3 p-4 text-left">
        {/* Unread indicator */}
        {!notif.read && <div className="w-2 h-2 rounded-full bg-blue-500 shrink-0 mt-2" />}

        <div
          role="img"
          aria-label={notif.type}
          className="w-9 h-9 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center text-lg shrink-0"
        >
          {notif.icon}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-slate-800">{notif.title}</span>
            <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-medium border ${badgeClass}`}>
              {notif.type}
            </span>
            {!notif.read && <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 font-semibold">NEW</span>}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">{notif.message}</p>
          <p className="text-[11px] text-slate-400 mt-1">{notif.time}</p>
        </div>

        {/* Expand chevron */}
        <svg
          className={`w-4 h-4 text-slate-400 shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="border-t border-slate-100 px-4 py-3 space-y-3">
          {/* Detail content */}
          <div className="bg-slate-50 border border-slate-100 rounded-xl p-3 space-y-1.5">
            <p className="text-xs text-slate-500 font-medium">Details</p>
            <div className="flex items-center gap-4 text-xs text-slate-600">
              <span><span className="text-slate-400">ID:</span> <span className="font-mono font-medium">#{notif.id}</span></span>
              <span><span className="text-slate-400">Time:</span> <span className="font-mono">{notif.time}</span></span>
              <span><span className="text-slate-400">Type:</span> <span className="capitalize">{notif.type}</span></span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {!notif.read && (
              <button onClick={onMarkRead} className="px-3 py-1.5 text-xs font-semibold text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                Mark as read
              </button>
            )}
            <button onClick={onDismiss} className="px-3 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-50 rounded-lg transition-colors">
              Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
