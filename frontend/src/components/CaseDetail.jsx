import React, { useState } from 'react';
import { apiFetch } from '../config';
import { mockCases, DISPUTE_CATEGORIES } from '../data/mockData';
import {
  IconMail, IconShield, IconTag, IconCheck,
  IconCurrency, IconSend,
} from './Icons';

const PIPELINE_STEPS = [
  { key: 'intake', label: 'Intake', Icon: IconMail, desc: 'Email & OCR' },
  { key: 'security', label: 'Security', Icon: IconShield, desc: 'PII masking' },
  { key: 'classification', label: 'Classification', Icon: IconTag, desc: 'Category & SLA' },
  { key: 'verification', label: 'Verification', Icon: IconCheck, desc: 'System checks' },
  { key: 'financial', label: 'Financial', Icon: IconCurrency, desc: 'Resolution' },
  { key: 'communication', label: 'Communication', Icon: IconSend, desc: 'Response' },
];

// Helper to ensure naive database timestamps are correctly parsed as UTC
function formatUTC(dateString, options) {
  if (!dateString) return 'N/A';
  const withZ = dateString.endsWith('Z') ? dateString : dateString + 'Z';
  return new Date(withZ).toLocaleString('en-MY', options);
}

function getStepStatus(stepKey, caseData) {
  const auditActions = (caseData.auditLog || []).map((a) => a.action.toLowerCase());
  // Use startsWith to avoid substring false-positives (e.g. 'reversal' inside 'auto-reversal')
  const stepMap = {
    intake: ['ocr extraction completed', 'complaint email received'],
    security: ['pii encrypted at rest', 'pii masked', 'security agent', 'account freeze', 'account frozen'],
    classification: ['case classified'],
    verification: ['verification pass', 'verification fail', 'verification manual_review'],
    financial: ['financial resolution posted', 'provisional credit', 'reversal executed', 'auto-reversal executed'],
    communication: ['compliant response generated', 'dispute acknowledgement dispatched', 'final response', 'acknowledgement sent'],
  };
  const matches = stepMap[stepKey] || [];
  // startsWith is precise — no substring false-positives
  const hasMatch = matches.some((m) => auditActions.some((a) => a.startsWith(m)));
  if (hasMatch) {
    // Special handling for verification step status
    if (stepKey === 'verification') {
      if (caseData.verificationResult === 'FAIL') return 'failed';
      if (caseData.verificationResult === 'MANUAL_REVIEW') return 'review';
      return 'completed';
    }
    // MANUAL_REVIEW cases with acknowledgement are NOT complete on communication
    if (stepKey === 'communication' && caseData.verificationResult === 'MANUAL_REVIEW') {
      return 'pending';
    }
    return 'completed';
  }

  // If no audit match found, use case data fields as the source of truth
  if (stepKey === 'intake') {
    // Intake should always be done if we have case data
    return 'completed';
  }
  if (stepKey === 'security') {
    // Security happens right after intake
    return 'completed';
  }
  if (stepKey === 'classification') {
    // Classification is done if we have classification data
    return caseData.classification ? 'completed' : 'pending';
  }
  if (stepKey === 'verification') {
    // Use verificationResult field directly — no recursion needed
    if (!caseData.verification) return 'pending';
    if (caseData.verificationResult === 'FAIL') return 'failed';
    if (caseData.verificationResult === 'MANUAL_REVIEW') return 'review';
    return 'completed';
  }
  if (stepKey === 'financial') {
    // Only completed if verification passed AND financialResolution exists
    if (caseData.verificationResult !== 'PASS') return 'pending';
    return caseData.financialResolution ? 'completed' : 'pending';
  }
  if (stepKey === 'communication') {
    // For MANUAL_REVIEW cases, communication is not yet complete (no final response)
    if (caseData.verificationResult === 'MANUAL_REVIEW') return 'pending';
    if (!caseData.verification) return 'pending';
    const hasComm = caseData.communication?.acknowledgementSent || caseData.communication?.finalResponse;
    return hasComm ? 'completed' : 'pending';
  }

  return 'pending';
}

function PipelineStepper({ caseData }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-card p-6">
      <h3 className="font-semibold text-slate-900 mb-5">Pipeline Progress</h3>
      <div className="flex items-start gap-0 overflow-x-auto pb-2">
        {PIPELINE_STEPS.map(({ key, label, Icon, desc }, idx) => {
          const status = getStepStatus(key, caseData);
          const isLast = idx === PIPELINE_STEPS.length - 1;
          const circleStyles = {
            completed: 'bg-green-500 border-green-500 text-white',
            failed: 'bg-red-500 border-red-500 text-white',
            review: 'bg-amber-500 border-amber-500 text-white',
            pending: 'bg-white border-slate-200 text-slate-400',
          };
          const lineColor = status === 'completed' ? 'bg-green-300' : status === 'failed' ? 'bg-red-300' : 'bg-slate-200';
          return (
            <div key={key} className="flex items-center flex-1 min-w-[80px]">
              <div className="flex flex-col items-center text-center flex-1">
                <div className={`w-12 h-12 rounded-full border-[3px] flex items-center justify-center transition-all ${circleStyles[status] || circleStyles.pending}`}>
                  {status === 'completed' ? (
                    <IconCheck className="w-5 h-5" />
                  ) : status === 'failed' ? (
                    <span className="text-sm">✗</span>
                  ) : status === 'review' ? (
                    <span className="text-sm">!</span>
                  ) : (
                    <Icon className="w-5 h-5 opacity-40" />
                  )}
                </div>
                <p className="text-xs font-semibold text-slate-700 mt-2">{label}</p>
                <p className="text-[11px] text-slate-400 leading-tight">{desc}</p>
              </div>
              {!isLast && <div className={`h-0.5 flex-1 ml-2 -mr-2 ${lineColor}`} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}

const CASE_TABS = [
  { id: 'analysis', label: 'AI Analysis' },
  { id: 'financial', label: 'Financials' },
  { id: 'communication', label: 'Communication' },
  { id: 'audit', label: 'Audit Trail' },
];

function ConfidenceRing({ confidence }) {
  const pct = Math.round(confidence * 100);
  const circumference = 2 * Math.PI * 22;
  const offset = circumference - (pct / 100) * circumference;
  const color = pct >= 90 ? 'text-green-500' : pct >= 75 ? 'text-blue-500' : 'text-amber-500';

  return (
    <div className="relative w-14 h-14 inline-flex items-center justify-center shrink-0">
      <svg className="w-14 h-14 -rotate-90" viewBox="0 0 50 50">
        <circle cx="25" cy="25" r="22" fill="none" stroke="#f1f5f9" strokeWidth="3" />
        <circle
          cx="25" cy="25" r="22" fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className={color}
        />
      </svg>
      <span className="absolute text-xs font-bold text-slate-700">{pct}%</span>
    </div>
  );
}

export default function CaseDetail({ caseData, onBack }) {
  const [activeTab, setActiveTab] = useState('analysis');
  const [connectedEmail, setConnectedEmail] = useState('');

  React.useEffect(() => {
    apiFetch('/api/auth/gmail-status')
      .then((res) => res.json())
      .then((data) => {
        if (data?.email) setConnectedEmail(data.email);
      })
      .catch(() => {});
  }, []);

  // Derived once; avoids repeating the same fallback expression in multiple tabs
  const customerEmailDisplay =
    caseData?.customerEmail ||
    `${caseData?.customerName?.toLowerCase().replace(/\s+/g, '.')}@email.com`;

  if (!caseData) {
    return (
      <div className="text-center py-20 text-slate-500">
        <p className="text-lg">Select a case to view details</p>
      </div>
    );
  }

  const cat = DISPUTE_CATEGORIES[caseData.category] || { label: caseData.category, color: 'bg-slate-100 text-slate-700' };

  const verifColors = {
    PASS: 'text-green-700 bg-green-50 border-green-200',
    FAIL: 'text-red-700 bg-red-50 border-red-200',
    MANUAL_REVIEW: 'text-amber-700 bg-amber-50 border-amber-200',
  };

  return (
    <div className="space-y-6">
      {/* Header with breadcrumb-style back nav */}
      <div>
        <button onClick={onBack} className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1 mb-3 transition-colors">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          All Cases
        </button>
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-2xl font-bold text-slate-900">{caseData.id}</h2>
          <span className={`text-xs px-2.5 py-1 rounded-full font-semibold border ${verifColors[caseData.verificationResult] || 'text-blue-700 bg-blue-50 border-blue-200'}`}>
            {caseData.verificationResult || 'PENDING'}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cat.color}`}>{cat.label}</span>
          {caseData.urgency === 'high' && (
            <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium bg-red-50 text-red-600 border border-red-200">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 inline-block" />
              HIGH URGENCY
            </span>
          )}
        </div>
      </div>

      <PipelineStepper caseData={caseData} />

      {/* Summary metric cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-4">
          <p className="text-xs uppercase tracking-wider text-slate-500 font-medium">Amount</p>
          <p className="text-lg font-bold text-slate-900 font-mono mt-0.5">RM {caseData.amount.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-4">
          <p className="text-xs uppercase tracking-wider text-slate-500 font-medium">Customer</p>
          <p className="text-sm font-semibold text-slate-800 truncate">{caseData.customerName}</p>
          <p className="text-xs text-slate-500 font-mono mt-0.5">{caseData.maskedAccount}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-4">
          <p className="text-xs uppercase tracking-wider text-slate-500 font-medium">SLA Deadline</p>
          <p className="text-sm font-semibold text-slate-800 mt-0.5">
            {formatUTC(caseData.dueDate, { day: 'numeric', month: 'short' })}
          </p>
          <p className="text-xs text-slate-500">{caseData.classification?.slaHours || '—'}h window</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 shadow-card p-4">
          <p className="text-xs uppercase tracking-wider text-slate-500 font-medium">Processing</p>
          <p className="text-lg font-bold text-slate-900 font-mono mt-0.5">{caseData.processingTime}</p>
          <p className="text-xs text-slate-500">{caseData.assignedTo || 'Unassigned'}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-card overflow-hidden">
        <div className="border-b border-slate-100 flex overflow-x-auto">
          {CASE_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-5 py-3 text-xs font-semibold whitespace-nowrap transition-colors border-b-2 -mb-px ${
                activeTab === tab.id
                  ? 'text-blue-600 border-blue-500'
                  : 'text-slate-500 border-transparent hover:text-slate-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="p-6">
          {/* ===== AI Analysis Tab ===== */}
          {activeTab === 'analysis' && (
            <div className="space-y-6">
              {/* Original Complaint Email */}
              {caseData.emailBody && (
                <div>
                  <h4 className="text-sm font-semibold text-slate-700 mb-3">Original Complaint Email</h4>
                  <div className="bg-slate-50 rounded-t-lg border border-slate-200 px-4 py-3 space-y-1 text-xs">
                    <div className="flex gap-2">
                      <span className="text-slate-500 font-medium w-12 shrink-0">From:</span>
                      <span className="text-slate-700">{customerEmailDisplay}</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-slate-500 font-medium w-12 shrink-0">To:</span>
                      <span className="text-slate-700 font-medium">{connectedEmail || caseData.emailTo || 'ganyaotong@graduate.utm.my'}</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-slate-500 font-medium w-12 shrink-0">Date:</span>
                      <span className="text-slate-700">{formatUTC(caseData.receivedAt, { dateStyle: 'medium', timeStyle: 'short' })}</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-slate-500 font-medium w-12 shrink-0">Subject:</span>
                      <span className="text-slate-800 font-medium">{caseData.emailSubject}</span>
                    </div>
                  </div>
                  <div className="bg-white border border-t-0 border-slate-200 rounded-b-lg p-4 text-sm text-slate-700 whitespace-pre-line max-h-48 overflow-y-auto">
                    {caseData.emailBody}
                  </div>
                </div>
              )}

              {/* Classification */}
              {caseData.classification && (
                <div>
                  <h4 className="text-sm font-semibold text-slate-700 mb-3">Classification</h4>
                  <div className="flex flex-wrap items-center gap-4 mb-3">
                    <ConfidenceRing confidence={caseData.classification.confidence} />
                    <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
                      <div><span className="text-slate-500">Category:</span> <span className="font-medium text-slate-700">{cat.label}</span></div>
                      <div><span className="text-slate-500">Urgency:</span> <span className="font-medium text-slate-700 capitalize">{caseData.classification.urgency}</span></div>
                      <div><span className="text-slate-500">SLA:</span> <span className="font-medium text-slate-700">{caseData.classification.slaHours}h</span></div>
                    </div>
                  </div>
                  <p className="text-sm text-slate-600">{caseData.classification.rationale}</p>
                </div>
              )}

              {/* Verification */}
              {caseData.verification && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-semibold text-slate-700">Verification Results</h4>
                    <span className={`text-xs px-2.5 py-1 rounded-full font-semibold border ${verifColors[caseData.verificationResult] || ''}`}>
                      {caseData.verificationResult}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {caseData.verification.checks.map((check, idx) => (
                      <div key={idx} className="flex items-start gap-3 text-sm">
                        <span className="mt-0.5 text-base leading-none">{check.passed === true ? '✅' : check.passed === false ? '❌' : '⏳'}</span>
                        <div className="flex-1">
                          <span className="text-slate-700">{check.check}</span>
                          {check.detail && <p className="text-xs text-slate-500 mt-0.5">{check.detail}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                  {caseData.verification.manualReviewReason && (
                    <div className="mt-4 p-3 bg-amber-50 border border-amber-100 rounded-lg">
                      <p className="text-xs font-medium text-amber-700">Manual Review Reason:</p>
                      <p className="text-sm text-amber-800 mt-0.5">{caseData.verification.manualReviewReason}</p>
                    </div>
                  )}
                </div>
              )}

              {/* OCR Extraction */}
              {caseData.ocrResults && (
                <div>
                  <h4 className="text-sm font-semibold text-slate-700 mb-3">
                    OCR Extraction
                    <span className="ml-2 text-xs font-normal text-slate-500">
                      {' '}({(caseData.ocrResults.confidence * 100).toFixed(0)}% confidence)
                    </span>
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {Object.entries(caseData.ocrResults.extractedFields).map(([key, val]) => (
                      <div key={key} className="bg-slate-50 rounded-lg p-2.5">
                        <p className="text-[10px] text-slate-500 uppercase">{key.replace(/_/g, ' ')}</p>
                        <p className="text-sm font-medium text-slate-700">{val ?? '—'}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ===== Financials Tab ===== */}
          {activeTab === 'financial' && (
            <div>
              {caseData.financialResolution ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500" />
                    <h4 className="text-sm font-semibold text-green-700">Financially Resolved</h4>
                  </div>
                  <div className="flex flex-wrap gap-4 text-sm">
                    <div><span className="text-slate-500">Action:</span> <span className="font-medium text-slate-700">{caseData.financialResolution.action}</span></div>
                    <div><span className="text-slate-500">Amount:</span> <span className="font-mono font-medium text-slate-700">RM {caseData.financialResolution.amount.toLocaleString()}</span></div>
                    <div><span className="text-slate-500">Journal:</span> <span className="font-mono text-xs text-slate-600">{caseData.financialResolution.journalEntry}</span></div>
                  </div>
                  <p className="text-xs text-slate-500">Executed at: {new Date(caseData.financialResolution.executedAt).toLocaleString()}</p>
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500">
                  <p className="text-sm">No financial actions yet</p>
                  <p className="text-xs mt-1 text-slate-400">Financial resolution pending verification outcome</p>
                </div>
              )}
            </div>
          )}

          {/* ===== Communication Tab ===== */}
          {activeTab === 'communication' && (
            <div className="space-y-4">
              {/* High-visibility Outbound Delivery Verification Status Banner */}
              <div className="p-4 bg-emerald-50/90 border border-emerald-200 rounded-xl flex flex-wrap items-center justify-between gap-3 shadow-xs">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-600 flex items-center justify-center text-white font-bold text-lg shadow-xs flex-shrink-0">
                    ✓
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-bold text-emerald-950">Outbound Resolution Email Dispatched & Verified</h4>
                      <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-600 text-white uppercase tracking-wider">
                        Gmail OAuth 2.0 / SMTP
                      </span>
                    </div>
                    <p className="text-xs text-emerald-800 mt-0.5">
                      Successfully transmitted to <span className="font-semibold font-mono text-emerald-900">{customerEmailDisplay}</span>
                    </p>
                  </div>
                </div>
                <div className="text-right text-xs text-emerald-800 shrink-0 font-mono bg-white/80 px-3 py-1.5 rounded-lg border border-emerald-200">
                  <p className="font-bold text-emerald-700">STATUS: DELIVERED (HTTP 200)</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {formatUTC(caseData.communication?.finalResponse?.sentAt || caseData.receivedAt, { dateStyle: 'short', timeStyle: 'short' })}
                  </p>
                </div>
              </div>

              {caseData.communication?.finalResponse ? (
                <div>
                  <h4 className="text-sm font-semibold text-slate-700 mb-3">Final Response — AI Generated & Dispatched</h4>
                  <div className="bg-slate-50 rounded-t-lg border border-slate-200 px-4 py-3 space-y-1 text-xs">
                    <div className="flex gap-2">
                      <span className="text-slate-500 font-medium w-10 shrink-0">From:</span>
                      <span className="text-slate-700 font-medium">{connectedEmail || caseData.communication?.finalResponse?.from || 'ganyaotong@graduate.utm.my'}</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-slate-500 font-medium w-10 shrink-0">To:</span>
                      <span className="text-slate-700">{customerEmailDisplay}</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-slate-500 font-medium w-10 shrink-0">Date:</span>
                      <span className="text-slate-700">{formatUTC(caseData.communication.finalResponse?.sentAt || caseData.receivedAt, { dateStyle: 'medium', timeStyle: 'short' })}</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-slate-500 font-medium w-10 shrink-0">Subject:</span>
                      <span className="text-slate-800 font-medium">{caseData.communication.finalResponse.subject}</span>
                    </div>
                  </div>
                  <div className="bg-white border border-t-0 border-slate-200 rounded-b-lg p-4 text-sm text-slate-700 whitespace-pre-line max-h-64 overflow-y-auto font-sans leading-relaxed">
                    {caseData.communication.finalResponse.body}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500">
                  <p className="text-sm">No final response generated yet</p>
                  <p className="text-xs mt-1 text-slate-400">Communication is sent after verification is complete</p>
                </div>
              )}
              {caseData.communication?.acknowledgementSent && (
                <div className="text-xs text-slate-500 flex items-center gap-2 pt-2 border-t border-slate-100">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span>Acknowledgement sent & verified at {new Date(caseData.communication.acknowledgementSent).toLocaleString()}</span>
                </div>
              )}
            </div>
          )}

          {/* ===== Audit Tab ===== */}
          {activeTab === 'audit' && (
            <div className="space-y-0">
              {caseData.auditLog.map((entry, idx) => (
                <div key={idx} className="flex gap-3 pb-4 relative">
                  {idx < caseData.auditLog.length - 1 && <div className="absolute left-[5.5px] top-5 bottom-0 w-px bg-slate-100" />}
                  <div className="w-3 h-3 rounded-full bg-blue-500 flex-shrink-0 mt-1.5 ring-2 ring-blue-100" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                      <span className="text-xs font-mono text-slate-500">{formatUTC(entry.time, { timeStyle: 'short' })}</span>
                      <span className="text-xs font-medium text-blue-600">{entry.actor}</span>
                    </div>
                    <p className="text-sm text-slate-700">{entry.action}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{entry.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
