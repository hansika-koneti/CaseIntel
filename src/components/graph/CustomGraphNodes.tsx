import { Handle, Position, type NodeProps } from 'reactflow';
import {
  User,
  Car,
  Clock,
  ShieldAlert,
  Zap,
  AlertTriangle,
  Camera,
  MapPin,
  Smartphone,
  CheckCircle2,
} from 'lucide-react';
import { normalizeLocationName } from '../../utils/location';

/**
 * SubjectNode: Primary Investigation Subject (Person / Vehicle).
 * Visually prominent with bold identity, confidence ring, duration chip, and high-contrast border.
 */
export function SubjectNode({ data, selected }: NodeProps) {
  const isPerson = data.type === 'person';
  const label = (data.label as string) || (data.raw_id as string) || 'Subject';
  const conf = data.confidence != null ? Number(data.confidence) : 95.0;
  const duration = (data.track_duration as string) || (data.duration as string) || '';

  return (
    <div
      style={{
        border: selected ? '2px solid #2563eb' : '2px solid #3b82f6',
        background: '#ffffff',
        borderRadius: 12,
        padding: '12px 16px',
        minWidth: 200,
        maxWidth: 240,
        boxShadow: selected
          ? '0 0 0 4px rgba(37, 99, 235, 0.25), 0 8px 24px rgba(37, 99, 235, 0.18)'
          : '0 4px 16px rgba(15, 23, 42, 0.08), 0 1px 3px rgba(15, 23, 42, 0.05)',
        transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
        position: 'relative',
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        style={{ background: '#2563eb', width: 8, height: 8, border: '2px solid #ffffff' }}
      />

      {/* Primary Badge Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: isPerson ? '#eff6ff' : '#f5f3ff',
              border: `1px solid ${isPerson ? '#bfdbfe' : '#ddd6fe'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {isPerson ? <User size={18} style={{ color: '#2563eb' }} /> : <Car size={18} style={{ color: '#7c3aed' }} />}
          </div>
          <div>
            <div
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 14,
                fontWeight: 800,
                color: '#0f172a',
                lineHeight: 1.2,
                letterSpacing: '-0.02em',
              }}
            >
              {label}
            </div>
            <div style={{ fontSize: 10, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              PRIMARY SUBJECT
            </div>
          </div>
        </div>
      </div>

      {/* Confidence Bar */}
      <div style={{ marginTop: 8, marginBottom: 6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#64748b', marginBottom: 2 }}>
          <span>Confidence</span>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, color: '#16a34a' }}>
            {conf.toFixed(1)}%
          </span>
        </div>
        <div style={{ height: 4, background: '#f1f5f9', borderRadius: 2, overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${Math.min(100, Math.max(10, conf))}%`,
              background: conf >= 80 ? '#16a34a' : '#d97706',
              borderRadius: 2,
            }}
          />
        </div>
      </div>

      {/* Duration Chip */}
      {duration && (
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            padding: '2px 8px',
            borderRadius: 6,
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            fontSize: 10,
            fontFamily: 'JetBrains Mono, monospace',
            color: '#475569',
            marginTop: 4,
          }}
        >
          <Clock size={10} style={{ color: '#64748b' }} />
          <span>{duration}</span>
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        id="right"
        style={{ background: '#2563eb', width: 8, height: 8, border: '2px solid #ffffff' }}
      />
    </div>
  );
}

/**
 * EventNode: Chronological Security Event Card.
 * Prominently displays action name, embedded timestamp chip, confidence, and suspicious alert badge.
 */
export function EventNode({ data, selected }: NodeProps) {
  const isSuspicious = Boolean(data.is_suspicious || data.isSuspicious || data.suspicious);
  const action = (data.label as string) || (data.action as string) || 'Event';
  const timestamp = (data.timestamp as string) || '00:00';
  const conf = data.confidence != null ? Number(data.confidence) : 90.0;
  const reason = (data.suspicion_reason as string) || (data.suspicionReason as string) || (data.description as string) || '';

  return (
    <div
      style={{
        border: isSuspicious
          ? selected
            ? '2px solid #dc2626'
            : '2px solid #ef4444'
          : selected
          ? '2px solid #d97706'
          : '1.5px solid #cbd5e1',
        background: isSuspicious ? '#fff1f2' : '#ffffff',
        borderRadius: 10,
        padding: '10px 14px',
        minWidth: 180,
        maxWidth: 220,
        boxShadow: isSuspicious
          ? selected
            ? '0 0 0 4px rgba(220, 38, 38, 0.2), 0 6px 20px rgba(220, 38, 38, 0.15)'
            : '0 3px 12px rgba(220, 38, 38, 0.12)'
          : selected
          ? '0 0 0 3px rgba(217, 119, 6, 0.2), 0 4px 12px rgba(0,0,0,0.06)'
          : '0 2px 6px rgba(0,0,0,0.04)',
        transition: 'all 0.15s ease',
        position: 'relative',
      }}
      title={isSuspicious && reason ? `⚠️ Suspicious: ${reason}` : undefined}
    >
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        style={{
          background: isSuspicious ? '#dc2626' : '#d97706',
          width: 7,
          height: 7,
          border: '1.5px solid #ffffff',
        }}
      />

      {/* Top row: Action Name & Suspicious Tag */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div
            style={{
              width: 22,
              height: 22,
              borderRadius: 6,
              background: isSuspicious ? '#fee2e2' : '#fffbeb',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            {isSuspicious ? (
              <ShieldAlert size={13} style={{ color: '#dc2626' }} />
            ) : (
              <Zap size={13} style={{ color: '#d97706' }} />
            )}
          </div>
          <div
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: isSuspicious ? '#991b1b' : '#0f172a',
              lineHeight: 1.25,
            }}
          >
            {action}
          </div>
        </div>
      </div>

      {/* Bottom row: Embedded Timestamp & Confidence */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 3,
            padding: '2px 6px',
            borderRadius: 5,
            background: isSuspicious ? '#fecaca' : '#f1f5f9',
            color: isSuspicious ? '#991b1b' : '#334155',
            fontSize: 10,
            fontFamily: 'JetBrains Mono, monospace',
            fontWeight: 600,
          }}
        >
          <Clock size={10} />
          <span>{timestamp}</span>
        </div>

        <span
          style={{
            fontSize: 10,
            fontFamily: 'JetBrains Mono, monospace',
            color: '#64748b',
          }}
        >
          {conf.toFixed(0)}% conf
        </span>
      </div>

      {/* Suspicious Alert Banner / Pulse */}
      {isSuspicious && (
        <div
          style={{
            marginTop: 6,
            padding: '3px 6px',
            borderRadius: 4,
            background: '#fee2e2',
            border: '1px solid #fca5a5',
            fontSize: 9,
            fontWeight: 700,
            color: '#b91c1c',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <AlertTriangle size={10} style={{ color: '#b91c1c' }} />
          <span style={{ textTransform: 'uppercase', letterSpacing: '0.04em' }}>Suspicious Action</span>
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        id="right"
        style={{
          background: isSuspicious ? '#dc2626' : '#d97706',
          width: 7,
          height: 7,
          border: '1.5px solid #ffffff',
        }}
      />
    </div>
  );
}

/**
 * CameraNode: Contextual camera hardware node.
 */
export function CameraNode({ data, selected }: NodeProps) {
  const label = (data.label as string) || 'Camera';
  const location = (data.location as string) || '';

  return (
    <div
      style={{
        border: selected ? '2px solid #db2777' : '1.5px solid #f472b6',
        background: '#ffffff',
        borderRadius: 10,
        padding: '8px 12px',
        minWidth: 150,
        maxWidth: 180,
        boxShadow: selected ? '0 0 0 3px rgba(219, 39, 119, 0.2)' : '0 2px 6px rgba(0,0,0,0.05)',
        transition: 'all 0.15s',
      }}
    >
      <Handle type="target" position={Position.Top} id="top" style={{ background: '#db2777', width: 6, height: 6 }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div
          style={{
            width: 26,
            height: 26,
            borderRadius: 6,
            background: '#fdf2f8',
            border: '1px solid #fbcfe8',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Camera size={14} style={{ color: '#db2777' }} />
        </div>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#0f172a', lineHeight: 1.2 }}>{label}</div>
          <div style={{ fontSize: 10, color: '#9d174d', display: 'flex', alignItems: 'center', gap: 4, marginTop: 1 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#16a34a', display: 'inline-block' }} />
            <span>Online</span>
          </div>
        </div>
      </div>
      {location && (
        <div style={{ fontSize: 10, color: '#64748b', marginTop: 4, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          📍 {location}
        </div>
      )}
      <Handle type="source" position={Position.Right} id="right" style={{ background: '#db2777', width: 6, height: 6 }} />
    </div>
  );
}

/**
 * LocationNode: Contextual physical premises/zone node.
 */
export function LocationNode({ data, selected }: NodeProps) {
  const label = normalizeLocationName((data.label as string) || (data.location as string));

  return (
    <div
      style={{
        border: selected ? '2px solid #16a34a' : '1.5px solid #86efac',
        background: '#ffffff',
        borderRadius: 10,
        padding: '8px 12px',
        minWidth: 150,
        maxWidth: 190,
        boxShadow: selected ? '0 0 0 3px rgba(22, 163, 74, 0.2)' : '0 2px 6px rgba(0,0,0,0.05)',
        transition: 'all 0.15s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div
          style={{
            width: 26,
            height: 26,
            borderRadius: 6,
            background: '#f0fdf4',
            border: '1px solid #bbf7d0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <MapPin size={14} style={{ color: '#16a34a' }} />
        </div>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#0f172a', lineHeight: 1.2 }}>{label}</div>
          <div style={{ fontSize: 9, fontWeight: 600, color: '#166534', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            MONITORED ZONE
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} id="bottom" style={{ background: '#16a34a', width: 6, height: 6 }} />
      <Handle type="target" position={Position.Left} id="left" style={{ background: '#16a34a', width: 6, height: 6 }} />
    </div>
  );
}

/**
 * TimestampNode: Low-level technical node for Cypher Topology view.
 */
export function TimestampNode({ data, selected }: NodeProps) {
  const label = (data.label as string) || '00:00';

  return (
    <div
      style={{
        border: selected ? '1.5px solid #64748b' : '1px dashed #cbd5e1',
        background: '#f8fafc',
        borderRadius: 6,
        padding: '4px 8px',
        fontSize: 10,
        fontFamily: 'JetBrains Mono, monospace',
        color: '#475569',
        display: 'flex',
        alignItems: 'center',
        gap: 4,
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: '#94a3b8', width: 5, height: 5 }} />
      <Clock size={10} style={{ color: '#94a3b8' }} />
      <span>{label}</span>
    </div>
  );
}

/**
 * ObjectNode: Key Monitored Object / Property (e.g. Phone-01).
 * Features cyan border, smartphone icon, and confidence indicator.
 */
export function ObjectNode({ data, selected }: NodeProps) {
  const label = (data.label as string) || (data.raw_id as string) || 'Object';
  const conf = data.confidence != null ? Number(data.confidence) : 90.0;

  return (
    <div
      style={{
        border: selected ? '2px solid #0891b2' : '2px solid #06b6d4',
        background: '#ffffff',
        borderRadius: 12,
        padding: '12px 16px',
        minWidth: 190,
        maxWidth: 230,
        boxShadow: selected
          ? '0 0 0 4px rgba(8, 145, 178, 0.25), 0 8px 24px rgba(8, 145, 178, 0.18)'
          : '0 4px 16px rgba(15, 23, 42, 0.08), 0 1px 3px rgba(15, 23, 42, 0.05)',
        transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
        position: 'relative',
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        style={{ background: '#0891b2', width: 8, height: 8, border: '2px solid #ffffff' }}
      />

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: '#ecfeff',
            border: '1px solid #a5f3fc',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Smartphone size={18} style={{ color: '#0891b2' }} />
        </div>
        <div>
          <div
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 14,
              fontWeight: 800,
              color: '#0f172a',
              lineHeight: 1.2,
            }}
          >
            {label}
          </div>
          <div style={{ fontSize: 10, fontWeight: 600, color: '#0e7490', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            KEY PROPERTY / OBJECT
          </div>
        </div>
      </div>

      <div style={{ marginTop: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#64748b', marginBottom: 2 }}>
          <span>Detection Confidence</span>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, color: '#0891b2' }}>
            {conf.toFixed(1)}%
          </span>
        </div>
        <div style={{ height: 4, background: '#f1f5f9', borderRadius: 2, overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${Math.min(100, Math.max(10, conf))}%`,
              background: '#0891b2',
              borderRadius: 2,
            }}
          />
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        id="right"
        style={{ background: '#0891b2', width: 8, height: 8, border: '2px solid #ffffff' }}
      />
    </div>
  );
}

/**
 * EvidenceNode: Grounded forensic evidence item.
 */
export function EvidenceNode({ data, selected }: NodeProps) {
  const label = (data.label as string) || (data.evidence_type as string) || 'Key Evidence';
  const isKey = Boolean(data.is_key_evidence ?? data.suspicious ?? false);

  return (
    <div
      style={{
        border: selected ? '2px solid #8b5cf6' : (isKey ? '1.5px solid #a855f7' : '1.5px solid #cbd5e1'),
        background: '#ffffff',
        borderRadius: 10,
        padding: '10px 14px',
        minWidth: 170,
        maxWidth: 210,
        boxShadow: selected ? '0 0 0 3px rgba(139, 92, 246, 0.2)' : '0 2px 8px rgba(0,0,0,0.05)',
        transition: 'all 0.15s ease',
        position: 'relative',
      }}
    >
      <Handle type="target" position={Position.Left} id="left" style={{ background: '#8b5cf6', width: 7, height: 7 }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <div
          style={{
            width: 24,
            height: 24,
            borderRadius: 6,
            background: isKey ? '#f3e8ff' : '#f8fafc',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: `1px solid ${isKey ? '#d8b4fe' : '#e2e8f0'}`,
          }}
        >
          <CheckCircle2 size={13} style={{ color: isKey ? '#9333ea' : '#64748b' }} />
        </div>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#0f172a', lineHeight: 1.2 }}>{label}</div>
          <div style={{ fontSize: 9, fontWeight: 600, color: isKey ? '#9333ea' : '#64748b', textTransform: 'uppercase' }}>
            {isKey ? 'KEY FORENSIC EVIDENCE' : 'SUPPORTING EVIDENCE'}
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Right} id="right" style={{ background: '#8b5cf6', width: 7, height: 7 }} />
    </div>
  );
}

export const customNodeTypes = {
  person: SubjectNode,
  vehicle: SubjectNode,
  object: ObjectNode,
  phone: ObjectNode,
  event: EventNode,
  camera: CameraNode,
  location: LocationNode,
  timestamp: TimestampNode,
  activity: EventNode,
  evidence: EvidenceNode,
};
