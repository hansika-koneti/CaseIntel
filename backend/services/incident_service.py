"""
CaseIntel — XGBoost Incident Classification Service
Loads trained XGBoost model artifact, transforms investigation features into
feature vectors, and predicts incident categories, severities, and feature contributions.
"""

import os
import json
import numpy as np
import xgboost as xgb
from typing import Dict, Any, List, Optional
from services.base import IncidentClassifierService

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "xgboost_incident_model.json")
META_PATH = os.path.join(MODEL_DIR, "xgboost_features_meta.json")


FEATURE_LABELS = {
    "person_count": "Subject / Person Count",
    "vehicle_count": "Vehicle Count in Proximity",
    "event_count": "Chronological Events Count",
    "evidence_count": "Key Evidence Count",
    "max_dwell_time_sec": "Stationary Dwell Duration",
    "night_time_flag": "After-Hours Activity Flag",
    "loitering_flag": "Loitering / Lingering Behavior",
    "unattended_bag_flag": "Unattended Baggage Detection",
    "forced_entry_flag": "Perimeter / Forced Entry Manipulation",
    "speed_max": "Displacement Velocity / Directness",
}


class XGBoostIncidentClassifierService(IncidentClassifierService):
    """Production XGBoost incident classification service."""

    def __init__(self, model_path: str = MODEL_PATH, meta_path: str = META_PATH):
        self.model_path = model_path
        self.meta_path = meta_path
        self.model = None
        self.feature_names = []
        self.classes = []
        self._load_or_train()

    def _load_or_train(self):
        """Load trained model or auto-train if artifact is missing."""
        if not os.path.exists(self.model_path):
            print("[XGBoostService] Model artifact not found. Bootstrapping training...")
            from models.train_xgboost import train_and_save_model
            self.model, meta = train_and_save_model()
            self.feature_names = meta["feature_names"]
            self.classes = meta["classes"]
            return

        try:
            self.model = xgb.XGBClassifier()
            self.model.load_model(self.model_path)
            if os.path.exists(self.meta_path):
                with open(self.meta_path, "r") as f:
                    meta = json.load(f)
                    self.feature_names = meta.get("feature_names", [])
                    self.classes = meta.get("classes", [])
            else:
                self.classes = [
                    "Suspicious Activity",
                    "Unauthorized Access",
                    "Perimeter Breach",
                    "Normal Operation",
                    "Theft / Tampering",
                ]
            print(f"[XGBoostService] Successfully loaded XGBoost model from '{self.model_path}'")
        except Exception as e:
            print(f"[XGBoostService] Error loading model ({e}). Re-training...")
            from models.train_xgboost import train_and_save_model
            self.model, meta = train_and_save_model()
            self.feature_names = meta["feature_names"]
            self.classes = meta["classes"]

    def extract_features_from_investigation(
        self,
        entities: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, float]:
        """Extract the 10-dimensional tabular feature vector from real case components."""
        # 1. Real entity counts (persons and vehicles only)
        persons = sum(1 for e in entities if str(e.get("type", "")).lower() == "person")
        vehicles = sum(1 for e in entities if str(e.get("type", "")).lower() in ["vehicle", "car", "truck", "bus", "motorcycle"])
        
        # Fallback to events if entities table had no rows
        if persons == 0 and vehicles == 0 and events:
            person_eids = {e.get("entity_id") or e.get("primary_entity_id") for e in events if str(e.get("entity_type", "")).lower() == "person"}
            vehicle_eids = {e.get("entity_id") or e.get("primary_entity_id") for e in events if str(e.get("entity_type", "")).lower() in ["vehicle", "car", "truck", "bus", "motorcycle"]}
            persons = len([eid for eid in person_eids if eid])
            vehicles = len([eid for eid in vehicle_eids if eid])

        event_count = len(events)
        evidence_count = len(evidence) if evidence else 0

        # 2. Dwell time: computed ONLY over mobile subjects (persons and vehicles)
        dwell_times = []
        for e in entities:
            ent_type = str(e.get("type", "")).lower()
            if ent_type in ["person", "vehicle", "car", "truck", "bus"]:
                dur_str = str(e.get("track_duration", "0"))
                try:
                    val = float(dur_str.replace("s", "").strip())
                    dwell_times.append(val)
                except ValueError:
                    pass
        
        # Fallback: check loitering/dwell event descriptions if entity track_duration is missing
        if not dwell_times and events:
            import re
            for evt in events:
                desc = str(evt.get("description", ""))
                m = re.search(r'(\d+\.?\d*)\s*s', desc)
                if m and ("dwell" in desc.lower() or "loiter" in desc.lower()):
                    dwell_times.append(float(m.group(1)))

        max_dwell = max(dwell_times) if dwell_times else 0.0

        # 3. Night-time flag: 1.0 only if absolute timestamp (HH:MM:SS) indicates after hours (20:00 - 06:00)
        night_flag = 0.0
        for evt in events:
            ts = str(evt.get("timestamp", ""))
            parts = ts.split(":")
            # Only 3-part timestamps (HH:MM:SS) represent absolute time of day
            if len(parts) == 3:
                try:
                    hour = int(parts[0])
                    if hour >= 20 or hour < 6:
                        night_flag = 1.0
                        break
                except ValueError:
                    pass

        # 4. Action flags from real events
        loiter_flag = 0.0
        bag_flag = 0.0
        forced_flag = 0.0
        running_flag = 0.0

        for evt in events:
            action_text = (
                str(evt.get("event_type", "")) + " " +
                str(evt.get("description", "")) + " " +
                str(evt.get("action", ""))
            ).lower()
            if any(w in action_text for w in ["loiter", "dwell", "linger"]):
                loiter_flag = 1.0
            if any(w in action_text for w in ["bag", "backpack", "suitcase", "unattended"]):
                bag_flag = 1.0
            # Strict forced entry & intrusion matching — DO NOT match normal departure 'boundary' phrases
            if any(w in action_text for w in ["forced entry", "break in", "tamper", "forced manipulation", "perimeter breach", "altercation", "confrontation", "intrusion", "unauthorized access"]):
                forced_flag = 1.0
            if any(w in action_text for w in ["running", "sprint", "speeding", "rapid"]):
                running_flag = 1.0

        # 5. Speed max derived from behavior evidence
        if forced_flag:
            speed_max = 14.2
        elif running_flag:
            speed_max = 18.5
        elif loiter_flag:
            speed_max = 2.5
        elif persons > 0 or vehicles > 0:
            speed_max = 3.5
        else:
            speed_max = 0.0

        return {
            "person_count": float(persons),
            "vehicle_count": float(vehicles),
            "event_count": float(event_count),
            "evidence_count": float(evidence_count),
            "max_dwell_time_sec": float(round(max_dwell, 1)),
            "night_time_flag": float(night_flag),
            "loitering_flag": float(loiter_flag),
            "unattended_bag_flag": float(bag_flag),
            "forced_entry_flag": float(forced_flag),
            "speed_max": float(round(speed_max, 1)),
        }


    def classify(
        self,
        events: List[Dict[str, Any]],
        entities: List[Dict[str, Any]],
        evidence: Optional[List[Dict[str, Any]]] = None,
        custom_features: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Classify security incident using the trained XGBoost model."""
        features_dict = custom_features or self.extract_features_from_investigation(
            entities=entities,
            events=events,
            evidence=evidence,
        )

        ordered_vec = [float(features_dict.get(fname, 0.0)) for fname in self.feature_names]

        X = np.array([ordered_vec])
        probas = self.model.predict_proba(X)[0]
        pred_idx = int(np.argmax(probas))
        primary_category = self.classes[pred_idx] if pred_idx < len(self.classes) else "Normal Operation"
        confidence_pct = round(float(probas[pred_idx]) * 100, 1)

        # Probabilities breakdown across all types
        probabilities_map = {}
        for idx, cls_name in enumerate(self.classes):
            probabilities_map[cls_name] = round(float(probas[idx]) * 100, 1)

        # Determine severity and risk score
        risk_score = round(confidence_pct * (0.95 if primary_category != "Normal Operation" else 0.05), 1)
        if primary_category in ["Perimeter Breach", "Theft / Tampering"]:
            severity = "CRITICAL"
        elif primary_category in ["Suspicious Activity", "Unauthorized Access"]:
            severity = "HIGH" if risk_score > 60 else "MEDIUM"
        else:
            severity = "LOW"

        # Compute dynamic feature contributions from XGBoost feature importances
        raw_importances = self.model.feature_importances_
        weights = [float(raw_importances[i]) * max(0.1, float(ordered_vec[i])) for i in range(len(raw_importances))]
        total_weight = float(sum(weights)) or 1.0
        normalized_contribs = [float((w / total_weight) * 100) for w in weights]

        feature_contributions = []
        for idx, fname in enumerate(self.feature_names):
            val = ordered_vec[idx]
            label = FEATURE_LABELS.get(fname, fname.replace("_", " ").title())
            if "sec" in fname:
                val_str = f"{val:.1f}s dwell"
            elif "flag" in fname:
                val_str = "Confirmed" if val > 0.5 else "None detected"
            elif "speed" in fname:
                val_str = f"{val:.1f}%/s velocity"
            else:
                val_str = f"{int(val)} observed"

            feature_contributions.append({
                "feature": label,
                "contribution": round(normalized_contribs[idx], 1),
                "value": val_str,
            })

        feature_contributions.sort(key=lambda x: x["contribution"], reverse=True)

        # Dynamic reasoning based on actual prediction and non-zero features
        if primary_category == "Normal Operation":
            reasoning = (
                f"The XGBoost model classified this activity as 'Normal Operation' with {confidence_pct}% confidence. "
                f"Observed subjects ({int(ordered_vec[0])} persons, {int(ordered_vec[1])} vehicles) exhibit baseline behavior "
                f"without loitering, forced boundary tampering, or suspicious after-hours presence."
            )
        else:
            top_active = [c["feature"] for c in feature_contributions if c["contribution"] > 10.0]
            reasoning = (
                f"The XGBoost model classified this incident as '{primary_category}' with {confidence_pct}% confidence. "
                f"Key contributing factors include {', '.join(top_active[:3]) if top_active else 'observed anomalous behavioral indicators'}."
            )

        return {
            "type": str(primary_category),
            "severity": str(severity),
            "confidence": float(confidence_pct),
            "incident_risk_score": float(risk_score),
            "classifier_version": "xgboost-1.8-caseintel",
            "feature_contributions": feature_contributions,
            "class_probabilities": {str(k): float(v) for k, v in probabilities_map.items()},
            "extracted_features": {str(k): float(v) for k, v in features_dict.items()},
            "reasoning": str(reasoning),
        }

