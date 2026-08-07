import React from 'react';
import { useAuth } from '../context/AuthContext';
import {
  IconDashboard,
  IconCases,
  IconReview,
  IconAudit,
  IconCopilot,
  IconLogout,
  IconRobot,
  IconMail,
} from './Icons';

const NAV_ITEMS_BASE = [
  { id: 'dashboard', label: 'Dashboard', Icon: IconDashboard },
  { id: 'cases', label: 'All Cases', Icon: IconCases },
  { id: 'review', label: 'Manual Review', Icon: IconReview },
  { id: 'audit', label: 'Audit Log', Icon: IconAudit },
  { id: 'taskforce', label: 'Taskforce', Icon: IconRobot },
  { id: 'copilot', label: 'AI Copilot', Icon: IconCopilot },
  { id: 'settings', label: 'Gmail & Integrations', Icon: IconMail },
];

export default function Sidebar({ currentPage, onNavigate, isOpen, cases = [] }) {
  const { logout } = useAuth();

  const manualReviewCount = cases.filter((c) => c.status === 'MANUAL_REVIEW').length;
  const taskforceMissionCount = cases.filter(
    (c) => c.status === 'MANUAL_REVIEW' || c.status === 'PENDING' || c.urgency === 'high' || c.amount >= 5000
  ).length;

  return (
    <aside
      aria-label="Main navigation"
      className={`
        fixed md:static inset-y-0 left-0 z-50 w-64 bg-slate-900 border-r border-slate-800
        flex flex-col flex-shrink-0 transition-transform duration-300
        ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}
    >
      <div className="p-5 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white font-bold text-lg shadow-lg">
            A
          </div>
          <div>
            <h1 className="font-bold text-white text-sm leading-tight">AduanFlow AI</h1>
            <p className="text-xs text-slate-400">Dispute Automation</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {NAV_ITEMS_BASE.map(({ id, label, Icon }) => {
          const isActive = currentPage === id;
          const badge = id === 'review' ? manualReviewCount : id === 'taskforce' ? taskforceMissionCount : undefined;

          return (
            <button
              key={id}
              onClick={() => onNavigate(id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                isActive
                  ? 'bg-slate-800/50 text-white border-l-2 border-blue-500 pl-[13px]'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
              <span className="flex-1 text-left">{label}</span>
              {badge !== undefined && badge > 0 && (
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                  id === 'taskforce' ? 'bg-blue-500/20 text-blue-300' : 'bg-amber-500/20 text-amber-300'
                }`}>
                  {badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800 space-y-3">
        <button
          onClick={() => logout()}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-red-400 transition-colors"
        >
          <IconLogout className="w-4 h-4 shrink-0" />
          Sign Out
        </button>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          System Operational
        </div>
        <p className="text-xs text-slate-500">v4.0 — Supabase</p>
      </div>
    </aside>
  );
}
