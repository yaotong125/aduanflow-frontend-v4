import React, { useEffect, useState } from 'react';
import { apiFetch } from '../config';
import { buildTaskforceOverview } from '../data/taskforceData';

function formatMoney(amount) {
  return `RM ${Number(amount || 0).toLocaleString('en-MY', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function SummaryCard({ label, value, hint, tone = 'blue' }) {
  const toneStyles = {
    blue: 'bg-blue-50 text-blue-700 border-blue-100',
    amber: 'bg-amber-50 text-amber-700 border-amber-100',
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    violet: 'bg-violet-50 text-violet-700 border-violet-100',
  };

  return (
    <div className={`rounded-2xl border p-5 ${toneStyles[tone] || toneStyles.blue}`}>
      <p className="text-xs uppercase tracking-[0.18em] font-semibold opacity-80">{label}</p>
      <p className="mt-3 text-3xl font-bold tracking-tight">{value}</p>
      <p className="mt-2 text-sm opacity-80">{hint}</p>
    </div>
  );
}

function MissionCard({ mission, onViewCase }) {
  const statusTone = {
    MANUAL_REVIEW: 'bg-amber-50 text-amber-700 border-amber-200',
    PENDING: 'bg-blue-50 text-blue-700 border-blue-200',
    FAIL: 'bg-rose-50 text-rose-700 border-rose-200',
    PASS: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <p className="font-mono text-sm font-semibold text-slate-700">{mission.caseId}</p>
            <span className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusTone[mission.status] || statusTone.PENDING}`}>
              {mission.status.replace(/_/g, ' ')}
            </span>
          </div>
          <h3 className="mt-2 text-base font-semibold text-slate-900">{mission.category}</h3>
          <p className="mt-1 text-sm text-slate-500">{mission.customerName} · {formatMoney(mission.amount)}</p>
        </div>
        {onViewCase && (
          <button
            onClick={() => onViewCase(mission.caseId)}
            className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 transition-colors"
          >
            View case
          </button>
        )}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-xl bg-slate-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Squad owner</p>
          <p className="mt-1 text-sm font-medium text-slate-800">{mission.squad} · {mission.owner}</p>
        </div>
        <div className="rounded-xl bg-slate-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Recommended action</p>
          <p className="mt-1 text-sm text-slate-700">{mission.recommendedAction}</p>
        </div>
      </div>

      <div className="mt-3 rounded-xl border border-dashed border-slate-200 bg-white p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Why the taskforce is watching</p>
        <p className="mt-1 text-sm text-slate-700">{mission.reason}</p>
      </div>
    </div>
  );
}

export default function TaskforceControlCenter({ onViewCase, onOpenCopilot }) {
  const [overview, setOverview] = useState(null);
  const [failedAvatars, setFailedAvatars] = useState({});

  useEffect(() => {
    let active = true;

    apiFetch('/api/taskforce/overview')
      .then((res) => {
        if (!res.ok) throw new Error('Taskforce API unavailable');
        return res.json();
      })
      .then((data) => {
        if (active && data?.team && data?.summary) {
          setOverview(data);
        }
      })
      .catch(() => {
        if (active) setOverview(buildTaskforceOverview());
      });

    return () => {
      active = false;
    };
  }, []);

  if (!overview) {
    return (
      <div className="flex h-64 items-center justify-center rounded-3xl border border-slate-200 bg-white">
        <p className="text-sm font-semibold text-slate-500">Loading Taskforce Command Center...</p>
      </div>
    );
  }

  const { team, summary, members, squads, missions, playbooks, commandPrompts } = overview;

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-r from-slate-900 via-slate-800 to-blue-900 p-6 text-white shadow-card">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-blue-100">
              Expert team integration live
            </div>
            <h2 className="mt-4 text-3xl font-bold tracking-tight">{team.name}</h2>
            <p className="mt-3 text-sm leading-6 text-slate-200">{team.tagline}</p>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">{team.mission}</p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/10 p-4 text-sm text-slate-100 lg:max-w-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-100">Operating cadence</p>
            <p className="mt-2 leading-6">{team.operatingCadence}</p>
            {onOpenCopilot && (
              <button
                onClick={onOpenCopilot}
                className="mt-4 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 hover:bg-blue-50 transition-colors"
              >
                Open AI Copilot
              </button>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          label="Active missions"
          value={summary.activeMissionCount}
          hint={`${summary.totalCases} total cases in the dispute estate`}
          tone="blue"
        />
        <SummaryCard
          label="Manual escalations"
          value={summary.manualEscalations}
          hint="Cases actively awaiting specialist review"
          tone="amber"
        />
        <SummaryCard
          label="High-value exposure"
          value={formatMoney(summary.highValueExposure)}
          hint="Priority financial surface tracked by the taskforce"
          tone="violet"
        />
        <SummaryCard
          label="Straight-through rate"
          value={`${summary.straightThroughRate}%`}
          hint={`${summary.priorityCoverage} high-urgency disputes under active watch`}
          tone="emerald"
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_1.4fr]">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-card">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="text-xl font-semibold text-slate-900">Team lineup</h3>
              <p className="mt-1 text-sm text-slate-500">Specialists adjusted for banking disputes, evidence review, and remediation.</p>
            </div>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            {members.map((member) => (
              <div key={member.name} className="rounded-2xl border border-slate-200 p-4 bg-white shadow-xs hover:border-blue-200 transition-colors">
                <div className="flex items-center gap-3">
                  <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br ${member.accent || 'from-blue-600 to-indigo-600'} text-lg font-bold text-white shadow-md ring-4 ring-slate-50`}>
                    {(member.name || 'A')[0]}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{member.name}</p>
                    <p className="text-xs text-slate-500">{member.role}</p>
                  </div>
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-600">{member.focus}</p>
                <div className="mt-3 inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                  {member.specialty}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-card">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="text-xl font-semibold text-slate-900">Priority mission board</h3>
              <p className="mt-1 text-sm text-slate-500">Cases currently under direct taskforce supervision.</p>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
              Live queue
            </span>
          </div>

          <div className="mt-5 space-y-4">
            {missions.length > 0 ? (
              missions.map((mission) => <MissionCard key={mission.caseId} mission={mission} onViewCase={onViewCase} />)
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-200 p-6 text-sm text-slate-500">
                No active taskforce missions right now.
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-card">
          <h3 className="text-xl font-semibold text-slate-900">Squad coverage</h3>
          <p className="mt-1 text-sm text-slate-500">How the expert team is partitioned across dispute types.</p>

          <div className="mt-5 space-y-4">
            {squads.map((squad) => (
              <div key={squad.name} className="rounded-2xl border border-slate-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h4 className="text-base font-semibold text-slate-900">{squad.name}</h4>
                    <p className="mt-1 text-sm text-slate-500">Lead: {squad.lead} · Backup: {squad.backup}</p>
                  </div>
                  <div className="text-right text-sm text-slate-600">
                    <p>{squad.caseCount} total cases</p>
                    <p>{squad.activeCount} active · {squad.highValueCount} high-value</p>
                  </div>
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-600">{squad.objective}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {squad.handles.map((handle) => (
                    <span key={handle} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                      {handle.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-card">
            <h3 className="text-xl font-semibold text-slate-900">Playbooks</h3>
            <p className="mt-1 text-sm text-slate-500">Operational flows the integrated taskforce uses when cases get complicated.</p>
            <div className="mt-5 space-y-4">
              {playbooks.map((playbook) => (
                <div key={playbook.name} className="rounded-2xl border border-slate-200 p-4">
                  <h4 className="text-base font-semibold text-slate-900">{playbook.name}</h4>
                  <p className="mt-1 text-sm text-slate-500">Trigger: {playbook.trigger}</p>
                  <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6 text-slate-600">
                    {playbook.steps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-card">
            <h3 className="text-xl font-semibold text-slate-900">Suggested prompts</h3>
            <p className="mt-1 text-sm text-slate-500">Questions the integrated team is now ready to answer in the copilot surface.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {commandPrompts.map((prompt) => (
                <span key={prompt} className="rounded-full border border-blue-100 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700">
                  {prompt}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
