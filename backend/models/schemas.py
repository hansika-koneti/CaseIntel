"""
CaseIntel — Pydantic Schemas
All request/response models for the API.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel


# ── Enums ──────────────────────────────────────────────────────────────────
class InvestigationStatus(str, Enum):
    pending              = "pending"
    processing           = "processing"
    under_investigation  = "under_investigation"
    closed               = "closed"
    escalated            = "escalated"


class Severity(str, Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class EntityType(str, Enum):
    person    = "person"
    vehicle   = "vehicle"
    camera    = "camera"
    location  = "location"
    event     = "event"
    activity  = "activity"
    timestamp = "timestamp"


# ── Activity ────────────────────────────────────────────────────────────────
class Activity(BaseModel):
    id:         str
    label:      str
    confidence: float
    start_time: str
    end_time:   str


# ── Entity ──────────────────────────────────────────────────────────────────
class Entity(BaseModel):
    id:             str
    type:           EntityType
    label:          str
    confidence:     float
    first_seen:     str
    last_seen:      str
    track_duration: str
    activities:     List[Activity] = []
    camera_ids:     List[str] = []
    metadata:       Dict[str, Any] = {}


# ── Event ────────────────────────────────────────────────────────────────────
class InvestigationEvent(BaseModel):
    id:                str
    timestamp:         str
    entity_id:         str
    entity_type:       EntityType
    action:            str
    location:          str
    camera_id:         str
    confidence:        float
    evidence_id:       Optional[str] = None
    is_suspicious:     bool
    description:       str
    related_entity_id: Optional[str] = None


# ── Evidence ─────────────────────────────────────────────────────────────────
class Evidence(BaseModel):
    id:                  str
    timestamp:           str
    camera_id:           str
    type:                str
    primary_entity_id:   str
    secondary_entity_id: Optional[str] = None
    confidence:          float
    event_id:            str
    frame_url:           Optional[str] = None
    description:         str
    is_key_evidence:     bool


# ── Incident ──────────────────────────────────────────────────────────────────
class FeatureContribution(BaseModel):
    feature:      str
    contribution: float
    direction:    str  # "positive" | "negative"


class IncidentResult(BaseModel):
    type:                   str
    confidence:             float
    severity:               Severity
    feature_contributions:  List[FeatureContribution]
    reasoning:              str
    classifier_version:     str


# ── Report ────────────────────────────────────────────────────────────────────
class ReportSection(BaseModel):
    id:      str
    title:   str
    content: str


class Report(BaseModel):
    id:               str
    investigation_id: str
    generated_at:     str
    generator_model:  str
    executive_summary: str
    sections:         List[ReportSection]
    disclaimer:       str


# ── Knowledge Graph ───────────────────────────────────────────────────────────
class GraphNode(BaseModel):
    id:         str
    label:      str
    type:       EntityType
    confidence: Optional[float] = None
    x:          float
    y:          float


class GraphEdge(BaseModel):
    id:           str
    source:       str
    target:       str
    relationship: str
    suspicious:   bool = False


class KnowledgeGraphResponse(BaseModel):
    investigation_id: str
    nodes:            List[GraphNode]
    edges:            List[GraphEdge]


# ── Investigation ─────────────────────────────────────────────────────────────
class Investigation(BaseModel):
    id:               str
    case_number:      str
    status:           InvestigationStatus
    created_at:       str
    updated_at:       str
    investigator:     str
    camera_ids:       List[str]
    location:         str
    video_count:      int
    duration_analyzed: str
    incident:         IncidentResult
    entities:         List[Entity]
    events:           List[InvestigationEvent]
    evidence:         List[Evidence]
    report:           Optional[Report] = None
    ai_insight:       str


class InvestigationSummary(BaseModel):
    id:            str
    case_number:   str
    status:        InvestigationStatus
    incident_type: str
    severity:      Severity
    confidence:    float
    location:      str
    created_at:    str
    investigator:  str
    video_count:   int


class InvestigationCreateRequest(BaseModel):
    case_number:   str
    incident_type: str
    location:      str
    severity:      Severity = Severity.HIGH
    status:        InvestigationStatus = InvestigationStatus.under_investigation
    video_count:   int = 1
    confidence:    float = 85.0
    investigator:  str = "Unassigned"


# ── Video Upload ──────────────────────────────────────────────────────────────
class VideoAnalysisRequest(BaseModel):
    camera_id:     str
    location:      str
    date:          str
    start_time:    str
    analysis_mode: str = "full"


class VideoAnalysisStatus(BaseModel):
    video_id:         str
    status:           str
    pipeline_stages:  List[Dict[str, Any]]
    completed_stages: int
    total_stages:     int
    result_summary:   Optional[str] = None
