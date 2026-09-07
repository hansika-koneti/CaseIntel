"""
CaseIntel — Entities API Router
Returns entities for a given investigation, persisted via SQLAlchemy.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.db import EntityModel

router = APIRouter()


@router.get("")
@router.get("/")
def list_entities(
    investigation_id: Optional[str] = Query(None, description="Filter entities by investigation ID"),
    video_id: Optional[str] = Query(None, description="Filter entities by video ID"),
    db: Session = Depends(get_db),
):
    """
    Return entities for an investigation, optionally filtered by video ID.
    """
    query = db.query(EntityModel)
    if investigation_id:
        query = query.filter(EntityModel.investigation_id == investigation_id)
    if video_id:
        query = query.filter(EntityModel.video_id == video_id)
    records = query.all()
    entities = [
        {
            "id": e.id.split(":", 1)[1] if ":" in e.id else e.id,
            "type": e.type,
            "label": e.label,
            "confidence": e.confidence,
            "first_seen": e.first_seen,
            "last_seen": e.last_seen,
            "track_duration": e.track_duration,
            "metadata": e.metadata_json or {},
            "video_id": e.video_id,
        }
        for e in records
    ]
    return {
        "entities": entities,
        "total": len(entities),
        "investigation_id": investigation_id,
        "video_id": video_id,
    }


@router.get("/{entity_id}")
def get_entity(entity_id: str, db: Session = Depends(get_db)):
    """Return a single entity by ID."""
    entity = db.query(EntityModel).filter(
        (EntityModel.id == entity_id) | (EntityModel.id.endswith(f":{entity_id}"))
    ).first()
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")
    clean_id = entity.id.split(":", 1)[1] if ":" in entity.id else entity.id
    return {
        "id": clean_id,
        "type": entity.type,
        "label": entity.label,
        "confidence": entity.confidence,
        "first_seen": entity.first_seen,
        "last_seen": entity.last_seen,
        "track_duration": entity.track_duration,
        "metadata": entity.metadata_json or {},
    }
