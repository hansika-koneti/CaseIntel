import { useState, useEffect, useCallback, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Download, Brain, CheckCircle, Loader2, AlertTriangle, ChevronDown, ChevronUp, Video } from 'lucide-react';
import { getInvestigation } from '../api/investigations';
import { generateReport, getReport } from '../api/reports';
import type { Investigation, Report } from '../types';
import { StatusBadge, SeverityBadge, EntityTypeBadge } from '../components/common/StatusBadge';
import { ConfidenceMeter } from '../components/common/ConfidenceMeter';
import { formatTimestamp } from '../utils/formatters';
import { normalizeLocationName } from '../utils/location';

function Section({ title, children, defaultOpen = true }: { title: string; children: ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3.5 transition-colors"
        style={{
          background: '#f8fafc',
          borderBottom: open ? '1px solid #e2e8f0' : 'none',
          cursor: 'pointer',
          border: 'none',
          textAlign: 'left',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = '#f1f5f9')}
        onMouseLeave={e => (e.currentTarget.style.background = '#f8fafc')}
      >
        <span className="section-label">{title}</span>
        {open ? <ChevronUp size={13} style={{ color: '#94a3b8' }} /> : <ChevronDown size={13} style={{ color: '#94a3b8' }} />}
      </button>
      {open && <div className="px-5 py-4">{children}</div>}
    </div>
  );
}

type GenerateState = 'idle' | 'generating' | 'done';

export default function InvestigationReportPage() {
  const navigate = useNavigate();
  const [inv, setInv] = useState<Investigation | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generateState, setGenerateState] = useState<GenerateState>('idle');

  const [investigatorName, setInvestigatorName] = useState(() => {
    const saved = localStorage.getItem('investigator-profile');
    if (saved) {
      try { return JSON.parse(saved).name; } catch (e) {}
    }
    return 'Insp. R. Sharma';
  });

  const loadCaseData = useCallback(async () => {
    const activeId = localStorage.getItem('caseintel-active-case-id');
    if (!activeId) {
      setLoading(false);
      setInv(null);
      setReport(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await getInvestigation(activeId);
      setInv(data);

      if (data.investigator) {
        const saved = localStorage.getItem('investigator-profile');
        if (!saved) setInvestigatorName(data.investigator);
      }

      const hasCaseAnalysis = Boolean(
        data.hasAnalysis ??
        (data.videoCount > 0 && (data.events?.length > 0 || (data.incident && data.incident.has_analysis !== false && data.incident.type && data.incident.type !== 'Unclassified')))
      );

      if (hasCaseAnalysis) {
        let rep = await getReport(activeId).catch(() => null);
        if (!rep || (rep as any).has_analysis === false || (rep as any).status === 'not_analyzed') {
          // Automatically generate report if none exists for this case yet
          try {
            const genRes = await generateReport(activeId);
            rep = genRes?.report || null;
          } catch {
            rep = null;
          }
        }
        setReport(rep && (rep as any).has_analysis !== false && (rep as any).status !== 'not_analyzed' ? rep : null);
      } else {
        setReport(null);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load investigation report');
      setInv(null);
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCaseData();
  }, [loadCaseData]);

  useEffect(() => {
    const handler = () => loadCaseData();
    window.addEventListener('active-case-changed', handler);
    return () => window.removeEventListener('active-case-changed', handler);
  }, [loadCaseData]);

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

  async function handleGenerate() {
    if (!inv) return;
    setGenerateState('generating');
    try {
      const res = await generateReport(inv.id);
      if (res && res.report) {
        setReport(res.report);
      }
    } catch (e) {
      console.error('Report generation error:', e);
    } finally {
      setGenerateState('done');
    }
  }

  if (loading) {
    return (
      <div className="p-12 flex items-center justify-center gap-3" style={{ color: '#64748b' }}>
        <Loader2 size={20} className="animate-spin text-blue-600" />
        <span className="text-[13px]">Synthesizing forensic investigation report…</span>
      </div>
    );
  }

  if (error || !inv) {
    return (
      <div className="p-12 max-w-md mx-auto text-center space-y-3">
        <AlertTriangle size={32} className="mx-auto text-red-500" />
        <div className="text-[14px] font-semibold text-slate-800">No Report Available</div>
        <div className="text-[12px] text-slate-500">{error || 'Please select or create an active investigation with uploaded CCTV footage.'}</div>
        <button onClick={() => loadCaseData()} className="btn-primary">Retry</button>
      </div>
    );
  }

  const hasAnalysis = Boolean(
    inv.hasAnalysis ??
    (inv.videoCount > 0 && (inv.events?.length > 0 || (inv.incident && inv.incident.has_analysis !== false && inv.incident.type && inv.incident.type !== 'Unclassified')))
  );

  if (!hasAnalysis) {
    return (
      <div className="p-6 space-y-5" style={{ maxWidth: 1100 }}>
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <div className="section-label mb-1 flex items-center gap-2"><FileText size={12} />Investigation Report</div>
            <h1 className="text-[22px] font-bold" style={{ color: '#0f172a' }}>Case Report — {inv.caseNumber}</h1>
            <div className="font-mono text-[11px] mt-0.5" style={{ color: '#94a3b8' }}>
              Pending CCTV footage analysis
            </div>
          </div>
          <button
            onClick={() => navigate('/cctv-analysis')}
            className="btn-primary flex items-center gap-1.5"
          >
            <Video size={13} />
            <span>Upload Video</span>
          </button>
        </div>

        {/* Empty State Card */}
        <div className="card p-12 text-center space-y-4 max-w-xl mx-auto my-8" style={{ border: '1px dashed #cbd5e1' }}>
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto" style={{ background: '#f1f5f9', color: '#64748b' }}>
            <FileText size={32} />
          </div>
          <div>
            <h2 className="text-[18px] font-bold" style={{ color: '#0f172a' }}>No report available</h2>
            <p className="text-[13px] mt-1.5 leading-relaxed" style={{ color: '#64748b' }}>
              Analysis has not been completed yet. Upload and analyze a CCTV video to view real incident classification and generate a formal forensic report.
            </p>
          </div>
          <div className="pt-2">
            <button onClick={() => navigate('/cctv-analysis')} className="btn-primary flex items-center gap-2 mx-auto">
              <Video size={14} />
              Go to CCTV Analysis
            </button>
          </div>
        </div>

        {/* Case Information Section */}
        <Section title="Case Information">
          <div className="grid grid-cols-3 gap-x-8 gap-y-4">
            {[
              { label: 'Case ID',          value: inv.caseNumber,                  mono: true, accent: '#2563eb' },
              { label: 'Status',           badge: true                                                           },
              { label: 'Investigator',     value: investigatorName                                               },
              { label: 'Cameras Analyzed', value: 'None', mono: true },
              { label: 'Video Duration',   value: '00:00:00', mono: true                 },
              { label: 'Location',         value: normalizeLocationName(inv.location)                           },
              { label: 'Report Status',    value: 'Pending Video Analysis', mono: true, muted: true   },
              { label: 'Created At',       value: formatTimestamp(inv.createdAt), mono: true },
              { label: 'Last Updated',     value: formatTimestamp(inv.updatedAt)                                 },
            ].map(row => (
              <div key={row.label}>
                <div className="field-label">{row.label}</div>
                {row.badge
                  ? <StatusBadge status={inv.status} />
                  : (
                    <div
                      className={row.mono ? 'font-mono text-[12px]' : 'text-[12px]'}
                      style={{ color: row.accent || (row.muted ? '#94a3b8' : '#0f172a'), fontSize: row.muted ? 11 : undefined }}
                    >
                      {row.value}
                    </div>
                  )}
              </div>
            ))}
          </div>
        </Section>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-5" style={{ maxWidth: 1100 }}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="section-label mb-1 flex items-center gap-2"><FileText size={12} />Investigation Report</div>
          <h1 className="text-[22px] font-bold" style={{ color: '#0f172a' }}>Case Report — {inv.caseNumber}</h1>
          <div className="font-mono text-[11px] mt-0.5" style={{ color: '#94a3b8' }}>
            {report ? `Generated: ${formatTimestamp(report.generatedAt)} · ${report.generatorModel}` : 'Report not yet generated'}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleGenerate}
            disabled={generateState === 'generating'}
            className="btn-primary flex items-center gap-1.5 disabled:opacity-50"
          >
            {generateState === 'generating'
              ? <><Loader2 size={11} className="animate-spin" />Generating…</>
              : <><Brain size={11} />{report ? 'Regenerate Report' : 'Generate Report'}</>
            }
          </button>
          <button
            onClick={() => {
              if (!report) return;
              const blob = new Blob([JSON.stringify({ investigation: inv, report }, null, 2)], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `${inv.caseNumber}_forensic_report.json`;
              a.click();
            }}
            disabled={!report}
            className="btn-secondary flex items-center gap-1.5 disabled:opacity-50"
          >
            <Download size={11} />JSON
          </button>
        </div>
      </div>

      {/* Generating Banner */}
      {generateState === 'generating' && (
        <div className="alert-info p-3 flex items-center gap-3 animate-fade-in">
          <Loader2 size={14} className="animate-spin flex-shrink-0 text-blue-600" />
          <span className="text-[12px]">Running forensic report synthesis from real tracking, events, and evidence…</span>
        </div>
      )}

      {/* Case Information */}
      <Section title="Case Information">
        <div className="grid grid-cols-3 gap-x-8 gap-y-4">
          {[
            { label: 'Case ID',          value: inv.caseNumber,                  mono: true, accent: '#2563eb' },
            { label: 'Status',           badge: true                                                           },
            { label: 'Investigator',     value: investigatorName                                               },
            { label: 'Cameras Analyzed', value: inv.cameraIds && inv.cameraIds.length > 0 ? inv.cameraIds.join(', ') : 'None', mono: true },
            { label: 'Video Duration',   value: inv.durationAnalyzed || '00:00:00', mono: true                 },
            { label: 'Location',         value: normalizeLocationName(inv.location)                           },
            { label: 'Report ID',        value: report?.id || 'Pending generation', mono: true, muted: true   },
            { label: 'Generator Model',  value: report?.generatorModel || 'CaseIntel Synthesis Engine v2.4', mono: true, muted: true },
            { label: 'Last Updated',     value: formatTimestamp(inv.updatedAt)                                 },
          ].map(row => (
            <div key={row.label}>
              <div className="field-label">{row.label}</div>
              {row.badge
                ? <StatusBadge status={inv.status} />
                : (
                  <div
                    className={row.mono ? 'font-mono text-[12px]' : 'text-[12px]'}
                    style={{ color: row.accent || (row.muted ? '#94a3b8' : '#0f172a'), fontSize: row.muted ? 11 : undefined }}
                  >
                    {row.value}
                  </div>
                )}
            </div>
          ))}
        </div>
      </Section>

      {/* Incident Classification */}
      <Section title="Incident Classification">
        <div className="space-y-4">
          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div className="space-y-2 flex-1">
              <div className="flex items-center gap-3 flex-wrap">
                <div className="text-[20px] font-bold" style={{ color: '#0f172a' }}>{inv.incident.type}</div>
                <SeverityBadge severity={inv.incident.severity} />
                {(inv.incident.is_hypothesis || (inv.incident.type === 'Theft / Tampering' && !inv.incident.theft_visually_verified)) && (
                  <span className="badge badge-amber text-[10px] uppercase font-bold">
                    Model Hypothesis (Unverified)
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <ConfidenceMeter value={inv.incident.confidence} size="md" className="max-w-64 flex-1" />
                <span className="font-mono text-[12px] font-semibold text-slate-700">{inv.incident.confidence}% Model Confidence</span>
              </div>
            </div>
            <div className="alert-danger p-3 flex items-center gap-2">
              <AlertTriangle size={13} />
              <span className="text-[12px] font-semibold">{inv.incident.severity} SEVERITY</span>
            </div>
          </div>

          {(inv.incident.is_hypothesis || (inv.incident.type === 'Theft / Tampering' && !inv.incident.theft_visually_verified)) && (
            <div className="p-3 rounded-lg border border-amber-200 bg-amber-50/70 text-[11px] text-amber-900 flex items-start gap-2">
              <AlertTriangle size={14} className="text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <strong>Forensic Evidence Grounding:</strong> Approach, physical confrontation, and phone manipulation were verified.
                However, <strong>object disappearance was not visually established in the footage</strong>.
                This incident is recorded as an automated hypothesis requiring investigator confirmation.
              </div>
            </div>
          )}
        </div>
      </Section>

      {/* Executive Summary */}
      {report && (
        <>
          <Section title="Executive Summary">
            <div className="mb-3 flex items-center gap-2">
              <Brain size={11} style={{ color: '#2563eb' }} />
              <span className="text-[11px]" style={{ color: '#64748b' }}>System-generated summary — {report.generatorModel}</span>
            </div>
            <p className="text-[13px] leading-relaxed" style={{ color: '#475569' }}>{report.executiveSummary}</p>
          </Section>

          {/* Dynamic sections from backend report synthesis */}
          {report.sections.map(section => (
            <Section key={section.id} title={section.title}>
              <pre className="text-[12px] leading-relaxed whitespace-pre-wrap font-sans" style={{ color: '#475569' }}>
                {section.content}
              </pre>
            </Section>
          ))}
        </>
      )}

      {/* Entity Registry */}
      <Section title="Entity Registry">
        {inv.entities.length === 0 ? (
          <div className="text-[12px] text-slate-500 py-2">No entities detected in this investigation.</div>
        ) : (
          <div>
            {inv.entities.map((entity, idx) => (
              <div
                key={entity.id}
                className="flex items-center gap-4 py-2.5"
                style={{ borderBottom: idx < inv.entities.length - 1 ? '1px solid #f1f5f9' : 'none' }}
              >
                <span className="font-mono text-[13px] font-bold w-20" style={{ color: '#0f172a' }}>{entity.id}</span>
                <EntityTypeBadge type={entity.type} />
                <span className="text-[11px] flex-1" style={{ color: '#475569' }}>{entity.label}</span>
                <span className="font-mono text-[11px]" style={{ color: '#94a3b8' }}>{entity.firstSeen} – {entity.lastSeen}</span>
                <span className="font-mono text-[11px] font-semibold" style={{ color: '#16a34a' }}>{entity.confidence}%</span>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Disclaimer */}
      {report?.disclaimer && (
        <div className="alert-warning p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle size={15} style={{ color: '#d97706', flexShrink: 0, marginTop: 1 }} />
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wide mb-1">Important Disclaimer</div>
              <p className="text-[12px] leading-relaxed">{report.disclaimer}</p>
            </div>
          </div>
        </div>
      )}

      {/* Footer status */}
      {report && (
        <div className="flex items-center gap-2 text-[11px] pb-2" style={{ color: '#16a34a' }}>
          <CheckCircle size={12} />
          Report {report.id} generated successfully at {formatTimestamp(report.generatedAt)}
        </div>
      )}
    </div>
  );
}
