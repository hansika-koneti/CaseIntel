"""
CaseIntel — Events API Router
Returns events for a given investigation, persisted via SQLAlchemy.
"""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.db import EventModel, EvidenceModel
from services.base import normalize_location_name

router = APIRouter()


def _parse_ts_sec(ts_str: str) -> float:
    """Parse MM:SS or HH:MM:SS into seconds for accurate chronological sorting."""
    try:
        parts = str(ts_str).split(":")
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        return float(ts_str)
    except Exception:
        return 0.0


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("")
@router.get("/")
def list_events(
    investigation_id: Optional[str] = Query(None, description="Filter events by investigation ID"),
    entity_id:        Optional[str] = Query(None, description="Filter events by entity ID"),
    video_id:         Optional[str] = Query(None, description="Filter events by video ID"),
    suspicious_only:  bool          = Query(False, description="Return only suspicious events"),
    db: Session                     = Depends(get_db),
):
    """
    Return events, optionally filtered by investigation, entity, video, or suspicion flag.
    Guarantees strict chronological ordering.
    """
    query = db.query(EventModel)
    if investigation_id:
        query = query.filter(EventModel.investigation_id == investigation_id)
    if entity_id:
        query = query.filter(EventModel.entity_id == entity_id)
    if video_id:
        query = query.filter(EventModel.video_id == video_id)
    if suspicious_only:
        query = query.filter(EventModel.is_suspicious == True)

    events_records = query.all()
    events = [
        {
            "id": e.id,
            "timestamp": e.timestamp,
            "entity_id": e.entity_id,
            "entity_type": e.entity_type,
            "action": e.action,
            "location": normalize_location_name(e.location),
            "camera_id": e.camera_id,
            "confidence": e.confidence,
            "evidence_id": e.evidence_id,
            "is_suspicious": e.is_suspicious,
            "description": e.description,
            "related_entity_id": e.related_entity_id,
            "video_id": e.video_id,
        }
        for e in events_records
    ]

    # Strictly sort events chronologically
    events.sort(key=lambda ev: _parse_ts_sec(ev.get("timestamp", "00:00")))


    ev_query = db.query(EvidenceModel)
    if investigation_id:
        ev_query = ev_query.filter(EvidenceModel.investigation_id == investigation_id)
    evidence_records = ev_query.all()
    evidence = [
        {
            "id": ev.id,
            "timestamp": ev.timestamp,
            "camera_id": ev.camera_id,
            "type": ev.type,
            "primary_entity_id": ev.primary_entity_id,
            "secondary_entity_id": ev.secondary_entity_id,
            "confidence": ev.confidence,
            "event_id": ev.event_id,
            "description": ev.description,
            "is_key_evidence": ev.is_key_evidence,
            "sha256": ev.sha256,
            "created_at": ev.created_at,
        }
        for ev in evidence_records
    ]

    return {
        "events": events,
        "evidence": evidence,
        "total": len(events),
        "investigation_id": investigation_id,
    }


@router.get("/{event_id}")
def get_event(event_id: str, db: Session = Depends(get_db)):
    """Return a single event by ID searched across the database."""
    event = db.query(EventModel).filter(EventModel.id == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")
    return {
        "id": event.id,
        "timestamp": event.timestamp,
        "entity_id": event.entity_id,
        "entity_type": event.entity_type,
        "action": event.action,
        "location": normalize_location_name(event.location),
        "camera_id": event.camera_id,
        "confidence": event.confidence,
        "evidence_id": event.evidence_id,
        "is_suspicious": event.is_suspicious,
        "description": event.description,
        "related_entity_id": event.related_entity_id,
    }

