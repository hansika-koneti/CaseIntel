"""
CaseIntel — Knowledge Graph API
Queries dynamic case subgraphs using Neo4j and SQLite case components.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.db import InvestigationModel, EntityModel, EventModel, EvidenceModel, VideoModel
from services.neo4j_service import Neo4jKnowledgeGraphService

router = APIRouter()
kg_service = Neo4jKnowledgeGraphService()


@router.get("/{investigation_id}")
def get_knowledge_graph(investigation_id: str, db: Session = Depends(get_db)):
    """
    Query the knowledge graph representation of an investigation.
    Returns dynamic nodes (persons, vehicles, cameras, locations, events, activities, timestamps),
    edges (ENTERED, APPROACHED, DETECTED_BY, TRIGGERED, PERFORMED, MONITORS, LOCATED_IN),
    and entity inspector details.
    """
    inv = db.query(InvestigationModel).filter(InvestigationModel.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    video_db = None
    if inv.active_video_id:
        video_db = db.query(VideoModel).filter(VideoModel.id == inv.active_video_id, VideoModel.investigation_id == inv.id).first()
        entities_db = db.query(EntityModel).filter(EntityModel.investigation_id == inv.id, EntityModel.video_id == inv.active_video_id).all()
        events_db = db.query(EventModel).filter(EventModel.investigation_id == inv.id, EventModel.video_id == inv.active_video_id).all()
        evidence_db = db.query(EvidenceModel).filter(EvidenceModel.investigation_id == inv.id, EvidenceModel.video_id == inv.active_video_id).all()
        if not entities_db and not events_db:
            entities_db = db.query(EntityModel).filter(EntityModel.investigation_id == inv.id).all()
            events_db = db.query(EventModel).filter(EventModel.investigation_id == inv.id).all()
            evidence_db = db.query(EvidenceModel).filter(EvidenceModel.investigation_id == inv.id).all()
    else:
        entities_db = db.query(EntityModel).filter(EntityModel.investigation_id == inv.id).all()
        events_db = db.query(EventModel).filter(EventModel.investigation_id == inv.id).all()
        evidence_db = db.query(EvidenceModel).filter(EvidenceModel.investigation_id == inv.id).all()

    if not video_db:
        video_db = db.query(VideoModel).filter(VideoModel.investigation_id == inv.id).order_by(VideoModel.uploaded_at.desc()).first()

    entity_events_map: dict = {}
    for ev in events_db:
        clean_eid = ev.entity_id.split(":", 1)[1] if (ev.entity_id and ":" in ev.entity_id) else (ev.entity_id or "")
        entity_events_map.setdefault(clean_eid, []).append(ev)

    known_entity_ids = set()
    entities = []
    for e in entities_db:
        clean_id = e.id.split(":", 1)[1] if ":" in e.id else e.id
        known_entity_ids.add(clean_id)
        ev_list = entity_events_map.get(clean_id, [])
        first_s = e.first_seen or (ev_list[0].timestamp if ev_list else "00:00")
        last_s = e.last_seen or (ev_list[-1].timestamp if ev_list else "00:16")
        entities.append({
            "id": clean_id,
            "type": e.type,
            "label": e.label,
            "confidence": e.confidence,
            "first_seen": first_s,
            "last_seen": last_s,
            "track_duration": e.track_duration or f"{first_s} - {last_s}",
            "activities": [
                {
                    "label": ev.action,
                    "confidence": ev.confidence,
                    "timestamp": ev.timestamp,
                    "is_suspicious": ev.is_suspicious,
                    "description": ev.description,
                }
                for ev in ev_list
            ]
        })

    # Synthesize any entities referenced in events that are not in the entities table
    for clean_eid, ev_list in entity_events_map.items():
        if clean_eid and clean_eid not in known_entity_ids:
            known_entity_ids.add(clean_eid)
            ent_type = ev_list[0].entity_type if ev_list else "person"
            first_s = ev_list[0].timestamp if ev_list else "00:00"
            last_s = ev_list[-1].timestamp if ev_list else "00:16"
            avg_conf = sum(ev.confidence for ev in ev_list) / len(ev_list) if ev_list else 90.0
            entities.append({
                "id": clean_eid,
                "type": ent_type,
                "label": clean_eid,
                "confidence": round(avg_conf, 1),
                "first_seen": first_s,
                "last_seen": last_s,
                "track_duration": f"{first_s} - {last_s}",
                "activities": [
                    {
                        "label": ev.action,
                        "confidence": ev.confidence,
                        "timestamp": ev.timestamp,
                        "is_suspicious": ev.is_suspicious,
                        "description": ev.description,
                    }
                    for ev in ev_list
                ]
            })

    events = [
        {
            "id": ev.id,
            "timestamp": ev.timestamp,
            "event_type": ev.action,
            "action": ev.action,
            "description": ev.description,
            "confidence": ev.confidence,
            "is_suspicious": ev.is_suspicious,
            "primary_entity_id": ev.entity_id.split(":", 1)[1] if (ev.entity_id and ":" in ev.entity_id) else ev.entity_id,
            "related_entity_id": ev.related_entity_id.split(":", 1)[1] if (ev.related_entity_id and ":" in ev.related_entity_id) else ev.related_entity_id,
            "camera_id": ev.camera_id or (video_db.camera_id if video_db else "C-01"),
            "location": ev.location if ev.location and ev.location not in ["undefined", "null", "Location not specified"] else inv.location,
        }
        for ev in events_db
    ]

    evidence = [
        {
            "id": evd.id,
            "type": evd.type,
            "confidence": evd.confidence,
            "is_key_evidence": evd.is_key_evidence,
            "primary_entity_id": evd.primary_entity_id.split(":", 1)[1] if (evd.primary_entity_id and ":" in evd.primary_entity_id) else evd.primary_entity_id,
            "secondary_entity_id": evd.secondary_entity_id.split(":", 1)[1] if (evd.secondary_entity_id and ":" in evd.secondary_entity_id) else evd.secondary_entity_id,
            "description": evd.description,
            "event_id": evd.event_id,
        }
        for evd in evidence_db
    ]

    camera_id = video_db.camera_id if video_db else (events_db[0].camera_id if events_db else "C-01")
    active_video_id = inv.active_video_id or (video_db.id if video_db else None)

    graph = kg_service.build_graph_from_case(
        investigation_id=inv.id,
        case_number=inv.case_number,
        location=inv.location,
        entities=entities,
        events=events,
        evidence=evidence,
        camera_id=camera_id,
        video_id=active_video_id,
        investigation_data={
            "id": inv.id,
            "case_number": inv.case_number,
            "incident_type": inv.incident_type,
            "severity": inv.severity,
            "status": inv.status,
            "confidence": inv.confidence,
            "location": inv.location,
        },
    )

    return graph

