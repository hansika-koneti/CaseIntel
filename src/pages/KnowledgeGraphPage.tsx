import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import type { MouseEvent } from 'react';
import ReactFlow, {
  type Node,
  type Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  MarkerType,
  type NodeProps,
  Handle,
  Position,
  type ReactFlowInstance,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  User,
  Car,
  Smartphone,
  Camera,
  MapPin,
  Zap,
  Clock,
  X,
  Search,
  Filter,
  Loader2,
  AlertTriangle,
  Network,
  Maximize2,
  ShieldAlert,
  Compass,
  Database,
  ArrowRight,
  Info,
  CheckCircle2,
} from 'lucide-react';
import { getKnowledgeGraph } from '../api/graph';
import { getInvestigation, getInvestigations } from '../api/investigations';
import type { Investigation } from '../types';
import { EntityTypeBadge } from '../components/common/StatusBadge';
import { ConfidenceMeter } from '../components/common/ConfidenceMeter';
import { normalizeLocationName } from '../utils/location';


// ── Custom ReactFlow Nodes ──────────────────────────────────────

/**
 * SubjectNode: Primary Investigation Subject (Person / Vehicle).
 * Visually prominent with bold identity, confidence ring, duration chip, and high-contrast border.
 */
function SubjectNode({ data, selected }: NodeProps) {
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
function EventNode({ data, selected }: NodeProps) {
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
function CameraNode({ data, selected }: NodeProps) {
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
function LocationNode({ data, selected }: NodeProps) {
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
function TimestampNode({ data, selected }: NodeProps) {
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
function ObjectNode({ data, selected }: NodeProps) {
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
function EvidenceNode({ data, selected }: NodeProps) {
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

const customNodeTypes = {
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

type ViewMode = 'investigator' | 'topology';
type FilterType = 'all' | 'people' | 'vehicles' | 'objects' | 'events' | 'suspicious';

export default function KnowledgeGraphPage() {
  const [inv, setInv] = useState<Investigation | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [rawNodes, setRawNodes] = useState<Node[]>([]);
  const [rawEdges, setRawEdges] = useState<Edge[]>([]);
  const [detailsMap, setDetailsMap] = useState<Record<string, any>>({});
  const [neo4jConnected, setNeo4jConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [viewMode, setViewMode] = useState<ViewMode>('investigator');
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<FilterType>('all');
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);

  const loadGraph = useCallback(async () => {
    let activeId = localStorage.getItem('caseintel-active-case-id');
    if (!activeId) {
      try {
        const invList = await getInvestigations();
        if (invList && invList.length > 0) {
          activeId = invList[0].id;
          localStorage.setItem('caseintel-active-case-id', activeId);
          window.dispatchEvent(new Event('active-case-changed'));
        }
      } catch {
        // ignore
      }
    }

    if (!activeId) {
      setLoading(false);
      setInv(null);
      setNodes([]);
      setEdges([]);
      setDetailsMap({});
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const [invData, graphData] = await Promise.all([
        getInvestigation(activeId),
        getKnowledgeGraph(activeId).catch(() => ({
          investigationId: activeId,
          nodes: [],
          edges: [],
          entityDetails: {},
          neo4jConnected: false,
        })),
      ]);

      setInv(invData);
      setNeo4jConnected(Boolean(graphData.neo4jConnected));

      // Map raw API nodes into specialized ReactFlow nodes
      const mappedNodes: Node[] = (graphData.nodes || []).map(n => {
        const nodeType = n.type.toLowerCase();
        const rawData = n.data || {};
        const isSusp = Boolean(
          rawData.is_suspicious ??
          rawData.isSuspicious ??
          rawData.suspicious ??
          (n as any).is_suspicious ??
          (n as any).isSuspicious ??
          (n as any).suspicious
        );
        const suspReason =
          rawData.suspicion_reason ??
          rawData.suspicionReason ??
          rawData.description ??
          (n as any).suspicion_reason ??
          (n as any).description ??
          '';
        const rawEid = rawData.entity_id ?? rawData.entityId ?? (n as any).entity_id ?? '';

        return {
          id: n.id,
          type: customNodeTypes[nodeType as keyof typeof customNodeTypes] ? nodeType : 'event',
          position: { x: n.x, y: n.y },
          data: {
            ...rawData,
            raw_id: n.id,
            label: n.label,
            type: nodeType,
            category: n.category || (nodeType === 'timestamp' ? 'technical' : 'primary'),
            is_technical: Boolean(n.is_technical || (n as any).isTechnical || nodeType === 'timestamp'),
            confidence: n.confidence,
            is_suspicious: isSusp,
            isSuspicious: isSusp,
            suspicious: isSusp,
            suspicion_reason: suspReason,
            suspicionReason: suspReason,
            entity_id: rawEid,
            entityId: rawEid,
          },
        };
      });

      // Map edges with investigator styling
      const mappedEdges: Edge[] = (graphData.edges || []).map(e => {
        const isSusp = Boolean(e.suspicious);
        const isSeq = e.relationship === 'THEN';
        const isObj = e.relationship === 'INVOLVES_OBJECT' || e.relationship === 'MANIPULATED';
        const isTech = Boolean(e.is_technical || (e as any).isTechnical || e.relationship === 'OCCURRED_AT');
        const edgeReason = e.reason || (isSusp ? 'Suspicious behavioral transition' : undefined);
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label || e.relationship,
          animated: isSusp || isSeq,
          data: {
            relationship: e.relationship,
            suspicious: isSusp,
            reason: edgeReason,
            is_technical: isTech,
          },
          style: isSusp
            ? { stroke: '#dc2626', strokeWidth: 2.2, strokeDasharray: '6 3' }
            : isSeq
            ? { stroke: '#0891b2', strokeWidth: 2, strokeDasharray: '4 4' }
            : isObj
            ? { stroke: '#0891b2', strokeWidth: 1.8 }
            : isTech
            ? { stroke: '#cbd5e1', strokeWidth: 1, strokeDasharray: '3 3' }
            : { stroke: '#94a3b8', strokeWidth: 1.6 },
          labelStyle: {
            fill: isSusp ? '#b91c1c' : isSeq ? '#0891b2' : isObj ? '#0891b2' : '#64748b',
            fontSize: 9,
            fontFamily: 'JetBrains Mono, monospace',
            fontWeight: (isSusp || isSeq) ? 700 : 500,
          },
          labelBgStyle: {
            fill: isSusp ? '#fee2e2' : isSeq ? '#ecfeff' : isObj ? '#ecfeff' : '#f8fafc',
            stroke: isSusp ? '#fca5a5' : isSeq ? '#a5f3fc' : isObj ? '#a5f3fc' : '#e2e8f0',
            strokeWidth: 1,
            rx: 4,
            ry: 4,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isSusp ? '#dc2626' : isSeq ? '#0891b2' : isObj ? '#0891b2' : isTech ? '#94a3b8' : '#64748b',
            width: 10,
            height: 10,
          },
        };
      });


      setRawNodes(mappedNodes);
      setRawEdges(mappedEdges);
      setDetailsMap(graphData.entityDetails || {});
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load knowledge graph';
      setError(msg);
      setRawNodes([]);
      setRawEdges([]);
    } finally {
      setLoading(false);
    }
  }, [setNodes, setEdges]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  useEffect(() => {
    const handler = () => loadGraph();
    window.addEventListener('active-case-changed', handler);
    return () => window.removeEventListener('active-case-changed', handler);
  }, [loadGraph]);

  // Handle View Mode & Filtering
  useEffect(() => {
    let filteredNodes = [...rawNodes];
    let filteredEdges = [...rawEdges];

    // 1. View Mode Filtering: Investigator Flow hides low-value technical timestamp nodes
    if (viewMode === 'investigator') {
      const visibleNodeIds = new Set<string>();
      filteredNodes = filteredNodes.filter(n => {
        const isTech = Boolean(n.data.is_technical);
        if (!isTech) {
          visibleNodeIds.add(n.id);
          return true;
        }
        return false;
      });
      filteredEdges = filteredEdges.filter(e => {
        const isTech = Boolean(e.data?.is_technical);
        return !isTech && visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target);
      });
    }

    // 2. Category / Entity Filter
    if (filter === 'people') {
      filteredNodes = filteredNodes.filter(n => n.data.type === 'person' || n.data.type === 'camera' || n.data.type === 'location');
    } else if (filter === 'vehicles') {
      filteredNodes = filteredNodes.filter(n => n.data.type === 'vehicle' || n.data.type === 'camera' || n.data.type === 'location');
    } else if (filter === 'objects') {
      filteredNodes = filteredNodes.filter(n => n.data.type === 'object' || n.data.type === 'phone' || n.data.type === 'camera' || n.data.type === 'location');
    } else if (filter === 'events') {
      filteredNodes = filteredNodes.filter(n => n.data.type === 'event' || n.data.type === 'activity');
    } else if (filter === 'suspicious') {
      const suspNodeIds = new Set<string>();
      filteredNodes.forEach(n => {
        const isSusp = Boolean(n.data.is_suspicious || n.data.isSuspicious || n.data.suspicious);
        if (isSusp) {
          suspNodeIds.add(n.id);
          const eid = n.data.entity_id || n.data.entityId;
          if (eid) suspNodeIds.add(eid);
        }
      });
      filteredNodes = filteredNodes.filter(n => suspNodeIds.has(n.id) || (suspNodeIds.size > 0 && (n.data.type === 'camera' || n.data.type === 'location')));
    }

    // 3. Search Query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      filteredNodes = filteredNodes.filter(n => {
        const label = String(n.data.label || '').toLowerCase();
        const id = String(n.id).toLowerCase();
        return label.includes(q) || id.includes(q);
      });
    }

    // Ensure edge ends remain connected
    const currentValidIds = new Set(filteredNodes.map(n => n.id));
    filteredEdges = filteredEdges.filter(e => currentValidIds.has(e.source) && currentValidIds.has(e.target));

    setNodes(filteredNodes);
    setEdges(filteredEdges);
  }, [rawNodes, rawEdges, viewMode, filter, searchQuery, setNodes, setEdges]);

  // Auto-fit view whenever nodes or view mode changes
  useEffect(() => {
    if (reactFlowInstance && nodes.length > 0) {
      const timer = setTimeout(() => {
        reactFlowInstance.fitView({ padding: 0.18, duration: 450 });
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [reactFlowInstance, viewMode, filter]);

  const onNodeClick = useCallback((_: MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleFitView = useCallback(() => {
    if (reactFlowInstance) {
      reactFlowInstance.fitView({ padding: 0.18, duration: 400 });
    }
  }, [reactFlowInstance]);

  // Selected Node Details
  const selectedDetails = selectedNode ? detailsMap[selectedNode.id] || selectedNode.data : null;
  const isEventNode = selectedNode?.data?.type === 'event' || selectedNode?.data?.type === 'activity';
  const isSubjectNode = selectedNode?.data?.type === 'person' || selectedNode?.data?.type === 'vehicle' || selectedNode?.data?.type === 'object' || selectedNode?.data?.type === 'phone';

  // Counts for quick filter pills
  const counts = useMemo(() => {
    let people = 0;
    let vehicles = 0;
    let objects = 0;
    let events = 0;
    let suspicious = 0;

    rawNodes.forEach(n => {
      const t = String(n.data.type || '').toLowerCase();
      if (t === 'person') people++;
      if (t === 'vehicle' || t === 'car' || t === 'truck') vehicles++;
      if (t === 'object' || t === 'phone') objects++;
      if (t === 'event' || t === 'activity') {
        events++;
        const isSusp = Boolean(n.data.is_suspicious || n.data.isSuspicious || n.data.suspicious);
        if (isSusp) suspicious++;
      }
    });

    return { people, vehicles, objects, events, suspicious, total: rawNodes.length };
  }, [rawNodes]);


  if (loading && rawNodes.length === 0) {
    return (
      <div className="p-12 flex items-center justify-center gap-3" style={{ color: '#64748b', height: 'calc(100vh - 48px)' }}>
        <Loader2 size={22} className="animate-spin text-blue-600" />
        <span className="text-[13px] font-medium">Constructing investigator knowledge graph from live case telemetry…</span>
      </div>
    );
  }

  if (error && rawNodes.length === 0) {
    return (
      <div className="p-12 max-w-md mx-auto text-center space-y-3" style={{ marginTop: '100px' }}>
        <AlertTriangle size={32} className="mx-auto text-red-500" />
        <div className="text-[14px] font-semibold text-slate-800">Unable to load Knowledge Graph</div>
        <div className="text-[12px] text-slate-500">{error}</div>
        <button onClick={() => loadGraph()} className="btn-primary mt-2">Retry</button>
      </div>
    );
  }

  if (!inv && rawNodes.length === 0) {
    return (
      <div className="p-12 max-w-md mx-auto text-center space-y-3" style={{ marginTop: '100px' }}>
        <Network size={32} className="mx-auto text-slate-400" />
        <div className="text-[14px] font-semibold text-slate-800">No Active Investigation</div>
        <div className="text-[12px] text-slate-500">Upload and analyze CCTV video to synthesize dynamic case entities and relationships.</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 48px)', background: '#f8fafc' }}>
      {/* Top Investigator Command Toolbar */}
      <div
        className="flex items-center justify-between px-4 py-2.5 border-b border-slate-200 bg-white"
        style={{ zIndex: 20 }}
      >
        {/* Left: View Mode Toggle & Case Badge */}
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200">
            <button
              onClick={() => setViewMode('investigator')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold rounded-md transition-all ${
                viewMode === 'investigator'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Investigator View: Groups technical nodes and presents clean sequential actions"
            >
              <Compass size={13} />
              <span>Investigator Flow</span>
            </button>
            <button
              onClick={() => setViewMode('topology')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold rounded-md transition-all ${
                viewMode === 'topology'
                  ? 'bg-white text-indigo-600 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Cypher Topology: Complete multi-node database representation with raw timestamp nodes"
            >
              <Database size={13} />
              <span>Cypher Topology</span>
            </button>
          </div>

          <div className="h-4 w-px bg-slate-200" />

          {/* Quick Filters */}
          <div className="flex items-center gap-1">
            {[
              { id: 'all', label: 'All' },
              { id: 'people', label: `People (${counts.people})` },
              ...(counts.vehicles > 0 ? [{ id: 'vehicles', label: `Vehicles (${counts.vehicles})` }] : []),
              ...(counts.objects > 0 ? [{ id: 'objects', label: `Objects (${counts.objects})` }] : []),
              { id: 'events', label: `Events (${counts.events})` },
              { id: 'suspicious', label: `Suspicious Only (${counts.suspicious})`, alert: counts.suspicious > 0 },
            ].map(f => (
              <button
                key={f.id}
                onClick={() => setFilter(f.id as FilterType)}
                className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-colors ${
                  filter === f.id
                    ? f.alert
                      ? 'bg-red-50 text-red-700 border border-red-200 font-semibold'
                      : 'bg-blue-50 text-blue-700 border border-blue-200 font-semibold'
                    : f.alert
                    ? 'text-red-600 hover:bg-red-50/50'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Right: Search & View Controls */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search graph entities…"
              className="pl-7 pr-3 py-1 text-[11px] rounded-md border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:border-blue-500 w-44 transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X size={11} />
              </button>
            )}
          </div>

          <button
            onClick={handleFitView}
            className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-md transition-colors"
            title="Fit graph to viewport"
          >
            <Maximize2 size={12} />
            <span>Fit View</span>
          </button>

          <div className="flex items-center gap-2 text-[10px] text-slate-600 pl-2 border-l border-slate-200">
            <span className={`inline-block w-2 h-2 rounded-full ${neo4jConnected ? 'bg-emerald-500' : 'bg-blue-500'}`} />
            <span className="font-mono font-medium">
              {neo4jConnected ? 'Graph Engine: Neo4j' : 'Graph Engine: In-Memory Forensic Topology'}
            </span>
          </div>

        </div>
      </div>

      {/* Main Canvas & Inspector Panel */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* ReactFlow Canvas */}
        <div className="flex-1 relative bg-slate-50">
          {nodes.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center p-8 bg-white border border-slate-200 rounded-xl shadow-sm max-w-sm">
                <Network size={32} className="mx-auto text-slate-400 mb-3" />
                <div className="text-[14px] font-semibold text-slate-800">
                  {rawNodes.length === 0 ? 'No Graph Data Available' : 'No Matching Graph Nodes'}
                </div>
                <div className="text-[12px] text-slate-500 mt-1">
                  {rawNodes.length === 0
                    ? 'Upload and analyze a CCTV video to construct knowledge graph entities and relationships.'
                    : 'Adjust your search or filter settings to view case relationships.'}
                </div>
                {rawNodes.length > 0 && (filter !== 'all' || searchQuery) && (
                  <button
                    onClick={() => {
                      setFilter('all');
                      setSearchQuery('');
                    }}
                    className="mt-3 px-3 py-1 text-[11px] font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100 transition-colors"
                  >
                    Reset Filters
                  </button>
                )}
              </div>
            </div>
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              onPaneClick={onPaneClick}
              nodeTypes={customNodeTypes}
              onInit={setReactFlowInstance}
              fitView
              fitViewOptions={{ padding: 0.18 }}
              minZoom={0.3}
              maxZoom={2.2}
              attributionPosition="bottom-right"
            >
              <Background variant={BackgroundVariant.Dots} gap={20} size={1.2} color="#cbd5e1" />
              <Controls showInteractive={false} className="bg-white border border-slate-200 shadow-sm rounded-lg" />
              <MiniMap
                nodeColor={n => {
                  if (n.data?.is_suspicious) return '#dc2626';
                  if (n.data?.type === 'person') return '#2563eb';
                  if (n.data?.type === 'vehicle') return '#7c3aed';
                  if (n.data?.type === 'object' || n.data?.type === 'phone') return '#0891b2';
                  if (n.data?.type === 'camera') return '#db2777';
                  if (n.data?.type === 'location') return '#16a34a';
                  if (n.data?.type === 'event') return '#d97706';
                  return '#94a3b8';
                }}
                maskColor="rgba(241, 245, 249, 0.75)"
                className="border border-slate-200 rounded-lg shadow-sm"
              />
            </ReactFlow>
          )}

          {/* Quick Legend Overlay */}
          <div
            className="absolute bottom-3 left-3 z-10 bg-white/95 backdrop-blur-sm border border-slate-200 rounded-lg p-2.5 shadow-sm"
            style={{ minWidth: 160 }}
          >
            <div className="text-[10px] font-bold text-slate-700 uppercase tracking-wider mb-1.5 flex items-center gap-1">
              <Info size={10} /> Hierarchy Legend
            </div>
            <div className="space-y-1 text-[10px] text-slate-600">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-600" />
                <span>Primary Subject</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#0891b2' }} />
                <span>Object / Property</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                <span>Security Event</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-600" />
                <span>Suspicious Action ⚠️</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-pink-600" />
                <span>Camera Sensor</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-600" />
                <span>Monitored Location</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Node Inspector Panel */}
        {selectedNode && (
          <div
            className="w-80 flex-shrink-0 bg-white border-l border-slate-200 flex flex-col h-full overflow-y-auto animate-fade-in shadow-lg"
            style={{ zIndex: 15 }}
          >
            {/* Inspector Header */}
            <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div>
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  Node Inspector
                </div>
                <div className="text-[14px] font-bold text-slate-900 mt-0.5">
                  {selectedNode.data.label || selectedNode.id}
                </div>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              >
                <X size={15} />
              </button>
            </div>

            {/* Inspector Content */}
            <div className="p-4 space-y-4 text-[12px]">
              {/* Event Node Details (Requirement 11) */}
              {isEventNode && (
                <>
                  <div className="space-y-2.5">
                    <div className="flex justify-between items-center py-1 border-b border-slate-100">
                      <span className="text-slate-500">Event Action</span>
                      <span className="font-semibold text-slate-900">
                        {selectedDetails?.event_type || selectedDetails?.action || selectedNode.data.label}
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-1 border-b border-slate-100">
                      <span className="text-slate-500">Timestamp</span>
                      <span className="font-mono font-medium text-slate-900 flex items-center gap-1">
                        <Clock size={11} className="text-slate-400" />
                        {selectedDetails?.timestamp || selectedNode.data.timestamp || '00:00'}
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-1 border-b border-slate-100">
                      <span className="text-slate-500">Confidence</span>
                      <span className="font-mono font-semibold text-emerald-700">
                        {(Number(selectedDetails?.confidence || selectedNode.data.confidence || 90)).toFixed(1)}%
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-1 border-b border-slate-100">
                      <span className="text-slate-500">Subject Entity</span>
                      <button
                        type="button"
                        onClick={() => {
                          const entId = selectedDetails?.entity_id || selectedNode.data.entity_id;
                          const target = nodes.find(n => n.id === entId);
                          if (target) setSelectedNode(target);
                        }}
                        className="font-mono font-medium text-blue-700 hover:text-blue-900 hover:underline inline-flex items-center gap-1 cursor-pointer"
                        title="Click to focus on Subject"
                      >
                        <span>{selectedDetails?.entity_id || selectedNode.data.entity_id || 'Person-01'}</span>
                        <ArrowRight size={11} />
                      </button>
                    </div>

                    <div className="flex justify-between items-center py-1 border-b border-slate-100">
                      <span className="text-slate-500">Camera</span>
                      <span className="font-medium text-slate-900">
                        {selectedDetails?.camera || selectedNode.data.camera || 'Camera C-01'}
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-1 border-b border-slate-100">
                      <span className="text-slate-500">Location</span>
                      <span className="font-medium text-slate-900">
                        {normalizeLocationName(selectedDetails?.location || selectedNode.data.location)}
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-1 border-b border-slate-100">
                      <span className="text-slate-500">Underlying Event ID</span>
                      <span className="font-mono text-[11px] text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded">
                        {selectedDetails?.underlying_id || selectedDetails?.underlyingId || selectedNode.data.raw_id || selectedNode.id}
                      </span>
                    </div>
                  </div>

                  {/* Suspicious Status Box */}
                  <div
                    className={`p-3 rounded-lg border ${
                      Boolean(selectedDetails?.is_suspicious || selectedDetails?.isSuspicious || selectedNode.data.is_suspicious || selectedNode.data.isSuspicious)
                        ? 'bg-red-50/80 border-red-200'
                        : 'bg-emerald-50/60 border-emerald-200'
                    }`}
                  >
                    <div className="flex items-center gap-1.5 font-bold text-[11px] mb-1">
                      {Boolean(selectedDetails?.is_suspicious || selectedDetails?.isSuspicious || selectedNode.data.is_suspicious || selectedNode.data.isSuspicious) ? (
                        <>
                          <ShieldAlert size={14} className="text-red-600" />
                          <span className="text-red-800">Suspicious Event Flagged</span>
                        </>
                      ) : (
                        <>
                          <CheckCircle2 size={14} className="text-emerald-600" />
                          <span className="text-emerald-800">Baseline Security Event</span>
                        </>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-700 leading-relaxed font-medium">
                      {selectedDetails?.suspicion_reason ||
                        selectedDetails?.suspicionReason ||
                        selectedDetails?.description ||
                        selectedNode.data.suspicion_reason ||
                        selectedNode.data.suspicionReason ||
                        selectedNode.data.description ||
                        'Normal pedestrian movement within monitored perimeter.'}
                    </div>
                  </div>
                </>
              )}


              {/* Person / Vehicle Node Details (Requirement 12) */}
              {isSubjectNode && (
                <>
                  <div className="space-y-2.5">
                    <div className="flex justify-between items-center py-1 border-b border-slate-100">
                      <span className="text-slate-500">Track ID</span>
                      <span className="font-mono font-bold text-blue-700">
                        {selectedDetails?.track_id || selectedNode.id}
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-1 border-b border-slate-100">
                      <span className="text-slate-500">Entity Type</span>
                      <EntityTypeBadge type={selectedNode.data.type as string} />
                    </div>

                    <div className="flex justify-between items-center py-1 border-b border-slate-100">
                      <span className="text-slate-500">Track Confidence</span>
                      <span className="font-mono font-semibold text-emerald-700">
                        {(Number(selectedDetails?.confidence || selectedNode.data.confidence || 90)).toFixed(1)}%
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-1 border-b border-slate-100">
                      <span className="text-slate-500">Track Duration</span>
                      <span className="font-mono font-medium text-slate-900">
                        {selectedDetails?.track_duration || selectedNode.data.track_duration || '16.1s'}
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-1 border-b border-slate-100">
                      <span className="text-slate-500">First / Last Seen</span>
                      <span className="font-mono text-slate-700 text-[11px]">
                        {selectedDetails?.first_seen || '00:00'} → {selectedDetails?.last_seen || '00:16'}
                      </span>
                    </div>

                    <div className="flex justify-between items-center py-1 border-b border-slate-100">
                      <span className="text-slate-500">Camera</span>
                      <span className="font-medium text-slate-900">
                        {selectedDetails?.camera || 'Camera C-01'}
                      </span>
                    </div>
                  </div>

                  {/* Associated Events List */}
                  {selectedDetails?.events && selectedDetails.events.length > 0 && (
                    <div className="pt-2">
                      <div className="text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-2">
                        Associated Events ({selectedDetails.events.length})
                      </div>
                      <div className="space-y-1.5">
                        {selectedDetails.events.map((ev: any, idx: number) => {
                          const evAction = ev.action || ev.event_type || ev.id;
                          const isSusp = Boolean(ev.is_suspicious);
                          return (
                            <div
                              key={idx}
                              onClick={() => {
                                const targetNode = nodes.find(n => n.id === ev.id);
                                if (targetNode) setSelectedNode(targetNode);
                              }}
                              className={`p-2 rounded-lg border text-[11px] cursor-pointer transition-all ${
                                isSusp
                                  ? 'bg-red-50/70 border-red-200 hover:bg-red-100/70'
                                  : 'bg-slate-50 border-slate-200 hover:bg-slate-100'
                              }`}
                            >
                              <div className="flex items-center justify-between font-medium">
                                <span className={isSusp ? 'text-red-900 font-bold' : 'text-slate-900'}>
                                  {evAction}
                                </span>
                                <span className="font-mono text-[10px] text-slate-500">{ev.timestamp}</span>
                              </div>
                              {ev.description && (
                                <div className="text-[10px] text-slate-500 mt-1 line-clamp-2">
                                  {ev.description}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* Camera / Location Node Details */}
              {!isEventNode && !isSubjectNode && (
                <div className="space-y-2.5">
                  <div className="flex justify-between items-center py-1 border-b border-slate-100">
                    <span className="text-slate-500">Identifier</span>
                    <span className="font-mono font-medium text-slate-900">{selectedNode.id}</span>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-slate-100">
                    <span className="text-slate-500">Node Type</span>
                    <span className="font-semibold capitalize text-slate-800">{selectedNode.data.type}</span>
                  </div>
                  {selectedNode.data.location && (
                    <div className="flex justify-between items-center py-1 border-b border-slate-100">
                      <span className="text-slate-500">Location</span>
                      <span className="font-medium text-slate-800">{normalizeLocationName(selectedNode.data.location)}</span>
                    </div>
                  )}
                  {selectedDetails?.relationships && selectedDetails.relationships.length > 0 && (
                    <div className="pt-2">
                      <div className="text-[11px] font-bold uppercase tracking-wider text-slate-700 mb-2">
                        Relationships
                      </div>
                      <div className="space-y-1">
                        {selectedDetails.relationships.map((rel: string, idx: number) => (
                          <div
                            key={idx}
                            className="p-1.5 bg-slate-50 border border-slate-200 rounded text-[10px] font-mono text-slate-700"
                          >
                            {rel}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
