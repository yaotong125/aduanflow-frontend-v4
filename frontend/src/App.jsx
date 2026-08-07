import React, { useState, useCallback, useEffect, useRef } from 'react';
import { apiFetch } from './config';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './components/LoginPage';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import CaseList from './components/CaseList';
import CaseDetail from './components/CaseDetail';
import ManualReview from './components/ManualReview';
import AuditLog from './components/AuditLog';
import Copilot from './components/Copilot';
import TaskforceControlCenter from './components/TaskforceControlCenter';
import ProfileSettings from './components/ProfileSettings';
import NotificationCenter from './components/NotificationCenter';

import { IconMenu, IconLogout, IconUser } from './components/Icons';

const PAGE_LABELS = {
  dashboard: 'Dashboard',
  cases: 'All Cases',
  caseDetail: 'Case Detail',
  review: 'Manual Review',
  audit: 'Audit Log',
  taskforce: 'Taskforce Control Center',
  copilot: 'AI Copilot',
  settings: 'Settings',
  notifications: 'Notifications',
};

const OVERLAY_PAGES = ['settings', 'notifications'];

function UserDropdown({ onNavigateToOverlay }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (open) {
      const handler = () => setOpen(false);
      document.addEventListener('click', handler);
      return () => document.removeEventListener('click', handler);
    }
  }, [open]);

  const initials = (user?.name || 'U')[0].toUpperCase();

  return (
    <div className="relative" onClick={(e) => e.stopPropagation()}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 group"
        aria-expanded={open}
        aria-haspopup="true"
      >
        <span className="text-xs text-slate-600 font-medium group-hover:text-blue-600 transition-colors hidden xl:inline">
          {user?.name}
        </span>
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold text-xs shadow-md ring-2 ring-blue-100 group-hover:ring-blue-300 transition-all cursor-pointer">
          {initials}
        </div>
        <svg className={`w-4 h-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-12 w-64 bg-white rounded-xl border border-slate-200 shadow-card z-50 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50">
            <p className="text-sm font-semibold text-slate-800">{user?.name}</p>
            <p className="text-xs text-slate-500 capitalize">{user?.role} Account</p>
          </div>
          <div className="py-1">
            <button
              onClick={() => {
                onNavigateToOverlay('settings');
                setOpen(false);
              }}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
            >
              <IconUser className="w-4 h-4 text-slate-400" />
              Profile Settings
            </button>
            <button
              onClick={() => {
                onNavigateToOverlay('notifications');
                setOpen(false);
              }}
              className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
            >
              <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 110-9h5.19c2.902 0 5.117.884 6.83 2.34.713.466 1.13 1.233 1.13 2.06 0 .828-.417 1.594-1.13 2.06A7.78 7.78 0 0115.25 15.75" />
              </svg>
              Notifications
            </button>
          </div>
          <div className="border-t border-slate-100" />
          <button
            onClick={() => logout()}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
          >
            <IconLogout className="w-4 h-4" />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

function MobileHeader({ currentPage, sourcePage, goToMain, setSidebarOpen }) {
  const { logout } = useAuth();
  const isOverlay = OVERLAY_PAGES.includes(currentPage);

  return (
    <div className="md:hidden flex items-center gap-3 p-4 bg-white border-b border-gray-200 sticky top-0 z-30">
      {isOverlay ? (
        <button
          onClick={() => goToMain(sourcePage)}
          className="flex items-center gap-1 text-sm text-blue-600 font-semibold"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Back
        </button>
      ) : (
        <>
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 -ml-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <IconMenu className="w-6 h-6 text-gray-600" />
          </button>
          <div className="flex items-center gap-2 flex-1">
            <div className="w-7 h-7 rounded-md bg-blue-500 flex items-center justify-center text-white font-bold text-sm">
              A
            </div>
            <span className="font-semibold text-gray-900 text-sm">AduanFlow AI</span>
          </div>
          <button
            onClick={() => logout()}
            aria-label="Sign out"
            className="p-2 rounded-lg hover:bg-red-50 text-slate-500 hover:text-red-600 transition-colors"
          >
            <IconLogout className="w-5 h-5" />
          </button>
        </>
      )}
    </div>
  );
}

function DashboardView() {
  const [currentPage, setCurrentPage] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has('oauth_cancelled') || params.has('oauth_success') || params.has('oauth_error')) {
      return 'settings';
    }
    // Restore page from browser history state if available
    const histState = window.history.state;
    return histState?.page || 'dashboard';
  });
  const [selectedCaseId, setSelectedCaseId] = useState(() => window.history.state?.caseId || null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sourcePage, setSourcePage] = useState(() => window.history.state?.sourcePage || 'dashboard');
  const [cases, setCases] = useState([]);
  const [pageKey, setPageKey] = useState(0); // used to trigger fade animation
  const isPopState = useRef(false);

  // Push a new history entry on page change
  const pushHistory = useCallback((page, caseId = null, source = null) => {
    const state = { page, caseId, sourcePage: source };
    window.history.pushState(state, '', window.location.pathname);
  }, []);

  // Handle browser back/forward button
  useEffect(() => {
    const onPopState = (e) => {
      if (!e.state) return;
      isPopState.current = true;
      setCurrentPage(e.state.page || 'dashboard');
      setSelectedCaseId(e.state.caseId || null);
      setSourcePage(e.state.sourcePage || 'dashboard');
      setPageKey(k => k + 1);
      isPopState.current = false;
    };
    window.addEventListener('popstate', onPopState);
    // Seed the initial history entry so back doesn't exit the app
    if (!window.history.state) {
      window.history.replaceState({ page: currentPage, caseId: selectedCaseId, sourcePage }, '', window.location.pathname);
    }
    return () => window.removeEventListener('popstate', onPopState);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchCases = useCallback(() => {
    apiFetch('/api/cases')
      .then((res) => {
        if (!res.ok) throw new Error('API Error');
        return res.json();
      })
      .then((data) => {
        if (data) setCases(data);
      })
      .catch((err) => {
        console.error('Failed to fetch cases from database:', err);
      });
  }, []);

  useEffect(() => {
    fetchCases();
    const interval = setInterval(fetchCases, 10000);

    return () => clearInterval(interval);
  }, [fetchCases]);

  const selectedCase = cases.find((c) => c.id === selectedCaseId);

  const goToMain = useCallback((page, caseId = null) => {
    setCurrentPage(page);
    setSelectedCaseId(caseId);
    setSidebarOpen(false);
    setPageKey(k => k + 1);
    pushHistory(page, caseId, sourcePage);
  }, [pushHistory, sourcePage]);

  const goToOverlay = useCallback(
    (page) => {
      const src = currentPage === 'caseDetail' ? 'cases' : currentPage;
      setSourcePage(src);
      setCurrentPage(page);
      setPageKey(k => k + 1);
      pushHistory(page, selectedCaseId, src);
    },
    [currentPage, selectedCaseId, pushHistory]
  );

  const getBreadcrumbs = () => {
    if (currentPage === 'caseDetail' && selectedCase) {
      return [
        { label: 'Cases', action: () => goToMain('cases') },
        { label: selectedCase.id },
      ];
    }

    if (OVERLAY_PAGES.includes(currentPage)) {
      return [
        { label: PAGE_LABELS[sourcePage] || 'Dashboard', action: () => goToMain(sourcePage) },
        { label: PAGE_LABELS[currentPage] || currentPage },
      ];
    }

    if (PAGE_LABELS[currentPage]) {
      return [{ label: PAGE_LABELS[currentPage] }];
    }

    return [{ label: 'Dashboard' }];
  };

  const breadcrumbs = getBreadcrumbs();

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return (
          <Dashboard
            cases={cases}
            onViewCase={(id) => goToMain('caseDetail', id)}
            onViewAll={() => goToMain('cases')}
          />
        );
      case 'cases':
        return <CaseList cases={cases} onViewCase={(id) => goToMain('caseDetail', id)} />;
      case 'caseDetail':
        return <CaseDetail caseData={selectedCase} onBack={() => goToMain('cases')} />;
      case 'review':
        return <ManualReview cases={cases} onViewCase={(id) => goToMain('caseDetail', id)} />;
      case 'audit':
        return <AuditLog cases={cases} fetchCases={fetchCases} />;
      case 'taskforce':
        return (
          <TaskforceControlCenter
            onViewCase={(id) => goToMain('caseDetail', id)}
            onOpenCopilot={() => goToMain('copilot')}
          />
        );
      case 'copilot':
        return <Copilot onViewCase={(id) => goToMain('caseDetail', id)} />;
      case 'settings':
        return <ProfileSettings />;
      case 'notifications':
        return <NotificationCenter />;
      default:
        return (
          <Dashboard
            cases={cases}
            onViewCase={(id) => goToMain('caseDetail', id)}
            onViewAll={() => goToMain('cases')}
          />
        );
    }
  };

  return (
    <div className="flex h-screen overflow-hidden relative">
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <Sidebar currentPage={currentPage} onNavigate={goToMain} isOpen={sidebarOpen} cases={cases} />

      <main className="flex-1 overflow-y-auto bg-surface">
        <div className="hidden md:flex items-center justify-between px-6 py-2.5 bg-white border-b border-slate-200 sticky top-0 z-30">
          <div className="flex items-center gap-1.5 text-sm">
            {breadcrumbs.map((crumb, idx) => {
              const isLast = idx === breadcrumbs.length - 1;
              return (
                <React.Fragment key={idx}>
                  {idx > 0 && <span className="text-slate-300 text-xs">&rsaquo;</span>}
                  {isLast ? (
                    crumb.action ? (
                      <button
                        onClick={crumb.action}
                        className="text-blue-600 hover:text-blue-700 text-sm font-semibold transition-colors"
                      >
                        {crumb.label}
                      </button>
                    ) : (
                      <span className="text-slate-600 font-semibold text-sm truncate">{crumb.label}</span>
                    )
                  ) : (
                    <button
                      onClick={crumb.action}
                      className="text-slate-500 hover:text-slate-700 text-sm transition-colors"
                    >
                      {crumb.label}
                    </button>
                  )}
                </React.Fragment>
              );
            })}
          </div>

          <UserDropdown onNavigateToOverlay={goToOverlay} />
        </div>

        <MobileHeader
          currentPage={currentPage}
          sourcePage={sourcePage}
          goToMain={goToMain}
          setSidebarOpen={setSidebarOpen}
        />

        <div
          key={pageKey}
          className="p-4 md:p-6 mx-auto max-w-7xl animate-fadeIn"
        >
          {renderPage()}
        </div>
      </main>
    </div>
  );
}

function AppShell() {
  const { isLoggedIn } = useAuth();
  return isLoggedIn ? <DashboardView /> : <LoginPage />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}
