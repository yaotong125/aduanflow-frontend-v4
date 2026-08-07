import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { apiFetch } from '../config';
import { IconSearch } from './Icons';

/** Map each agent actor to a colour accent so entries are visually distinct. */
const ACTOR_COLORS = {
  'Email MCP':            'bg-blue-100 text-blue-700 border-blue-200',
  'Intake Agent':         'bg-emerald-100 text-emerald-700 border-emerald-200',
  'Security Agent':       'bg-red-100 text-red-700 border-red-200',
  'Classification Agent': 'bg-violet-100 text-violet-700 border-violet-200',
  'Verification Agent':   'bg-amber-100 text-amber-700 border-amber-200',
  'Financial Agent':      'bg-green-100 text-green-700 border-green-200',
  'Comms Agent':          'bg-cyan-100 text-cyan-700 border-cyan-200',
  'Gmail Sync Agent':     'bg-indigo-100 text-indigo-700 border-indigo-200',
  'System':               'bg-slate-100 text-slate-600 border-slate-200',
};

const ACTOR_DOT = {
  'Email MCP':            'bg-blue-500',
  'Intake Agent':         'bg-emerald-500',
  'Security Agent':       'bg-red-500',
  'Classification Agent': 'bg-violet-500',
  'Verification Agent':   'bg-amber-500',
  'Financial Agent':      'bg-green-500',
  'Comms Agent':          'bg-cyan-500',
  'Gmail Sync Agent':     'bg-indigo-500',
  'System':               'bg-slate-400',
};

function ActorBadge({ actor }) {
  const cls = ACTOR_COLORS[actor] || 'bg-slate-100 text-slate-600 border-slate-200';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${cls}`}>
      {actor}
    </span>
  );
}

function Spinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
      <span className="ml-3 text-sm text-slate-500">Loading audit trail…</span>
    </div>
  );
}

export default function AuditLog({ cases = [], fetchCases }) {
  const [search, setSearch]           = useState('');
  const [actorFilter, setActorFilter] = useState('All');
  const [dbLogs, setDbLogs]           = useState([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);
  const [deletingId, setDeletingId]   = useState(null);

  // ─── Fetch from /api/audit (real DB table) ────────────────────────────────
  const fetchAuditLogs = useCallback(() => {
    apiFetch('/api/audit?limit=500')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setDbLogs(Array.isArray(data) ? data : []);
        setError(null);
      })
      .catch((err) => {
        console.error('[AuditLog] Failed to fetch from /api/audit:', err);
        setError('Could not load audit logs from database.');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchAuditLogs();
    // Auto-refresh every 15 seconds to show live pipeline activity
    const timer = setInterval(fetchAuditLogs, 15000);
    return () => clearInterval(timer);
  }, [fetchAuditLogs]);

  // ─── Fallback: merge JSON blobs from case objects if DB table is sparse ──
  const caseLogs = useMemo(
    () =>
      cases.flatMap((c) =>
        (c.auditLog || []).map((entry) => ({
          id:         `case-blob-${c.id}-${entry.actor}-${entry.action}`,
          case_id:    c.id,
          actor:      entry.actor,
          action:     entry.action,
          detail:     entry.detail,
          created_at: null,  // JSON blobs have no ISO timestamp
          _time:      entry.time,  // HH:MM:SS string from blob
        }))
      ),
    [cases]
  );

  // Normalise DB rows into the same shape as case blob entries
  const normalisedDbLogs = useMemo(
    () =>
      dbLogs.map((row) => ({
        id:         row.id,
        case_id:    row.case_id,
        actor:      row.actor,
        action:     row.action,
        detail:     row.detail || '',
        created_at: row.created_at,
        _time:      row.created_at
          ? new Date(row.created_at).toLocaleTimeString('en-MY', { hour12: false })
          : '—',
        _fromDb: true,
      })),
    [dbLogs]
  );

  // Deduplicate: prefer DB rows; fall back to case-blob entries for any case not yet in DB
  const dbCaseIds = useMemo(() => new Set(dbLogs.map((r) => r.case_id)), [dbLogs]);
  const fallbackLogs = useMemo(
    () => caseLogs.filter((e) => !dbCaseIds.has(e.case_id)),
    [caseLogs, dbCaseIds]
  );

  const allLogs = useMemo(
    () => [...normalisedDbLogs, ...fallbackLogs],
    [normalisedDbLogs, fallbackLogs]
  );

  const allActors = useMemo(
    () => ['All', ...new Set(allLogs.map((l) => l.actor))].sort(),
    [allLogs]
  );

  const filtered = useMemo(
    () =>
      allLogs.filter((l) => {
        const matchSearch =
          (l.case_id || '').toLowerCase().includes(search.toLowerCase()) ||
          (l.action  || '').toLowerCase().includes(search.toLowerCase()) ||
          (l.detail  || '').toLowerCase().includes(search.toLowerCase()) ||
          (l.actor   || '').toLowerCase().includes(search.toLowerCase());
        const matchActor = actorFilter === 'All' || l.actor === actorFilter;
        return matchSearch && matchActor;
      }),
    [allLogs, search, actorFilter]
  );

  // ─── Delete an audit log entry ────────────────────────────────────────────
  const handleDelete = useCallback(async (id) => {
    if (!window.confirm('Remove this audit entry?')) return;
    setDeletingId(id);
    try {
      const res = await apiFetch(`/api/audit/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setDbLogs((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  }, []);

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Audit Log</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Complete AI pipeline audit trail —{' '}
            <span className="font-semibold text-blue-600">{allLogs.length}</span> events
            {normalisedDbLogs.length > 0 && (
              <span className="ml-1 text-xs text-emerald-600">
                ({normalisedDbLogs.length} from database)
              </span>
            )}
          </p>
        </div>
        <button
          onClick={() => { setLoading(true); fetchAuditLogs(); if (fetchCases) fetchCases(); }}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-sm"
          title="Refresh audit trail"
        >
          <svg className="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Filter bar */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[240px] relative">
            <IconSearch className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Search by case ID, actor, action, or detail…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
            />
          </div>
          <select
            value={actorFilter}
            onChange={(e) => setActorFilter(e.target.value)}
            className="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
          >
            {allActors.map((a) => (
              <option key={a} value={a}>{a === 'All' ? 'All Actors' : a}</option>
            ))}
          </select>
          <span className="text-xs text-slate-500 ml-auto">{filtered.length} events</span>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700 flex items-center gap-2">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          {error} Showing cached data from case records as fallback.
        </div>
      )}

      {/* Timeline */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        {loading ? (
          <Spinner />
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            <svg className="w-12 h-12 mx-auto mb-3 text-slate-200" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
            </svg>
            <p className="font-medium">No audit events match your filters</p>
            <p className="text-xs mt-1 text-slate-400">Events appear here as the AI pipeline processes incoming disputes.</p>
          </div>
        ) : (
          <div className="space-y-0">
            {filtered.map((entry, idx) => {
              const dotColor = ACTOR_DOT[entry.actor] || 'bg-slate-400';
              const isDbEntry = !!entry._fromDb;
              return (
                <div key={entry.id || idx} className="flex gap-3 pb-5 relative group">
                  {idx < filtered.length - 1 && (
                    <div className="absolute left-[5.5px] top-5 bottom-0 w-px bg-slate-100" />
                  )}
                  {/* Timeline dot */}
                  <div className={`w-3 h-3 rounded-full ${dotColor} flex-shrink-0 mt-1.5 ring-2 ring-white shadow-sm`} />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-2 mb-1 flex-wrap">
                      <span className="text-xs font-mono text-slate-400 mt-0.5">{entry._time}</span>
                      <ActorBadge actor={entry.actor} />
                      <span className="text-xs font-mono text-slate-400 mt-0.5 truncate">{entry.case_id}</span>
                      {!isDbEntry && (
                        <span className="text-xs text-slate-300 italic mt-0.5">(cached)</span>
                      )}
                    </div>
                    <p className="text-sm font-medium text-slate-700">{entry.action}</p>
                    {entry.detail && (
                      <p className="text-xs text-slate-500 mt-0.5">{entry.detail}</p>
                    )}
                    {/* Delete button — only for real DB entries */}
                    {isDbEntry && (
                      <button
                        onClick={() => handleDelete(entry.id)}
                        disabled={deletingId === entry.id}
                        className="mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity text-xs text-red-400 hover:text-red-600 flex items-center gap-1"
                        title="Remove audit entry"
                      >
                        {deletingId === entry.id ? (
                          <span>Deleting…</span>
                        ) : (
                          <>
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                            Remove
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
