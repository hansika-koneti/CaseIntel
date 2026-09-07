"""
CaseIntel — SHAP Explainability Service
Computes exact TreeSHAP values for XGBoost physical security incident classifications,
extracting base expected values, positive/negative feature contributors, and normalized impacts.
"""

import os
import json
from typing import Dict, Any, List, Optional
import numpy as np
import shap
import xgboost as xgb

from services.incident_service import XGBoostIncidentClassifierService

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "xgboost_incident_model.json")
META_PATH = os.path.join(MODEL_DIR, "xgboost_features_meta.json")

FEATURE_LABELS = {
    "person_count": "Subject / Person Count",
    "vehicle_count": "Vehicle Count in Proximity",
    "event_count": "Chronological Events Count",
    "evidence_count": "Key Evidence Count",
    "max_dwell_time_sec": "Stationary Dwell Duration",
    "night_time_flag": "After-Hours Window Indicator",
    "loitering_flag": "Loitering / Lingering Behavior",
    "unattended_bag_flag": "Unattended Baggage Detection",
    "forced_entry_flag": "Perimeter / Forced Entry Manipulation",
    "speed_max": "Displacement Velocity / Directness",
}


class SHAPExplainabilityService:
    """Service for computing real TreeSHAP explainability on XGBoost incident predictions."""

    def __init__(self, incident_service: Optional[XGBoostIncidentClassifierService] = None):
        self.incident_service = incident_service or XGBoostIncidentClassifierService()
        self.model = self.incident_service.model
        self.feature_names = self.incident_service.feature_names or [
            "person_count",
            "vehicle_count",
            "event_count",
            "evidence_count",
            "max_dwell_time_sec",
            "night_time_flag",
            "loitering_flag",
            "unattended_bag_flag",
            "forced_entry_flag",
            "speed_max",
        ]
        self.classes = self.incident_service.classes or [
            "Suspicious Activity",
            "Unauthorized Access",
            "Perimeter Breach",
            "Normal Operation",
            "Theft / Tampering",
        ]
        self.explainer = shap.TreeExplainer(self.model)
        print("[SHAPService] Initialized TreeExplainer for XGBoost incident model.")

    def explain(
        self,
        features_dict: Dict[str, float],
        target_class_idx: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Compute real TreeSHAP values for the specified tabular feature vector.
        """
        ordered_vec = [float(features_dict.get(fname, 0.0)) for fname in self.feature_names]
        X = np.array([ordered_vec])

        # Predict class probabilities
        probas = self.model.predict_proba(X)[0]
        if target_class_idx is None:
            target_class_idx = int(np.argmax(probas))

        predicted_class = self.classes[target_class_idx]
        confidence_pct = round(float(probas[target_class_idx]) * 100, 1)

        # Compute SHAP values
        raw_shap = self.explainer.shap_values(X)
        # raw_shap shape is (1, n_features, n_classes) or list of (1, n_features)
        if isinstance(raw_shap, list):
            class_shap = raw_shap[target_class_idx][0]
        elif len(raw_shap.shape) == 3:
            class_shap = raw_shap[0, :, target_class_idx]
        else:
            class_shap = raw_shap[0]

        # Base value
        if isinstance(self.explainer.expected_value, (list, np.ndarray)):
            base_value = float(self.explainer.expected_value[target_class_idx])
        else:
            base_value = float(self.explainer.expected_value)

        total_abs_shap = float(np.sum(np.abs(class_shap))) or 1.0

        all_contributions = []
        positive_contributors = []
        negative_contributors = []

        for i, fname in enumerate(self.feature_names):
            phi = float(class_shap[i])
            val = float(ordered_vec[i])
            label = FEATURE_LABELS.get(fname, fname.replace("_", " ").title())

            # Format human readable value string
            if "sec" in fname:
                val_str = f"{val:.1f}s"
            elif "flag" in fname:
                val_str = "Confirmed" if val > 0.5 else "None"
            elif "speed" in fname:
                val_str = f"{val:.1f}%/s"
            else:
                val_str = str(int(val))

            impact_pct = round((abs(phi) / total_abs_shap) * 100, 1)
            is_positive = phi >= 0

            item = {
                "feature_name": fname,
                "feature": label,
                "raw_value": val,
                "value": val_str,
                "shap_value": round(phi, 4),
                "contribution": impact_pct,
                "impact_direction": "positive" if is_positive else "negative",
            }
            all_contributions.append(item)

            if is_positive:
                positive_contributors.append(item)
            else:
                negative_contributors.append(item)

        # Sort all contributions by absolute impact descending
        all_contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        positive_contributors.sort(key=lambda x: x["shap_value"], reverse=True)
        negative_contributors.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

        top_pos = [f"{c['feature']} ({c['value']})" for c in positive_contributors[:2]]
        pos_summary = f"driven predominantly by {', '.join(top_pos)}" if top_pos else "with baseline indicators"

        narrative = (
            f"TreeSHAP analysis confirms the '{predicted_class}' classification (base value {base_value:.2f}, "
            f"confidence {confidence_pct}%) is {pos_summary}."
        )

        return {
            "predicted_class": predicted_class,
            "confidence": confidence_pct,
            "base_value": round(base_value, 4),
            "feature_contributions": all_contributions,
            "positive_contributors": positive_contributors,
            "negative_contributors": negative_contributors,
            "feature_names": self.feature_names,
            "shap_values_vector": [round(float(s), 4) for s in class_shap],
            "narrative": narrative,
        }
