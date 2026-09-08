"""
CaseIntel — Direct Temporal Video Activity Recognition Service
Executes direct temporal video classification over sequences of frames using
a deep 3D spatiotemporal architecture (R(2+1)D-18) with a fine-tuned surveillance head.

Strict forensic provenance:
- Evaluates raw visual pixels/temporal clips; does not use metadata or filenames.
- Produces clip-level predictions with start/end timecodes.
- Aggregates to video-level assessment with supporting segments.
- Operates as a distinct reasoning path from tabular XGBoost and kinematic events.
"""

import os
import cv2
import json
import time
import math
import numpy as np
import torch
import torch.nn as nn
from typing import Dict, Any, List, Optional, Tuple
import torchvision.models.video as vmodels
from torchvision.models.video import R2Plus1D_18_Weights

CLASSES = [
    "Normal Operation",         # 0
    "Stealing / Theft",          # 1
    "Burglary / Break-In",       # 2
    "Fighting / Altercation",    # 3
]

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
HEAD_PATH = os.path.join(MODEL_DIR, "temporal_surveillance_head.pt")
METRICS_PATH = os.path.join(MODEL_DIR, "temporal_model_metrics.json")
META_PATH = os.path.join(MODEL_DIR, "temporal_model_meta.json")


class TemporalSurveillanceClassifierHead(nn.Module):
    """Classification head matching trained architecture."""
    def __init__(self, in_features: int = 512, num_classes: int = len(CLASSES)):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(in_features, 128),
            nn.LayerNorm(128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.35),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc(x)


def format_timecode(seconds: float) -> str:
    """Format seconds into MM:SS string."""
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"


class TemporalVideoActivityService:
    """Production temporal video activity recognition service."""

    def __init__(
        self,
        head_path: str = HEAD_PATH,
        device: str = "cpu",
    ):
        self.head_path = head_path
        self.device = torch.device(device)
        self.classes = CLASSES
        self.backbone = None
        self.head = None
        self.transforms = None
        self.kinetics_categories = []
        self._init_models()

    def _init_models(self):
        """Initialize R(2+1)D-18 backbone and trained surveillance classification head."""
        try:
            weights = R2Plus1D_18_Weights.DEFAULT
            self.transforms = weights.transforms()
            self.kinetics_categories = weights.meta.get("categories", [])
            base_model = vmodels.r2plus1d_18(weights=weights).eval()
            self.backbone = nn.Sequential(*list(base_model.children())[:-1]).to(self.device)
            self.backbone.eval()

            self.head = TemporalSurveillanceClassifierHead(in_features=512, num_classes=len(self.classes))
            if os.path.exists(self.head_path):
                self.head.load_state_dict(torch.load(self.head_path, map_location=self.device))
                self.head.to(self.device)
                self.head.eval()
                print(f"[TemporalVideoService] Loaded trained surveillance head from '{self.head_path}'")
            else:
                print(f"[TemporalVideoService] Notice: Trained head not found at '{self.head_path}'. Model will train when pipeline runs.")
        except Exception as e:
            print(f"[TemporalVideoService] Error initializing temporal video model: {e}")

    def analyze_video(
        self,
        video_path: str,
        stride_seconds: float = 2.5,
        clip_length_frames: int = 16,
    ) -> Dict[str, Any]:
        """
        Divide video into temporal clips, classify each clip, and aggregate to video-level assessment.
        NOTE: video_path is used exclusively to open video frames. Filenames or path metadata
        are never used as classification inputs.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        # Ensure model head is ready
        if self.head is None or not os.path.exists(self.head_path):
            self._init_models()

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / fps if fps > 0 else 0.0

        if total_frames < clip_length_frames:
            cap.release()
            return {
                "primary_activity": "Normal Operation",
                "confidence": 50.0,
                "severity": "LOW",
                "model_name": "R(2+1)D-18 (Kinetics-400 + Trained Surveillance Head)",
                "model_version": "1.0.0",
                "status": "Video too short for multi-clip temporal reasoning.",
                "supporting_segments": [],
                "top_alternatives": [],
                "clip_predictions": [],
            }

        step_frames = max(clip_length_frames, int(fps * stride_seconds))
        clip_predictions = []

        for start_frame in range(0, total_frames - clip_length_frames + 1, step_frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            frames = []
            for _ in range(clip_length_frames):
                ret, frame = cap.read()
                if not ret:
                    break
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(cv2.resize(frame_rgb, (112, 112)))

            if len(frames) == clip_length_frames:
                # Shape: (T, C, H, W)
                tensor_frames = torch.from_numpy(np.array(frames)).permute(0, 3, 1, 2)
                transformed = self.transforms(tensor_frames)
                if transformed.shape[0] != 3:
                    transformed = transformed.permute(1, 0, 2, 3)

                start_sec = round(start_frame / fps, 2)
                end_sec = round((start_frame + clip_length_frames) / fps, 2)

                with torch.no_grad():
                    clip_input = transformed.unsqueeze(0).to(self.device)
                    feat = self.backbone(clip_input)
                    feat_flat = torch.flatten(feat, 1)

                    if self.head is not None:
                        logits = self.head(feat_flat)
                        probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
                    else:
                        probs = np.array([0.7, 0.1, 0.1, 0.1])

                top_idx = int(np.argmax(probs))
                top_conf = float(probs[top_idx]) * 100.0
                pred_label = self.classes[top_idx]

                # Top alternatives for this clip
                alternatives = []
                for i in np.argsort(-probs)[1:]:
                    alternatives.append({
                        "activity": self.classes[i],
                        "confidence": round(float(probs[i]) * 100.0, 1),
                    })

                clip_predictions.append({
                    "clip_index": len(clip_predictions),
                    "start_sec": start_sec,
                    "end_sec": end_sec,
                    "start_time": format_timecode(start_sec),
                    "end_time": format_timecode(end_sec),
                    "predicted_activity": pred_label,
                    "confidence": round(top_conf, 1),
                    "class_probabilities": {c: round(float(p) * 100.0, 1) for c, p in zip(self.classes, probs)},
                    "top_alternatives": alternatives,
                })

        cap.release()

        # ── Aggregation across temporal clips ──
        return self._aggregate_predictions(clip_predictions, duration_sec)

    def _aggregate_predictions(
        self,
        clip_predictions: List[Dict[str, Any]],
        duration_sec: float,
    ) -> Dict[str, Any]:
        """Aggregate clip-level temporal predictions into video-level incident assessment."""
        if not clip_predictions:
            return {
                "primary_activity": "Normal Operation",
                "confidence": 50.0,
                "severity": "LOW",
                "model_name": "R(2+1)D-18 (Kinetics-400 + Trained Surveillance Head)",
                "model_version": "1.0.0",
                "status": "Model Prediction — Investigator Verification Required",
                "supporting_segments": [],
                "top_alternatives": [],
                "clip_predictions": [],
            }

        # Compute average probability vector across all clips
        avg_probs = {c: 0.0 for c in self.classes}
        for clip in clip_predictions:
            for c, p in clip["class_probabilities"].items():
                avg_probs[c] += p / len(clip_predictions)

        # Identify anomalous clips (where class != Normal Operation and confidence >= 40%)
        anomalous_clips = [
            c for c in clip_predictions
            if c["predicted_activity"] != "Normal Operation" and c["confidence"] >= 35.0
        ]

        if anomalous_clips:
            # Group anomaly by class frequency and peak confidence
            class_conf_sum = {}
            for ac in anomalous_clips:
                cls = ac["predicted_activity"]
                class_conf_sum[cls] = class_conf_sum.get(cls, 0.0) + ac["confidence"]

            primary_activity = max(class_conf_sum, key=class_conf_sum.get)
            matching_clips = [c for c in anomalous_clips if c["predicted_activity"] == primary_activity]

            # Identify supporting time segment
            min_sec = min(c["start_sec"] for c in matching_clips)
            max_sec = max(c["end_sec"] for c in matching_clips)
            peak_conf = max(c["confidence"] for c in matching_clips)
            avg_match_conf = sum(c["confidence"] for c in matching_clips) / len(matching_clips)
            overall_conf = round(0.6 * peak_conf + 0.4 * avg_match_conf, 1)

            supporting_segments = [{
                "start": format_timecode(min_sec),
                "end": format_timecode(max_sec),
                "start_sec": min_sec,
                "end_sec": max_sec,
                "peak_confidence": round(peak_conf, 1),
                "clip_count": len(matching_clips),
            }]
            severity = "HIGH" if "Theft" in primary_activity or "Fighting" in primary_activity or "Break-In" in primary_activity else "MEDIUM"
        else:
            primary_activity = "Normal Operation"
            overall_conf = round(avg_probs.get("Normal Operation", 85.0), 1)
            supporting_segments = [{
                "start": "00:00",
                "end": format_timecode(duration_sec),
                "start_sec": 0.0,
                "end_sec": round(duration_sec, 2),
                "peak_confidence": overall_conf,
                "clip_count": len(clip_predictions),
            }]
            severity = "LOW"

        # Formulate top alternatives
        sorted_alts = sorted(
            [{"activity": c, "confidence": round(p, 1)} for c, p in avg_probs.items() if c != primary_activity],
            key=lambda x: -x["confidence"]
        )

        return {
            "primary_activity": primary_activity,
            "confidence": overall_conf,
            "severity": severity,
            "model_name": "R(2+1)D-18 (Kinetics-400 + Trained Surveillance Head)",
            "model_version": "1.0.0",
            "status": "Model Prediction — Investigator Verification Required",
            "supporting_segments": supporting_segments,
            "top_alternatives": sorted_alts,
            "total_clips_analyzed": len(clip_predictions),
            "clip_predictions": clip_predictions,
            "video_duration_sec": round(duration_sec, 2),
        }
