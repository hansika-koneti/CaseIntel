"""
CaseIntel — Temporal Video Activity Recognition Training Pipeline
Trains a surveillance activity classification head over pretrained R(2+1)D-18
spatiotemporal features using labeled surveillance video clips from UCF-Crime.

Strict integrity enforcement:
- Stealing002_x264.mp4 is strictly held out from training and validation.
- Burglary003_x264.mp4 is strictly held out from training and validation.
- No filename, directory, or ground-truth metadata is accessible during inference.
"""

import os
import sys
import json
import time
import hashlib
import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_recall_fscore_support
import torchvision.models.video as vmodels
from torchvision.models.video import R2Plus1D_18_Weights

CLASSES = [
    "Normal Operation",         # 0
    "Stealing / Theft",          # 1
    "Burglary / Break-In",       # 2
    "Fighting / Altercation",    # 3
]

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
HEAD_SAVE_PATH = os.path.join(MODEL_DIR, "temporal_surveillance_head.pt")
METRICS_SAVE_PATH = os.path.join(MODEL_DIR, "temporal_model_metrics.json")
META_SAVE_PATH = os.path.join(MODEL_DIR, "temporal_model_meta.json")

TRAIN_VIDEOS = [
    # Category, RelPath, Label_Idx
    ("Stealing", os.path.join("backend", "data", "ucf_crime_train", "Stealing007_x264.mp4"), 1),
    ("Stealing", os.path.join("backend", "data", "ucf_crime_train", "Stealing008_x264.mp4"), 1),
    ("Burglary", os.path.join("backend", "data", "ucf_crime_train", "Burglary002_x264.mp4"), 2),
    ("Fighting", os.path.join("backend", "data", "ucf_crime_train", "Fighting005_x264.mp4"), 3),
    ("Fighting", os.path.join("backend", "data", "ucf_crime_train", "Fighting006_x264.mp4"), 3),
    ("Normal", os.path.join("backend", "test_footage", "3878245337-preview.mp4"), 0),
]

HELD_OUT_EVAL_VIDEOS = [
    ("Stealing", os.path.join("backend", "test_footage", "ucf_crime_stealing002.mp4"), 1),
    ("Burglary", os.path.join("backend", "data", "ucf_crime_train", "Burglary003_x264.mp4"), 2),
]


class TemporalSurveillanceClassifierHead(nn.Module):
    """Classification head attached to R(2+1)D-18 spatiotemporal feature embedding."""
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


CACHE_PATH = os.path.join("backend", "data", "ucf_crime_train", "extracted_features.npz")


def extract_clips_and_features():
    """Extract 16-frame clips and compute 512-dim R(2+1)D embeddings with local caching."""
    if os.path.exists(CACHE_PATH):
        print(f"[1/4] Loading cached extracted clip features from '{CACHE_PATH}'...")
        data = np.load(CACHE_PATH, allow_pickle=True)
        return data["X"], data["y"], data["manifest"].tolist()

    print("[1/4] Initializing R(2+1)D-18 pretrained backbone (Kinetics-400)...")
    weights = R2Plus1D_18_Weights.DEFAULT
    transforms = weights.transforms()
    base_model = vmodels.r2plus1d_18(weights=weights).eval()

    # Extract backbone features prior to final fc layer
    backbone = nn.Sequential(*list(base_model.children())[:-1])
    backbone.eval()

    X_features = []
    y_labels = []
    clip_manifest = []

    print("[2/4] Extracting temporal video clips from authentic surveillance footage...")
    for cat_name, video_path, label_idx in TRAIN_VIDEOS:
        if not os.path.exists(video_path):
            print(f"  [WARNING] Video {video_path} not found. Skipping.")
            continue

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / fps if fps > 0 else 0
        cap.release()

        print(f"  Processing {os.path.basename(video_path)} ({cat_name}, {duration_sec:.1f}s, {total_frames} frames)...")
        
        cap = cv2.VideoCapture(video_path)
        # For normal video, sample densely; for anomaly, sample every 2.0s
        step_frames = int(fps * 0.8) if label_idx == 0 else max(16, int(fps * 2.0))
        extracted_from_vid = 0

        for start_frame in range(0, total_frames - 16, step_frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            frames = []
            for _ in range(16):
                ret, frame = cap.read()
                if not ret:
                    break
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(cv2.resize(frame_rgb, (112, 112)))

            if len(frames) == 16:
                tensor_frames = torch.from_numpy(np.array(frames)).permute(0, 3, 1, 2)
                transformed = transforms(tensor_frames)
                if transformed.shape[0] != 3:
                    transformed = transformed.permute(1, 0, 2, 3)

                with torch.no_grad():
                    feat = backbone(transformed.unsqueeze(0))
                    feat = torch.flatten(feat, 1).squeeze(0).cpu().numpy()

                X_features.append(feat)
                y_labels.append(label_idx)
                clip_manifest.append({
                    "video": os.path.basename(video_path),
                    "category": cat_name,
                    "start_sec": round(start_frame / fps, 2),
                    "end_sec": round((start_frame + 16) / fps, 2),
                    "label": label_idx,
                })
                extracted_from_vid += 1

        cap.release()
        print(f"    Extracted {extracted_from_vid} temporal clips.")

    # Also extract initial baseline normal clips from the start of anomaly videos before action
    for cat_name, video_path, _ in TRAIN_VIDEOS:
        if cat_name == "Normal" or not os.path.exists(video_path):
            continue
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        # First 2-3 seconds are baseline empty / routine surveillance
        for start_frame in [0, int(fps * 0.8), int(fps * 1.6)]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            frames = []
            for _ in range(16):
                ret, frame = cap.read()
                if not ret:
                    break
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(cv2.resize(frame_rgb, (112, 112)))
            if len(frames) == 16:
                tensor_frames = torch.from_numpy(np.array(frames)).permute(0, 3, 1, 2)
                transformed = transforms(tensor_frames)
                if transformed.shape[0] != 3:
                    transformed = transformed.permute(1, 0, 2, 3)
                with torch.no_grad():
                    feat = backbone(transformed.unsqueeze(0))
                    feat = torch.flatten(feat, 1).squeeze(0).cpu().numpy()
                X_features.append(feat)
                y_labels.append(0)  # Normal Operation baseline
                clip_manifest.append({
                    "video": os.path.basename(video_path),
                    "category": "Normal Operation (Baseline)",
                    "start_sec": round(start_frame / fps, 2),
                    "end_sec": round((start_frame + 16) / fps, 2),
                    "label": 0,
                })
        cap.release()

    X_arr = np.array(X_features)
    y_arr = np.array(y_labels)
    np.savez(CACHE_PATH, X=X_arr, y=y_arr, manifest=clip_manifest)
    print(f"  Total labeled clips extracted: {len(X_features)}. Saved cache to '{CACHE_PATH}'")
    return X_arr, y_arr, clip_manifest


def train_classifier():
    """Train surveillance classification head on extracted R(2+1)D clip embeddings."""
    X, y, manifest = extract_clips_and_features()

    if len(X) < 20:
        print("[ERROR] Insufficient clip data to train legitimate model.")
        sys.exit(1)

    print("[3/4] Partitioning into Train / Validation sets (stratified 80/20)...")
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    print(f"  Training clips: {len(X_train)}")
    print(f"  Validation clips: {len(X_val)}")
    for i, c in enumerate(CLASSES):
        print(f"    Class {i} ({c}): Train={sum(y_train == i)}, Val={sum(y_val == i)}")

    train_dataset = TensorDataset(torch.tensor(X_train, dtype=torch.float32), torch.tensor(y_train, dtype=torch.long))
    val_dataset = TensorDataset(torch.tensor(X_val, dtype=torch.float32), torch.tensor(y_val, dtype=torch.long))

    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)

    head = TemporalSurveillanceClassifierHead(in_features=512, num_classes=len(CLASSES))
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(head.parameters(), lr=0.002, weight_decay=1e-4)

    epochs = 30
    best_val_loss = float("inf")
    history = []

    print("[4/4] Training TemporalSurveillanceClassifierHead...")
    for epoch in range(1, epochs + 1):
        head.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = head(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * len(batch_y)
            preds = torch.argmax(outputs, dim=1)
            correct += (preds == batch_y).sum().item()
            total += len(batch_y)

        train_loss = total_loss / total
        train_acc = correct / total

        # Validation phase
        head.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        all_val_preds = []
        all_val_targets = []

        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                outputs = head(batch_x)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item() * len(batch_y)
                preds = torch.argmax(outputs, dim=1)
                val_correct += (preds == batch_y).sum().item()
                val_total += len(batch_y)
                all_val_preds.extend(preds.cpu().numpy())
                all_val_targets.extend(batch_y.cpu().numpy())

        val_loss = val_loss / val_total
        val_acc = val_correct / val_total

        history.append({
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "train_acc": round(train_acc, 4),
            "val_loss": round(val_loss, 4),
            "val_acc": round(val_acc, 4),
        })

        if epoch % 5 == 0 or epoch == epochs:
            print(f"  Epoch {epoch:02d}/{epochs:02d} | Train Loss: {train_loss:.4f}, Acc: {train_acc*100:.1f}% | Val Loss: {val_loss:.4f}, Acc: {val_acc*100:.1f}%")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(head.state_dict(), HEAD_SAVE_PATH)

    print(f"  Saved trained classification head to '{HEAD_SAVE_PATH}'")

    # Load best model for evaluation metrics
    head.load_state_dict(torch.load(HEAD_SAVE_PATH, map_location="cpu"))
    head.eval()

    val_preds = []
    val_targets = []
    with torch.no_grad():
        for batch_x, batch_y in val_loader:
            outputs = head(batch_x)
            val_preds.extend(torch.argmax(outputs, dim=1).cpu().numpy())
            val_targets.extend(batch_y.cpu().numpy())

    prec, rec, f1, _ = precision_recall_fscore_support(val_targets, val_preds, average="weighted", zero_division=0)
    acc = accuracy_score(val_targets, val_preds)
    cm = confusion_matrix(val_targets, val_preds).tolist()
    clf_rep = classification_report(val_targets, val_preds, target_names=CLASSES, output_dict=True, zero_division=0)

    print("\nValidation Performance Metrics:")
    print(f"  Overall Accuracy: {acc*100:.2f}%")
    print(f"  Weighted Precision: {prec*100:.2f}%")
    print(f"  Weighted Recall:    {rec*100:.2f}%")
    print(f"  Weighted F1-Score:  {f1*100:.2f}%")
    print("  Confusion Matrix:")
    for row in cm:
        print("   ", row)

    metrics = {
        "model_architecture": "R(2+1)D-18 (Kinetics-400) + Trained Temporal Head",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "epochs": epochs,
        "train_clips": len(X_train),
        "val_clips": len(X_val),
        "classes": CLASSES,
        "metrics": {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "confusion_matrix": cm,
            "classification_report": clf_rep,
        },
        "training_history": history,
    }

    with open(METRICS_SAVE_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

    meta = {
        "classes": CLASSES,
        "in_features": 512,
        "clip_length_frames": 16,
        "spatial_resolution": [112, 112],
        "normalization": {
            "mean": [0.43216, 0.394666, 0.37645],
            "std": [0.22803, 0.22145, 0.216989],
        },
        "train_videos": [v[1] for v in TRAIN_VIDEOS],
        "held_out_eval_videos": [v[1] for v in HELD_OUT_EVAL_VIDEOS],
        "integrity_attestation": "Stealing002_x264.mp4 and Burglary003_x264.mp4 strictly held out from training and validation."
    }

    with open(META_SAVE_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"  Metrics written to '{METRICS_SAVE_PATH}'")
    print(f"  Metadata written to '{META_SAVE_PATH}'")


if __name__ == "__main__":
    train_classifier()
