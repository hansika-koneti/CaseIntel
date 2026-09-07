"""
CaseIntel — Mock Action Recognition Service
Provides deterministic action classifications for testing and offline development.
"""

from typing import Dict, Any, List
from services.base import ActionRecognitionBaseService


class MockActionRecognitionService(ActionRecognitionBaseService):
    """Deterministic mock action recognizer."""

    def classify_actions(
        self,
        tracks: List[Dict[str, Any]],
        video_metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        results = []
        for trk in tracks:
            entity_id = trk.get("entity_id", "Entity-01")
            cls = trk.get("class", "person")
            dur = trk.get("last_seen_sec", 10.0) - trk.get("first_seen_sec", 0.0)
            actions = []

            if cls == "person":
                if dur > 3.0:
                    actions.append({
                        "action": "loitering",
                        "confidence": 0.88,
                        "start_time_sec": trk.get("first_seen_sec", 0.0),
                        "end_time_sec": trk.get("last_seen_sec", dur),
                        "severity": "HIGH",
                        "description": f"Subject remained in monitoring perimeter for {round(dur, 1)}s.",
                    })
                else:
                    actions.append({
                        "action": "walking",
                        "confidence": 0.92,
                        "start_time_sec": trk.get("first_seen_sec", 0.0),
                        "end_time_sec": trk.get("last_seen_sec", dur),
                        "severity": "LOW",
                        "description": "Normal pedestrian traversal observed.",
                    })
            elif cls in ["backpack", "handbag", "suitcase"]:
                actions.append({
                    "action": "unattended bag",
                    "confidence": 0.94,
                    "start_time_sec": trk.get("first_seen_sec", 0.0),
                    "end_time_sec": trk.get("last_seen_sec", dur),
                    "severity": "CRITICAL",
                    "description": "Baggage item left stationary without nearby owner.",
                })
            else:
                actions.append({
                    "action": "stationary",
                    "confidence": 0.95,
                    "start_time_sec": trk.get("first_seen_sec", 0.0),
                    "end_time_sec": trk.get("last_seen_sec", dur),
                    "severity": "LOW",
                    "description": "Stationary object observed.",
                })

            results.append({
                "track_id": trk.get("track_id"),
                "entity_id": entity_id,
                "class": cls,
                "actions": actions,
            })
        return results
