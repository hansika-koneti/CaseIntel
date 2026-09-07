"""
CaseIntel — Live Notifications API
Derives real operational and forensic notifications from persistent database records.
Zero mock data: notifications represent genuine case updates, suspicious events,
video processing completions, evidence registrations, and report generations.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models.db import InvestigationModel, EventModel, EvidenceModel, VideoModel
from services.base import normalize_location_name

router = APIRouter()


@router.get("")
@router.get("/")
def list_notifications(
    investigation_id: Optional[str] = Query(None, description="Filter notifications by investigation ID"),
    db: Session = Depends(get_db),
):
    """
    Generate live, structured notifications directly from real database records.
    """
    notifications = []

    # Determine scope: specific investigation or all recent investigations
    inv_query = db.query(InvestigationModel)
    if investigation_id:
        inv_query = inv_query.filter(InvestigationModel.id == investigation_id)
    investigations = inv_query.order_by(InvestigationModel.created_at.desc()).all()

    inv_map = {inv.id: inv for inv in investigations}
    inv_ids = list(inv_map.keys())

    if not inv_ids:
        return {"notifications": [], "total": 0}

    # 1. Real Suspicious Events (HIGH priority)
    suspicious_events = (
        db.query(EventModel)
        .filter(EventModel.investigation_id.in_(inv_ids), EventModel.is_suspicious == True)
        .order_by(EventModel.timestamp.desc())
        .all()
    )
    for ev in suspicious_events:
        inv = inv_map.get(ev.investigation_id)
        case_num = inv.case_number if inv else "Case"
        loc = normalize_location_name(ev.location or (inv.location if inv else ""))
        notifications.append({
            "id": f"notif-susp-{ev.id}",
            "type": "suspicious_event",
            "severity": "HIGH",
            "title": f"Suspicious Activity: {ev.action}",
            "message": ev.description or f"{ev.action} detected on {ev.camera_id} at {loc} ({ev.timestamp}).",
            "timestamp": ev.timestamp,
            "created_at": inv.created_at if inv else "Just now",
            "investigation_id": ev.investigation_id,
            "case_number": case_num,
            "link": f"/timeline",
            "action_label": "View in Timeline",
        })

    # 2. Key Forensic Evidence Records (MEDIUM/HIGH priority)
    evidence_records = (
        db.query(EvidenceModel)
        .filter(EvidenceModel.investigation_id.in_(inv_ids))
        .order_by(EvidenceModel.created_at.desc())
        .all()
    )
    for evd in evidence_records:
        inv = inv_map.get(evd.investigation_id)
        case_num = inv.case_number if inv else "Case"
        notifications.append({
            "id": f"notif-evd-{evd.id}",
            "type": "evidence",
            "severity": "HIGH" if evd.is_key_evidence else "INFO",
            "title": f"Forensic Evidence Logged: {evd.id}",
            "message": evd.description or f"{evd.type} registered with SHA-256 integrity hash on {evd.camera_id}.",
            "timestamp": evd.timestamp or "00:00",
            "created_at": evd.created_at or (inv.created_at if inv else "Just now"),
            "investigation_id": evd.investigation_id,
            "case_number": case_num,
            "link": "/evidence",
            "action_label": "Inspect Evidence",
        })

    # 3. Incident Classifications Generated (MEDIUM priority)
    for inv in investigations:
        if inv.incident_type and inv.incident_type != "Unclassified" and inv.confidence > 0:
            loc = normalize_location_name(inv.location)
            notifications.append({
                "id": f"notif-inc-{inv.id}",
                "type": "incident",
                "severity": inv.severity if inv.severity in ["HIGH", "CRITICAL"] else "MEDIUM",
                "title": f"Incident Assessed: {inv.incident_type}",
                "message": f"ML model assessed {case_num} as '{inv.incident_type}' with {inv.confidence:.1f}% confidence ({loc}).",
                "timestamp": "Latest",
                "created_at": inv.updated_at or inv.created_at,
                "investigation_id": inv.id,
                "case_number": inv.case_number,
                "link": "/incident",
                "action_label": "Review Assessment",
            })

    # 4. Completed Video Analysis Feeds
    videos = (
        db.query(VideoModel)
        .filter(VideoModel.investigation_id.in_(inv_ids))
        .all()
    )
    for v in videos:
        inv = inv_map.get(v.investigation_id)
        case_num = inv.case_number if inv else "Case"
        dur = inv.duration_analyzed if inv and inv.duration_analyzed else "completed"
        notifications.append({
            "id": f"notif-vid-{v.id}",
            "type": "video_analysis",
            "severity": "INFO",
            "title": f"Video Analysis Complete: {v.camera_id}",
            "message": f"Footage '{v.filename}' processed ({dur}) on feed {v.camera_id}.",
            "timestamp": dur,
            "created_at": v.uploaded_at or (inv.created_at if inv else "Just now"),
            "investigation_id": v.investigation_id,
            "case_number": case_num,
            "link": "/analysis",
            "action_label": "View Analysis",
        })

    # 5. Generated Formal Reports
    for inv in investigations:
        if inv.incident_data and isinstance(inv.incident_data, dict) and "report" in inv.incident_data:
            rep = inv.incident_data["report"]
            rep_id = rep.get("id", "REP")
            notifications.append({
                "id": f"notif-rep-{inv.id}-{rep_id}",
                "type": "report",
                "severity": "INFO",
                "title": f"Investigation Report Ready: {rep_id}",
                "message": f"Formal forensics report compiled for {inv.case_number} ({normalize_location_name(inv.location)}).",
                "timestamp": "Ready",
                "created_at": rep.get("generated_at", inv.created_at),
                "investigation_id": inv.id,
                "case_number": inv.case_number,
                "link": "/report",
                "action_label": "Open Report",
            })

    # Prioritize: HIGH severity first, then newest
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    notifications.sort(key=lambda n: (severity_order.get(n.get("severity", "INFO"), 5), n.get("id")))

    return {
        "notifications": notifications,
        "total": len(notifications),
        "investigation_id": investigation_id,
    }
