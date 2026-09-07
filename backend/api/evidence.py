"""
CaseIntel — Evidence API Router
Returns and creates evidence for investigations, persisted via SQLAlchemy.
"""

from datetime import datetime, timezone
from uuid import uuid4
import hashlib
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.db import EvidenceModel

router = APIRouter()


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


# ── Request schema ─────────────────────────────────────────────────────────
class EvidenceCreateRequest(BaseModel):
    investigation_id: str
    camera_id: str
    type: str
    primary_entity_id: str
    secondary_entity_id: Optional[str] = None
    event_id: str
    confidence: float = 90.0
    description: str
    is_key_evidence: bool = False


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("")
@router.get("/")
def list_evidence(
    investigation_id: Optional[str] = Query(None, description="Filter by investigation ID"),
    video_id: Optional[str] = Query(None, description="Filter by video ID"),
    db: Session = Depends(get_db),
):
    """Return evidence list, optionally filtered by investigation or video from database."""
    query = db.query(EvidenceModel)
    if investigation_id:
        query = query.filter(EvidenceModel.investigation_id == investigation_id)
    if video_id:
        query = query.filter(EvidenceModel.video_id == video_id)

    items = [
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
            "video_id": ev.video_id,
        }
        for ev in query.order_by(EvidenceModel.created_at.desc()).all()
    ]

    return {"evidence": items, "total": len(items)}


@router.get("/{evidence_id}")
def get_evidence(evidence_id: str, db: Session = Depends(get_db)):
    """Return a single evidence item by ID from the database."""
    ev = db.query(EvidenceModel).filter(EvidenceModel.id == evidence_id).first()
    if ev is None:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")
    return {
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


@router.post("", status_code=201)
@router.post("/", status_code=201)
def create_evidence(body: EvidenceCreateRequest, db: Session = Depends(get_db)):
    """
    Create a new evidence record and persist to database.
    Generates a SHA-256 hash from the description + timestamp for chain-of-custody.
    """
    new_id = f"EV-{uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    sha = _sha256(f"{body.description}|{now}|{new_id}")

    new_item = EvidenceModel(
        id=new_id,
        investigation_id=body.investigation_id,
        timestamp=now,
        camera_id=body.camera_id,
        type=body.type,
        primary_entity_id=body.primary_entity_id,
        secondary_entity_id=body.secondary_entity_id,
        confidence=body.confidence,
        event_id=body.event_id,
        description=body.description,
        is_key_evidence=body.is_key_evidence,
        sha256=sha,
        created_at=now,
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return {
        "id": new_item.id,
        "timestamp": new_item.timestamp,
        "camera_id": new_item.camera_id,
        "type": new_item.type,
        "primary_entity_id": new_item.primary_entity_id,
        "secondary_entity_id": new_item.secondary_entity_id,
        "confidence": new_item.confidence,
        "event_id": new_item.event_id,
        "description": new_item.description,
        "is_key_evidence": new_item.is_key_evidence,
        "sha256": new_item.sha256,
        "created_at": new_item.created_at,
    }


@router.get("/{evidence_id}/chain-of-custody")
def get_chain_of_custody(evidence_id: str, db: Session = Depends(get_db)):
    """Return an audit chain-of-custody log for an evidence item."""
    ev = db.query(EvidenceModel).filter(EvidenceModel.id == evidence_id).first()
    if ev is None:
        raise HTTPException(status_code=404, detail=f"Evidence '{evidence_id}' not found")
    return {
        "evidence_id": evidence_id,
        "chain": [
            {
                "action": "COLLECTED",
                "actor": "AI Pipeline",
                "timestamp": ev.timestamp or ev.created_at,
                "note": "Auto-collected from CCTV analysis pipeline",
            },
            {
                "action": "HASHED",
                "actor": "CaseIntel System",
                "timestamp": ev.created_at or ev.timestamp,
                "sha256": ev.sha256,
            },
        ],
    }
