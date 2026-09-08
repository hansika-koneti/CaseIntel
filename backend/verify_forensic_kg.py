import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from services.incident_service import XGBoostIncidentClassifierService
from services.neo4j_service import Neo4jKnowledgeGraphService
from services.report_service import LLMReportGeneratorService

def test_incident():
    clf = XGBoostIncidentClassifierService()
    # Tabular features that trigger Theft / Tampering in XGBoost model
    features = {
        "person_count": 2.0,
        "vehicle_count": 1.0,
        "event_count": 6.0,
        "evidence_count": 4.0,
        "max_dwell_time_sec": 45.0,
        "night_time_flag": 1.0,
        "loitering_flag": 1.0,
        "unattended_bag_flag": 0.0,
        "forced_entry_flag": 1.0,
        "speed_max": 14.2,
    }
    events = [
        {"action": "Zone Entry", "event_type": "Zone Entry", "timestamp": "00:01", "description": "Subject entered zone", "confidence": 92.0},
        {"action": "Physical Interaction / Altercation Suspected", "event_type": "Physical Interaction / Altercation Suspected", "timestamp": "00:07", "description": "Physical confrontation detected", "confidence": 89.0, "is_suspicious": True},
        {"action": "Object Interaction", "event_type": "Object Interaction", "timestamp": "00:11", "description": "Interaction with Phone-01", "confidence": 91.0, "is_suspicious": True},
    ]
    entities = [
        {"id": "Person-01", "type": "person", "label": "Person-01", "confidence": 95.0, "track_duration": "16.1s"},
        {"id": "Person-02", "type": "person", "label": "Person-02", "confidence": 88.0, "track_duration": "10.2s"},
        {"id": "Phone-01", "type": "object", "label": "Phone-01", "confidence": 91.2, "track_duration": "12.0s"},
    ]
    res = clf.classify(events=events, entities=entities, custom_features=features)
    print("CLASSIFICATION RESULT:")
    print("  Type:", res["type"])
    print("  Confidence:", res["confidence"])
    print("  Severity:", res["severity"])
    print("  Is Hypothesis:", res["is_hypothesis"])
    print("  Theft Visually Verified:", res["theft_visually_verified"])
    print("  Hypothesis Status:", res["hypothesis_status"])
    print("  Visual Summary:", res["visual_evidence_summary"])
    print("  Forensic Steps:", len(res["forensic_rule_evaluation"]))
    for s in res["forensic_rule_evaluation"]:
        print(f"    Step {s['step']}: {s['name']} -> {s['status']} ({s['detail']})")

    assert res["type"] == "Theft / Tampering"
    assert res["is_hypothesis"] is True
    assert res["theft_visually_verified"] is False
    assert res["severity"] == "HIGH"
    print(">> Incident Classification test PASSED")

def test_graph():
    kg = Neo4jKnowledgeGraphService()
    events = [
        {"id": "EVT-01", "action": "Zone Entry", "timestamp": "00:01", "description": "Person-01 entered zone", "entity_id": "Person-01", "confidence": 92.0},
        {"id": "EVT-02", "action": "Physical Interaction / Altercation Suspected", "timestamp": "00:07", "description": "Altercation between Person-01 and Person-02", "entity_id": "Person-01", "confidence": 89.0, "is_suspicious": True},
        {"id": "EVT-03", "action": "Object Interaction", "timestamp": "00:11", "description": "Person-01 manipulated Phone-01", "entity_id": "Person-01", "confidence": 91.0, "is_suspicious": True},
    ]
    entities = [
        {"id": "Person-01", "type": "person", "label": "Person-01", "confidence": 95.0},
        {"id": "Person-02", "type": "person", "label": "Person-02", "confidence": 88.0},
        {"id": "Phone-01", "type": "object", "label": "Phone-01", "confidence": 91.2},
    ]
    g = kg.build_graph_from_case("inv-1", "CASE-001", "Main Entryway", entities, events)
    print("\nGRAPH RESULT:")
    print("  Nodes count:", len(g["nodes"]))
    print("  Edges count:", len(g["edges"]))
    print("  Summary:", g["summary"])
    print("  Graph Engine:", g["graph_engine"])
    node_types = {n["id"]: n["type"] for n in g["nodes"]}
    print("  Node types:", node_types)
    assert "Phone-01" in node_types
    assert node_types["Phone-01"] == "object"
    
    edge_rels = [e["relationship"] for e in g["edges"]]
    print("  Edge relationships:", edge_rels)
    assert "THEN" in edge_rels
    assert "CONFRONTED" in edge_rels or "PARTICIPATED_IN" in edge_rels
    assert g["graph_engine"] in ["Neo4j", "In-Memory Forensic Topology"]
    print(">> Knowledge Graph test PASSED")

def test_report():
    rep_svc = LLMReportGeneratorService()
    inv_data = {
        "id": "inv-1",
        "case_number": "CASE-001",
        "location": "Main Lobby",
        "entities": [
            {"id": "Person-01", "type": "person", "label": "Person-01"},
            {"id": "Person-02", "type": "person", "label": "Person-02"},
            {"id": "Phone-01", "type": "object", "label": "Phone-01"},
        ],
        "events": [
            {"id": "EVT-01", "action": "Physical Interaction / Altercation Suspected", "timestamp": "00:07", "description": "Altercation"},
        ],
        "incident": {
            "type": "Theft / Tampering",
            "confidence": 37.5,
            "severity": "HIGH",
            "incident_risk_score": 35.6,
            "is_hypothesis": True,
            "theft_visually_verified": False,
        }
    }
    rep = rep_svc.generate(inv_data)
    print("\nREPORT RESULT:")
    print("  Exec summary:", rep["executive_summary"])
    print("  Sections:", len(rep["sections"]))
    assert "MODEL HYPOTHESIS" in rep["executive_summary"] or "HYPOTHESIS" in rep["executive_summary"]
    assert "DISCLAIMER" in rep["disclaimer"].upper()
    print(">> Report test PASSED")

if __name__ == "__main__":
    test_incident()
    test_graph()
    test_report()
    print("\nALL BACKEND TESTS PASSED!")
