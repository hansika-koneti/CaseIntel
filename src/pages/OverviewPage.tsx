import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Shield, Clock, Video, Users, Car, Zap,
  AlertTriangle, TrendingUp, FileText, ChevronRight, Activity
} from 'lucide-react';
import { getInvestigation } from '../api/investigations';
import type { Investigation } from '../types';
import { StatusBadge, SeverityBadge } from '../components/common/StatusBadge';
import { ConfidenceMeter, ConfidenceRing } from '../components/common/ConfidenceMeter';
import { formatTimestamp, normalizeLocationName } from '../utils/formatters';


interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
}

function MetricCard({ icon, label, value, sub, accent = '#2563eb' }: MetricCardProps) {
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="section-label">{label}</div>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: `${accent}14`, color: accent }}>
          {icon}
        </div>
      </div>
      <div className="text-2xl font-bold font-mono" style={{ color: accent }}>{value}</div>
      {sub && <div className="text-[11px] mt-1" style={{ color: '#94a3b8' }}>{sub}</div>}
    </div>
  );
}

export default function OverviewPage() {
  const navigate = useNavigate();
  const [hoveredEvent, setHoveredEvent] = useState<string | null>(null);

  const [inv, setInv] = useState<Investigation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchActiveInvestigation = useCallback(async () => {
    const activeId = localStorage.getItem('caseintel-active-case-id');
    if (!activeId) {
      setInv(null);
      setLoading(false);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getInvestigation(activeId);
      setInv(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load investigation');
      setInv(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchActiveInvestigation();
  }, [fetchActiveInvestigation]);

  useEffect(() => {
    const handler = () => fetchActiveInvestigation();
    window.addEventListener('active-case-changed', handler);
    return () => window.removeEventListener('active-case-changed', handler);
  }, [fetchActiveInvestigation]);

  const [investigatorName, setInvestigatorName] = useState(() => {
    const saved = localStorage.getItem('investigator-profile');
    if (saved) {
      try { return JSON.parse(saved).name; } catch (e) {}
    }
    return inv?.investigator ?? 'Unassigned';
  });

  useEffect(() => {
    const handler = () => {
      const saved = localStorage.getItem('investigator-profile');
      if (saved) {
        try { setInvestigatorName(JSON.parse(saved).name); } catch (e) {}
      }
    };
    window.addEventListener('profile-updated', handler);
    return () => window.removeEventListener('profile-updated', handler);
  }, []);

  useEffect(() => {
    const saved = localStorage.getItem('investigator-profile');
    if (!saved && inv?.investigator) setInvestigatorName(inv.investigator);
  }, [inv]);

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="text-[13px]" style={{ color: '#94a3b8' }}>Loading investigation…</div>
      </div>
    );
  }

  if (!inv) {
    return (
      <div className="p-6 space-y-5" style={{ maxWidth: 1600 }}>
        <div>
          <div className="section-label mb-1">Investigation Overview</div>
          <h1 className="text-[22px] font-bold" style={{ color: '#0f172a' }}>Dashboard</h1>
        </div>
        <div className="card p-8 text-center">
          <Shield size={32} style={{ color: '#94a3b8', margin: '0 auto 12px' }} />
          <div className="text-[14px] font-semibold mb-2" style={{ color: '#475569' }}>No active investigation</div>
          <div className="text-[12px] mb-4" style={{ color: '#94a3b8' }}>
            {error
              ? `Error: ${error}`
              : 'Upload a CCTV video on the Analysis page to create an investigation.'}
          </div>
          <button onClick={() => navigate('/cctv-analysis')} className="btn-primary">
            Go to CCTV Analysis
          </button>
        </div>
      </div>
    );
  }

  const hasAnalysis = Boolean(
    inv.hasAnalysis ??
    (inv.videoCount > 0 && (inv.events?.length > 0 || (inv.incident && inv.incident.has_analysis !== false && inv.incident.type && inv.incident.type !== 'Unclassified')))
  );

  const suspiciousCount = inv.events.filter(e => e.isSuspicious).length;
  const personCount = inv.entities ? inv.entities.filter((e: { type: string }) => e.type === 'person').length : 0;
  const vehicleCount = inv.entities ? inv.entities.filter((e: { type: string }) => e.type === 'vehicle').length : 0;
  const personLabel = personCount === 1
    ? inv.entities?.find((e: { type: string }) => e.type === 'person')?.id ?? 'tracked'
    : `${personCount} subjects`;
  const vehicleLabel = vehicleCount === 1
    ? inv.entities?.find((e: { type: string }) => e.type === 'vehicle')?.id ?? 'tracked'
    : `${vehicleCount} vehicles`;

  return (
    <div className="p-6 space-y-5" style={{ maxWidth: 1600 }}>
      {/* Page Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="section-label mb-1">Investigation Overview</div>
          <h1 className="text-[22px] font-bold" style={{ color: '#0f172a' }}>Dashboard</h1>
          <div className="text-[12px] mt-0.5" style={{ color: '#94a3b8' }}>
            Last updated: {formatTimestamp(inv.updatedAt)}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={inv.status} />
          {hasAnalysis ? (
            <button
              onClick={() => navigate('/incident?view=technical')}
              className="flex items-center gap-1.5 btn-secondary"
              title="View detailed XGBoost, TreeSHAP, and feature attribution analysis"
            >
              <Activity size={12} style={{ color: '#2563eb' }} />
              <span style={{ color: '#2563eb' }}>View Full Analysis</span>
            </button>
          ) : (
            <button
              onClick={() => navigate('/cctv-analysis')}
              className="flex items-center gap-1.5 btn-primary"
            >
              <Video size={13} />
              <span>Upload Video</span>
            </button>
          )}
        </div>
      </div>

      {!hasAnalysis ? (
        /* Explicit Empty State for New Investigation with No Video */
        <div className="space-y-5">
          <div className="card p-10 text-center space-y-4" style={{ border: '1px dashed #cbd5e1' }}>
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto" style={{ background: '#eff6ff', color: '#2563eb' }}>
              <Video size={28} />
            </div>
            <div className="max-w-md mx-auto">
              <h2 className="text-[18px] font-bold" style={{ color: '#0f172a' }}>No analysis done yet</h2>
              <p className="text-[13px] mt-1.5 leading-relaxed" style={{ color: '#64748b' }}>
                This investigation has no analyzed CCTV footage. Upload a surveillance video to extract forensic entities, classify behavioral events, and generate explainable ML incident predictions.
              </p>
            </div>
            <div className="pt-2">
              <button onClick={() => navigate('/cctv-analysis')} className="btn-primary flex items-center gap-2 mx-auto">
                <Video size={14} />
                Upload CCTV Footage
              </button>
            </div>
          </div>

          {/* Case Information Summary */}
          <div className="card p-5">
            <div className="section-label mb-4 flex items-center gap-2">
              <Shield size={12} />Case Details
            </div>
            <div className="grid grid-cols-4 gap-x-8 gap-y-4">
              {[
                { label: 'Case ID',         value: inv.caseNumber,                       mono: true, accent: '#2563eb' },
                { label: 'Status',          value: '',                                    badge: true },
                { label: 'Investigator',    value: investigatorName                                   },
                { label: 'Location',        value: normalizeLocationName(inv.location)                },
                { label: 'Videos Analyzed', value: '0 videos',                           mono: true   },
                { label: 'Incident Status', value: 'Pending Video Analysis',              muted: true  },
                { label: 'Created At',      value: formatTimestamp(inv.createdAt),       mono: true   },
                { label: 'Pipeline',        value: 'YOLOv11 + ByteTrack + XGBoost Ready', muted: true },
              ].map(row => (
                <div key={row.label}>
                  <div className="field-label">{row.label}</div>
                  {row.badge ? (
                    <StatusBadge status={inv.status} />
                  ) : (
                    <div
                      className={row.mono ? 'font-mono text-[13px]' : 'text-[13px]'}
                      style={{
                        color: row.accent || (row.muted ? '#94a3b8' : '#0f172a'),
                        fontWeight: row.accent ? 600 : 400,
                      }}
                    >
                      {row.value}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* Real Analyzed Dashboard */
        <>
          {/* Case Summary + Incident Risk */}
          <div className="grid grid-cols-3 gap-4">
            {/* Case Summary */}
            <div className="col-span-2 card p-5">
              <div className="section-label mb-4 flex items-center gap-2">
                <Shield size={12} />Case Summary
              </div>
              <div className="grid grid-cols-3 gap-x-8 gap-y-4">
                {[
                  { label: 'Case ID',         value: inv.caseNumber,           mono: true,  accent: '#2563eb' },
                  { label: 'Status',          value: '',                        badge: true  },
                  { label: 'Incident Type',   value: inv.incident.type || 'Unclassified', bold: true },
                  { label: 'CCTV Sources',    value: inv.cameraIds.join(', '),  mono: true   },
                  { label: 'Duration',        value: inv.durationAnalyzed,      mono: true   },
                  { label: 'Investigator',    value: investigatorName                        },
                  { label: 'Location',        value: normalizeLocationName(inv.location)     },
                  { label: 'Videos Analyzed', value: String(inv.videoCount),    mono: true   },
                  { label: 'Classifier',      value: inv.incident.classifierVersion, mono: true, muted: true },
                ].map(row => (
                  <div key={row.label}>
                    <div className="field-label">{row.label}</div>
                    {row.badge
                      ? <StatusBadge status={inv.status} />
                      : (
                        <div
                          className={row.mono ? 'font-mono text-[13px]' : 'text-[13px]'}
                          style={{
                            color: row.accent || (row.muted ? '#94a3b8' : '#0f172a'),
                            fontWeight: row.bold ? 600 : 400,
                            fontSize: row.muted ? 11 : undefined,
                          }}
                        >
                          {row.value}
                        </div>
                      )}
                  </div>
                ))}
              </div>
              <div className="mt-4 pt-4" style={{ borderTop: '1px solid #e2e8f0' }}>
                <ConfidenceMeter value={inv.incident.confidence} size="md" />
              </div>
            </div>

            {/* Incident Risk */}
            <div className="card p-5 flex flex-col" style={{ border: '1px solid #fecaca' }}>
              <div className="section-label mb-3 flex items-center gap-2">
                <AlertTriangle size={12} style={{ color: '#dc2626' }} />
                Incident Detected
              </div>
              <div className="flex-1 flex flex-col items-center justify-center gap-3 py-2">
                <div className="relative">
                  <ConfidenceRing value={inv.incident.confidence} size={100} />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="font-mono text-[18px] font-bold" style={{ color: '#0f172a' }}>
                      {inv.incident.confidence.toFixed(1)}%
                    </div>
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-[16px] font-bold mb-1.5" style={{ color: '#0f172a' }}>{inv.incident.type}</div>
                  {inv.incident.severity && <SeverityBadge severity={inv.incident.severity} />}
                </div>
              </div>
              <button
                onClick={() => navigate('/incident?view=summary')}
                className="mt-3 w-full py-2 btn-secondary flex items-center justify-center gap-1.5"
                title="View investigator executive summary and key findings"
              >
                View Incident <ChevronRight size={12} />
              </button>
            </div>
          </div>

          {/* Key Metrics */}
          <div>
            <div className="section-label mb-3 flex items-center gap-2">
              <Activity size={12} />Key Metrics
            </div>
            <div className="grid grid-cols-6 gap-3">
              <MetricCard icon={<Video size={14} />}         label="Videos Analyzed"    value={inv.videoCount}              sub={`${(inv.cameraIds ?? []).length || 1} camera${(inv.cameraIds ?? []).length !== 1 ? 's' : ''}`} accent="#2563eb" />
              <MetricCard icon={<Users size={14} />}         label="Persons Detected"   value={personCount}                 sub={personLabel}       accent="#0284c7" />
              <MetricCard icon={<Car size={14} />}           label="Vehicles Detected"  value={vehicleCount}                sub={vehicleLabel}      accent="#7c3aed" />
              <MetricCard icon={<Zap size={14} />}           label="Events Extracted"   value={inv.events.length}           sub="From pipeline"      accent="#d97706" />
              <MetricCard icon={<AlertTriangle size={14} />} label="Suspicious Events"  value={suspiciousCount}             sub="Flagged by system"  accent="#dc2626" />
              <MetricCard icon={<TrendingUp size={14} />}    label="Overall Confidence" value={`${inv.incident.confidence}%`} sub={inv.incident.severity ? `${inv.incident.severity} severity` : 'HIGH severity'} accent="#16a34a" />
            </div>
          </div>

          {/* Timeline Preview + AI Insight */}
          <div className="grid grid-cols-3 gap-4">
            {/* Timeline */}
            <div className="col-span-2 card p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="section-label flex items-center gap-2">
                  <Clock size={12} />Investigation Timeline
                </div>
                <button
                  onClick={() => navigate('/timeline')}
                  className="text-[11px] font-medium flex items-center gap-1"
                  style={{ color: '#2563eb' }}
                >
                  Full Timeline <ChevronRight size={10} />
                </button>
              </div>
              <div className="space-y-0">
                {inv.events.map((event, idx) => (
                  <div
                    key={event.id}
                    className="flex items-start gap-3 py-2.5 cursor-pointer group transition-colors rounded-md px-2 -mx-2"
                    style={{ background: hoveredEvent === event.id ? '#f8fafc' : 'transparent' }}
                    onMouseEnter={() => setHoveredEvent(event.id)}
                    onMouseLeave={() => setHoveredEvent(null)}
                    onClick={() => navigate('/timeline')}
                  >
                    <div className="flex flex-col items-center mt-1">
                      <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${event.isSuspicious ? 'timeline-dot-suspicious' : 'timeline-dot-normal'}`}
                        style={{
                          background: event.isSuspicious ? '#dc2626' : '#3b82f6',
                          border: `2px solid ${event.isSuspicious ? '#b91c1c' : '#2563eb'}`,
                        }}
                      />
                      {idx < inv.events.length - 1 && (
                        <div className="w-px h-6 mt-1" style={{ background: '#e2e8f0' }} />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-mono text-[11px] font-semibold" style={{ color: '#2563eb' }}>{event.timestamp}</span>
                        <span
                          className="font-mono text-[10px] px-1.5 py-0.5 rounded"
                          style={{ background: '#f1f5f9', color: '#475569', border: '1px solid #e2e8f0' }}
                        >
                          {event.entityId}
                        </span>
                        {event.isSuspicious && (
                          <span className="badge badge-red text-[10px]">SUSPICIOUS</span>
                        )}
                      </div>
                      <div className="text-[12px] font-medium" style={{ color: '#0f172a' }}>{event.action}</div>
                      <div className="text-[11px]" style={{ color: '#94a3b8' }}>{normalizeLocationName(event.location)} · Cam {event.cameraId} · {event.confidence}%</div>
                    </div>
                    <ChevronRight size={12} style={{ color: '#cbd5e1', marginTop: 4, flexShrink: 0 }} />
                  </div>
                ))}
              </div>
            </div>

            {/* Case Insight */}
            <div className="card p-5 flex flex-col" style={{ border: '1px solid #bfdbfe' }}>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-6 h-6 rounded-lg flex items-center justify-center" style={{ background: '#dbeafe', border: '1px solid #bfdbfe' }}>
                  <FileText size={12} style={{ color: '#2563eb' }} />
                </div>
                <div>
                  <div className="section-label">Case Insight</div>
                  <div className="text-[10px]" style={{ color: '#94a3b8' }}>System-generated · {inv.incident.classifierVersion}</div>
                </div>
              </div>
              <div className="flex-1 rounded-lg p-3" style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                <p className="text-[12px] leading-relaxed" style={{ color: '#475569' }}>{inv.aiInsight}</p>
              </div>
              <div className="mt-3 pt-3 text-[10px] flex items-center gap-1.5" style={{ borderTop: '1px solid #e2e8f0', color: '#94a3b8' }}>
                <AlertTriangle size={10} style={{ color: '#d97706' }} />
                System-generated. Requires investigator validation.
              </div>
              <button
                onClick={() => navigate('/report')}
                className="mt-3 w-full py-2 btn-secondary flex items-center justify-center gap-1.5"
              >
                View Full Report <ChevronRight size={12} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
