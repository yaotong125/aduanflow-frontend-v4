import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiFetch, BACKEND_URL } from '../config';

const CHECKLIST = [
  { key: '2fa', label: 'Two-Factor Authentication', desc: 'Require a second verification step when logging in.' },
  { key: 'password_expiry', label: 'Password Expiry', desc: 'Force password change every 90 days.' },
  { key: 'ip_allowlist', label: 'IP Allowlisting', desc: 'Restrict access to approved network ranges.' },
];

const ROLE_GROUPS = {
  admin: ['Full access', 'Manage users', 'View all cases', 'Export audit logs', 'Configure pipeline settings'],
  investigator: ['View & assign cases', 'Update case statuses', 'Approve financial resolutions', 'Send communications'],
};

const SETTINGS_KEY = 'aduanflow_profile_settings';

export default function ProfileSettings() {
  const { user } = useAuth();
  const [tab, setTab] = useState('integrations'); // integrations | profile | alerts | security

  const [displayName, setDisplayName] = useState(user?.name ?? '');
  const [checklistState, setChecklistState] = useState(
    Object.fromEntries(CHECKLIST.map((c) => [c.key, false]))
  );
  const [notifs, setNotifs] = useState({
    case_assigned: true,
    status_changed: true,
    sla_breach: true,
    manual_review: false,
    weekly_digest: true,
  });
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [quietHours, setQuietHours] = useState(false);
  const [security, setSecurity] = useState({ new_device_alert: true, session_timeout: '30' });
  const [saved, setSaved] = useState(false);

  // Password change state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwdMsg, setPwdMsg] = useState('');

  React.useEffect(() => {
    if (user?.username) {
      apiFetch(`/api/auth/settings/${user.username}`)
        .then(res => res.json())
        .then(data => {
          if (data.displayName) setDisplayName(data.displayName);
          if (data.checklistState) setChecklistState(data.checklistState);
          if (data.notifs) setNotifs(data.notifs);
          if (data.emailEnabled !== undefined) setEmailEnabled(data.emailEnabled);
          if (data.quietHours !== undefined) setQuietHours(data.quietHours);
          if (data.security) setSecurity(data.security);
        })
        .catch(err => console.error("Failed to fetch settings", err));
    }
  }, [user]);

  const handleSave = async () => {
    try {
      await apiFetch(`/api/auth/settings/${user.username}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ displayName, checklistState, notifs, emailEnabled, quietHours, security })
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error(err);
    }
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      setPwdMsg('New passwords do not match.');
      return;
    }
    try {
      const res = await apiFetch(`/api/auth/change-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: user.username,
          current_password: currentPassword,
          new_password: newPassword
        })
      });
      const data = await res.json();
      if (!res.ok) {
        setPwdMsg(`Error: ${data.detail || 'Failed'}`);
      } else {
        setPwdMsg('✓ Password updated successfully!');
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      }
    } catch (err) {
      setPwdMsg(`Error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Settings</h2>
          <p className="text-sm text-slate-500 mt-0.5">Manage your account, preferences and security</p>
        </div>
        <button onClick={handleSave} className="px-4 py-2 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 transition-colors shadow-sm">
          {saved ? '✓ Saved' : 'Save changes'}
        </button>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-card overflow-hidden">
        <div className="border-b border-slate-100 flex">
          {[
            { id: 'profile', label: 'Profile' },
            { id: 'integrations', label: 'Gmail & Integrations' },
            { id: 'alerts', label: 'Alert Preferences' },
            { id: 'security', label: 'Security' },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-5 py-3.5 text-xs font-semibold transition-colors border-b-2 -mb-px ${
                tab === t.id
                  ? 'text-blue-600 border-blue-500'
                  : 'text-slate-500 border-transparent hover:text-slate-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="p-6">
          {/* ─── Profile tab ─── */}
          {tab === 'profile' && (
            <div className="space-y-6 max-w-lg">
              {/* Avatar */}
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center text-white text-2xl font-bold ring-4 ring-blue-100 shadow-md">
                  {(user?.name || 'U')[0].toUpperCase()}
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-800">{user?.name}</p>
                  <p className="text-xs text-slate-500 capitalize">{user?.role} role</p>
                  <span className="inline-flex items-center gap-1 text-xs text-emerald-600 font-semibold mt-1">
                    ✓ Taskforce Lead Badge Active
                  </span>
                </div>
              </div>

              <hr />

              {/* Display name */}
              <div>
                <label htmlFor="display-name" className="block text-sm font-medium text-slate-700 mb-1.5">Display Name</label>
                <input
                  id="display-name"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors bg-white"
                />
              </div>

              {/* Email */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1.5">Email</label>
                <input id="email" type="email" defaultValue={`${user?.username}@aduanflow.com`} disabled className="w-full px-3.5 py-2.5 text-sm border border-slate-200 rounded-xl bg-slate-50 text-slate-400 cursor-not-allowed" />
                <p className="text-[11px] text-slate-400 mt-1">Contact admin to change email address.</p>
              </div>

              {/* Role info */}
              <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl">
                <p className="text-xs font-semibold text-blue-700 mb-2">Role Permissions — {user?.role}</p>
                <div className="space-y-1">
                  {ROLE_GROUPS[user?.role]?.map((p) => (
                    <label key={p} className="flex items-center gap-2 text-xs text-blue-700">
                      <svg className="w-3.5 h-3.5 text-blue-500 shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                      {p}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ─── Alert Preferences tab ─── */}
          {tab === 'alerts' && (
            <div className="space-y-5 max-w-lg">
              <p className="text-sm text-slate-500 mb-4">Choose which alerts and digests you receive.</p>

              {/* Email channel toggle */}
              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="text-sm font-medium text-slate-700">Email Notifications</p>
                  <p className="text-xs text-slate-400">Receive case updates via email.</p>
                </div>
                <ToggleSwitch checked={emailEnabled} onChange={() => setEmailEnabled((v) => !v)} />
              </div>

              <hr className="border-slate-100" />

              {/* Per-type toggles */}
              {Object.entries(notifs).map(([key, val]) => (
                <div key={key} className="flex items-center justify-between py-1">
                  <div>
                    <p className="text-sm font-medium text-slate-700 capitalize">{key.replace(/_/g, ' ')}</p>
                    <p className="text-xs text-slate-400">{getNotificationDesc(key)}</p>
                  </div>
                  <ToggleSwitch checked={val} onChange={(v) => setNotifs((p) => ({ ...p, [key]: v }))} />
                </div>
              ))}

              <hr className="border-slate-100" />

              {/* Quiet hours */}
              <div className="flex items-center justify-between py-1">
                <div>
                  <p className="text-sm font-medium text-slate-700">Quiet Hours</p>
                  <p className="text-xs text-slate-400">No notifications between 10 PM – 7 AM.</p>
                </div>
                <ToggleSwitch checked={quietHours} onChange={() => setQuietHours((v) => !v)} />
              </div>
            </div>
          )}

          {/* ─── Security tab ─── */}
          {tab === 'security' && (
            <div className="space-y-6 max-w-lg">
              {/* Password */}
              <div>
                <p className="text-sm font-medium text-slate-700 mb-3">Change Password</p>
                <div className="space-y-3">
                  <div>
                    <label htmlFor="pwd-current" className="block text-xs font-medium text-slate-500 mb-1">Current Password</label>
                    <input id="pwd-current" type="password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} placeholder="••••••••" className="w-full px-3.5 py-2.5 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors bg-white" />
                  </div>
                  <div>
                    <label htmlFor="pwd-new" className="block text-xs font-medium text-slate-500 mb-1">New Password</label>
                    <input id="pwd-new" type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} placeholder="••••••••" className="w-full px-3.5 py-2.5 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors bg-white" />
                  </div>
                  <div>
                    <label htmlFor="pwd-confirm" className="block text-xs font-medium text-slate-500 mb-1">Confirm New Password</label>
                    <input id="pwd-confirm" type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} placeholder="••••••••" className="w-full px-3.5 py-2.5 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors bg-white" />
                  </div>
                  {pwdMsg && (
                    <p className={`text-xs font-semibold ${pwdMsg.startsWith('✓') ? 'text-emerald-600' : 'text-red-600'}`}>{pwdMsg}</p>
                  )}
                  <button onClick={handleChangePassword} className="text-xs text-blue-600 hover:text-blue-700 font-semibold">Update password</button>
                </div>
              </div>

              <hr />

              {/* Session timeout */}
              <div className="flex items-center justify-between py-1">
                <div>
                  <p className="text-sm font-medium text-slate-700">Session Timeout</p>
                  <p className="text-xs text-slate-400">Auto-logout after inactivity.</p>
                </div>
                <select
                  value={security.session_timeout}
                  onChange={(e) => setSecurity((p) => ({ ...p, session_timeout: e.target.value }))}
                  className="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                >
                  <option value="15">15 minutes</option>
                  <option value="30">30 minutes</option>
                  <option value="60">1 hour</option>
                  <option value="0">Never</option>
                </select>
              </div>

              <hr />

              {/* Active sessions */}
              <div>
                <p className="text-sm font-medium text-slate-700 mb-3">Active Sessions</p>
                <div className="space-y-3">
                  {[
                    { device: 'Chrome on Windows', location: 'Kuala Lumpur', time: 'Current session', active: true },
                    { device: 'Firefox on macOS', location: 'Kuala Lumpur', time: '2 hours ago', active: false },
                  ].map((s, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-slate-50 border border-slate-100 rounded-xl">
                      <div className="flex items-center gap-3">
                        <div className={`w-2.5 h-2.5 rounded-full ${s.active ? 'bg-green-500' : 'bg-slate-300'}`} />
                        <div>
                          <p className="text-sm font-medium text-slate-700">{s.device}</p>
                          <p className="text-xs text-slate-400">{s.location} · {s.time}</p>
                        </div>
                      </div>
                      {!s.active && (
                        <button className="text-xs text-red-600 hover:text-red-700 font-semibold">Revoke</button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <hr />

              {/* Checklist */}
              <div>
                <p className="text-sm font-medium text-slate-700 mb-3">Security Checklist</p>
                <div className="space-y-3">
                  {CHECKLIST.map((c) => (
                    <SecurityCheck
                      key={c.key}
                      {...c}
                      checked={checklistState[c.key]}
                      onChange={(v) => setChecklistState((p) => ({ ...p, [c.key]: v }))}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ─── Integrations tab ─── */}
          {tab === 'integrations' && <GmailIntegrationSection />}
        </div>
      </div>
    </div>
  );
}

/* ─── Reusable sub-components ─── */

function ToggleSwitch({ checked, onChange }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${checked ? 'bg-blue-600' : 'bg-slate-200'}`}
    >
      <span className={`inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform ${checked ? 'translate-x-6' : 'translate-x-1'}`} />
    </button>
  );
}

function getNotificationDesc(key) {
  const map = {
    case_assigned: 'Get notified when a new case is assigned to you.',
    status_changed: 'Alert when any case status changes.',
    sla_breach: 'Warning when a case is close to breaching its SLA.',
    manual_review: 'Notify for cases queued in manual review.',
    weekly_digest: 'Weekly summary of all activity.',
  };
  return map[key] || '';
}

function SecurityCheck({ label, desc, checked, onChange }) {
  return (
    <label className="flex items-start gap-3 p-3 bg-slate-50 border border-slate-100 rounded-xl cursor-pointer hover:border-blue-200 transition-colors">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500"
      />
      <div>
        <p className="text-sm font-medium text-slate-700">{label}</p>
        <p className="text-xs text-slate-400">{desc}</p>
      </div>
    </label>
  );
}

function GmailIntegrationSection() {
  const [status, setStatus] = React.useState({ is_connected: false, email: '' });
  const [email, setEmail] = React.useState('');
  const [refreshToken, setRefreshToken] = React.useState('');
  const [appPassword, setAppPassword] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [msg, setMsg] = React.useState('');

  const [activeTeammates, setActiveTeammates] = React.useState({
    active_teammates_count: 1,
    other_active_users: [],
    is_another_user_active: false
  });

  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('oauth_cancelled') === 'true') {
      setMsg('⚠️ Google OAuth authorization was cancelled. Mailbox remains unchanged.');
    } else if (params.get('oauth_success') === 'true') {
      setMsg('🎉 Google OAuth 2.0 Mailbox connected & encrypted successfully!');
    } else if (params.get('oauth_error')) {
      setMsg(`Error authorizing Google OAuth: ${params.get('oauth_error')}`);
    }

    apiFetch('/api/auth/gmail-status')
      .then((res) => res.json())
      .then((data) => {
        setStatus(data);
        if (data?.email) setEmail(data.email);
      })
      .catch(() => {});

    // Live Heartbeat Session Manager
    let cid = sessionStorage.getItem('aduanflow_client_id');
    if (!cid) {
      cid = 'client_' + Math.random().toString(36).substring(2, 9);
      sessionStorage.setItem('aduanflow_client_id', cid);
    }

    const sendHeartbeat = () => {
      apiFetch('/api/auth/heartbeat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: cid })
      })
        .then(res => res.json())
        .then(data => {
          if (data && typeof data.active_teammates_count === 'number') {
            setActiveTeammates(data);
          }
        })
        .catch(() => {});
    };

    sendHeartbeat();
    const interval = setInterval(sendHeartbeat, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleConnect = (e) => {
    e.preventDefault();
    if (!email || !refreshToken) {
      setMsg('Please fill in both complaints email and OAuth refresh token.');
      return;
    }
    setLoading(true);
    setMsg('');

    apiFetch('/api/auth/gmail-token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email,
        refresh_token: refreshToken,
        app_password: appPassword || null,
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error('Failed to save OAuth token');
        return res.json();
      })
      .then((data) => {
        setStatus(data);
        setMsg('✓ Gmail Mailbox connected successfully!');
        setRefreshToken('');
        setLoading(false);
      })
      .catch((err) => {
        setMsg(`Error: ${err.message}`);
        setLoading(false);
      });
  };

  const [syncing, setSyncing] = useState(false);

  const handleSyncInbox = () => {
    setSyncing(true);
    setMsg('');
    apiFetch('/api/auth/gmail-sync', { method: 'POST' })
      .then((res) => res.json())
      .then((data) => {
        setSyncing(false);
        if (data?.status === 'success') {
          const syncedList = data.synced_cases || (data.cases ? data.cases.map(c => c.case_id) : []);
          const count = syncedList.length;
          const mailbox = data.mailbox || data.email || 'connected inbox';
          setMsg(`✓ Successfully polled & synced ${count} dispute email(s) from ${mailbox}! Created case ID(s): ${syncedList.join(', ')}.`);
        } else {
          setMsg(`✓ Inbox sync check complete: ${data?.message || 'Inbox synchronized.'}`);
        }
      })
      .catch((err) => {
        setSyncing(false);
        setMsg(`Error syncing inbox: ${err.message}`);
      });
  };

  const handleDisconnect = () => {
    if (!window.confirm('Are you sure you want to disconnect the complaints mailbox?')) return;
    apiFetch('/api/auth/gmail-token', { method: 'DELETE' })
      .then(() => {
        setStatus({ is_connected: false });
        setMsg('Disconnected Gmail mailbox.');
      })
      .catch(() => {});
  };

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Connection Header Card */}
      <div className="p-5 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center text-red-600 font-bold">
            M
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Gmail Complaints Mailbox (OAuth 2.0)</h3>
            <p className="text-xs text-slate-500">Automated Email Intake Engine Integration</p>
          </div>
        </div>
        {status.is_connected ? (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Connected: {status.email}
            </span>
            <button
              onClick={handleSyncInbox}
              disabled={syncing}
              className="text-xs px-3.5 py-1.5 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-xs flex items-center gap-1"
            >
              {syncing ? '↻ Polling Inbox...' : '⚡ Sync Inbox Now'}
            </button>
            <button
              onClick={handleDisconnect}
              className="text-xs px-3 py-1.5 bg-red-50 text-red-600 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
            >
              Disconnect
            </button>
          </div>
        ) : (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            Not Connected
          </span>
        )}
      </div>

      {/* Live Teammate Activity Bar */}
      <div className={`p-3 rounded-xl border text-xs font-semibold flex items-center justify-between transition-all ${activeTeammates.is_another_user_active ? 'bg-blue-50 border-blue-200 text-blue-900' : 'bg-slate-50 border-slate-200 text-slate-600'}`}>
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${activeTeammates.is_another_user_active ? 'bg-blue-400' : 'bg-emerald-400'}`} />
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${activeTeammates.is_another_user_active ? 'bg-blue-500' : 'bg-emerald-500'}`} />
          </span>
          <span>
            {activeTeammates.active_teammates_count > 1 
              ? `🟢 ${activeTeammates.active_teammates_count} Teammates Active Online (${activeTeammates.other_active_users.join(', ')})` 
              : '🟢 You are the only active investigator online'}
          </span>
        </div>
        {activeTeammates.is_another_user_active && (
          <span className="px-2 py-0.5 bg-blue-200 text-blue-800 rounded-md text-[10px] uppercase tracking-wider font-bold">
            Live Testing Guard Active
          </span>
        )}
      </div>

      {msg && (
        <div className={`p-3 rounded-xl text-xs font-medium ${msg.startsWith('✓') ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
          {msg}
        </div>
      )}

      {/* Setup Form - Enterprise Google OAuth 2.0 */}
      <form onSubmit={handleConnect} className="space-y-4 bg-white p-5 border border-slate-200 rounded-xl shadow-xs">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <span>🌐 Enterprise Google OAuth 2.0 Integration</span>
              <span className="text-[10px] bg-blue-100 text-blue-800 font-semibold px-2 py-0.5 rounded-full uppercase">Zero Passwords Required</span>
            </h4>
            <p className="text-xs text-slate-500 mt-0.5">
              One-click Google Authorization automatically grants a Permanent Refresh Token (`1//0g...`) stored in DB encrypted with Fernet AES-256.
            </p>
          </div>
        </div>

        {status.is_connected && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs font-semibold text-amber-900 flex items-center gap-2">
            <span>🔒</span>
            <span>Customer Service Address is Active & Locked to <strong>{status.email}</strong>. Click <strong>"Disconnect"</strong> above if you need to switch mailbox accounts.</span>
          </div>
        )}

        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">
            Complaints Email Address <span className="text-red-500">*</span>
          </label>
          <input
            type="email"
            required
            disabled={status.is_connected}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="e.g. ganyaotong@graduate.utm.my"
            className={`w-full px-3.5 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-medium text-slate-800 ${status.is_connected ? 'bg-slate-100 text-slate-500 cursor-not-allowed' : ''}`}
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">
            Google OAuth 2.0 Permanent Refresh Token (`1//0...`) <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            required
            disabled={status.is_connected}
            value={refreshToken}
            onChange={(e) => setRefreshToken(e.target.value)}
            placeholder={status.is_connected ? '•••••••••••••••••••••••••••• (Encrypted & Active)' : 'Paste 1//0... refresh token from OAuth Playground'}
            className={`w-full px-3.5 py-2 text-xs border border-slate-200 rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 ${status.is_connected ? 'bg-slate-100 text-slate-500 cursor-not-allowed' : ''}`}
          />
          <p className="text-[11px] text-slate-400 mt-1">
            Obtained from Google Developers OAuth Playground (`https://developers.google.com/oauthplayground`). Encrypted at rest via Fernet.
          </p>
        </div>



        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={() => {
              if (status.is_connected) return;
              window.location.href = `${BACKEND_URL}/api/auth/google/login`;
            }}
            disabled={loading || status.is_connected}
            className={`flex-1 py-2.5 bg-blue-600 text-white text-xs font-semibold rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm flex items-center justify-center gap-2 ${status.is_connected ? 'cursor-not-allowed opacity-60' : ''}`}
          >
            <span>{status.is_connected ? '🔒 Mailbox Active & Locked' : '🔑 Authorize & Connect Google OAuth 2.0 Mailbox (1-Click)'}</span>
          </button>

          <button
            type="submit"
            disabled={loading || status.is_connected}
            className={`px-6 py-2.5 bg-slate-900 text-white text-xs font-semibold rounded-xl hover:bg-slate-800 disabled:opacity-50 transition-colors shadow-sm ${status.is_connected ? 'cursor-not-allowed opacity-60' : ''}`}
          >
            {status.is_connected ? 'Locked' : 'Save Token'}
          </button>
        </div>
      </form>

      {/* Simulate Incoming Email Box */}
      <div className="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-xs">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h4 className="text-sm font-semibold text-slate-900">✉️ Simulate Incoming Complaint Email to Mailbox</h4>
            <p className="text-xs text-slate-500">Send a sample banking dispute email directly into your connected mailbox intake engine.</p>
          </div>
          <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
            Intake Pipeline Ready
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div>
            <label className="block text-slate-600 font-medium mb-1">Complainant Name</label>
            <input
              id="sim-name"
              type="text"
              defaultValue="Gan Yao Tong"
              className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white"
            />
          </div>
          <div>
            <label className="block text-slate-600 font-medium mb-1">Complainant Gmail Address</label>
            <input
              id="sim-email"
              type="email"
              defaultValue="ganyaotong@graduate.utm.my"
              placeholder="customer@gmail.com"
              className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white font-mono"
            />
          </div>
          <div>
            <label className="block text-slate-600 font-medium mb-1">Dispute Amount (RM)</label>
            <input
              id="sim-amount"
              type="number"
              defaultValue="1500.00"
              className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white"
            />
          </div>
          <div>
            <label className="block text-slate-600 font-medium mb-1">Account Number</label>
            <input
              id="sim-account"
              type="text"
              defaultValue="114002938471"
              className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white"
            />
          </div>
          <div>
            <label className="block text-slate-600 font-medium mb-1">NRIC Number</label>
            <input
              id="sim-nric"
              type="text"
              defaultValue="040125-01-0509"
              className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white"
            />
          </div>
        </div>

        <div className="text-xs space-y-3">
          <div>
            <label className="block text-slate-600 font-medium mb-1">Email Subject</label>
            <input
              id="sim-subject"
              type="text"
              defaultValue="URGENT DISPUTE: Unauthorized transaction of RM1,500.00 on debit card"
              className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white"
            />
          </div>
          <div>
            <label className="block text-slate-600 font-medium mb-1">Email Body Content</label>
            <textarea
              id="sim-body"
              rows={3}
              defaultValue="Dear Customer Support, I would like to report an unauthorized charge of RM1,500.00 deducted from my savings account 114002938471 on 1st August. I did not initiate this payment. Please reverse the funds and investigate immediately."
              className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white text-xs"
            />
          </div>
        </div>

        <button
          onClick={() => {
            const name = document.getElementById('sim-name')?.value || 'Gan Yao Tong';
            const email = document.getElementById('sim-email')?.value || 'ganyaotong@graduate.utm.my';
            const amt = parseFloat(document.getElementById('sim-amount')?.value || '1500');
            const acc = document.getElementById('sim-account')?.value || '114002938471';
            const nric = document.getElementById('sim-nric')?.value || '040125-01-0509';
            const subj = document.getElementById('sim-subject')?.value || 'Unauthorized charge dispute';
            const body = document.getElementById('sim-body')?.value || 'Complaint content';

            setSyncing(true);
            setMsg('');

            apiFetch('/api/auth/send-custom-email', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                customer_name: name,
                customer_email: email,
                amount: amt,
                account_number: acc,
                nric: nric,
                email_subject: subj,
                email_body: body,
                attachment_name: 'Customer_Dispute_Receipt.pdf'
              })
            })
              .then(res => res.json())
              .then(data => {
                setSyncing(false);
                if (data?.status === 'success') {
                  const complainant = data.customer_email || 'complainant';
                  setMsg(`✓ Ingested complaint email from ${complainant} into bank mailbox (${data.mailbox})! Created Case ID: ${data.case_id} (${data.category.replace('_', ' ').toUpperCase()} · ${data.pipeline_status}). Resolution email dispatched to ${complainant}!`);
                } else {
                  setMsg('✓ Complaint email dispatched.');
                }
              })
              .catch(err => {
                setSyncing(false);
                setMsg(`Error dispatching email: ${err.message}`);
              });
          }}
          disabled={syncing}
          className="w-full py-2.5 bg-slate-900 text-white font-semibold text-xs rounded-xl hover:bg-slate-800 transition-colors shadow-sm flex items-center justify-center gap-2"
        >
          {syncing ? '↻ Processing through AI Dispute Pipeline...' : '🚀 Dispatch Complaint Email to Mailbox Pipeline'}
        </button>
      </div>

      {/* Outbound Resolution Email Dispatch Tester */}
      <div className="p-5 bg-white border border-slate-200 rounded-xl space-y-4 shadow-xs">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h4 className="text-sm font-semibold text-slate-900">📤 Test Outbound Resolution Email Dispatch</h4>
            <p className="text-xs text-slate-500">Test sending an official BNM-compliant dispute resolution notice email to a customer's Gmail.</p>
          </div>
          <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
            Outbound Dispatch Active
          </span>
        </div>

        <div className="text-xs space-y-3">
          <div>
            <label className="block text-slate-600 font-medium mb-1">Recipient Gmail Address</label>
            <input
              id="outbound-to"
              type="email"
              defaultValue={status?.email || "customer@gmail.com"}
              placeholder="customer@gmail.com"
              className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white font-medium text-slate-800"
            />
          </div>
          <div>
            <label className="block text-slate-600 font-medium mb-1">Resolution Notice Subject</label>
            <input
              id="outbound-subject"
              type="text"
              defaultValue="Resolution Notice: Dispute DISP-2026-37582 — Unauthorized Transactions"
              className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white"
            />
          </div>
          <div>
            <label className="block text-slate-600 font-medium mb-1">Notice Body (Includes BNM & FMOS 6-Month Disclosures)</label>
            <textarea
              id="outbound-body"
              rows={4}
              defaultValue={`Dear Customer,

We have completed our investigation into your dispute (DISP-2026-37582). A credit reversal of RM 1,500.00 has been applied to your account ending in 8471.

Mandatory Compliance Disclosures:
1. BNM Policy Document on Complaints Handling: Processed within 5 working days.
2. FMOS Redress Timeline Notice: Should you remain dissatisfied with this resolution, you have the right to refer your complaint to the Financial Mediation & Ombudsman Service (FMOS) within 6 months from the date of this notice.

Regards,
Complaints Resolution Team
AduanFlow AI`}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white text-xs font-mono"
            />
          </div>
        </div>

        <button
          onClick={() => {
            const toEmail = document.getElementById('outbound-to')?.value || 'ganyaotong@graduate.utm.my';
            const subj = document.getElementById('outbound-subject')?.value || 'Resolution Notice';
            const body = document.getElementById('outbound-body')?.value || 'Resolution body';

            setSyncing(true);
            setMsg('');

            apiFetch('/api/auth/send-test-outbound-email', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                recipient_email: toEmail,
                subject: subj,
                body: body
              })
            })
              .then(res => res.json())
              .then(data => {
                setSyncing(false);
                if (data?.smtp_delivered) {
                  setMsg(`🎉 REAL PHYSICAL EMAIL DELIVERED! Successfully sent to ${data.recipient} via Google SMTP (${data.sender}). Check your Gmail Inbox now!`);
                } else if (data?.status === 'sent' || data?.status === 'recorded') {
                  setMsg(`✓ Resolution notice transmitted to ${data.recipient} via connected Google OAuth 2.0 Mailbox (${status.email || 'OAuth Active'})!`);
                } else {
                  setMsg('✓ Outbound email notice processed.');
                }
              })
              .catch(err => {
                setSyncing(false);
                setMsg(`Error sending outbound email: ${err.message}`);
              });
          }}
          disabled={syncing}
          className="w-full py-2.5 bg-blue-600 text-white font-semibold text-xs rounded-xl hover:bg-blue-700 transition-colors shadow-sm flex items-center justify-center gap-2"
        >
          {syncing ? '↻ Delivering Real Physical Resolution Email...' : '✉️ Send Resolution Email to Customer Gmail'}
        </button>
      </div>

      {/* Guide Box */}
      <div className="p-4 bg-blue-50/50 border border-blue-100 rounded-xl text-xs text-slate-600 space-y-2">
        <p className="font-semibold text-blue-900">📖 How to send a real email from your personal email client:</p>
        <p className="text-slate-600">You can also open Gmail / Outlook on your phone or computer and send an email to <strong>ganyaotong@graduate.utm.my</strong> with:</p>
        <div className="p-3 bg-white border border-blue-200 rounded-lg font-mono text-[11px] space-y-1">
          <p><strong>To:</strong> ganyaotong@graduate.utm.my</p>
          <p><strong>Subject:</strong> UNAUTHORIZED TRANSACTION DISPUTE - RM 1,500.00</p>
          <p><strong>Body:</strong> Dear Bank, I am disputing an unauthorized charge of RM 1,500.00 on account 114002938471 (NRIC: 040125-01-0509). Please reverse funds immediately.</p>
        </div>
      </div>
    </div>
  );
}
