"""
CaseIntel — Incident Classification & SHAP Explainability API
Integrates trained XGBoost incident prediction with TreeSHAP explainability,
computing exact feature contributions, baseline expected values, and directional impacts.
"""

from typing import Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from database import get_db
from models.db import InvestigationModel, EntityModel, EventModel, EvidenceModel, VideoModel
from services.incident_service import XGBoostIncidentClassifierService
from services.shap_service import SHAPExplainabilityService

router = APIRouter()
incident_service = XGBoostIncidentClassifierService()
shap_service = SHAPExplainabilityService(incident_service)


@router.get("/{investigation_id}")
def get_incident(investigation_id: str, db: Session = Depends(get_db)):
    """
    Generate real XGBoost incident classification and real TreeSHAP feature importance scores
    for an active investigation using its recorded entities, events, and evidence.
    Returns explicit not_analyzed status when no analyzed video or events exist.
    """
    inv = db.query(InvestigationModel).filter(InvestigationModel.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    inv_videos = db.query(VideoModel).filter(VideoModel.investigation_id == inv.id).all()
    analyzed_videos = [v for v in inv_videos if v.status == "analyzed"]

    # If no videos uploaded or no analyzed videos and no events
    if not inv_videos:
        return {
            "status": "not_analyzed",
            "has_analysis": False,
            "investigation_id": inv.id,
            "case_number": inv.case_number,
            "message": "No analysis available for this investigation.",
            "type": None,
            "confidence": 0.0,
            "severity": None,
            "feature_contributions": [],
            "positive_contributors": [],
            "negative_contributors": [],
            "reasoning": "No video uploaded or analyzed yet.",
            "extracted_features": {},
            "shap_explanation": None,
        }

    # Resolve active video
    target_vid_id = None
    if inv.active_video_id and any(v.id == inv.active_video_id for v in inv_videos):
        target_vid_id = inv.active_video_id
    elif analyzed_videos:
        target_vid_id = analyzed_videos[0].id
    elif inv_videos:
        target_vid_id = inv_videos[0].id

    # Check if target video is not analyzed
    target_video = next((v for v in inv_videos if v.id == target_vid_id), None)
    if target_video and target_video.status != "analyzed" and not inv.events:
        return {
            "status": "not_analyzed",
            "has_analysis": False,
            "investigation_id": inv.id,
            "case_number": inv.case_number,
            "message": "Video uploaded but analysis not completed yet.",
            "type": None,
            "confidence": 0.0,
            "severity": None,
            "feature_contributions": [],
            "positive_contributors": [],
            "negative_contributors": [],
            "reasoning": "Analysis not completed yet for the active video.",
            "extracted_features": {},
            "shap_explanation": None,
        }

    # Query entities, events, evidence scoped to target video
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
        # Fallback to case-wide if events have no video_id
        if not events_db and not entities_db:
            entities_db = db.query(EntityModel).filter(EntityModel.investigation_id == inv.id).all()
            events_db = db.query(EventModel).filter(EventModel.investigation_id == inv.id).all()
            evidence_db = db.query(EvidenceModel).filter(EvidenceModel.investigation_id == inv.id).all()
    else:
        entities_db = db.query(EntityModel).filter(EntityModel.investigation_id == inv.id).all()
        events_db = db.query(EventModel).filter(EventModel.investigation_id == inv.id).all()
        evidence_db = db.query(EvidenceModel).filter(EvidenceModel.investigation_id == inv.id).all()

    if not events_db and not entities_db:
        return {
            "status": "not_analyzed",
            "has_analysis": False,
            "investigation_id": inv.id,
            "case_number": inv.case_number,
            "message": "No analysis available for this investigation.",
            "type": None,
            "confidence": 0.0,
            "severity": None,
            "feature_contributions": [],
            "positive_contributors": [],
            "negative_contributors": [],
            "reasoning": "No events or entities extracted yet.",
            "extracted_features": {},
            "shap_explanation": None,
        }

    entities = [
        {
            "id": e.id.split(":", 1)[1] if ":" in e.id else e.id,
            "type": e.type,
            "label": e.label,
            "confidence": e.confidence,
            "track_duration": e.track_duration,
        }
        for e in entities_db
    ]

    # Synthesize entities from event records if entities table is empty
    if not entities and events_db:
        seen_eids = set()
        for ev in events_db:
            clean_eid = ev.entity_id.split(":", 1)[1] if ":" in ev.entity_id else ev.entity_id
            if clean_eid and clean_eid not in seen_eids:
                seen_eids.add(clean_eid)
                entities.append({
                    "id": clean_eid,
                    "type": ev.entity_type or "person",
                    "label": clean_eid,
                    "confidence": ev.confidence,
                    "track_duration": "16.1s",
                })

    events = [
        {
            "id": ev.id,
            "timestamp": ev.timestamp,
            "event_type": ev.action,
            "description": ev.description,
            "confidence": ev.confidence,
            "severity": "HIGH" if ev.is_suspicious else "LOW",
            "primary_entity_id": ev.entity_id,
        }
        for ev in events_db
    ]

    evidence = [
        {
            "id": evd.id,
            "type": evd.type,
            "confidence": evd.confidence,
            "is_key_evidence": evd.is_key_evidence,
        }
        for evd in evidence_db
    ]

    classification = incident_service.classify(
        events=events,
        entities=entities,
        evidence=evidence,
    )
    classification["has_analysis"] = True
    classification["status"] = "completed"
    classification["investigation_id"] = inv.id
    classification["case_number"] = inv.case_number

    # Compute real TreeSHAP explainability
    shap_res = shap_service.explain(classification.get("extracted_features", {}))
    classification["shap_explanation"] = shap_res
    # Replace feature contributions with real TreeSHAP contributions
    classification["feature_contributions"] = shap_res["feature_contributions"]
    classification["base_value"] = shap_res["base_value"]
    classification["positive_contributors"] = shap_res["positive_contributors"]
    classification["negative_contributors"] = shap_res["negative_contributors"]
    classification["reasoning"] = shap_res["narrative"]

    return classification


@router.get("/{investigation_id}/shap")
def get_shap_explanation(investigation_id: str, db: Session = Depends(get_db)):
    """
    Compute TreeSHAP explainability specifically for an investigation.
    """
    incident_data = get_incident(investigation_id, db=db)
    return incident_data.get("shap_explanation", {})


@router.post("/predict")
def predict_incident_from_features(features: Dict[str, float] = Body(...)):
    """
    Run XGBoost prediction directly from tabular feature vector.
    """
    result = incident_service.classify(
        events=[],
        entities=[],
        custom_features=features,
    )
    # Compute real TreeSHAP
    shap_res = shap_service.explain(features)
    result["shap_explanation"] = shap_res
    result["feature_contributions"] = shap_res["feature_contributions"]
    result["base_value"] = shap_res["base_value"]
    result["positive_contributors"] = shap_res["positive_contributors"]
    result["negative_contributors"] = shap_res["negative_contributors"]
    return result


@router.post("/shap")
def compute_shap_from_features(features: Dict[str, float] = Body(...)):
    """
    Compute real TreeSHAP values directly from custom tabular feature vector.
    """
    return shap_service.explain(features)
