import React from 'react';
import { DISPUTE_CATEGORIES } from '../data/mockData';

export default function ManualReview({ cases = [], onViewCase }) {
  const reviewCases = cases.filter((c) => c.status === 'MANUAL_REVIEW');

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Manual Review Queue</h2>
        <p className="text-sm text-slate-500 mt-0.5">{reviewCases.length} cases requiring human investigation</p>
      </div>

      {reviewCases.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-12 text-center">
          <p className="text-4xl mb-3">🎉</p>
          <p className="text-lg font-semibold text-slate-700">All clear!</p>
          <p className="text-sm mt-1 text-slate-500">No cases pending manual review</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reviewCases.map((c) => {
            const cat = DISPUTE_CATEGORIES[c.category] || { label: c.category, color: 'bg-slate-100 text-slate-700' };

            return (
              <div
                key={c.id}
                role="button"
                tabIndex={0}
                onClick={() => onViewCase(c.id)}
                onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onViewCase(c.id)}
                className="bg-white rounded-xl border border-slate-200 shadow-card p-5 hover:shadow-elevated hover:border-slate-300 cursor-pointer transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <div className="flex flex-wrap items-start gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1.5 flex-wrap">
                      <span className="text-sm font-mono font-semibold text-slate-800">{c.id}</span>
                      <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold border border-amber-200 bg-amber-50 text-amber-700">MANUAL REVIEW</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cat.color}`}>{cat.label}</span>
                      {c.urgency === 'high' && (
                        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium bg-red-50 text-red-600 border border-red-200">
                          <span className="w-1.5 h-1.5 rounded-full bg-red-500 inline-block" />
                          HIGH
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-600">{c.customerName}</p>
                    <div className="mt-3 p-3 bg-amber-50/50 border border-amber-100 rounded-lg">
                      <p className="text-xs font-medium text-amber-700 mb-1">Reason for Review:</p>
                      <p className="text-sm text-amber-800">{c.verification?.manualReviewReason || 'Insufficient evidence'}</p>
                    </div>
                    {c.verification?.checks && (
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {c.verification.checks.filter((ch) => ch.passed === null || ch.passed === false).map((ch, i) => (
                          <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                            {ch.passed === false ? '❌' : '⏳'} {ch.check}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="text-right flex-shrink-0 space-y-1">
                    <p className="text-lg font-bold text-slate-900 font-mono">RM {c.amount.toLocaleString()}</p>
                    <p className="text-xs text-slate-500 font-mono">{c.maskedAccount}</p>
                    <p className="text-xs text-slate-500">Due: {c.dueDate ? new Date(c.dueDate).toLocaleDateString('en-MY', { day: 'numeric', month: 'short' }) : 'N/A'}</p>

                    <p className="text-xs text-slate-500">{c.assignedTo ? `👤 ${c.assignedTo}` : '⚠️ Unassigned'}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
