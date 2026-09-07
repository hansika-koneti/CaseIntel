"""
CaseIntel — Videos API Router
Handles real multipart video uploads, metadata extraction via OpenCV,
file streaming, and pipeline analysis execution.
"""

import os
import time
from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models.db import VideoModel, EntityModel, EventModel, EvidenceModel, InvestigationModel
from services.yolo_service import YOLOv11DetectorService
from services.action_recognition_service import ActionRecognitionService
from services.incident_service import XGBoostIncidentClassifierService
from services.shap_service import SHAPExplainabilityService
from services.ocr_service import EasyOCRService

router = APIRouter()
yolo_detector = YOLOv11DetectorService()
action_service = ActionRecognitionService()
incident_classifier = XGBoostIncidentClassifierService()
shap_service = SHAPExplainabilityService(incident_classifier)
ocr_service = EasyOCRService()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _get_video_metadata(filepath: str) -> dict:
    """Extract real video metadata using OpenCV if available."""
    try:
        import cv2
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            return {"valid": False}
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = round(frame_count / fps, 2) if fps > 0 else 0
        cap.release()
        return {
            "valid": True,
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "duration_seconds": duration,
        }
    except Exception:
        return {"valid": False}


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    camera_id: str = Form("C-01"),
    location: Optional[str] = Form(None),
    investigation_id: Optional[str] = Form(None),
    analysis_mode: str = Form("full"),
    db: Session = Depends(get_db),
):
    """
    Accepts real multipart/form-data video upload, saves it to disk in the
    backend uploads directory, inspects technical video metadata, and registers
    the record in the database.
    If no investigation_id is provided, automatically creates a fresh investigation
    with clean zero counts.
    """
    video_id = f"vid-{uuid4().hex[:8]}"
    safe_filename = file.filename.replace(" ", "_") if file.filename else "video.mp4"
    dest_path = os.path.join(UPLOAD_DIR, f"{video_id}_{safe_filename}")

    # Stream upload to disk
    total_bytes = 0
    with open(dest_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            buffer.write(chunk)
            total_bytes += len(chunk)

    meta = _get_video_metadata(dest_path)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Resolve investigation
    resolved_inv_id = investigation_id

    # Resolve location: Never invent or default to Parking Area
    clean_loc = (location or "").strip()
    if resolved_inv_id:
        existing_inv = db.query(InvestigationModel).filter(InvestigationModel.id == resolved_inv_id).first()
        if not existing_inv:
            resolved_inv_id = None
        elif not clean_loc:
            clean_loc = existing_inv.location or "Location not specified"

    if not clean_loc:
        clean_loc = "Location not specified"

    if not resolved_inv_id:
        # Auto-create a fresh investigation for this upload
        auto_id = f"inv-{uuid4().hex[:8]}"
        auto_case_num = f"CASE-AUTO-{auto_id[-6:].upper()}"
        auto_inv = InvestigationModel(
            id=auto_id,
            case_number=auto_case_num,
            status="under_investigation",
            incident_type="Unclassified",
            severity="MEDIUM",
            confidence=0.0,
            location=clean_loc,
            created_at=now,
            updated_at=now,
            investigator="Unassigned",
            video_count=1,
            duration_analyzed="00:00:00",
            ai_insight="Investigation auto-created from video upload. Pending analysis.",
            incident_data={
                "type": "Unclassified",
                "confidence": 0.0,
                "severity": "MEDIUM",
                "classifier_version": "pending",
                "feature_contributions": [],
                "reasoning": "Analysis not yet performed.",
            },
            active_video_id=video_id,
        )
        db.add(auto_inv)
        db.commit()
        db.refresh(auto_inv)
        resolved_inv_id = auto_id
    else:
        # Update existing investigation's location and active_video_id
        existing_inv = db.query(InvestigationModel).filter(InvestigationModel.id == resolved_inv_id).first()
        if existing_inv:
            existing_inv.active_video_id = video_id
            if clean_loc != "Location not specified" and (not existing_inv.location or existing_inv.location == "Location not specified"):
                existing_inv.location = clean_loc
            db.commit()

    # Persist in VideoModel
    video_record = VideoModel(
        id=video_id,
        investigation_id=resolved_inv_id,
        filename=safe_filename,
        filepath=dest_path,
        camera_id=camera_id,
        location=clean_loc,
        status="uploaded",
        uploaded_at=now,
    )
    db.add(video_record)
    db.commit()
    db.refresh(video_record)

    return {
        "video_id": video_id,
        "filename": safe_filename,
        "filepath": dest_path,
        "size_bytes": total_bytes,
        "status": "uploaded",
        "camera_id": camera_id,
        "location": clean_loc,
        "investigation_id": resolved_inv_id,
        "metadata": meta,
    }



@router.post("/{video_id}/analyze")
async def analyze_video(
    video_id: str,
    body: dict = Body(default={}),
    db: Session = Depends(get_db),
):
    """
    Execute full multi-modal video analysis pipeline on uploaded video:
    1. Real YOLOv11 object detection and ByteTrack tracking
    2. Real EntityModel registration and trajectory persistence
    3. ActionRecognitionService spatio-temporal behavioral analysis
    4. Real EventModel registration (movement, dwell, suspicious actions)
    5. SHA-256 cryptographic video evidence registration
    6. Real XGBoost incident classification and risk scoring
    """
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    filepath = video.filepath
    inv_id = video.investigation_id
    if not inv_id:
        raise HTTPException(status_code=400, detail="Video has no associated investigation ID")
    camera_id = video.camera_id or "C-01"
    location = video.location or "Location not specified"

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Video file not found at '{filepath}'")

    result = {
        "video_id": video_id,
        "investigation_id": inv_id,
        "status": "completed",
        "entities": [],
        "events": [],
        "evidence": [],
    }

    # 1. Compute real SHA-256 hash of the video file
    import hashlib
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    video_sha256 = hasher.hexdigest()

    # 2. Run real YOLOv11 + ByteTrack tracking at 4 FPS with tracklet merging
    track_res = yolo_detector.process_video_with_tracking(filepath, sample_fps=4.0, conf_thresh=0.25)
    result["yolo_tracking"] = track_res

    # Run EasyOCR on video footage
    ocr_res = ocr_service.extract_timestamp_and_text(filepath)
    result["ocr"] = ocr_res

    # Clean up previous events and entities for this investigation to eliminate stale track fragments
    db.query(EventModel).filter(
        EventModel.investigation_id == inv_id,
        EventModel.camera_id == camera_id,
    ).delete()
    db.query(EntityModel).filter(
        EntityModel.investigation_id == inv_id,
    ).delete()
    db.commit()

    # 3. Persist tracked entities to EntityModel
    ELIGIBLE_SUBJECT_CLASSES = {
        "person": "person",
        "car": "vehicle",
        "truck": "vehicle",
        "bus": "vehicle",
        "motorcycle": "vehicle",
        "bicycle": "vehicle",
        "backpack": "baggage",
        "handbag": "baggage",
        "suitcase": "baggage",
        "cell phone": "object",
        "laptop": "object",
    }

    # Persist only genuine security subjects to EntityModel
    tracks = track_res.get("tracks", [])
    registered_entities = []
    for t in tracks:
        cls_name = str(t.get("class", "")).lower()
        if cls_name not in ELIGIBLE_SUBJECT_CLASSES:
            # Skip non-subject objects (furniture, plants, decor, etc.)
            continue

        entity_id = t["entity_id"]
        ent_type = ELIGIBLE_SUBJECT_CLASSES[cls_name]
        avg_conf = round(float(t.get("avg_confidence", 0.85)) * 100, 1)
        first_sec = float(t.get("first_seen_sec", 0.0))
        last_sec = float(t.get("last_seen_sec", 1.0))
        dur = round(last_sec - first_sec, 1)

        first_seen_str = f"{int(first_sec) // 60:02d}:{int(first_sec) % 60:02d}"
        last_seen_str = f"{int(last_sec) // 60:02d}:{int(last_sec) % 60:02d}"
        dur_str = f"{dur}s"

        if str(entity_id).lower().startswith(("person", "vehicle", "car")):
            label_str = entity_id
        else:
            label_str = f"Person {entity_id}" if ent_type == "person" else f"{cls_name.title()} {entity_id}"

        ent_key = f"{inv_id}:{entity_id}"
        ent_rec = db.query(EntityModel).filter(EntityModel.id == ent_key).first()
        if not ent_rec:
            ent_rec = EntityModel(
                id=ent_key,
                investigation_id=inv_id,
                video_id=video_id,
                type=ent_type,
                label=label_str,
                confidence=avg_conf,
                first_seen=first_seen_str,
                last_seen=last_seen_str,
                track_duration=dur_str,
                metadata_json={"trajectory": t["trajectory"], "class": cls_name, "video_id": video_id},
            )
            db.add(ent_rec)
        else:
            ent_rec.video_id = video_id
            ent_rec.type = ent_type
            ent_rec.label = label_str
            ent_rec.confidence = avg_conf
            ent_rec.first_seen = first_seen_str
            ent_rec.last_seen = last_seen_str
            ent_rec.track_duration = dur_str
            ent_rec.metadata_json = {"trajectory": t["trajectory"], "class": cls_name, "video_id": video_id}

        registered_entities.append({
            "id": entity_id,
            "type": ent_type,
            "label": label_str,
            "confidence": avg_conf,
            "first_seen": first_seen_str,
            "last_seen": last_seen_str,
            "track_duration": dur_str,
            "video_id": video_id,
        })

    # 4. Run Action Recognition on real tracks
    actions_per_track = action_service.classify_actions(
        tracks=tracks,
        video_metadata={"fps": track_res.get("fps"), "duration": track_res.get("duration_seconds")},
    )
    result["action_recognition"] = actions_per_track

    # 5. Generate and persist real EventModel records
    registered_events = []
    track_lookup = {t["entity_id"]: t for t in tracks}

    for item in actions_per_track:
        entity_id = item["entity_id"]
        cls_name = str(item.get("class", "")).lower()

        # Rule 3 & 4: Inanimate background objects never generate security events
        if cls_name not in ELIGIBLE_SUBJECT_CLASSES:
            continue

        entity_type = ELIGIBLE_SUBJECT_CLASSES[cls_name]
        parent_track = track_lookup.get(entity_id, {})
        base_conf = round(float(parent_track.get("avg_confidence", 0.85)) * 100, 1)
        first_sec = float(parent_track.get("first_seen_sec", 0.0))
        ts_entry = f"{int(first_sec) // 60:02d}:{int(first_sec) % 60:02d}"

        # Subject Entry / Presence ONLY for genuine person entities
        if cls_name == "person":
            traj = parent_track.get("trajectory", [])
            first_pt = traj[0] if traj else {"x": 50.0, "y": 50.0}
            first_x = first_pt.get("x", 50.0)
            first_y = first_pt.get("y", 50.0)

            # Differentiate: Present at recording start inside room vs Entry across boundary
            if first_sec <= 0.5 and (10.0 <= first_x <= 90.0) and (10.0 <= first_y <= 90.0):
                action_name = "Subject Present"
                desc_text = f"Subject {entity_id} detected present in monitored zone at start of recording."
            else:
                action_name = "Subject Entry"
                loc_phrase = f"in {location}" if location and location != "Location not specified" else "the monitored zone"
                desc_text = f"Person {entity_id} observed entering {loc_phrase} on camera {camera_id}."


            evt_entry_id = f"EVT-{uuid4().hex[:8].upper()}"
            existing_entry = db.query(EventModel).filter(EventModel.id == evt_entry_id).first()
            if not existing_entry:
                new_entry_evt = EventModel(
                    id=evt_entry_id,
                    investigation_id=inv_id,
                    video_id=video_id,
                    timestamp=ts_entry,
                    entity_id=entity_id,
                    entity_type="person",
                    action=action_name,
                    location=location,
                    camera_id=camera_id,
                    confidence=base_conf,
                    is_suspicious=False,
                    description=desc_text,
                )
                db.add(new_entry_evt)
            else:
                existing_entry.video_id = video_id
                existing_entry.action = action_name
                existing_entry.confidence = base_conf
                existing_entry.timestamp = ts_entry
                existing_entry.description = desc_text

            registered_events.append({
                "id": evt_entry_id,
                "timestamp": ts_entry,
                "entity_id": entity_id,
                "entity_type": "person",
                "action": action_name,
                "confidence": base_conf,
                "is_suspicious": False,
                "description": desc_text,
                "video_id": video_id,
            })

        # Vehicle Entry ONLY for vehicles
        elif entity_type == "vehicle":
            evt_ventry_id = f"EVT-{uuid4().hex[:8].upper()}"
            existing_ventry = db.query(EventModel).filter(EventModel.id == evt_ventry_id).first()
            if not existing_ventry:
                new_ventry_evt = EventModel(
                    id=evt_ventry_id,
                    investigation_id=inv_id,
                    video_id=video_id,
                    timestamp=ts_entry,
                    entity_id=entity_id,
                    entity_type="vehicle",
                    action="Vehicle Entry",
                    location=location,
                    camera_id=camera_id,
                    confidence=base_conf,
                    is_suspicious=False,
                    description=f"{cls_name.title()} {entity_id} entered monitored zone on camera {camera_id}.",
                )
                db.add(new_ventry_evt)
            else:
                existing_ventry.video_id = video_id
                existing_ventry.action = "Vehicle Entry"
                existing_ventry.confidence = base_conf
                existing_ventry.timestamp = ts_entry
                existing_ventry.description = f"{cls_name.title()} {entity_id} entered monitored zone on camera {camera_id}."

            registered_events.append({
                "id": evt_ventry_id,
                "timestamp": ts_entry,
                "entity_id": entity_id,
                "entity_type": "vehicle",
                "action": "Vehicle Entry",
                "confidence": base_conf,
                "is_suspicious": False,
                "description": f"{cls_name.title()} {entity_id} entered monitored zone on camera {camera_id}.",
                "video_id": video_id,
            })

        # Process behavioral actions (discarding "Stationary Object")
        for act in item.get("actions", []):
            raw_act_name = str(act.get("action", "")).strip()
            if not raw_act_name or raw_act_name.lower() in ["stationary object", "none"]:
                continue

            if any(kw in raw_act_name for kw in ["Altercation", "Proximity", "Theft", "Tampering", "Approached", "Interaction"]):
                act_name = raw_act_name
            else:
                act_name = raw_act_name.title()

            is_susp = act.get("severity") in ["HIGH", "CRITICAL"] or act.get("is_suspicious", False)
            conf = round(float(act.get("event_confidence", act.get("activity_confidence", act.get("confidence", 0.85)))) * 100, 1)
            start_sec = float(act.get("start_time_sec", 0.0))
            ts_act = f"{int(start_sec) // 60:02d}:{int(start_sec) % 60:02d}"
            sec_ent = act.get("secondary_entity_id")
            evt_id = f"EVT-{uuid4().hex[:8].upper()}"

            # Avoid adding duplicate action event for same entity and action
            if any(e["entity_id"] == entity_id and e["action"] == act_name for e in registered_events):
                continue

            existing_evt = db.query(EventModel).filter(EventModel.id == evt_id).first()
            if not existing_evt:
                new_evt = EventModel(
                    id=evt_id,
                    investigation_id=inv_id,
                    video_id=video_id,
                    timestamp=ts_act,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    action=act_name,
                    location=location,
                    camera_id=camera_id,
                    confidence=conf,
                    is_suspicious=is_susp,
                    description=act.get("description", f"{act_name} detected for {entity_id}"),
                    related_entity_id=sec_ent,
                )
                db.add(new_evt)
            else:
                existing_evt.video_id = video_id
                existing_evt.action = act_name
                existing_evt.confidence = conf
                existing_evt.timestamp = ts_act
                existing_evt.is_suspicious = is_susp
                existing_evt.description = act.get("description", f"{act_name} detected for {entity_id}")
                existing_evt.related_entity_id = sec_ent

            registered_events.append({
                "id": evt_id,
                "timestamp": ts_act,
                "entity_id": entity_id,
                "entity_type": entity_type,
                "action": act_name,
                "confidence": conf,
                "is_suspicious": is_susp,
                "description": act.get("description", f"{act_name} detected for {entity_id}"),
                "related_entity_id": sec_ent,
                "video_id": video_id,
            })

    # 6. Generate and persist EvidenceModel for video file with SHA-256
    # Deduplicate: one evidence record per (investigation, sha256) — never create duplicates
    # on re-analysis of the same file.
    existing_sha_evd = db.query(EvidenceModel).filter(
        EvidenceModel.investigation_id == inv_id,
        EvidenceModel.sha256 == video_sha256,
    ).first()

    first_ent = registered_entities[0]["id"] if registered_entities else None
    first_evt_id = registered_events[0]["id"] if registered_events else None

    if existing_sha_evd:
        # Update the existing evidence record with the latest entity/event IDs and video_id
        existing_sha_evd.video_id = video_id
        if first_ent:
            existing_sha_evd.primary_entity_id = first_ent
        if first_evt_id:
            existing_sha_evd.event_id = first_evt_id
        result["evidence"].append({
            "id": existing_sha_evd.id,
            "type": existing_sha_evd.type,
            "sha256": video_sha256,
            "camera_id": camera_id,
            "video_id": video_id,
        })
    elif first_ent and first_evt_id:
        evd_id = f"EVD-{uuid4().hex[:8].upper()}"
        loc_suffix = f" at {location}" if location and location != "Location not specified" else ""
        new_evd = EvidenceModel(
            id=evd_id,
            investigation_id=inv_id,
            video_id=video_id,
            timestamp="00:00",
            camera_id=camera_id,
            type="CCTV Video Recording",
            primary_entity_id=first_ent,
            confidence=99.0,
            event_id=first_evt_id,
            description=f"Forensic CCTV footage ({video.filename}) from {camera_id}{loc_suffix}.",
            is_key_evidence=True,
            sha256=video_sha256,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        db.add(new_evd)
        result["evidence"].append({
            "id": evd_id,
            "type": "CCTV Video Recording",
            "sha256": video_sha256,
            "camera_id": camera_id,
            "video_id": video_id,
        })

    # Flush newly added records to the transaction so they are queryable
    db.flush()

    # 7. Update Investigation with real XGBoost incident classification and TreeSHAP
    inv = db.query(InvestigationModel).filter(InvestigationModel.id == inv_id).first()
    if inv:
        all_events = db.query(EventModel).filter(EventModel.investigation_id == inv_id).all()
        all_entities = db.query(EntityModel).filter(EntityModel.investigation_id == inv_id).all()
        all_evidence = db.query(EvidenceModel).filter(EvidenceModel.investigation_id == inv_id).all()

        events_dicts = [
            {"action": e.action, "timestamp": e.timestamp, "is_suspicious": e.is_suspicious, "description": e.description}
            for e in all_events
        ]
        entities_dicts = [
            {"type": e.type, "track_duration": e.track_duration}
            for e in all_entities
        ]
        evidence_dicts = [
            {"type": evd.type, "confidence": evd.confidence}
            for evd in all_evidence
        ]

        incident_res = incident_classifier.classify(
            events=events_dicts,
            entities=entities_dicts,
            evidence=evidence_dicts,
        )

        # Compute TreeSHAP explainability for the exact same feature vector
        shap_res = shap_service.explain(incident_res.get("extracted_features", {}))
        incident_res["shap_explanation"] = shap_res
        incident_res["feature_contributions"] = shap_res["feature_contributions"]
        incident_res["base_value"] = shap_res["base_value"]
        incident_res["positive_contributors"] = shap_res["positive_contributors"]
        incident_res["negative_contributors"] = shap_res["negative_contributors"]
        incident_res["reasoning"] = shap_res["narrative"]

        inv.incident_data = incident_res
        inv.incident_type = incident_res.get("type", inv.incident_type)
        inv.severity = incident_res.get("severity", inv.severity)
        inv.confidence = incident_res.get("confidence", inv.confidence)
        inv.active_video_id = video_id
        inv.duration_analyzed = f"{int(round(track_res.get('duration_seconds', 0)))}s"
        result["incident"] = incident_res

    video.status = "analyzed"

    # Update video_count to reflect the number of *distinct* video sources analyzed for this investigation
    real_video_count = db.query(VideoModel.filename).filter(
        VideoModel.investigation_id == inv_id,
        VideoModel.status == "analyzed",
    ).distinct().count()
    if inv:
        inv.video_count = real_video_count


    db.commit()

    result["entities"] = registered_entities
    result["events"] = registered_events
    return result


@router.post("/{video_id}/detect")
async def run_yolo_detection(
    video_id: str,
    conf_thresh: float = 0.35,
    sample_fps: float = 1.0,
    db: Session = Depends(get_db),
):
    """
    Execute actual YOLOv11 frame-by-frame object detection on the uploaded video footage.
    """
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if not video or not os.path.exists(video.filepath):
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' file not found")

    result = yolo_detector.process_video(
        video.filepath,
        sample_fps=sample_fps,
        conf_thresh=conf_thresh,
    )
    result["video_id"] = video_id
    result["filename"] = video.filename
    return result


@router.post("/{video_id}/track")
async def run_bytetrack_tracking(
    video_id: str,
    conf_thresh: float = 0.35,
    sample_fps: float = 1.0,
    db: Session = Depends(get_db),
):
    """
    Execute YOLOv11 + ByteTrack multi-object tracking on video footage.
    Generates persistent entity IDs (Person-01, Vehicle-01), trajectory polylines,
    and registers tracked entities in the persistent investigation database.
    """
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if not video or not os.path.exists(video.filepath):
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' file not found")

    result = yolo_detector.process_video_with_tracking(
        video.filepath,
        sample_fps=sample_fps,
        conf_thresh=conf_thresh,
    )
    result["video_id"] = video_id
    result["filename"] = video.filename

    # If associated with an investigation, persist tracked entities into database
    if video.investigation_id and result.get("tracks"):
        for t in result["tracks"]:
            entity_id = t["entity_id"]
            ent_key = f"{video.investigation_id}:{entity_id}"
            existing = db.query(EntityModel).filter(
                EntityModel.id == ent_key,
                EntityModel.investigation_id == video.investigation_id
            ).first()

            duration_str = f"{round(t['last_seen_sec'] - t['first_seen_sec'], 1)}s"
            if not existing:
                new_entity = EntityModel(
                    id=ent_key,
                    investigation_id=video.investigation_id,
                    type="person" if t["class"] == "person" else ("vehicle" if t["class"] in ["car", "truck", "bus", "motorcycle"] else t["class"]),
                    label=entity_id,
                    confidence=round(t["avg_confidence"] * 100, 1),
                    first_seen=f"{t['first_seen_sec']}s",
                    last_seen=f"{t['last_seen_sec']}s",
                    track_duration=duration_str,
                    metadata_json={"trajectory": t["trajectory"]},
                )
                db.add(new_entity)
            else:
                existing.confidence = round(t["avg_confidence"] * 100, 1)
                existing.last_seen = f"{t['last_seen_sec']}s"
                existing.metadata_json = {"trajectory": t["trajectory"]}
        db.commit()

    return result


@router.post("/{video_id}/actions")
async def run_action_recognition(
    video_id: str,
    conf_thresh: float = 0.35,
    sample_fps: float = 1.0,
    db: Session = Depends(get_db),
):
    """
    Execute behavioral action recognition on video tracks.
    Classifies actions (loitering, running, unattended bag, forced entry),
    and automatically registers high-severity security events into the database.
    """
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if not video or not os.path.exists(video.filepath):
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' file not found")

    track_result = yolo_detector.process_video_with_tracking(
        video.filepath,
        sample_fps=sample_fps,
        conf_thresh=conf_thresh,
    )

    tracks = track_result.get("tracks", [])
    actions_per_track = action_service.classify_actions(
        tracks=tracks,
        video_metadata={"fps": track_result.get("fps"), "duration": track_result.get("duration_seconds")},
    )

    # Automatically generate security event records in database for suspicious actions
    created_events = []
    if video.investigation_id:
        for item in actions_per_track:
            entity_id = item["entity_id"]
            for act in item.get("actions", []):
                if act.get("severity") in ["HIGH", "CRITICAL"]:
                    event_id = f"evt-{uuid4().hex[:6]}"
                    event_record = EventModel(
                        id=event_id,
                        investigation_id=video.investigation_id,
                        timestamp=f"{act.get('start_time_sec', 0.0)}s",
                        action=act["action"].title(),
                        entity_id=entity_id,
                        entity_type="person" if "person" in entity_id.lower() else "vehicle",
                        location=video.location,
                        description=act.get("description", f"Action {act['action']} detected."),
                        camera_id=video.camera_id,
                        confidence=round(act.get("confidence", 0.85) * 100, 1),
                        is_suspicious=True,
                    )
                    db.add(event_record)
                    created_events.append(event_id)
        if created_events:
            db.commit()

    return {
        "video_id": video_id,
        "filename": video.filename,
        "investigation_id": video.investigation_id,
        "tracks_analyzed": len(tracks),
        "actions": actions_per_track,
        "created_events_count": len(created_events),
        "created_event_ids": created_events,
    }


@router.get("/{video_id}/status")
def get_video_status(video_id: str, db: Session = Depends(get_db)):
    """Return pipeline execution status for a video."""
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    status_info = analyzer.get_status(video_id)
    if video:
        status_info["filename"] = video.filename
        status_info["camera_id"] = video.camera_id
        status_info["location"] = video.location
    return status_info


@router.get("/{video_id}")
def get_video_info(video_id: str, db: Session = Depends(get_db)):
    """Return video record detail including investigation_id and status."""
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail=f"Video record for '{video_id}' not found")
    return {
        "id": video.id,
        "investigation_id": video.investigation_id,
        "filename": video.filename,
        "camera_id": video.camera_id,
        "location": video.location,
        "status": video.status,
        "uploaded_at": video.uploaded_at,
    }


@router.get("/{video_id}/stream")
def stream_video(video_id: str, db: Session = Depends(get_db)):
    """Stream the physical video file belonging to the requested video_id."""
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail=f"Video record for '{video_id}' not found")
    if not os.path.exists(video.filepath):
        raise HTTPException(status_code=404, detail=f"Physical video file not found at '{video.filepath}'")

    return FileResponse(
        video.filepath,
        media_type="video/mp4",
        filename=video.filename,
        headers={
            "Cache-Control": "no-cache, must-revalidate",
            "X-Video-ID": video_id,
            "X-Video-Investigation": str(video.investigation_id),
        },
    )


@router.get("/{video_id}/ocr")
def get_video_ocr(video_id: str, db: Session = Depends(get_db)):
    """Return EasyOCR text and timestamp extraction results for a video."""
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if not video or not os.path.exists(video.filepath):
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' file not found")

    return ocr_service.extract_timestamp_and_text(video.filepath)
