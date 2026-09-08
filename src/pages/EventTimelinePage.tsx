import { useState, useEffect, useCallback } from 'react';
import { Clock, Filter, AlertTriangle, CheckCircle, User, Car, X, ChevronDown, Loader2 } from 'lucide-react';
import { getEvents } from '../api/events';
import type { InvestigationEvent, Evidence } from '../types';
import { EntityTypeBadge } from '../components/common/StatusBadge';
import { ConfidenceMeter } from '../components/common/ConfidenceMeter';
import { normalizeLocationName } from '../utils/location';

function parseTimestampToSeconds(ts: string): number | null {
  if (!ts) return null;
  if (ts.includes(':')) {
    const parts = ts.split(':').map(Number);
    if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
      return parts[0] * 60 + parts[1];
    }
    if (parts.length === 3 && !isNaN(parts[0]) && !isNaN(parts[1]) && !isNaN(parts[2])) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }
  }
  const parsed = Date.parse(ts);
  if (!isNaN(parsed)) {
    return Math.floor(parsed / 1000);
  }
  return null;
}

function computeTimeSpan(eventsList: InvestigationEvent[]): string {
  if (eventsList.length === 0) return '00:00';
  const secList = eventsList
    .map(e => parseTimestampToSeconds(e.timestamp))
    .filter((s): s is number => s !== null);
  if (secList.length === 0) return '00:00';
  const minSec = Math.min(...secList);
  const maxSec = Math.max(...secList);
  const diff = Math.max(0, maxSec - minSec);
  const mm = Math.floor(diff / 60);
  const ss = diff % 60;
  return `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`;
}

export default function EventTimelinePage() {
  // ── Data state ────────────────────────────────────────────────────────────
  const [events, setEvents] = useState<InvestigationEvent[]>([]);
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEvents = useCallback(async () => {
    const activeId = localStorage.getItem('caseintel-active-case-id');
    if (!activeId) {
      setEvents([]);
      setEvidenceList([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getEvents({ investigationId: activeId });
      setEvents(data.events);
      setEvidenceList(data.evidence);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch events from backend';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  useEffect(() => {
    const handler = () => fetchEvents();
    window.addEventListener('active-case-changed', handler);
    return () => window.removeEventListener('active-case-changed', handler);
  }, [fetchEvents]);

  const [filterEntity, setFilterEntity]       = useState('all');
  const [filterSuspicious, setFilterSuspicious] = useState<'all' | 'suspicious' | 'normal'>('all');
  const [filterConf, setFilterConf]           = useState(0);
  const [selectedEvent, setSelectedEvent]     = useState<InvestigationEvent | null>(null);
  const [showFilters, setShowFilters]         = useState(false);

  const entities = ['all', ...Array.from(new Set(events.map(e => e.entityId)))];

  const filtered = events.filter(evt => {
    if (filterEntity !== 'all' && evt.entityId !== filterEntity) return false;
    if (filterSuspicious === 'suspicious' && !evt.isSuspicious) return false;
    if (filterSuspicious === 'normal' && evt.isSuspicious) return false;
    if (evt.confidence < filterConf) return false;
    return true;
  });

  const evidence = selectedEvent ? evidenceList.find(e => e.id === selectedEvent.evidenceId) : null;

  return (
    <div className="p-6" style={{ maxWidth: 1600 }}>
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <div className="section-label mb-1 flex items-center gap-2"><Clock size={12} />Event Timeline</div>
          <h1 className="text-[22px] font-bold" style={{ color: '#0f172a' }}>Chronological Event Reconstruction</h1>
          <div className="text-[12px] mt-0.5" style={{ color: '#94a3b8' }}>
            {loading ? 'Loading events…' : `${filtered.length} events · ${events.filter(e => e.isSuspicious).length} flagged suspicious`}
          </div>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="btn-secondary flex items-center gap-2"
        >
          <Filter size={12} />Filters
          <ChevronDown size={12} style={{ transform: showFilters ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
        </button>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="card p-8 mb-5 flex items-center justify-center gap-3" style={{ color: '#64748b' }}>
          <Loader2 size={18} className="animate-spin" />
          <span className="text-[13px]">Loading events from API…</span>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="card p-5 mb-5 flex items-center justify-between gap-4" style={{ borderLeft: '4px solid #ef4444', background: '#fef2f2' }}>
          <div className="flex items-center gap-3">
            <AlertTriangle size={18} className="text-red-500 flex-shrink-0" />
            <div>
              <div className="text-[13px] font-semibold text-red-900">Backend Connection Error</div>
              <div className="text-[12px] text-red-700 mt-0.5">{error}</div>
            </div>
          </div>
          <button onClick={fetchEvents} className="btn-secondary text-[12px] py-1.5 px-3">
            Retry Connection
          </button>
        </div>
      )}

      {/* Filters */}
      {showFilters && (
        <div className="card p-4 mb-5 animate-fade-in">
          <div className="grid grid-cols-4 gap-4">
            <div>
              <label className="field-label">Entity</label>
              <select value={filterEntity} onChange={e => setFilterEntity(e.target.value)} className="input-field">
                {entities.map(e => <option key={e} value={e}>{e === 'all' ? 'All Entities' : e}</option>)}
              </select>
            </div>
            <div>
              <label className="field-label">Event Type</label>
              <select value={filterSuspicious} onChange={e => setFilterSuspicious(e.target.value as 'all' | 'suspicious' | 'normal')} className="input-field">
                <option value="all">All Events</option>
                <option value="suspicious">Suspicious Only</option>
                <option value="normal">Normal Only</option>
              </select>
            </div>
            <div>
              <label className="field-label">Min. Confidence: {filterConf}%</label>
              <input
                type="range" min="0" max="100" value={filterConf}
                onChange={e => setFilterConf(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#2563eb' }}
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={() => { setFilterEntity('all'); setFilterSuspicious('all'); setFilterConf(0); }}
                className="text-[11px] font-medium"
                style={{ color: '#2563eb' }}
              >
                Clear Filters
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-5">
        {/* Timeline */}
        <div className="col-span-2">
          <div className="card overflow-hidden">
            <div className="px-5 py-3" style={{ borderBottom: '1px solid #e2e8f0', background: '#f8fafc' }}>
              <div className="section-label">Event Log</div>
            </div>
            <div className="relative">
              {/* Vertical line */}
              <div className="absolute" style={{ left: 100, top: 0, bottom: 0, width: 1, background: '#e2e8f0' }} />

              {filtered.map(event => (
                <div
                  key={event.id}
                  onClick={() => setSelectedEvent(selectedEvent?.id === event.id ? null : event)}
                  className={`flex items-start gap-4 px-5 py-3.5 cursor-pointer transition-colors ${event.isSuspicious ? 'suspicious-row' : ''}`}
                  style={{
                    background: selectedEvent?.id === event.id ? '#eff6ff' : 'white',
                    borderBottom: '1px solid #f1f5f9',
                    borderLeft: event.isSuspicious ? '3px solid #dc2626' : '3px solid transparent',
                  }}
                  onMouseEnter={e => { if (selectedEvent?.id !== event.id) (e.currentTarget as HTMLElement).style.background = '#f8fafc'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = selectedEvent?.id === event.id ? '#eff6ff' : 'white'; }}
                >
                  {/* Timestamp */}
                  <div className="text-right flex-shrink-0" style={{ width: 80 }}>
                    <div className="font-mono text-[12px] font-semibold" style={{ color: '#2563eb' }}>{event.timestamp}</div>
                    <div className="font-mono text-[10px]" style={{ color: '#94a3b8' }}>{event.cameraId || ''}</div>
                  </div>

                  {/* Node */}
                  <div className="flex-shrink-0 mt-1.5">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{
                        background: event.isSuspicious ? '#fee2e2' : '#dbeafe',
                        border: `2px solid ${event.isSuspicious ? '#dc2626' : '#3b82f6'}`,
                      }}
                    />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="font-mono text-[12px] font-bold" style={{ color: '#0f172a' }}>{event.entityId}</span>
                      <EntityTypeBadge type={event.entityType} />
                      {event.relatedEntityId && (
                        <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                          ↔ {event.relatedEntityId}
                        </span>
                      )}
                      {event.isSuspicious && (
                        <span className="badge badge-red text-[10px] flex items-center gap-1">
                          <AlertTriangle size={9} />SUSPICIOUS
                        </span>
                      )}
                    </div>
                    <div className="text-[13px] font-medium" style={{ color: '#0f172a' }}>{event.action}</div>
                    <div className="text-[11px]" style={{ color: '#64748b' }}>{normalizeLocationName(event.location)}</div>
                    {selectedEvent?.id === event.id && (
                      <div className="mt-2 text-[11px] leading-relaxed animate-fade-in pt-2" style={{ color: '#475569', borderTop: '1px solid #e2e8f0' }}>
                        {event.description}
                      </div>
                    )}
                  </div>

                  {/* Confidence */}
                  <div className="flex-shrink-0 text-right">
                    <div
                      className="font-mono text-[13px] font-bold"
                      style={{ color: event.confidence >= 90 ? '#16a34a' : '#d97706' }}
                    >
                      {event.confidence}%
                    </div>
                    <div className="text-[10px]" style={{ color: '#94a3b8' }}>confidence</div>
                    {event.evidenceId && (
                      <div className="font-mono text-[10px] mt-0.5" style={{ color: '#2563eb' }}>{event.evidenceId}</div>
                    )}
                  </div>
                </div>
              ))}

              {filtered.length === 0 && (
                <div className="py-12 text-center text-[12px]" style={{ color: '#94a3b8' }}>
                  No events match the current filters
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Detail + Stats */}
        <div className="space-y-4">
          {selectedEvent ? (
            <div className="card p-4 animate-fade-in">
              <div className="flex items-center justify-between mb-3">
                <div className="section-label">Event Detail</div>
                <button onClick={() => setSelectedEvent(null)} style={{ color: '#94a3b8' }}>
                  <X size={13} />
                </button>
              </div>
              <div className="space-y-3">
                {[
                  { label: 'Event ID',  value: selectedEvent.id,        mono: true  },
                  { label: 'Timestamp', value: selectedEvent.timestamp, mono: true, accent: '#2563eb' },
                  { label: 'Action',    value: selectedEvent.action                  },
                  { label: 'Location',  value: normalizeLocationName(selectedEvent.location) },
                ].map(row => (
                  <div key={row.label}>
                    <div className="field-label">{row.label}</div>
                    <div className={row.mono ? 'font-mono text-[12px]' : 'text-[12px]'}
                      style={{ color: row.accent || '#0f172a' }}>
                      {row.value}
                    </div>
                  </div>
                ))}
                <div>
                  <div className="field-label">Entity</div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[12px] font-medium" style={{ color: '#0f172a' }}>{selectedEvent.entityId}</span>
                    <EntityTypeBadge type={selectedEvent.entityType} />
                  </div>
                </div>
                <div>
                  <div className="field-label">Confidence</div>
                  <ConfidenceMeter value={selectedEvent.confidence} size="sm" />
                </div>
                <div>
                  <div className="field-label">Description</div>
                  <div className="text-[11px] leading-relaxed" style={{ color: '#475569' }}>{selectedEvent.description}</div>
                </div>
                {selectedEvent.isSuspicious && (
                  <div className="alert-danger p-2.5 flex items-center gap-2">
                    <AlertTriangle size={11} />
                    <span className="text-[11px] font-medium">Flagged as suspicious by classifier</span>
                  </div>
                )}
              </div>

              {evidence && (
                <div className="mt-4 pt-4" style={{ borderTop: '1px solid #e2e8f0' }}>
                  <div className="section-label mb-2">Linked Evidence</div>
                  <div className="p-3 rounded-lg" style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-[11px] font-semibold" style={{ color: '#2563eb' }}>{evidence.id}</span>
                      {evidence.isKeyEvidence && <span className="badge badge-amber">KEY EVIDENCE</span>}
                    </div>
                    <div className="text-[11px]" style={{ color: '#475569' }}>{evidence.description}</div>
                    <div className="flex items-center gap-2 mt-2 text-[10px]" style={{ color: '#94a3b8' }}>
                      <span>{evidence.type}</span>
                      <span>·</span>
                      <span>{evidence.confidence}% confidence</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="card p-6 text-center">
              <Clock size={24} style={{ color: '#cbd5e1', margin: '0 auto 12px' }} />
              <div className="text-[12px]" style={{ color: '#94a3b8' }}>Select an event to view details and linked evidence</div>
            </div>
          )}

          {/* Summary */}
          <div className="card p-4">
            <div className="section-label mb-3">Timeline Summary</div>
            <div className="space-y-2.5">
              {[
                { label: 'Total Events',     value: events.length,                              icon: <CheckCircle size={11} style={{ color: '#16a34a' }} /> },
                { label: 'Suspicious Events',value: events.filter(e => e.isSuspicious).length,  icon: <AlertTriangle size={11} style={{ color: '#dc2626' }} /> },
                { label: 'Person Events',    value: events.filter(e => e.entityType === 'person').length, icon: <User size={11} style={{ color: '#2563eb' }} /> },
                { label: 'Vehicle Events',   value: events.filter(e => e.entityType === 'vehicle').length, icon: <Car size={11} style={{ color: '#7c3aed' }} /> },
                { label: 'Time Span',        value: computeTimeSpan(events),                    icon: <Clock size={11} style={{ color: '#d97706' }} /> },
              ].map(item => (
                <div key={item.label} className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-[11px]" style={{ color: '#64748b' }}>
                    {item.icon}{item.label}
                  </div>
                  <div className="font-mono text-[12px] font-semibold" style={{ color: '#0f172a' }}>{item.value}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
