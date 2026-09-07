"""
CaseIntel — Investigations API Router
Handles CRUD for investigations, persisted via SQLAlchemy.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.db import InvestigationModel, VideoModel
from models.schemas import InvestigationCreateRequest
from services.base import normalize_location_name

router = APIRouter()


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("")
@router.get("/")
def list_investigations(db: Session = Depends(get_db)):
    """Return the full investigations list as summary objects from the database."""
    records = db.query(InvestigationModel).order_by(InvestigationModel.created_at.desc()).all()
    investigations = [
        {
            "id": inv.id,
            "case_number": inv.case_number,
            "status": inv.status,
            "incident_type": inv.incident_type,
            "severity": inv.severity,
            "confidence": inv.confidence,
            "location": normalize_location_name(inv.location),
            "created_at": inv.created_at,
            "investigator": inv.investigator,
            "video_count": len(inv.videos) if inv.videos else 0,
        }
        for inv in records
    ]
    return {"investigations": investigations, "total": len(investigations)}



@router.post("", status_code=201)
@router.post("/", status_code=201)
def create_investigation(body: InvestigationCreateRequest, db: Session = Depends(get_db)):
    """
    Create a new investigation.
    Starts completely clean: 0 videos, 0 entities, 0 events, 0 evidence, 0.0% confidence.
    """
    new_id = f"inv-{uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    severity_val = body.severity.value if hasattr(body.severity, "value") else str(body.severity)
    status_val = body.status.value if hasattr(body.status, "value") else str(body.status)
    loc_clean = body.location.strip() if body.location and body.location.strip() else "Location not specified"

    new_item = InvestigationModel(
        id=new_id,
        case_number=body.case_number,
        status=status_val,
        incident_type=body.incident_type or "Unclassified",
        severity=severity_val,
        confidence=0.0,
        location=loc_clean,
        created_at=now,
        updated_at=now,
        investigator=body.investigator or "Unassigned",
        video_count=0,
        duration_analyzed="00:00:00",
        ai_insight=f"Investigation {body.case_number} initialised. Pending video analysis.",
        incident_data={
            "type": body.incident_type or "Unclassified",
            "confidence": 0.0,
            "severity": severity_val,
            "classifier_version": "pending",
            "feature_contributions": [],
            "reasoning": "No video analyzed yet.",
        },
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return {
        "id": new_item.id,
        "case_number": new_item.case_number,
        "status": new_item.status,
        "incident_type": new_item.incident_type,
        "severity": new_item.severity,
        "confidence": new_item.confidence,
        "location": new_item.location,
        "created_at": new_item.created_at,
        "investigator": new_item.investigator,
        "video_count": 0,
    }



@router.get("/{investigation_id}")
def get_investigation(investigation_id: str, db: Session = Depends(get_db)):
    """
    Return full investigation detail from the database, including related
    events, evidence, and detected entities.
    """
    inv = db.query(InvestigationModel).filter(InvestigationModel.id == investigation_id).first()
    if inv is None:
        raise HTTPException(status_code=404, detail=f"Investigation '{investigation_id}' not found")

    events = [
        {
            "id": e.id,
            "timestamp": e.timestamp,
            "entity_id": e.entity_id,
            "entity_type": e.entity_type,
            "action": e.action,
            "location": e.location,
            "camera_id": e.camera_id,
            "confidence": e.confidence,
            "evidence_id": e.evidence_id,
            "is_suspicious": e.is_suspicious,
            "description": e.description,
            "related_entity_id": e.related_entity_id,
            "video_id": e.video_id,
        }
        for e in inv.events
    ]

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
            "video_id": ev.video_id,
        }
        for ev in inv.evidence
    ]

    # Build a map of entity_id -> list of events for that entity
    entity_events_map: dict = {}
    for e in inv.events:
        entity_events_map.setdefault(e.entity_id, []).append(e)

    entities = []
    for ent in inv.entities:
        clean_id = ent.id.split(":", 1)[1] if ":" in ent.id else ent.id
        # Derive real camera IDs from events for this entity
        ent_cams = sorted({e.camera_id for e in entity_events_map.get(clean_id, []) if e.camera_id})
        if not ent_cams:
            ent_cams = [ent.metadata_json.get("camera_id", "C-01")] if isinstance(ent.metadata_json, dict) else ["C-01"]

        # Build activities from matching events (excluding basic entry/departure placeholders)
        activities = [
            {
                "id": f"act-{e.id}",
                "label": e.action,
                "confidence": e.confidence,
                "start_time": e.timestamp,
                "end_time": e.timestamp,
            }
            for e in entity_events_map.get(clean_id, [])
        ]

        # Safely serialize metadata — ensure it is always a flat dict of scalars
        raw_meta = ent.metadata_json or {}
        safe_meta = {}
        if isinstance(raw_meta, dict):
            for k, v in raw_meta.items():
                if k == "trajectory":
                    # Summarise trajectory as a count rather than a nested list
                    safe_meta["trajectory_points"] = len(v) if isinstance(v, list) else 0
                elif isinstance(v, (str, int, float, bool)):
                    safe_meta[k] = v
                else:
                    safe_meta[k] = str(v)

        entities.append({
            "id": clean_id,
            "type": ent.type,
            "label": ent.label,
            "confidence": ent.confidence,
            "first_seen": ent.first_seen,
            "last_seen": ent.last_seen,
            "track_duration": ent.track_duration,
            "activities": activities,
            "camera_ids": ent_cams,
            "metadata": safe_meta,
            "trajectory": raw_meta.get("trajectory", []) if isinstance(raw_meta, dict) else [],
            "video_id": ent.video_id,
        })

    # Synthesize entities from event records if entities table had no persisted rows for this investigation
    if not entities and entity_events_map:
        for clean_eid, ev_list in entity_events_map.items():
            if not clean_eid:
                continue
            ent_type = ev_list[0].entity_type if ev_list else "person"
            first_s = ev_list[0].timestamp if ev_list else "00:00"
            last_s = ev_list[-1].timestamp if ev_list else "00:16"
            avg_conf = round(sum(ev.confidence for ev in ev_list) / len(ev_list), 1) if ev_list else 85.0
            ent_cams = sorted({e.camera_id for e in ev_list if e.camera_id}) or ["C-01"]
            activities = [
                {
                    "id": f"act-{e.id}",
                    "label": e.action,
                    "confidence": e.confidence,
                    "start_time": e.timestamp,
                    "end_time": e.timestamp,
                }
                for e in ev_list
            ]
            entities.append({
                "id": clean_eid,
                "type": ent_type,
                "label": clean_eid,
                "confidence": avg_conf,
                "first_seen": first_s,
                "last_seen": last_s,
                "track_duration": f"{first_s} - {last_s}",
                "activities": activities,
                "camera_ids": ent_cams,
                "metadata": {"trajectory_points": 0, "class": ent_type},
                "trajectory": [],
                "video_id": ev_list[0].video_id if ev_list else None,
            })

    # Derive real camera IDs and video records ordered by uploaded_at desc
    inv_videos = db.query(VideoModel).filter(
        VideoModel.investigation_id == investigation_id
    ).order_by(VideoModel.uploaded_at.desc()).all()

    analyzed_videos = [v for v in inv_videos if v.status == "analyzed"]
    has_analysis = bool(analyzed_videos or len(inv.events) > 0)

    if not has_analysis:
        incident = {
            "type": None,
            "confidence": 0.0,
            "severity": None,
            "classifier_version": "pending",
            "feature_contributions": [],
            "reasoning": "No video analysis performed yet.",
            "has_analysis": False,
            "status": "not_analyzed",
        }
    else:
        incident = inv.incident_data or {
            "type": inv.incident_type,
            "confidence": inv.confidence,
            "severity": inv.severity,
            "classifier_version": "v1.0",
            "feature_contributions": [],
            "reasoning": "Analysis completed.",
            "has_analysis": True,
            "status": "completed",
        }
        if isinstance(incident, dict):
            incident["has_analysis"] = True

    real_camera_ids = sorted({v.camera_id for v in inv_videos if v.camera_id})
    if not real_camera_ids:
        # Fall back to camera IDs from event records
        real_camera_ids = sorted({e.camera_id for e in inv.events if e.camera_id})

    valid_vid_ids = {v.id for v in inv_videos}
    # Validate active_video_id belongs to THIS investigation
    if inv.active_video_id and inv.active_video_id in valid_vid_ids:
        primary_vid_id = inv.active_video_id
    elif inv_videos:
        primary_vid_id = inv_videos[0].id
    else:
        primary_vid_id = None

    normalized_loc = normalize_location_name(inv.location)

    # Normalize locations in events
    for evt in events:
        evt["location"] = normalize_location_name(evt.get("location")) or normalized_loc

    return {
        "id": inv.id,
        "case_number": inv.case_number,
        "status": inv.status,
        "incident_type": incident.get("type") if has_analysis else "Unclassified",
        "severity": inv.severity if has_analysis else "MEDIUM",
        "confidence": inv.confidence if has_analysis else 0.0,
        "location": normalized_loc,
        "created_at": inv.created_at,
        "updated_at": inv.updated_at or inv.created_at,
        "investigator": inv.investigator,
        "video_count": len(analyzed_videos),
        "total_videos": len(inv_videos),
        "has_analysis": has_analysis,
        "camera_ids": real_camera_ids,
        "duration_analyzed": inv.duration_analyzed if has_analysis else "00:00:00",
        "ai_insight": inv.ai_insight if has_analysis else "Investigation registered. Pending CCTV footage upload and forensic analysis.",
        "incident": incident,
        "entities": entities if has_analysis else [],
        "events": events if has_analysis else [],
        "evidence": evidence if has_analysis else [],
        "video_id": primary_vid_id,
        "active_video_id": primary_vid_id,
        "videos": [
            {
                "id": v.id,
                "filename": v.filename,
                "camera_id": v.camera_id,
                "uploaded_at": v.uploaded_at,
                "status": v.status,
                "location": v.location,
            }
            for v in inv_videos
        ],
    }


@router.post("/{investigation_id}/set-active-video/{video_id}")
def set_active_video(investigation_id: str, video_id: str, db: Session = Depends(get_db)):
    """Explicitly set and validate the active video for an investigation."""
    inv = db.query(InvestigationModel).filter(InvestigationModel.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    video = db.query(VideoModel).filter(
        VideoModel.id == video_id,
        VideoModel.investigation_id == investigation_id,
    ).first()
    if not video:
        raise HTTPException(status_code=400, detail=f"Video '{video_id}' does not belong to investigation '{investigation_id}'")

    inv.active_video_id = video_id
    db.commit()
    return {
        "success": True,
        "investigation_id": investigation_id,
        "active_video_id": video_id,
        "filename": video.filename,
    }



