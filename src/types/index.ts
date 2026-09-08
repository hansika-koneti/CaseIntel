// ============================================================
// CaseIntel — Core TypeScript Types
// ============================================================

export type InvestigationStatus =
  | 'pending'
  | 'processing'
  | 'under_investigation'
  | 'closed'
  | 'escalated';

export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type EntityType = 'person' | 'vehicle' | 'camera' | 'location' | 'event' | 'activity' | 'timestamp' | 'object';

export type PipelineStageStatus = 'pending' | 'processing' | 'completed' | 'error';

// ── Entity ───────────────────────────────────────────────────
export interface Activity {
  id: string;
  label: string;
  confidence: number;
  startTime: string;
  endTime: string;
}

export interface TrajectoryPoint {
  frame: number;
  timestampSec?: number;
  x: number;
  y: number;
}

export interface Entity {
  id: string;
  type: EntityType;
  label: string;
  confidence: number;
  firstSeen: string;
  lastSeen: string;
  trackDuration: string;
  activities: Activity[];
  cameraIds: string[];
  metadata?: Record<string, string | number | boolean>;
  trajectory?: TrajectoryPoint[];
  videoId?: string;
}

// ── Event ────────────────────────────────────────────────────
export interface InvestigationEvent {
  id: string;
  timestamp: string;
  entityId: string;
  entityType: EntityType;
  action: string;
  location: string;
  cameraId: string;
  confidence: number;
  evidenceId?: string;
  isSuspicious: boolean;
  description: string;
  relatedEntityId?: string;
  videoId?: string;
}

// ── Evidence ─────────────────────────────────────────────────
export interface Evidence {
  id: string;
  timestamp: string;
  cameraId: string;
  type: string;
  primaryEntityId: string;
  secondaryEntityId?: string;
  confidence: number;
  eventId: string;
  frameUrl?: string;
  description: string;
  isKeyEvidence: boolean;
  sha256?: string;
  createdAt?: string;
  videoId?: string;
}

// ── Incident ─────────────────────────────────────────────────
export interface FeatureContribution {
  feature: string;
  contribution: number;
  direction: 'positive' | 'negative';
}

export interface ForensicRuleStep {
  step: number;
  name: string;
  status: 'detected' | 'unverified' | 'detected_or_observed' | 'not_detected' | string;
  detail: string;
}

export interface VerifiedObservation {
  action: string;
  confidence: number;
  severity: string;
  description: string;
  timestamp: string;
  entity_id: string;
}

export interface IncidentResult {
  type: string | null;
  confidence: number;
  severity: Severity | null;
  incident_risk_score?: number;
  incidentRiskScore?: number;
  featureContributions: FeatureContribution[];
  reasoning: string;
  classifierVersion: string;
  has_analysis?: boolean;
  hasAnalysis?: boolean;
  status?: string;
  theft_visually_verified?: boolean;
  theftVisuallyVerified?: boolean;
  is_hypothesis?: boolean;
  isHypothesis?: boolean;
  hypothesis_status?: string;
  hypothesisStatus?: string;
  visual_evidence_summary?: string;
  visualEvidenceSummary?: string;
  forensic_rule_evaluation?: ForensicRuleStep[];
  forensicRuleEvaluation?: ForensicRuleStep[];
  verified_observations?: VerifiedObservation[];
  verifiedObservations?: VerifiedObservation[];
  class_probabilities?: Record<string, number>;
  extracted_features?: Record<string, number>;
  base_value?: number;
}

// ── Knowledge Graph ──────────────────────────────────────────
export interface GraphNodeData {
  label: string;
  entityType: EntityType;
  confidence?: number;
  metadata?: Record<string, string | number | boolean>;
}

export interface GraphEdgeData {
  relationship: string;
}

// ── Pipeline ─────────────────────────────────────────────────
export interface PipelineStage {
  id: string;
  label: string;
  status: PipelineStageStatus;
  progress: number;
  processingTimeMs?: number;
  detail?: string;
}

// ── Report ───────────────────────────────────────────────────
export interface ReportSection {
  id: string;
  title: string;
  content: string;
}

export interface Report {
  id: string;
  investigationId: string;
  generatedAt: string;
  generatorModel: string;
  executiveSummary: string;
  sections: ReportSection[];
  disclaimer: string;
  has_analysis?: boolean;
}

// ── Investigation ────────────────────────────────────────────
export interface Investigation {
  id: string;
  caseNumber: string;
  status: InvestigationStatus;
  createdAt: string;
  updatedAt: string;
  investigator: string;
  cameraIds: string[];
  location: string;
  videoCount: number;
  durationAnalyzed: string;
  incident: IncidentResult;
  entities: Entity[];
  events: InvestigationEvent[];
  evidence: Evidence[];
  report?: Report;
  aiInsight: string;
  has_analysis?: boolean;
  hasAnalysis?: boolean;
  videoId?: string;
  activeVideoId?: string;
  videos?: Array<{
    id: string;
    filename: string;
    camera_id?: string;
    cameraId?: string;
    uploaded_at?: string;
    uploadedAt?: string;
    status?: string;
    location?: string;
  }>;
}

// ── Camera ───────────────────────────────────────────────────
export interface Camera {
  id: string;
  label: string;
  location: string;
  status: 'online' | 'offline' | 'recording';
}

// ── Video Upload ─────────────────────────────────────────────
export interface VideoUpload {
  id: string;
  filename: string;
  size: number;
  progress: number;
  status: 'uploading' | 'uploaded' | 'error';
  cameraId?: string;
  location?: string;
}

// ── System Status ────────────────────────────────────────────
export interface SystemStatus {
  videoAnalyzer: 'online' | 'offline' | 'degraded';
  knowledgeGraph: 'online' | 'offline' | 'degraded';
  classifier: 'online' | 'offline' | 'degraded';
  reportGenerator: 'online' | 'offline' | 'degraded';
}
