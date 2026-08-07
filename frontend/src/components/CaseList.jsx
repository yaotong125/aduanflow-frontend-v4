import React, { useState } from 'react';
import { DISPUTE_CATEGORIES } from '../data/mockData';
import { IconSearch, IconChevronRight } from './Icons';
import { STATUS_BADGE } from './Dashboard';

const statusOptions = ['All', 'PASS', 'FAIL', 'MANUAL_REVIEW', 'PENDING'];

export default function CaseList({ cases = [], onViewCase }) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [categoryFilter, setCategoryFilter] = useState('All');

  const filtered = cases.filter((c) => {
    const matchSearch = c.id.toLowerCase().includes(search.toLowerCase()) ||
      c.customerName.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === 'All' || c.status === statusFilter;
    const matchCategory = categoryFilter === 'All' || c.category === categoryFilter;
    return matchSearch && matchStatus && matchCategory;
  });

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-900">All Cases</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          {filtered.length} of {cases.length} cases
        </p>
      </div>

      {/* Filter bar */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-card p-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="flex-1 min-w-[240px] relative">
            <IconSearch className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Search by case ID or customer name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
            />
          </div>
          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
          >
            {statusOptions.map((s) => (
              <option key={s} value={s}>
                {s === 'All' ? 'All Statuses' : s.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
          {/* Category filter */}
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
          >
            <option value="All">All Categories</option>
            {Object.entries(DISPUTE_CATEGORIES).map(([key, val]) => (
              <option key={key} value={key}>{val.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Tabular case list */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50/50 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">
                <th className="px-6 py-3.5">Case ID</th>
                <th className="px-6 py-3.5">Customer</th>
                <th className="px-6 py-3.5">Category</th>
                <th className="px-6 py-3.5 text-right">Amount</th>
                <th className="px-6 py-3.5 text-center">Status</th>
                <th className="px-6 py-3.5 text-center">Urgency</th>
                <th className="px-6 py-3.5 text-right">Received</th>
                <th className="px-6 py-3.5"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((c) => {
                const cat = DISPUTE_CATEGORIES[c.category] || { label: c.category, color: 'bg-slate-100 text-slate-700' };

                return (
                  <tr
                    key={c.id}
                    onClick={() => onViewCase(c.id)}
                    onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onViewCase(c.id)}
                    role="button"
                    tabIndex={0}
                    className="hover:bg-slate-50/50 cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
                  >
                    <td className="px-6 py-3.5">
                      <span className="text-sm font-mono font-medium text-slate-700">{c.id}</span>
                    </td>
                    <td className="px-6 py-3.5">
                      <span className="text-sm text-slate-600">{c.customerName}</span>
                    </td>
                    <td className="px-6 py-3.5">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cat.color}`}>{cat.label}</span>
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <span className="text-sm font-mono font-medium text-slate-700">
                        RM {c.amount.toLocaleString()}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-center">
                      <span className={`text-xs px-2.5 py-0.5 rounded-full border font-medium ${STATUS_BADGE[c.status] || STATUS_BADGE.PENDING}`}>
                        {c.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-center">
                      {c.urgency === 'high' ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-red-600">
                          <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
                          High
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400 capitalize">{c.urgency}</span>
                      )}
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <span className="text-xs text-slate-500">
                        {new Date(c.receivedAt).toLocaleDateString('en-MY', { day: 'numeric', month: 'short' })}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <IconChevronRight className="w-4 h-4 text-slate-300" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Empty state */}
        {filtered.length === 0 && (
          <div className="text-center py-12 text-slate-500">
            <p className="text-base font-medium">No cases match your filters</p>
            <p className="text-sm mt-1 text-slate-400">Try adjusting your search criteria</p>
          </div>
        )}
      </div>
    </div>
  );
}
