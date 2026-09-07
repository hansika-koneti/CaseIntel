import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bell, User, Activity, Clock, CheckCircle, X, Shield, Mail,
  AlertTriangle, AlertOctagon, Video, FileText, Check, ChevronRight
} from 'lucide-react';
import { checkSystemHealth } from '../../api/system';
import { getInvestigation } from '../../api/investigations';
import { getNotifications, type NotificationItem } from '../../api/notifications';

interface InvestigatorProfile {
  name: string;
  role: string;
  badge: string;
  department: string;
  email: string;
}

const DEFAULT_PROFILE: InvestigatorProfile = {
  name: 'Insp. R. Sharma',
  role: 'Senior Investigator',
  badge: 'B-4082',
  department: 'Cyber & CCTV Forensic Division',
  email: 'r.sharma@investigation.gov',
};

export default function TopBar() {
  const navigate = useNavigate();
  const [now, setNow] = useState(new Date());
  const [isLive, setIsLive] = useState(false);
  const [activeCase, setActiveCase] = useState<{ caseNumber: string; status: string } | null>(null);

  // ── Live Notifications State ─────────────────────────────────────────────
  const notifRef = useRef<HTMLDivElement>(null);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [readIds, setReadIds] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem('caseintel-read-notifications');
      return saved ? new Set(JSON.parse(saved)) : new Set();
    } catch {
      return new Set();
    }
  });

  // Fetch real notifications from active investigation or recent cases
  useEffect(() => {
    let mounted = true;
    const fetchNotifs = async () => {
      try {
        const activeId = localStorage.getItem('caseintel-active-case-id') || undefined;
        const res = await getNotifications(activeId);
        if (mounted) {
          setNotifications(res.notifications || []);
        }
      } catch (err) {
        // Polling catch
      }
    };

    fetchNotifs();
    const interval = setInterval(fetchNotifs, 10000);
    const handler = () => fetchNotifs();
    window.addEventListener('active-case-changed', handler);
    return () => {
      mounted = false;
      clearInterval(interval);
      window.removeEventListener('active-case-changed', handler);
    };
  }, []);

  // Dismiss notification popover on click outside or Escape
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setIsNotifOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsNotifOpen(false);
    };
    if (isNotifOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isNotifOpen]);

  const markAsRead = (id: string) => {
    setReadIds(prev => {
      const next = new Set(prev).add(id);
      localStorage.setItem('caseintel-read-notifications', JSON.stringify(Array.from(next)));
      return next;
    });
  };

  const markAllAsRead = () => {
    setReadIds(prev => {
      const next = new Set(prev);
      notifications.forEach(n => next.add(n.id));
      localStorage.setItem('caseintel-read-notifications', JSON.stringify(Array.from(next)));
      return next;
    });
  };

  const unreadCount = notifications.filter(n => !readIds.has(n.id)).length;

  const handleNotificationClick = (item: NotificationItem) => {
    markAsRead(item.id);
    setIsNotifOpen(false);
    if (item.investigationId) {
      localStorage.setItem('caseintel-active-case-id', item.investigationId);
      window.dispatchEvent(new Event('active-case-changed'));
    }
    navigate(item.link);
  };

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        const res = await checkSystemHealth();
        if (mounted) setIsLive(res.status === 'healthy');
      } catch {
        if (mounted) setIsLive(false);
      }
    };
    check();
    const interval = setInterval(check, 5000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  // Fetch real case details from backend when active-case-id changes
  useEffect(() => {
    let mounted = true;
    const load = async () => {
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
    return () => { mounted = false; window.removeEventListener('active-case-changed', handler); };
  }, []);

  const [profile, setProfile] = useState<InvestigatorProfile>(() => {
    const saved = localStorage.getItem('investigator-profile');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return DEFAULT_PROFILE;
  });
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [editForm, setEditForm] = useState<InvestigatorProfile>(profile);

  useEffect(() => {
    const interval = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);


  useEffect(() => {
    const handler = () => {
      const saved = localStorage.getItem('investigator-profile');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          setProfile(parsed);
          setEditForm(parsed);
        } catch (e) {}
      }
    };
    window.addEventListener('profile-updated', handler);
    return () => window.removeEventListener('profile-updated', handler);
  }, []);

  const timeStr = now.toLocaleTimeString('en-IN', { hour12: false });
  const dateStr = now.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    localStorage.setItem('investigator-profile', JSON.stringify(editForm));
    setProfile(editForm);
    setIsProfileOpen(false);
    window.dispatchEvent(new Event('profile-updated'));
  };

  return (
    <>
      <header
        className="h-12 flex items-center px-5 gap-4 flex-shrink-0 sticky top-0 z-10"
        style={{
          background: 'white',
          borderBottom: '1px solid #e2e8f0',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        }}
      >
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 mr-auto">
          <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#94a3b8' }}>Case</span>
          <span style={{ color: '#e2e8f0' }}>›</span>
          {activeCase ? (
            <>
              <span className="font-mono text-[12px] font-semibold" style={{ color: '#2563eb' }}>{activeCase.caseNumber}</span>
              <span style={{ color: '#e2e8f0' }}>·</span>
              <span className={`text-[12px] font-medium ${
                activeCase.status === 'closed' ? 'text-green-600' :
                activeCase.status === 'pending' ? 'text-slate-500' :
                'text-amber-600'
              }`}>
                {activeCase.status === 'closed' ? 'Closed' : activeCase.status === 'pending' ? 'Pending Review' : 'Under Investigation'}
              </span>
            </>
          ) : (
            <span className="text-[12px] font-medium" style={{ color: '#94a3b8' }}>No Active Case</span>
          )}
        </div>

        {/* System Status */}
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-md"
          style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}
        >
          {isLive
            ? <CheckCircle size={12} style={{ color: '#16a34a' }} />
            : <Activity size={12} style={{ color: '#d97706' }} />
          }
          <span className="text-[11px] font-medium" style={{ color: '#475569' }}>
            {isLive ? 'All AI Services Online' : 'Backend Connecting / Offline'}
          </span>
          <div className="flex items-center gap-1 ml-1">
            {[1, 2, 3, 4, 5].map((_, i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: isLive ? '#16a34a' : '#d97706' }}
              />
            ))}
          </div>
        </div>

        {/* Clock */}
        <div className="flex items-center gap-1.5" style={{ color: '#64748b' }}>
          <Clock size={12} />
          <span className="font-mono text-[11px]">{timeStr}</span>
          <span style={{ color: '#e2e8f0' }}>·</span>
          <span className="text-[11px]">{dateStr}</span>
        </div>

        {/* Notifications Popover */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => setIsNotifOpen(prev => !prev)}
            title="Investigation Notifications"
            aria-label="View notifications"
            className="relative w-8 h-8 flex items-center justify-center rounded-lg transition-all border cursor-pointer"
            style={{
              color: isNotifOpen ? '#2563eb' : '#64748b',
              background: isNotifOpen ? '#eff6ff' : '#f8fafc',
              borderColor: isNotifOpen ? '#bfdbfe' : '#e2e8f0',
            }}
            onMouseEnter={e => {
              if (!isNotifOpen) e.currentTarget.style.background = '#f1f5f9';
            }}
            onMouseLeave={e => {
              if (!isNotifOpen) e.currentTarget.style.background = '#f8fafc';
            }}
          >
            <Bell size={14} />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 min-w-[17px] h-[17px] px-1 bg-red-600 text-white text-[10px] font-bold rounded-full flex items-center justify-center shadow-xs border border-white">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Dropdown Panel */}
          {isNotifOpen && (
            <div
              className="absolute right-0 mt-2 w-[390px] max-w-[calc(100vw-2rem)] bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden z-50 animate-fade-in"
              style={{ maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}
            >
              {/* Header */}
              <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between bg-slate-50/90">
                <div className="flex items-center gap-2">
                  <Bell size={14} className="text-blue-600" />
                  <span className="font-semibold text-slate-800 text-[13px]">Notifications</span>
                  {unreadCount > 0 ? (
                    <span className="px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 text-[10px] font-bold">
                      {unreadCount} unread
                    </span>
                  ) : (
                    <span className="px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-500 text-[10px]">
                      0 unread
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="text-[11px] font-medium text-blue-600 hover:text-blue-800 transition-colors flex items-center gap-1 cursor-pointer bg-transparent border-none"
                  >
                    <Check size={12} /> Mark all read
                  </button>
                )}
              </div>

              {/* Notification Items List */}
              <div className="overflow-y-auto flex-1 divide-y divide-slate-100" style={{ maxHeight: '360px' }}>
                {notifications.length === 0 ? (
                  <div className="py-8 px-4 text-center">
                    <CheckCircle size={28} className="mx-auto text-emerald-500 mb-2 opacity-80" />
                    <div className="text-[13px] font-semibold text-slate-800">No new notifications</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">All forensic feeds and investigations are up to date.</div>
                  </div>
                ) : (
                  notifications.map(item => {
                    const isUnread = !readIds.has(item.id);
                    return (
                      <div
                        key={item.id}
                        onClick={() => handleNotificationClick(item)}
                        className={`p-3.5 hover:bg-slate-50 cursor-pointer transition-colors flex gap-3 items-start ${
                          isUnread ? 'bg-blue-50/35' : ''
                        }`}
                      >
                        <div
                          className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                          style={{
                            background:
                              item.type === 'suspicious_event'
                                ? '#fef2f2'
                                : item.type === 'incident'
                                ? '#f5f3ff'
                                : item.type === 'evidence'
                                ? '#eff6ff'
                                : '#f8fafc',
                            color:
                              item.type === 'suspicious_event'
                                ? '#dc2626'
                                : item.type === 'incident'
                                ? '#7c3aed'
                                : item.type === 'evidence'
                                ? '#2563eb'
                                : '#475569',
                            border: `1px solid ${
                              item.type === 'suspicious_event'
                                ? '#fecaca'
                                : item.type === 'incident'
                                ? '#ddd6fe'
                                : item.type === 'evidence'
                                ? '#bfdbfe'
                                : '#e2e8f0'
                            }`,
                          }}
                        >
                          {item.type === 'suspicious_event' && <AlertTriangle size={13} />}
                          {item.type === 'incident' && <AlertOctagon size={13} />}
                          {item.type === 'evidence' && <Shield size={13} />}
                          {item.type === 'video_analysis' && <Video size={13} />}
                          {item.type === 'report' && <FileText size={13} />}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-1 mb-0.5">
                            <span className="text-[12px] font-semibold text-slate-900 truncate">{item.title}</span>
                            <span className="font-mono text-[10px] text-slate-400 flex-shrink-0">{item.timestamp}</span>
                          </div>
                          <p className="text-[11px] text-slate-600 line-clamp-2 leading-relaxed mb-1.5">{item.message}</p>
                          <div className="flex items-center justify-between text-[10px]">
                            <span className="font-mono text-slate-500 font-medium">{item.caseNumber}</span>
                            <span className="text-blue-600 font-semibold flex items-center gap-0.5 hover:underline">
                              {item.actionLabel || 'View'} <ChevronRight size={10} />
                            </span>
                          </div>
                        </div>

                        {isUnread && (
                          <div className="w-2 h-2 rounded-full bg-blue-600 flex-shrink-0 mt-1" />
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>

        {/* Investigator */}
        <div
          onClick={() => {
            setEditForm(profile);
            setIsProfileOpen(true);
          }}
          className="flex items-center gap-2 pl-3 cursor-pointer group hover:opacity-85 transition-opacity"
          style={{ borderLeft: '1px solid #e2e8f0' }}
        >
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center transition-colors group-hover:bg-[#dbeafe]"
            style={{ background: '#f1f5f9', border: '1px solid #cbd5e1' }}
          >
            <User size={13} style={{ color: '#2563eb' }} />
          </div>
          <div>
            <div className="text-[12px] font-semibold group-hover:text-[#2563eb] transition-colors" style={{ color: '#0f172a' }}>{profile.name}</div>
            <div className="text-[10px]" style={{ color: '#94a3b8' }}>{profile.role}</div>
          </div>
        </div>
      </header>

      {/* Profile Modal */}
      {isProfileOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-lg border border-slate-200 max-w-md w-full overflow-hidden animate-fade-in">
            {/* Header */}
            <div className="px-5 py-4 flex items-center justify-between border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Shield size={16} className="text-blue-600" />
                <span className="font-bold text-slate-800 text-[14px]">Investigator Credentials</span>
              </div>
              <button
                onClick={() => setIsProfileOpen(false)}
                className="text-slate-400 hover:text-slate-600 transition-colors border-none bg-transparent cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleSaveProfile} className="p-5 space-y-4">
              <div>
                <label className="field-label">Full Name</label>
                <input
                  type="text"
                  required
                  value={editForm.name}
                  onChange={e => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                  className="input-field"
                  placeholder="e.g. Insp. R. Sharma"
                />
              </div>

              <div>
                <label className="field-label">Rank / Designation</label>
                <input
                  type="text"
                  required
                  value={editForm.role}
                  onChange={e => setEditForm(prev => ({ ...prev, role: e.target.value }))}
                  className="input-field"
                  placeholder="e.g. Senior Investigator"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="field-label">Badge Number</label>
                  <input
                    type="text"
                    required
                    value={editForm.badge}
                    onChange={e => setEditForm(prev => ({ ...prev, badge: e.target.value }))}
                    className="input-field font-mono"
                    placeholder="e.g. B-4082"
                  />
                </div>
                <div>
                  <label className="field-label">Department</label>
                  <input
                    type="text"
                    required
                    value={editForm.department}
                    onChange={e => setEditForm(prev => ({ ...prev, department: e.target.value }))}
                    className="input-field"
                    placeholder="e.g. Cyber Division"
                  />
                </div>
              </div>

              <div>
                <label className="field-label">Email Address</label>
                <div className="relative">
                  <Mail size={12} className="absolute text-slate-400" style={{ left: 10, top: '50%', transform: 'translateY(-50%)' }} />
                  <input
                    type="email"
                    required
                    value={editForm.email}
                    onChange={e => setEditForm(prev => ({ ...prev, email: e.target.value }))}
                    className="input-field"
                    style={{ paddingLeft: 28 }}
                    placeholder="e.g. investigator@agency.gov"
                  />
                </div>
              </div>

              {/* Actions */}
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsProfileOpen(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

