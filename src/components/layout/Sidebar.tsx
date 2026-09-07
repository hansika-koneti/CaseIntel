import React, { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { checkSystemHealth } from '../../api/system';
import { getInvestigation, getInvestigations } from '../../api/investigations';
import {
  LayoutDashboard,
  FolderOpen,
  Video,
  Clock,
  Network,
  AlertOctagon,
  Archive,
  FileText,
  Shield,
  ChevronRight,
  PlaySquare,
  Dot,
} from 'lucide-react';

interface NavItem {
  to: string;
  icon: React.ReactNode;
  label: string;
  badge?: string;
  sub?: boolean;
  dividerBefore?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/',                    icon: <LayoutDashboard size={15} />, label: 'Overview' },
  { to: '/investigations',      icon: <FolderOpen size={15} />,      label: 'Investigations' },
  { to: '/cctv-analysis',       icon: <Video size={15} />,           label: 'CCTV Analysis', dividerBefore: true },
  { to: '/cctv-analysis/video', icon: <PlaySquare size={13} />,      label: 'Video Viewer', sub: true },
  { to: '/timeline',            icon: <Clock size={15} />,           label: 'Event Timeline' },
  { to: '/graph',               icon: <Network size={15} />,         label: 'Entity Graph' },
  { to: '/incident',            icon: <AlertOctagon size={15} />,    label: 'Incident Review', dividerBefore: true },
  { to: '/evidence',            icon: <Archive size={15} />,         label: 'Evidence' },
  { to: '/report',              icon: <FileText size={15} />,        label: 'Case Report' },
];

export default function Sidebar() {
  const location = useLocation();

  const [isBackendLive, setIsBackendLive] = useState(false);

  useEffect(() => {
    let mounted = true;
    const checkHealth = async () => {
      try {
        const res = await checkSystemHealth();
        if (mounted) {
          setIsBackendLive(res.status === 'healthy');
        }
      } catch {
        if (mounted) {
          setIsBackendLive(false);
        }
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const [activeCase, setActiveCase] = useState<{ caseNumber: string; status: string } | null>(null);
  const [investigationCount, setInvestigationCount] = useState<number>(0);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      // Load real investigation count
      try {
        const list = await getInvestigations();
        if (mounted) setInvestigationCount(list.length);
      } catch { /* ignore */ }

      // Load active case details
      const activeId = localStorage.getItem('caseintel-active-case-id');
      if (!activeId) { if (mounted) setActiveCase(null); return; }
      try {
        const data = await getInvestigation(activeId);
        if (mounted) setActiveCase({ caseNumber: data.caseNumber, status: data.status });
      } catch {
        if (mounted) setActiveCase(null);
      }
    };
    load();
    const handler = () => load();
    window.addEventListener('active-case-changed', handler);
    window.addEventListener('storage', handler);
    return () => {
      mounted = false;
      window.removeEventListener('active-case-changed', handler);
      window.removeEventListener('storage', handler);
    };
  }, []);

  return (
    <aside className="sidebar-root w-56 flex-shrink-0 flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-4 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'rgba(96,165,250,0.2)' }}>
            <Shield size={15} className="text-blue-300" />
          </div>
          <div>
            <div className="text-[14px] font-bold text-white tracking-wide">CaseIntel</div>
            <div className="text-[10px] uppercase tracking-widest" style={{ color: '#64748b' }}>Investigation System</div>
          </div>
        </div>
      </div>

      {/* Active Case */}
      <div className="px-4 py-3 mx-3 mt-3 rounded-lg" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}>
        <div className="text-[10px] uppercase tracking-widest mb-1" style={{ color: '#64748b' }}>Active Case</div>
        {activeCase ? (
          <>
            <div className="font-mono text-[12px] font-semibold text-white">{activeCase.caseNumber}</div>
            <div className="flex items-center gap-1 mt-1">
              <Dot size={14} className={activeCase.status === 'closed' ? 'text-green-400 -ml-1' : 'text-amber-400 -ml-1'} />
              <span className={`text-[11px] font-medium ${activeCase.status === 'closed' ? 'text-green-400' : 'text-amber-400'}`}>
                {activeCase.status === 'closed' ? 'Closed' : activeCase.status === 'pending' ? 'Pending Review' : 'Under Investigation'}
              </span>
            </div>
          </>
        ) : (
          <div className="text-[11px]" style={{ color: '#475569' }}>No active case</div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-3 overflow-y-auto">
        <div className="text-[10px] uppercase tracking-widest px-2 mb-2" style={{ color: '#475569' }}>Navigation</div>
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.to === '/'
              ? location.pathname === '/'
              : location.pathname === item.to || location.pathname.startsWith(item.to + '/');
          const isSubActive = item.sub ? location.pathname === item.to : false;
          const active = item.sub ? isSubActive : isActive;

          return (
            <React.Fragment key={item.to}>
              {item.dividerBefore && !item.sub && (
                <div style={{ height: '1px', background: 'rgba(255,255,255,0.06)', margin: '8px 0' }} />
              )}
              <NavLink
                to={item.to}
                className={`sidebar-nav-item ${active ? 'active' : ''} ${item.sub ? 'sub' : ''}`}
              >
                <span style={{ opacity: active ? 1 : 0.6 }}>{item.icon}</span>
                <span className="flex-1">{item.label}</span>
                {item.to === '/investigations' && (
                  <span
                    className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded"
                    style={{ background: 'rgba(37,99,235,0.3)', color: '#93c5fd' }}
                  >
                    {investigationCount}
                  </span>
                )}
                {active && <ChevronRight size={10} style={{ color: '#93c5fd', opacity: 0.7 }} />}
              </NavLink>
            </React.Fragment>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="text-[10px] uppercase tracking-widest mb-1" style={{ color: '#475569' }}>System Mode</div>
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${isBackendLive ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
          <span className={`text-[11px] font-medium ${isBackendLive ? 'text-emerald-400' : 'text-amber-400'}`}>
            {isBackendLive ? 'Live Data' : 'Backend Offline'}
          </span>
        </div>
        <div className="text-[10px] mt-1" style={{ color: '#475569' }}>
          {isBackendLive ? 'FastAPI :8000 Connected' : 'Waiting for Backend'}
        </div>
      </div>
    </aside>
  );
}
