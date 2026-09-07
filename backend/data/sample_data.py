"""
CaseIntel — Sample Data (mirrors src/data/mockData.ts)
Single source of truth for all mock investigation data in the backend.
"""

MOCK_INVESTIGATION = {
    "id": "inv-001",
    "case_number": "CASE-2026-001",
    "status": "under_investigation",
    "created_at": "2026-08-26T21:28:00Z",
    "updated_at": "2026-08-26T21:35:00Z",
    "investigator": "Insp. R. Sharma",
    "camera_ids": ["C-01", "C-02"],
    "location": "Parking Area — Block B, Sector 14",
    "video_count": 2,
    "duration_analyzed": "00:04:22",
    "ai_insight": (
        "The incident was classified as suspicious activity because tracked individual P102 "
        "maintained proximity to vehicle V014 for an extended period, followed by vehicle movement "
        "and rapid departure. The temporal sequence and spatial proximity of these events contributed "
        "significantly to the high-confidence classification."
    ),
    "incident": {
        "type": "Suspicious Activity",
        "confidence": 87.4,
        "severity": "HIGH",
        "classifier_version": "MockXGBoost-v1.0",
        "feature_contributions": [
            {"feature": "Extended presence near vehicle", "contribution": 31, "direction": "positive"},
            {"feature": "Approach behavior detected",    "contribution": 24, "direction": "positive"},
            {"feature": "Vehicle movement correlation",  "contribution": 18, "direction": "positive"},
            {"feature": "Unusual time of day (21:30)",  "contribution": 14, "direction": "positive"},
            {"feature": "Departure pattern post-event", "contribution": 10, "direction": "positive"},
            {"feature": "Ambient lighting (low)",       "contribution": 3,  "direction": "positive"},
        ],
        "reasoning": (
            "Person P102 was detected entering the area at 21:31:04. The individual subsequently "
            "walked in a direct path toward vehicle V014 and remained in close proximity for 16 seconds "
            "before the vehicle exhibited movement. This temporally connected sequence of events — "
            "approach, proximity, vehicle activation, and rapid departure — formed the primary evidence "
            "pattern for suspicious activity classification."
        ),
    },
    "entities": [
        {
            "id": "P102", "type": "person", "label": "Person #P102",
            "confidence": 96.2, "first_seen": "21:31:04", "last_seen": "21:32:05",
            "track_duration": "01:01", "camera_ids": ["C-01"],
            "activities": [
                {"id": "A001", "label": "Walking",               "confidence": 97.1, "start_time": "21:31:04", "end_time": "21:31:17"},
                {"id": "A002", "label": "Approaching vehicle",   "confidence": 91.4, "start_time": "21:31:17", "end_time": "21:31:48"},
                {"id": "A003", "label": "Standing near vehicle", "confidence": 88.9, "start_time": "21:31:48", "end_time": "21:32:05"},
                {"id": "A004", "label": "Leaving area",          "confidence": 95.3, "start_time": "21:32:05", "end_time": "21:32:05"},
            ],
            "metadata": {"height_estimate": "175cm", "clothing": "Dark jacket"},
        },
        {
            "id": "V014", "type": "vehicle", "label": "Vehicle #V014",
            "confidence": 94.8, "first_seen": "21:31:32", "last_seen": "21:31:48",
            "track_duration": "00:16", "camera_ids": ["C-01"],
            "activities": [
                {"id": "A005", "label": "Stationary",       "confidence": 98.2, "start_time": "21:31:32", "end_time": "21:31:44"},
                {"id": "A006", "label": "Vehicle movement", "confidence": 94.1, "start_time": "21:31:44", "end_time": "21:31:48"},
            ],
            "metadata": {"vehicle_type": "Sedan", "color_estimate": "Dark grey"},
        },
    ],
    "events": [
        {"id": "EVT-001", "timestamp": "21:31:04", "entity_id": "P102", "entity_type": "person",
         "action": "Entered monitored area",          "location": "Parking Area – North Entrance",
         "camera_id": "C-01", "confidence": 98, "evidence_id": "EV-001",
         "is_suspicious": False, "description": "Person P102 entered the monitored parking area.",
         "related_entity_id": "LOC-PARK-A"},
        {"id": "EVT-002", "timestamp": "21:31:17", "entity_id": "P102", "entity_type": "person",
         "action": "Walking toward vehicle V014",     "location": "Parking Area – Centre",
         "camera_id": "C-01", "confidence": 95, "evidence_id": "EV-002",
         "is_suspicious": False, "description": "P102 moving in direct path toward V014.",
         "related_entity_id": "V014"},
        {"id": "EVT-003", "timestamp": "21:31:32", "entity_id": "P102", "entity_type": "person",
         "action": "Approached vehicle V014",         "location": "Parking Area – Centre",
         "camera_id": "C-01", "confidence": 91, "evidence_id": "EV-003",
         "is_suspicious": True,  "description": "P102 within 1.2m of V014 for 16 seconds.",
         "related_entity_id": "V014"},
        {"id": "EVT-004", "timestamp": "21:31:48", "entity_id": "V014", "entity_type": "vehicle",
         "action": "Vehicle movement detected",       "location": "Parking Area – Centre",
         "camera_id": "C-01", "confidence": 94, "evidence_id": "EV-004",
         "is_suspicious": True,  "description": "V014 exhibited movement while P102 in proximity.",
         "related_entity_id": "P102"},
        {"id": "EVT-005", "timestamp": "21:32:05", "entity_id": "P102", "entity_type": "person",
         "action": "Left monitored area",             "location": "Parking Area – North Entrance",
         "camera_id": "C-01", "confidence": 97, "evidence_id": "EV-005",
         "is_suspicious": True,  "description": "P102 departed rapidly after V014 movement.",
         "related_entity_id": "LOC-PARK-A"},
    ],
    "evidence": [
        {"id": "EV-001", "timestamp": "21:31:04", "camera_id": "C-01",
         "type": "Person entry detection", "primary_entity_id": "P102",
         "confidence": 98, "event_id": "EVT-001", "is_key_evidence": False,
         "description": "Person P102 detected at perimeter boundary."},
        {"id": "EV-002", "timestamp": "21:31:17", "camera_id": "C-01",
         "type": "Directional movement analysis", "primary_entity_id": "P102", "secondary_entity_id": "V014",
         "confidence": 95, "event_id": "EVT-002", "is_key_evidence": False,
         "description": "ByteTrack trajectory shows direct path toward V014."},
        {"id": "EV-003", "timestamp": "21:31:32", "camera_id": "C-01",
         "type": "Person–vehicle proximity event", "primary_entity_id": "P102", "secondary_entity_id": "V014",
         "confidence": 91, "event_id": "EVT-003", "is_key_evidence": True,
         "description": "P102 within 1.2m of V014 for 16 seconds."},
        {"id": "EV-004", "timestamp": "21:31:48", "camera_id": "C-01",
         "type": "Vehicle motion detection", "primary_entity_id": "V014", "secondary_entity_id": "P102",
         "confidence": 94, "event_id": "EVT-004", "is_key_evidence": True,
         "description": "V014 optical flow analysis detected lateral movement."},
        {"id": "EV-005", "timestamp": "21:32:05", "camera_id": "C-01",
         "type": "Subject departure detection", "primary_entity_id": "P102",
         "confidence": 97, "event_id": "EVT-005", "is_key_evidence": True,
         "description": "P102 exited area rapidly following V014 movement."},
    ],
}

MOCK_KNOWLEDGE_GRAPH = {
    "investigation_id": "inv-001",
    "nodes": [
        {"id": "P102",         "label": "P102",         "type": "person",    "confidence": 96.2, "x": 80,  "y": 200},
        {"id": "V014",         "label": "V014",         "type": "vehicle",   "confidence": 94.8, "x": 400, "y": 300},
        {"id": "C-01",         "label": "Camera C-01",  "type": "camera",    "confidence": 100,  "x": 240, "y": 40 },
        {"id": "LOC-PARK-A",   "label": "Parking Area", "type": "location",                      "x": 580, "y": 160},
        {"id": "EVT-003",      "label": "EVT-003",      "type": "event",                          "x": 240, "y": 340},
        {"id": "ACT-APPROACH", "label": "Approaching",  "type": "activity",  "confidence": 91.4, "x": 400, "y": 460},
        {"id": "TS-2131",      "label": "21:31:32",     "type": "timestamp",                      "x": 600, "y": 340},
    ],
    "edges": [
        {"id": "e1", "source": "P102",    "target": "LOC-PARK-A",   "relationship": "ENTERED",    "suspicious": False},
        {"id": "e2", "source": "P102",    "target": "V014",         "relationship": "APPROACHED",  "suspicious": True },
        {"id": "e3", "source": "P102",    "target": "C-01",         "relationship": "DETECTED_BY", "suspicious": False},
        {"id": "e4", "source": "V014",    "target": "C-01",         "relationship": "DETECTED_BY", "suspicious": False},
        {"id": "e5", "source": "EVT-003", "target": "TS-2131",      "relationship": "OCCURRED_AT", "suspicious": False},
        {"id": "e6", "source": "P102",    "target": "EVT-003",      "relationship": "TRIGGERED",   "suspicious": True },
        {"id": "e7", "source": "P102",    "target": "ACT-APPROACH", "relationship": "PERFORMED",   "suspicious": False},
        {"id": "e8", "source": "C-01",    "target": "LOC-PARK-A",   "relationship": "MONITORS",    "suspicious": False},
        {"id": "e9", "source": "V014",    "target": "LOC-PARK-A",   "relationship": "LOCATED_IN",  "suspicious": False},
    ],
}
