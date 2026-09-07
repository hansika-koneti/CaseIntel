import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderOpen, ChevronRight, AlertTriangle, Clock, Plus, X, Shield, Loader2 } from 'lucide-react';
import { StatusBadge, SeverityBadge } from '../components/common/StatusBadge';
import { ConfidenceMeter } from '../components/common/ConfidenceMeter';
import {
  createInvestigation,
  getInvestigations,
  type InvestigationSummary as InvestigationItem,
} from '../api/investigations';
import { normalizeLocationName } from '../utils/location';

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  });
}

export default function InvestigationsPage() {
  const navigate = useNavigate();

  // ── Data State ──────────────────────────────────────────────────────────
  const [investigations, setInvestigations] = useState<InvestigationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ── Modal State ─────────────────────────────────────────────────────────
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // ── Form State ──────────────────────────────────────────────────────────
  const [caseNumber, setCaseNumber] = useState('');
  const [incidentType, setIncidentType] = useState('Suspicious Activity');
  const [location, setLocation] = useState('');
  const [severity, setSeverity] = useState<'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'>('HIGH');
  const [status, setStatus] = useState<'under_investigation' | 'closed' | 'pending'>('under_investigation');

  // ── Active Case (UI-only, kept in localStorage) ─────────────────────────
  const [activeCaseId, setActiveCaseId] = useState(() => {
    return localStorage.getItem('caseintel-active-case-id') || '';
  });

  useEffect(() => {
    const handler = () => {
      setActiveCaseId(localStorage.getItem('caseintel-active-case-id') || '');
    };
    window.addEventListener('active-case-changed', handler);
    return () => window.removeEventListener('active-case-changed', handler);
  }, []);

  // ── Investigator profile (UI-only, kept in localStorage) ─────────────────
  const [investigatorName, setInvestigatorName] = useState('Insp. R. Sharma');

  useEffect(() => {
    const loadProfile = () => {
      const saved = localStorage.getItem('investigator-profile');
      if (saved) {
        try { setInvestigatorName(JSON.parse(saved).name); } catch (e) {}
      }
    };
    loadProfile();
    window.addEventListener('profile-updated', loadProfile);
    return () => window.removeEventListener('profile-updated', loadProfile);
  }, []);

  // ── Fetch investigations from FastAPI ─────────────────────────────────────
  const fetchInvestigations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getInvestigations();
      setInvestigations(data);
      const currentActive = localStorage.getItem('caseintel-active-case-id');
      if ((!currentActive || !data.some(i => i.id === currentActive)) && data.length > 0) {
        localStorage.setItem('caseintel-active-case-id', data[0].id);
        setActiveCaseId(data[0].id);
        window.dispatchEvent(new Event('active-case-changed'));
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to connect to FastAPI backend';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInvestigations();
  }, [fetchInvestigations]);

  // ── Modal open ────────────────────────────────────────────────────────
  const handleOpenModal = () => {
    const count = investigations.length + 1;
    setCaseNumber(`CASE-2026-0${count < 10 ? '0' + count : count}`);
    setLocation('');
    setSubmitError(null);
    setIsModalOpen(true);
  };

  // ── Create via API ──────────────────────────────────────────────────
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitError(null);
    const payload = {
      caseNumber: caseNumber || `CASE-2026-0${investigations.length + 1}`,
      incidentType,
      severity,
      status,
      location: location.trim() || 'Location not specified',
      videoCount: 0,
      confidence: 0,
      investigator: investigatorName,
    };
    try {
      const newInv = await createInvestigation(payload);
      setInvestigations(prev => [newInv, ...prev]);
      localStorage.setItem('caseintel-active-case-id', newInv.id);
      localStorage.removeItem('caseintel-active-video-id');
      setActiveCaseId(newInv.id);
      window.dispatchEvent(new Event('active-case-changed'));
      window.dispatchEvent(new Event('active-video-changed'));
      setIsModalOpen(false);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create investigation on backend';
      setSubmitError(message);
    } finally {
      setIsSubmitting(false);
    }
  };


  // ── Dynamic stats ─────────────────────────────────────────────────────
  const totalCases = investigations.length;
  const underInvestigation = investigations.filter(i => i.status === 'under_investigation').length;
  const closedCases = investigations.filter(i => i.status === 'closed').length;
  const pendingCases = investigations.filter(i => i.status === 'pending').length;

  return (
    <div className="p-6 space-y-5" style={{ maxWidth: 1600 }}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="section-label mb-1 flex items-center gap-2">
            <FolderOpen size={12} />Investigations
          </div>
          <h1 className="text-[22px] font-bold" style={{ color: '#0f172a' }}>All Investigations</h1>
          <div className="text-[12px] mt-0.5" style={{ color: '#94a3b8' }}>
            {loading ? 'Loading…' : `${totalCases} cases in system`}
          </div>
        </div>
        <button onClick={handleOpenModal} className="btn-primary flex items-center gap-1.5 border-none">
          <Plus size={13} />New Investigation
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Total Cases',         value: totalCases,          color: '#0f172a' },
          { label: 'Under Investigation', value: underInvestigation,  color: '#d97706' },
          { label: 'Closed',              value: closedCases,         color: '#16a34a' },
          { label: 'Pending Review',      value: pendingCases,        color: '#64748b' },
        ].map(item => (
          <div key={item.label} className="card p-4">
            <div className="section-label mb-1">{item.label}</div>
            <div className="text-2xl font-bold font-mono" style={{ color: item.color }}>{item.value}</div>
          </div>
        ))}
      </div>

      {/* Loading state */}
      {loading && (
        <div className="card p-8 flex items-center justify-center gap-3" style={{ color: '#64748b' }}>
          <Loader2 size={18} className="animate-spin" />
          <span className="text-[13px]">Loading investigations…</span>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="card p-5 flex items-center justify-between gap-4" style={{ borderLeft: '4px solid #ef4444', background: '#fef2f2' }}>
          <div className="flex items-center gap-3">
            <AlertTriangle size={18} className="text-red-500 flex-shrink-0" />
            <div>
              <div className="text-[13px] font-semibold text-red-900">Backend Connection Error</div>
              <div className="text-[12px] text-red-700 mt-0.5">{error}</div>
            </div>
          </div>
          <button onClick={fetchInvestigations} className="btn-secondary text-[12px] py-1.5 px-3">
            Retry Connection
          </button>
        </div>
      )}

      {/* Investigation Table */}
      {!loading && (
        <div className="card overflow-hidden">
          <div className="px-5 py-3.5" style={{ borderBottom: '1px solid #e2e8f0', background: '#f8fafc' }}>
            <div className="section-label">Case Records</div>
          </div>
          <div>
            {investigations.length === 0 ? (
              <div className="p-8 text-center text-[13px]" style={{ color: '#94a3b8' }}>
                No investigations found. Click "New Investigation" to create the first case.
              </div>
            ) : (
              investigations.map((inv, idx) => (
                <div
                  key={inv.id}
                  onClick={() => {
                    localStorage.setItem('caseintel-active-case-id', inv.id);
                    localStorage.removeItem('caseintel-active-video-id');
                    window.dispatchEvent(new Event('active-case-changed'));
                    window.dispatchEvent(new Event('active-video-changed'));
                    navigate('/');
                  }}
                  className="flex items-center gap-4 px-5 py-4 cursor-pointer group transition-colors"
                  style={{
                    borderBottom: idx < investigations.length - 1 ? '1px solid #f1f5f9' : 'none',
                    background: inv.id === activeCaseId ? '#eff6ff' : 'white',
                  }}
                  onMouseEnter={e => { if (inv.id !== activeCaseId) (e.currentTarget as HTMLElement).style.background = '#f8fafc'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = inv.id === activeCaseId ? '#eff6ff' : 'white'; }}
                >
                  {/* Case Number + Status */}
                  <div style={{ minWidth: 160 }}>
                    <div className="font-mono text-[13px] font-bold flex items-center gap-2" style={{ color: '#2563eb' }}>
                      {inv.caseNumber}
                      {inv.id === activeCaseId && <span className="badge badge-blue text-[10px]">ACTIVE</span>}
                    </div>
                    <div className="text-[11px] mt-1" style={{ color: '#94a3b8' }}>
                      <Clock size={9} className="inline mr-1" />{formatDate(inv.createdAt)}
                    </div>
                  </div>

                  {/* Incident type + location */}
                  <div className="flex-1 min-w-0">
                    <div className="text-[13px] font-medium" style={{ color: '#0f172a' }}>
                      <AlertTriangle size={11} className="inline mr-1.5" style={{ color: '#d97706' }} />
                      {inv.incidentType}
                    </div>
                    <div className="text-[11px] mt-0.5" style={{ color: '#64748b' }}>{normalizeLocationName(inv.location)}</div>
                  </div>

                  {/* Badges */}
                  <div className="flex items-center gap-2">
                    <StatusBadge status={inv.status} />
                    <SeverityBadge severity={inv.severity} />
                  </div>

                  {/* Videos */}
                  <div className="text-[11px] text-center" style={{ color: '#64748b', minWidth: 60 }}>
                    {inv.videoCount} video{inv.videoCount > 1 ? 's' : ''}
                  </div>

                  {/* Investigator */}
                  <div className="text-[11px]" style={{ color: '#64748b', minWidth: 120 }}>
                    {inv.investigator}
                  </div>

                  {/* Confidence */}
                  <div style={{ width: 120 }}>
                    <ConfidenceMeter value={inv.confidence} size="sm" />
                  </div>

                  <ChevronRight size={14} style={{ color: '#cbd5e1', flexShrink: 0 }} />
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* New Investigation Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-lg border border-slate-200 max-w-lg w-full overflow-hidden animate-fade-in">
            {/* Header */}
            <div className="px-5 py-4 flex items-center justify-between border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Shield size={16} className="text-blue-600" />
                <span className="font-bold text-slate-800 text-[14px]">Initialize New Case</span>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 transition-colors border-none bg-transparent cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleCreate} className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="field-label">Case ID Reference</label>
                  <input
                    type="text"
                    required
                    value={caseNumber}
                    onChange={e => setCaseNumber(e.target.value)}
                    className="input-field font-mono font-semibold"
                    placeholder="e.g. CASE-2026-004"
                  />
                </div>
                <div>
                  <label className="field-label">Incident Type</label>
                  <select
                    value={incidentType}
                    onChange={e => setIncidentType(e.target.value)}
                    className="input-field"
                  >
                    <option value="Suspicious Activity">Suspicious Activity</option>
                    <option value="Unauthorized Access">Unauthorized Access</option>
                    <option value="Perimeter Breach">Perimeter Breach</option>
                    <option value="Object Theft">Object Theft</option>
                    <option value="Vandalism">Vandalism</option>
                    <option value="Unclassified">Unclassified</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="field-label">Primary Investigation Sector / Location</label>
                <input
                  type="text"
                  required
                  value={location}
                  onChange={e => setLocation(e.target.value)}
                  className="input-field"
                  placeholder="e.g. Block A, Main Entrance Warehouse"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="field-label">Case Severity</label>
                  <select
                    value={severity}
                    onChange={e => setSeverity(e.target.value as any)}
                    className="input-field"
                  >
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                    <option value="CRITICAL">CRITICAL</option>
                  </select>
                </div>
                <div>
                  <label className="field-label">Initial Status</label>
                  <select
                    value={status}
                    onChange={e => setStatus(e.target.value as any)}
                    className="input-field"
                  >
                    <option value="under_investigation">Under Investigation</option>
                    <option value="pending">Pending Review</option>
                    <option value="closed">Closed / Solved</option>
                  </select>
                </div>
              </div>

              <div className="p-3 bg-blue-50/50 border border-blue-100 rounded-lg text-[11px] text-blue-700">
                New investigation initialises clean with 0 videos, 0 entities, 0 events, and 0 evidence items. Forensic data will be populated from uploaded CCTV footage.
              </div>


              <div className="p-3 bg-slate-50 border border-slate-100 rounded-lg text-[11px] text-slate-500">
                Case investigator will be assigned as <span className="font-semibold text-slate-700">{investigatorName}</span> automatically based on current active profile.
              </div>

              {/* Submit error */}
              {submitError && (
                <div className="flex items-start gap-2 p-3 rounded-lg text-[11px]" style={{ background: '#fff5f5', border: '1px solid #fecaca' }}>
                  <span style={{ color: '#dc2626' }}>{submitError}</span>
                </div>
              )}

              {/* Actions */}
              <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="btn-secondary"
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary flex items-center gap-1.5" disabled={isSubmitting}>
                  {isSubmitting ? (
                    <><Loader2 size={13} className="animate-spin" />Creating…</>
                  ) : (
                    'Create Case File'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
