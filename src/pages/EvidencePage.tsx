import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Archive, Camera, Star, Eye, Link2, X, Loader2, ShieldCheck, AlertTriangle } from 'lucide-react';
import { getEvidence, getChainOfCustody, type ChainOfCustody } from '../api/evidence';
import { getEvents } from '../api/events';
import type { Evidence, InvestigationEvent } from '../types';
import { ConfidenceMeter } from '../components/common/ConfidenceMeter';

function EvidenceFramePlaceholder({
  evidenceId,
  cameraId = '',
  timestamp = '00:00',
  isKeyEvidence = false,
}: {
  evidenceId: string;
  cameraId?: string;
  timestamp?: string;
  isKeyEvidence?: boolean;
}) {
  // Hash-based color to give each evidence a unique but consistent colour
  const hash = evidenceId.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
  const hue = hash % 360;
  const bg = `hsl(${hue}, 30%, 15%)`;

  return (
    <div className="relative w-full aspect-video rounded overflow-hidden" style={{ background: bg }}>
      <div
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.3) 1px, transparent 1px)',
          backgroundSize: '30px 30px',
        }}
      />
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <div className="font-mono text-[10px] uppercase tracking-widest mb-1" style={{ color: 'rgba(255,255,255,0.3)' }}>
            FRAME CAPTURE
          </div>
          <div className="font-mono text-[13px] font-bold" style={{ color: 'rgba(255,255,255,0.5)' }}>{evidenceId}</div>
        </div>
      </div>
      <div className="absolute top-1.5 left-2 font-mono text-[9px]" style={{ color: '#4ade80' }}>● REC</div>
      <div className="absolute top-1.5 right-2 font-mono text-[9px]" style={{ color: 'rgba(255,255,255,0.3)' }}>{cameraId}</div>
      <div className="absolute bottom-1.5 left-2 right-2 flex justify-between">
        <span className="font-mono text-[9px]" style={{ color: 'rgba(255,255,255,0.4)' }}>{timestamp}</span>
        <span className="font-mono text-[9px]" style={{ color: 'rgba(255,255,255,0.4)' }}>[FORENSIC]</span>
      </div>
      {isKeyEvidence && (
        <div className="absolute top-1.5" style={{ left: '50%', transform: 'translateX(-50%)' }}>
          <span className="badge badge-amber text-[9px] flex items-center gap-1">
            <Star size={7} />KEY
          </span>
        </div>
      )}
    </div>
  );
}

export default function EvidencePage() {
  const navigate = useNavigate();

  // ── Data State ──────────────────────────────────────────────────────────
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [events, setEvents] = useState<InvestigationEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);
  const [chainOfCustody, setChainOfCustody] = useState<ChainOfCustody | null>(null);
  const [loadingChain, setLoadingChain] = useState(false);
  const [filterKey, setFilterKey] = useState<'all' | 'key'>('all');
  const [markedImportant, setMarkedImportant] = useState<Set<string>>(new Set<string>());

  const fetchEvidence = useCallback(async () => {
    const activeId = localStorage.getItem('caseintel-active-case-id');
    if (!activeId) {
      setLoading(false);
      setError('No active investigation. Upload a video on the CCTV Analysis page.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [evData, evtData] = await Promise.all([
        getEvidence(activeId),
        getEvents({ investigationId: activeId }),
      ]);
      setEvidenceList(evData);
      setEvents(evtData.events);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch evidence from backend';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEvidence();
  }, [fetchEvidence]);

  useEffect(() => {
    const handler = () => fetchEvidence();
    window.addEventListener('active-case-changed', handler);
    return () => window.removeEventListener('active-case-changed', handler);
  }, [fetchEvidence]);

  // Fetch chain of custody when evidence is selected
  useEffect(() => {
    if (!selectedEvidence) {
      setChainOfCustody(null);
      return;
    }
    let cancelled = false;
    setLoadingChain(true);
    getChainOfCustody(selectedEvidence.id)
      .then(res => {
        if (!cancelled) setChainOfCustody(res);
      })
      .catch(() => {
        if (!cancelled) setChainOfCustody(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingChain(false);
      });
    return () => { cancelled = true; };
  }, [selectedEvidence]);

  const filtered = evidenceList.filter(ev => {
    if (filterKey === 'key') return ev.isKeyEvidence;
    return true;
  });

  const linkedEvent = selectedEvidence ? events.find(e => e.id === selectedEvidence.eventId) : null;

  const avgConfidence = evidenceList.length > 0
    ? (evidenceList.reduce((a, e) => a + e.confidence, 0) / evidenceList.length).toFixed(1)
    : '0';

  return (
    <div className="p-6 space-y-5" style={{ maxWidth: 1600 }}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="section-label mb-1 flex items-center gap-2"><Archive size={12} />Evidence</div>
          <h1 className="text-[22px] font-bold" style={{ color: '#0f172a' }}>Evidence Registry</h1>
          <div className="text-[12px] mt-0.5" style={{ color: '#94a3b8' }}>
            {loading ? 'Loading evidence…' : `${evidenceList.length} evidence items · ${evidenceList.filter(e => e.isKeyEvidence).length} key evidence`}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setFilterKey('all')}
            className={`btn-secondary ${filterKey === 'all' ? 'border-blue-300' : ''}`}
            style={filterKey === 'all' ? { background: '#eff6ff', color: '#2563eb', borderColor: '#bfdbfe' } : {}}
          >
            All Evidence
          </button>
          <button
            onClick={() => setFilterKey('key')}
            className="btn-secondary flex items-center gap-1.5"
            style={filterKey === 'key' ? { background: '#fffbeb', color: '#d97706', borderColor: '#fde68a' } : {}}
          >
            <Star size={11} />Key Evidence
          </button>
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="card p-8 flex items-center justify-center gap-3" style={{ color: '#64748b' }}>
          <Loader2 size={18} className="animate-spin" />
          <span className="text-[13px]">Loading evidence from API…</span>
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
          <button onClick={fetchEvidence} className="btn-secondary text-[12px] py-1.5 px-3">
            Retry Connection
          </button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Total Items',      value: evidenceList.length,                                         color: '#0f172a' },
          { label: 'Key Evidence',     value: evidenceList.filter(e => e.isKeyEvidence).length,            color: '#d97706' },
          { label: 'Marked Important', value: markedImportant.size,                                        color: '#2563eb' },
          { label: 'Avg. Confidence',  value: `${avgConfidence}%`,                                         color: '#16a34a' },
        ].map(item => (
          <div key={item.label} className="card p-4">
            <div className="section-label mb-1">{item.label}</div>
            <div className="text-2xl font-bold font-mono" style={{ color: item.color }}>{item.value}</div>
          </div>
        ))}
      </div>

      <div className="flex gap-5">
        <div className="flex-1">
          {filtered.length === 0 ? (
            <div className="card p-12 text-center">
              <Archive size={32} style={{ color: '#cbd5e1', margin: '0 auto 12px' }} />
              <div className="text-[14px] font-semibold text-slate-700 mb-1">No evidence items recorded</div>
              <div className="text-[12px] text-slate-500 mb-4">
                Upload and analyze a video on the CCTV Analysis page to extract forensic evidence.
              </div>
              <button onClick={() => navigate('/cctv-analysis')} className="btn-primary">
                Go to CCTV Analysis
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-4">
              {filtered.map(ev => {
                const isSelected = selectedEvidence?.id === ev.id;
                const isImportant = markedImportant.has(ev.id);
                return (
                  <div
                    key={ev.id}
                    onClick={() => setSelectedEvidence(isSelected ? null : ev)}
                    className="card card-hover cursor-pointer transition-all overflow-hidden"
                    style={{
                      border: isSelected ? '1.5px solid #2563eb' : '1px solid #e2e8f0',
                      background: isSelected ? '#f8fafc' : 'white',
                    }}
                  >
                    <EvidenceFramePlaceholder
                      evidenceId={ev.id}
                      cameraId={ev.cameraId}
                      timestamp={ev.timestamp}
                      isKeyEvidence={ev.isKeyEvidence}
                    />
                    <div className="p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[12px] font-bold" style={{ color: '#0f172a' }}>{ev.id}</span>
                    <div className="flex items-center gap-1">
                      {isImportant && (
                        <Star size={11} style={{ color: '#d97706', fill: '#d97706' }} />
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-[10px]" style={{ color: '#64748b' }}>
                    <Camera size={9} />
                    <span className="font-mono">{ev.cameraId}</span>
                    <span>·</span>
                    <span className="font-mono text-[10px]" style={{ color: '#2563eb' }}>{ev.timestamp}</span>
                  </div>
                  <div className="text-[11px]" style={{ color: '#475569' }}>{ev.type}</div>
                  <div className="flex items-center gap-1 flex-wrap">
                    <span className="badge badge-blue font-mono text-[10px]">{ev.primaryEntityId}</span>
                    {ev.secondaryEntityId && (
                      <>
                        <span style={{ color: '#cbd5e1', fontSize: 10 }}>→</span>
                        <span className="badge font-mono text-[10px]" style={{ background: '#f5f3ff', color: '#5b21b6', borderColor: '#ddd6fe', border: '1px solid' }}>{ev.secondaryEntityId}</span>
                      </>
                    )}
                  </div>
                  <ConfidenceMeter value={ev.confidence} size="sm" showLabel={false} />
                  <div className="text-[10px]" style={{ color: '#94a3b8' }}>
                    {ev.confidence}% confidence
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>

        {/* Detail Panel */}
        {selectedEvidence ? (
          <div className="w-72 flex-shrink-0 card p-4 h-fit animate-fade-in">
            <div className="flex items-center justify-between mb-4">
              <div className="section-label">Evidence Detail</div>
              <button onClick={() => setSelectedEvidence(null)} style={{ color: '#94a3b8' }}>
                <X size={13} />
              </button>
            </div>

            <div className="space-y-3">
              {[
                { label: 'Evidence ID', value: selectedEvidence.id,         mono: true, accent: '#0f172a' },
                { label: 'Timestamp',   value: selectedEvidence.timestamp,  mono: true, accent: '#2563eb' },
                { label: 'Camera',      value: selectedEvidence.cameraId,   mono: true, accent: '#7c3aed' },
                { label: 'Type',        value: selectedEvidence.type                                      },
              ].map(row => (
                <div key={row.label}>
                  <div className="field-label">{row.label}</div>
                  <div className={row.mono ? 'font-mono text-[12px]' : 'text-[12px]'} style={{ color: row.accent || '#475569' }}>
                    {row.value}
                  </div>
                </div>
              ))}

              <div>
                <div className="field-label">Entities</div>
                <div className="flex flex-wrap gap-1">
                  <span className="badge badge-blue font-mono text-[10px]">{selectedEvidence.primaryEntityId}</span>
                  {selectedEvidence.secondaryEntityId && (
                    <span className="badge font-mono text-[10px]" style={{ background: '#f5f3ff', color: '#5b21b6', borderColor: '#ddd6fe', border: '1px solid' }}>
                      {selectedEvidence.secondaryEntityId}
                    </span>
                  )}
                </div>
              </div>

              <div>
                <div className="field-label">Confidence</div>
                <ConfidenceMeter value={selectedEvidence.confidence} size="sm" />
              </div>

              <div>
                <div className="field-label">Description</div>
                <div className="text-[11px] leading-relaxed" style={{ color: '#475569' }}>{selectedEvidence.description}</div>
              </div>

              {linkedEvent && (
                <div>
                  <div className="field-label flex items-center gap-1"><Link2 size={9} />Linked Event</div>
                  <div className="p-2.5 rounded-lg" style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                    <div className="font-mono text-[10px] font-semibold mb-1" style={{ color: '#d97706' }}>{linkedEvent.id}</div>
                    <div className="text-[11px]" style={{ color: '#475569' }}>{linkedEvent.action}</div>
                  </div>
                </div>
              )}

              {/* Chain of Custody & SHA-256 */}
              {(selectedEvidence.sha256 || chainOfCustody) && (
                <div>
                  <div className="field-label flex items-center gap-1">
                    <ShieldCheck size={10} style={{ color: '#059669' }} />
                    Chain of Custody & Integrity
                  </div>
                  <div className="p-2.5 rounded-lg text-[10px] space-y-1.5" style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                    {selectedEvidence.sha256 && (
                      <div className="font-mono text-[9px] break-all" style={{ color: '#059669' }}>
                        <span className="font-semibold text-slate-600">SHA-256: </span>{selectedEvidence.sha256.substring(0, 16)}…
                      </div>
                    )}
                    {loadingChain && <div className="text-[10px] text-slate-400">Loading custody log…</div>}
                    {chainOfCustody && chainOfCustody.chain.map((c, i) => (
                      <div key={i} className="flex items-center justify-between text-[10px] pt-1" style={{ borderTop: i > 0 ? '1px dashed #e2e8f0' : 'none' }}>
                        <span className="font-semibold text-slate-700">{c.action}</span>
                        <span className="text-slate-500 font-mono text-[9px]">{c.actor}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="pt-3 space-y-2" style={{ borderTop: '1px solid #e2e8f0' }}>
                <button
                  onClick={() => navigate('/cctv-analysis/video')}
                  className="btn-secondary w-full flex items-center justify-center gap-2"
                >
                  <Eye size={11} />Jump to Video Timestamp
                </button>
                <button
                  onClick={() => {
                    const s = new Set(markedImportant);
                    if (s.has(selectedEvidence.id)) s.delete(selectedEvidence.id);
                    else s.add(selectedEvidence.id);
                    setMarkedImportant(s);
                  }}
                  className="w-full flex items-center justify-center gap-2 py-2 rounded-md text-[12px] font-medium transition-colors"
                  style={{
                    border: `1px solid ${markedImportant.has(selectedEvidence.id) ? '#fde68a' : '#e2e8f0'}`,
                    background: markedImportant.has(selectedEvidence.id) ? '#fffbeb' : 'white',
                    color: markedImportant.has(selectedEvidence.id) ? '#d97706' : '#475569',
                    cursor: 'pointer',
                  }}
                >
                  <Star size={11} style={{ fill: markedImportant.has(selectedEvidence.id) ? '#d97706' : 'none' }} />
                  {markedImportant.has(selectedEvidence.id) ? 'Marked Important' : 'Mark as Important'}
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="w-72 flex-shrink-0 card p-6 flex flex-col items-center justify-center h-fit">
            <Archive size={28} style={{ color: '#cbd5e1', marginBottom: 12 }} />
            <div className="text-[12px] text-center" style={{ color: '#94a3b8' }}>
              Select an evidence item to view details and actions
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
