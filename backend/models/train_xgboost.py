"""
CaseIntel — XGBoost Incident Classifier Training & Bootstrap Script
Trains a multi-class XGBoost gradient-boosted decision tree classifier
to predict physical security incidents from CCTV tabular features.
"""

import os
import json
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

MODEL_SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xgboost_incident_model.json")
META_SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xgboost_features_meta.json")

FEATURE_NAMES = [
    "person_count",          # 0: number of detected individuals
    "vehicle_count",         # 1: number of detected vehicles
    "event_count",           # 2: count of triggered chronological events
    "evidence_count",        # 3: count of registered key evidence items
    "max_dwell_time_sec",    # 4: peak dwell time across tracks in seconds
    "night_time_flag",       # 5: 1 if after hours (20:00-06:00), 0 otherwise
    "loitering_flag",        # 6: 1 if loitering behavior was confirmed, 0 otherwise
    "unattended_bag_flag",   # 7: 1 if unattended luggage observed, 0 otherwise
    "forced_entry_flag",     # 8: 1 if boundary/door tampering observed, 0 otherwise
    "speed_max",             # 9: peak velocity displacement %/s
]

CLASSES = [
    "Suspicious Activity",   # 0
    "Unauthorized Access",   # 1
    "Perimeter Breach",      # 2
    "Normal Operation",      # 3
    "Theft / Tampering",     # 4
]


def generate_synthetic_dataset(n_samples: int = 2500, random_seed: int = 42):
    """Generate realistic synthetic security incident features with noise."""
    np.random.seed(random_seed)

    X = []
    y = []

    for _ in range(n_samples):
        # Choose incident class with balanced distribution
        cls_idx = np.random.choice([0, 1, 2, 3, 4], p=[0.25, 0.20, 0.20, 0.20, 0.15])

        if cls_idx == 0:  # Suspicious Activity
            persons = np.random.randint(1, 4)
            vehicles = np.random.randint(1, 3)
            events = np.random.randint(3, 8)
            evidence = np.random.randint(2, 5)
            dwell = np.random.uniform(15.0, 90.0)
            night = np.random.choice([0, 1], p=[0.2, 0.8])
            loiter = np.random.choice([0, 1], p=[0.1, 0.9])
            bag = 0
            forced = 0
            speed = np.random.uniform(5.0, 18.0)

        elif cls_idx == 1:  # Unauthorized Access
            persons = np.random.randint(1, 3)
            vehicles = np.random.choice([0, 1], p=[0.7, 0.3])
            events = np.random.randint(2, 6)
            evidence = np.random.randint(2, 4)
            dwell = np.random.uniform(5.0, 30.0)
            night = np.random.choice([0, 1], p=[0.1, 0.9])
            loiter = np.random.choice([0, 1], p=[0.5, 0.5])
            bag = 0
            forced = np.random.choice([0, 1], p=[0.4, 0.6])
            speed = np.random.uniform(8.0, 22.0)

        elif cls_idx == 2:  # Perimeter Breach
            persons = np.random.randint(1, 5)
            vehicles = np.random.choice([0, 1, 2], p=[0.6, 0.3, 0.1])
            events = np.random.randint(2, 7)
            evidence = np.random.randint(1, 4)
            dwell = np.random.uniform(3.0, 20.0)
            night = np.random.choice([0, 1], p=[0.3, 0.7])
            loiter = 0
            bag = 0
            forced = np.random.choice([0, 1], p=[0.1, 0.9])
            speed = np.random.uniform(18.0, 35.0)

        elif cls_idx == 3:  # Normal Operation
            persons = np.random.randint(0, 8)
            vehicles = np.random.randint(0, 6)
            events = np.random.randint(1, 4)
            evidence = np.random.choice([0, 1], p=[0.85, 0.15])
            dwell = np.random.uniform(1.0, 12.0)
            night = np.random.choice([0, 1], p=[0.8, 0.2])
            loiter = 0
            bag = 0
            forced = 0
            speed = np.random.uniform(2.0, 12.0)

        else:  # Theft / Tampering
            persons = np.random.randint(1, 3)
            vehicles = np.random.choice([0, 1], p=[0.5, 0.5])
            events = np.random.randint(4, 9)
            evidence = np.random.randint(3, 6)
            dwell = np.random.uniform(25.0, 120.0)
            night = np.random.choice([0, 1], p=[0.15, 0.85])
            loiter = np.random.choice([0, 1], p=[0.2, 0.8])
            bag = np.random.choice([0, 1], p=[0.6, 0.4])
            forced = np.random.choice([0, 1], p=[0.2, 0.8])
            speed = np.random.uniform(6.0, 24.0)

        # Add Gaussian noise
        dwell = max(0.5, dwell + np.random.normal(0, 1.5))
        speed = max(0.5, speed + np.random.normal(0, 0.8))

        row = [
            float(persons),
            float(vehicles),
            float(events),
            float(evidence),
            float(round(dwell, 2)),
            float(night),
            float(loiter),
            float(bag),
            float(forced),
            float(round(speed, 2)),
        ]
        X.append(row)
        y.append(cls_idx)

    return np.array(X), np.array(y)


def train_and_save_model():
    """Train XGBoost multi-class classifier and save model artifact."""
    print("[XGBoost Train] Generating synthetic CCTV incident training dataset...")
    X, y = generate_synthetic_dataset(n_samples=3000)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = xgb.XGBClassifier(
        n_estimators=120,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        objective="multi:softprob",
        num_class=len(CLASSES),
        random_state=42,
        eval_metric="mlogloss",
    )

    print("[XGBoost Train] Fitting model...")
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"[XGBoost Train] Test Accuracy: {acc * 100:.2f}%")
    print("[XGBoost Train] Classification Report:")
    print(classification_report(y_test, y_pred, target_names=CLASSES))

    # Save model artifact
    model.save_model(MODEL_SAVE_PATH)
    print(f"[XGBoost Train] Saved XGBoost model artifact to: '{MODEL_SAVE_PATH}'")

    # Save feature metadata
    metadata = {
        "feature_names": FEATURE_NAMES,
        "classes": CLASSES,
        "accuracy": round(float(acc), 4),
        "n_features": len(FEATURE_NAMES),
        "model_version": "xgboost-1.8-caseintel",
    }
    with open(META_SAVE_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[XGBoost Train] Saved metadata to: '{META_SAVE_PATH}'")

    return model, metadata


if __name__ == "__main__":
    train_and_save_model()
