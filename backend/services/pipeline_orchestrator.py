"""
CaseIntel — Analysis Pipeline Orchestrator

Extracted from api/videos.py to separate orchestration logic from HTTP routing.
Coordinates the full multi-modal video analysis pipeline:
  1. SHA-256 cryptographic hash
  2. YOLOv11 + ByteTrack object detection & tracking
  3. EasyOCR timestamp extraction
  4. Entity registration (EntityModel)
  5. Action recognition (spatio-temporal behavioral analysis)
  6. Temporal video activity recognition (R(2+1)D-18)
  7. Event generation (EventModel)
  8. Evidence registration (EvidenceModel)
  9. XGBoost incident classification
  10. TreeSHAP explainability
"""

import os
import time
import hashlib
from uuid import uuid4
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from models.db import VideoModel, EntityModel, EventModel, EvidenceModel, InvestigationModel


# ── Eligible Subject Classes ─────────────────────────────────────────────
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


def format_timestamp(sec: float, force_hours: bool = False) -> str:
    """Format seconds into MM:SS or HH:MM:SS for long footage."""
    s = max(0, int(round(sec)))
    h = s // 3600
    m = (s % 3600) // 60
    sec_rem = s % 60
    if h > 0 or force_hours:
        return f"{h:02d}:{m:02d}:{sec_rem:02d}"
    return f"{m:02d}:{sec_rem:02d}"


def parse_timestamp_to_sec(ts: str) -> float:
    """Parse MM:SS or HH:MM:SS timestamp string to total seconds."""
    if not ts:
        return 0.0
    parts = ts.split(":")
    try:
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
    except Exception:
        pass
    return 0.0


class PipelineOrchestrator:
    """
    Orchestrates the full analysis pipeline with lazy-loaded services.
    Services are only instantiated on first use, not at module import time.
    """

    def __init__(self):
        self._yolo = None
        self._action = None
        self._incident = None
        self._shap = None
        self._ocr = None
        self._temporal = None

    @property
    def yolo_detector(self):
        if self._yolo is None:
            from services.yolo_service import YOLOv11DetectorService
            self._yolo = YOLOv11DetectorService()
        return self._yolo

    @property
    def action_service(self):
        if self._action is None:
            from services.action_recognition_service import ActionRecognitionService
            self._action = ActionRecognitionService()
        return self._action

    @property
    def incident_classifier(self):
        if self._incident is None:
            from services.incident_service import XGBoostIncidentClassifierService
            self._incident = XGBoostIncidentClassifierService()
        return self._incident

    @property
    def shap_service(self):
        if self._shap is None:
            from services.shap_service import SHAPExplainabilityService
            self._shap = SHAPExplainabilityService(self.incident_classifier)
        return self._shap

    @property
    def ocr_service(self):
        if self._ocr is None:
            from services.ocr_service import EasyOCRService
            self._ocr = EasyOCRService()
        return self._ocr

    @property
    def temporal_service(self):
        if self._temporal is None:
            from services.temporal_video_service import TemporalVideoActivityService
            self._temporal = TemporalVideoActivityService()
        return self._temporal

    def compute_file_hash(self, filepath: str) -> str:
        """Compute SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def run_detection_and_tracking(
        self,
        filepath: str,
        sample_fps: float = 4.0,
        conf_thresh: float = 0.25,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """Stage 1: YOLOv11 + ByteTrack detection and tracking."""
        return self.yolo_detector.process_video_with_tracking(
            filepath,
            sample_fps=sample_fps,
            conf_thresh=conf_thresh,
            progress_callback=progress_callback,
        )

    def run_ocr(self, filepath: str) -> Dict[str, Any]:
        """Stage 2: EasyOCR timestamp and text extraction."""
        return self.ocr_service.extract_timestamp_and_text(filepath)

    def register_entities(
        self,
        db: Session,
        tracks: List[Dict],
        inv_id: str,
        video_id: str,
        camera_id: str,
    ) -> List[Dict[str, Any]]:
        """Stage 3: Persist tracked entities to EntityModel."""
        registered = []
        for t in tracks:
            cls_name = str(t.get("class", "")).lower()
            if cls_name not in ELIGIBLE_SUBJECT_CLASSES:
                continue

            entity_id = t["entity_id"]
            ent_type = ELIGIBLE_SUBJECT_CLASSES[cls_name]
            avg_conf = round(float(t.get("avg_confidence", 0.85)) * 100, 1)
            first_sec = float(t.get("first_seen_sec", 0.0))
            last_sec = float(t.get("last_seen_sec", 1.0))
            dur = round(last_sec - first_sec, 1)

            first_seen_str = format_timestamp(first_sec)
            last_seen_str = format_timestamp(last_sec)
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

            registered.append({
                "id": entity_id,
                "type": ent_type,
                "label": label_str,
                "confidence": avg_conf,
                "first_seen": first_seen_str,
                "last_seen": last_seen_str,
                "track_duration": dur_str,
                "video_id": video_id,
            })

        return registered

    def run_action_recognition(
        self,
        tracks: List[Dict],
        video_metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Stage 4: Behavioral action classification."""
        return self.action_service.classify_actions(
            tracks=tracks,
            video_metadata=video_metadata,
        )

    def run_temporal_activity(self, filepath: str) -> Dict[str, Any]:
        """Stage 5: Direct temporal video activity recognition (R(2+1)D-18)."""
        try:
            return self.temporal_service.analyze_video(filepath)
        except Exception as te:
            print(f"[Pipeline] Temporal video recognition notice ({te})")
            return {
                "primary_activity": "Normal Operation",
                "confidence": 50.0,
                "severity": "LOW",
                "model_name": "R(2+1)D-18",
                "status": f"Execution notice: {te}",
                "supporting_segments": [],
                "top_alternatives": [],
            }

    def run_incident_classification(
        self,
        events: List[Dict],
        entities: List[Dict],
        evidence: List[Dict],
    ) -> Dict[str, Any]:
        """Stage 6: XGBoost incident classification."""
        return self.incident_classifier.classify(
            events=events,
            entities=entities,
            evidence=evidence,
        )

    def run_shap_explanation(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Stage 7: TreeSHAP explainability."""
        return self.shap_service.explain(features)


# Singleton instance — services are lazy-loaded on first use
pipeline = PipelineOrchestrator()
