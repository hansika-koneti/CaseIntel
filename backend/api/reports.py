"""
CaseIntel — Investigation Report Generation API
Integrates LLMReportGeneratorService with persistent investigation database components.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.db import InvestigationModel, EntityModel, EventModel, EvidenceModel, VideoModel
from services.report_service import LLMReportGeneratorService
from services.incident_service import XGBoostIncidentClassifierService

router = APIRouter()
report_service = LLMReportGeneratorService()
incident_service = XGBoostIncidentClassifierService()


from services.base import normalize_location_name

def _get_case_payload(inv: InvestigationModel, db: Session):
    """Assemble structured case components for report generation scoped to active video."""
    video_db = None
    if inv.active_video_id:
        video_db = db.query(VideoModel).filter(VideoModel.id == inv.active_video_id, VideoModel.investigation_id == inv.id).first()
    if not video_db:
        video_db = db.query(VideoModel).filter(VideoModel.investigation_id == inv.id).order_by(VideoModel.uploaded_at.desc()).first()

    target_vid_id = video_db.id if video_db else None

    if target_vid_id:
        entities_db = db.query(EntityModel).filter(
            EntityModel.investigation_id == inv.id,
            EntityModel.video_id == target_vid_id,
        ).all()
        events_db = db.query(EventModel).filter(
            EventModel.investigation_id == inv.id,
            EventModel.video_id == target_vid_id,
        ).all()
        evidence_db = db.query(EvidenceModel).filter(
            EvidenceModel.investigation_id == inv.id,
            EvidenceModel.video_id == target_vid_id,
        ).all()
        if not events_db and not entities_db:
            entities_db = db.query(EntityModel).filter(EntityModel.investigation_id == inv.id).all()
            events_db = db.query(EventModel).filter(EventModel.investigation_id == inv.id).all()
            evidence_db = db.query(EvidenceModel).filter(EvidenceModel.investigation_id == inv.id).all()
    else:
        entities_db = db.query(EntityModel).filter(EntityModel.investigation_id == inv.id).all()
        events_db = db.query(EventModel).filter(EventModel.investigation_id == inv.id).all()
        evidence_db = db.query(EvidenceModel).filter(EvidenceModel.investigation_id == inv.id).all()

    entities = [
        {"id": e.id.split(":", 1)[1] if ":" in e.id else e.id, "type": e.type, "label": e.label, "confidence": e.confidence}
        for e in entities_db
    ]

    events = [
        {
            "id": ev.id,
            "timestamp": ev.timestamp,
            "action": ev.action,
            "event_type": ev.action,
            "description": ev.description,
            "confidence": ev.confidence,
            "is_suspicious": ev.is_suspicious,
            "primary_entity_id": ev.entity_id,
        }
        for ev in events_db
    ]

    # Synthesize fallback entities if entities_db empty but events present
    if not entities and events:
        seen_entity_ids = set()
        for ev in events:
            ent_id = ev.get("primary_entity_id") or ""
            if ent_id and ent_id not in seen_entity_ids:
                seen_entity_ids.add(ent_id)
                entities.append({
                    "id": ent_id,
                    "type": "person" if "person" in ent_id.lower() or ent_id.startswith("P") else "vehicle",
                    "label": ent_id,
                    "confidence": ev.get("confidence", 90.0),
                })

    evidence = [
        {"id": evd.id, "type": evd.type, "description": evd.description, "confidence": evd.confidence}
        for evd in evidence_db
    ]

    # Calculate or retrieve real incident classification only if analysis has occurred
    has_analysis = bool(events or entities or (video_db and video_db.status == "analyzed"))
    if inv.incident_data and isinstance(inv.incident_data, dict) and inv.incident_data.get("has_analysis", True) and inv.incident_data.get("type") and inv.incident_data.get("type") != "Unclassified":
        incident_result = inv.incident_data
    elif has_analysis and (events or entities):
        incident_result = incident_service.classify(events=events, entities=entities, evidence=evidence)
    else:
        incident_result = None

    camera_ids = [video_db.camera_id] if video_db and video_db.camera_id else ["C-01"]

    return {
        "id": inv.id,
        "case_number": inv.case_number,
        "location": normalize_location_name(inv.location),
        "investigator": inv.investigator,
        "entities": entities,
        "events": events,
        "evidence": evidence,
        "incident": incident_result,
        "camera_ids": camera_ids,
    }


@router.post("/{investigation_id}/generate")
def generate_report(investigation_id: str, db: Session = Depends(get_db)):
    """
    Generate a new structured investigation report from real case components.
    Requires at least one analyzed video or extracted events.
    """
    inv = db.query(InvestigationModel).filter(InvestigationModel.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    has_analyzed = (
        db.query(VideoModel).filter(VideoModel.investigation_id == inv.id, VideoModel.status == "analyzed").first() is not None
        or (len(inv.events) > 0 and len(inv.entities) > 0)
    )
    if not has_analyzed:
        raise HTTPException(
            status_code=400,
            detail="Cannot generate report: No analyzed CCTV video footage available for this investigation.",
        )

    case_payload = _get_case_payload(inv, db)
    report = report_service.generate(case_payload)

    # Persist report in investigation record
    current_inc_data = inv.incident_data or {}
    current_inc_data["report"] = report
    inv.incident_data = current_inc_data
    db.commit()

    return {"status": "generated", "report": report}


@router.get("/{investigation_id}")
def get_report(investigation_id: str, db: Session = Depends(get_db)):
    """
    Fetch existing or freshly generated report for an active investigation.
    Returns not_analyzed if no video analysis has been performed.
    """
    inv = db.query(InvestigationModel).filter(InvestigationModel.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    has_analyzed = (
        db.query(VideoModel).filter(VideoModel.investigation_id == inv.id, VideoModel.status == "analyzed").first() is not None
        or (len(inv.events) > 0 and len(inv.entities) > 0)
    )
    if not has_analyzed:
        return {
            "status": "not_analyzed",
            "has_analysis": False,
            "message": "No report available: Analysis not completed yet.",
            "report": None,
        }

    if inv.incident_data and isinstance(inv.incident_data, dict) and "report" in inv.incident_data and inv.incident_data["report"]:
        return inv.incident_data["report"]

    # Generate if not cached
    case_payload = _get_case_payload(inv, db)
    report = report_service.generate(case_payload)
    return report
