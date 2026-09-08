"""
CaseIntel — Neo4j Knowledge Graph Persistence & Connectivity Test Suite
Tests:
1. Valid Neo4j connectivity with official driver
2. Invalid / missing credentials (graceful fallback)
3. Offline Neo4j fallback
4. Complete graph persistence (Investigation, Video, Camera, Location, Person, Object, Event, Evidence, Timestamp)
5. Graph querying via Cypher
6. Deduplication on repeated MERGE operations (idempotency)
7. Investigation isolation (no cross-investigation leakage)
8. Video isolation (no cross-video leakage)
9. Active-video switching
10. Entity, Person, and Object nodes (Phone-01)
11. Chronological THEN relationships
12. Multi-entity interaction relationships (CONFRONTED, MANIPULATED, INTERACTED_WITH)
13. Evidence linkage (PRODUCED_EVIDENCE, INVOLVED)
"""

import os
import sys

# Ensure backend directory is in path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

from services.neo4j_service import Neo4jKnowledgeGraphService


def test_1_connectivity_and_fallback():
    print("\n--- Test 1: Connectivity & Graceful Fallback ---")
    # A. Valid connection
    kg_valid = Neo4jKnowledgeGraphService(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password"),
    )
    assert kg_valid.is_connected is True, "Neo4j should connect with valid credentials"
    assert kg_valid.check_connection() is True
    print("  [Pass] Valid connection verified (is_connected=True)")

    # B. Invalid credentials -> graceful fallback
    kg_invalid = Neo4jKnowledgeGraphService(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="WRONG_PASSWORD_TEST_123",
    )
    assert kg_invalid.is_connected is False, "Service must not be connected with invalid password"
    # Ensure build_graph_from_case still works and falls back gracefully
    fallback_res = kg_invalid.build_graph_from_case(
        investigation_id="inv-fallback-test",
        case_number="CASE-FALLBACK",
        location="Fallback Zone",
        entities=[{"id": "Person-99", "type": "person", "label": "Person-99"}],
        events=[{"id": "EVT-99", "action": "Fallback Event", "timestamp": "00:01"}],
    )
    assert fallback_res["neo4j_connected"] is False, "Payload must truthfully state neo4j_connected=False"
    assert fallback_res["graph_engine"] == "In-Memory Forensic Topology", "Payload must state In-Memory Forensic Topology"
    assert len(fallback_res["nodes"]) > 0, "Fallback graph must still return nodes"
    print("  [Pass] Invalid credentials handled gracefully (in-memory fallback active)")

    # C. Offline / invalid port -> graceful fallback
    kg_offline = Neo4jKnowledgeGraphService(
        uri="bolt://localhost:17687",  # Non-existent port
        user="neo4j",
        password="password",
    )
    assert kg_offline.is_connected is False, "Offline instance must not be connected"
    offline_res = kg_offline.build_graph_from_case(
        investigation_id="inv-offline-test",
        case_number="CASE-OFFLINE",
        location="Offline Zone",
        entities=[],
        events=[],
    )
    assert offline_res["neo4j_connected"] is False
    assert offline_res["graph_engine"] == "In-Memory Forensic Topology"
    print("  [Pass] Offline port handled gracefully without crashing")


def test_2_graph_persistence_and_hierarchy():
    print("\n--- Test 2: Full Graph Persistence & Schema Hierarchy ---")
    kg = Neo4jKnowledgeGraphService()
    assert kg.is_connected is True, "Neo4j must be running for persistence test"

    inv_id = "inv-test-persist-01"
    vid_id = "vid-test-alpha"
    case_num = "CASE-TEST-PERSIST"
    loc = "Secured Vault Room"
    cam_id = "CAM-01"

    entities = [
        {"id": "Person-01", "type": "person", "label": "Person-01", "confidence": 98.0, "first_seen": "00:02", "last_seen": "00:15", "track_duration": "00:02 - 00:15"},
        {"id": "Person-02", "type": "person", "label": "Person-02", "confidence": 92.0, "first_seen": "00:05", "last_seen": "00:12", "track_duration": "00:05 - 00:12"},
        {"id": "Phone-01", "type": "object", "label": "Phone-01", "confidence": 94.5, "first_seen": "00:06", "last_seen": "00:10", "track_duration": "00:06 - 00:10"},
    ]

    events = [
        {"id": "EVT-101", "action": "Entry to Vault", "timestamp": "00:02", "confidence": 96.0, "description": "Subject entered vault", "entity_id": "Person-01", "camera_id": cam_id},
        {"id": "EVT-102", "action": "Physical Confrontation", "timestamp": "00:07", "confidence": 91.0, "description": "Confrontation between Person-01 and Person-02", "is_suspicious": True, "entity_id": "Person-01", "related_entity_id": "Person-02", "camera_id": cam_id},
        {"id": "EVT-103", "action": "Object Interaction", "timestamp": "00:09", "confidence": 95.0, "description": "Person-01 manipulated Phone-01", "is_suspicious": True, "entity_id": "Person-01", "camera_id": cam_id},
    ]

    evidence = [
        {"id": "EVD-201", "type": "Tampered Device", "confidence": 93.0, "is_key_evidence": True, "primary_entity_id": "Person-01", "secondary_entity_id": "Phone-01", "event_id": "EVT-103", "description": "Phone-01 shows physical tampering"},
    ]

    # Build and persist to Neo4j
    res = kg.build_graph_from_case(
        investigation_id=inv_id,
        case_number=case_num,
        location=loc,
        entities=entities,
        events=events,
        evidence=evidence,
        camera_id=cam_id,
        video_id=vid_id,
    )

    assert res["neo4j_connected"] is True
    assert res["graph_engine"] == "Neo4j"
    assert res["investigation_id"] == inv_id
    assert res["video_id"] == vid_id

    # Verify directly via Neo4j Cypher queries
    with kg.driver.session(database=kg.database) as session:
        # Check Investigation
        inv_record = session.run("MATCH (i:Investigation {id: $id}) RETURN i", id=inv_id).single()
        assert inv_record is not None, "Investigation node must exist in Neo4j"
        assert inv_record["i"]["case_number"] == case_num

        # Check Video & CONTAINS_VIDEO
        vid_record = session.run("MATCH (i:Investigation {id: $inv_id})-[:CONTAINS_VIDEO]->(v:Video {id: $vid_id}) RETURN v", inv_id=inv_id, vid_id=vid_id).single()
        assert vid_record is not None, "(:Investigation)-[:CONTAINS_VIDEO]->(:Video) must exist"

        # Check Video -> Camera (CAPTURED_BY)
        cam_record = session.run("MATCH (v:Video {id: $vid_id})-[:CAPTURED_BY]->(c:Camera {id: $cam_id}) RETURN c", vid_id=vid_id, cam_id=cam_id).single()
        assert cam_record is not None, "(:Video)-[:CAPTURED_BY]->(:Camera) must exist"

        # Check Camera -> Location (LOCATED_AT)
        loc_record = session.run("MATCH (c:Camera {id: $cam_id, investigation_id: $inv_id})-[:LOCATED_AT]->(l:Location {investigation_id: $inv_id}) RETURN l", cam_id=cam_id, inv_id=inv_id).single()
        assert loc_record is not None, "(:Camera)-[:LOCATED_AT]->(:Location) must exist"

        # Check Entity labels: Person and Object
        p1 = session.run("MATCH (p:Person {id: 'Person-01', investigation_id: $inv_id}) RETURN p", inv_id=inv_id).single()
        assert p1 is not None, "Person-01 must have :Person label"

        obj1 = session.run("MATCH (o:Object {id: 'Phone-01', investigation_id: $inv_id}) RETURN o", inv_id=inv_id).single()
        assert obj1 is not None, "Phone-01 must have :Object label"

        # Check DETECTED_BY relationship
        det_record = session.run("MATCH (p:Person {id: 'Person-01', investigation_id: $inv_id})-[:DETECTED_BY]->(c:Camera) RETURN c", inv_id=inv_id).single()
        assert det_record is not None, "(:Entity)-[:DETECTED_BY]->(:Camera) must exist"

        # Check PERFORMED relationships
        perf_record = session.run("MATCH (p:Person {id: 'Person-01', investigation_id: $inv_id})-[:PERFORMED]->(e:Event {id: 'EVT-101'}) RETURN e", inv_id=inv_id).single()
        assert perf_record is not None, "(:Entity)-[:PERFORMED]->(:Event) must exist"

        # Check Chronological THEN relationship
        then_record = session.run("MATCH (e1:Event {id: 'EVT-101', investigation_id: $inv_id})-[:THEN]->(e2:Event {id: 'EVT-102'}) RETURN e1, e2", inv_id=inv_id).single()
        assert then_record is not None, "Chronological (:Event)-[:THEN]->(:Event) must exist"

        # Check CONFRONTED altercation relationship
        conf_record = session.run("MATCH (p1:Person {id: 'Person-01', investigation_id: $inv_id})-[:CONFRONTED]->(p2:Person {id: 'Person-02'}) RETURN p1, p2", inv_id=inv_id).single()
        assert conf_record is not None, "(:Person)-[:CONFRONTED]->(:Person) altercation relationship must exist"

        # Check MANIPULATED object relationship
        manip_record = session.run("MATCH (p:Person {id: 'Person-01', investigation_id: $inv_id})-[:MANIPULATED]->(o:Object {id: 'Phone-01'}) RETURN p, o", inv_id=inv_id).single()
        assert manip_record is not None, "(:Person)-[:MANIPULATED]->(:Object) relationship must exist"

        # Check Evidence and PRODUCED_EVIDENCE
        evd_record = session.run("MATCH (e:Event {id: 'EVT-103', investigation_id: $inv_id})-[:PRODUCED_EVIDENCE]->(ev:Evidence {id: 'EVD-201'}) RETURN ev", inv_id=inv_id).single()
        assert evd_record is not None, "(:Event)-[:PRODUCED_EVIDENCE]->(:Evidence) must exist"

        # Check Evidence -> Entity linkage
        ev_ent_record = session.run("MATCH (ev:Evidence {id: 'EVD-201', investigation_id: $inv_id})-[:INVOLVED]->(p:Person {id: 'Person-01'}) RETURN ev, p", inv_id=inv_id).single()
        assert ev_ent_record is not None, "(:Evidence)-[:INVOLVED]->(:Entity) must exist"

    print("  [Pass] Hierarchy, all node labels, and all relationships verified in Neo4j")


def test_3_idempotency_and_no_duplicates():
    print("\n--- Test 3: Idempotency (Zero Duplication on Repeated MERGE) ---")
    kg = Neo4jKnowledgeGraphService()
    inv_id = "inv-test-idempotent"
    vid_id = "vid-test-idempotent"

    entities = [{"id": "Person-01", "type": "person", "label": "Person-01"}]
    events = [{"id": "EVT-01", "action": "Idempotent Check", "timestamp": "00:01"}]

    # Run 1
    kg.build_graph_from_case(inv_id, "CASE-IDEMP", "Zone A", entities, events, video_id=vid_id)

    # Count nodes
    with kg.driver.session(database=kg.database) as session:
        c1 = session.run("MATCH (n {investigation_id: $id}) RETURN count(n) as c", id=inv_id).single()["c"]
        r1 = session.run("MATCH (n {investigation_id: $id})-[r]->(m {investigation_id: $id}) RETURN count(r) as c", id=inv_id).single()["c"]

    # Run 2 (Identical call)
    kg.build_graph_from_case(inv_id, "CASE-IDEMP", "Zone A", entities, events, video_id=vid_id)

    # Count nodes again
    with kg.driver.session(database=kg.database) as session:
        c2 = session.run("MATCH (n {investigation_id: $id}) RETURN count(n) as c", id=inv_id).single()["c"]
        r2 = session.run("MATCH (n {investigation_id: $id})-[r]->(m {investigation_id: $id}) RETURN count(r) as c", id=inv_id).single()["c"]

    assert c1 == c2, f"Node count must not change on duplicate build: {c1} vs {c2}"
    assert r1 == r2, f"Edge count must not change on duplicate build: {r1} vs {r2}"
    print(f"  [Pass] Idempotency verified: exactly {c1} nodes and {r1} relationships after repeated calls")


def test_4_investigation_and_video_isolation():
    print("\n--- Test 4: Strict Investigation & Video Isolation ---")
    kg = Neo4jKnowledgeGraphService()

    # Create Case A with Video 1
    inv_a = "inv-iso-case-A"
    vid_a1 = "vid-iso-A1"
    kg.build_graph_from_case(
        inv_a, "CASE-A", "Location A",
        entities=[{"id": "Person-A1", "type": "person", "label": "Person-A1"}],
        events=[{"id": "EVT-A1", "action": "Action A1", "timestamp": "00:01"}],
        video_id=vid_a1,
    )

    # Create Case A with Video 2
    vid_a2 = "vid-iso-A2"
    kg.build_graph_from_case(
        inv_a, "CASE-A", "Location A",
        entities=[{"id": "Person-A2", "type": "person", "label": "Person-A2"}],
        events=[{"id": "EVT-A2", "action": "Action A2", "timestamp": "00:02"}],
        video_id=vid_a2,
    )

    # Create Case B
    inv_b = "inv-iso-case-B"
    vid_b1 = "vid-iso-B1"
    kg.build_graph_from_case(
        inv_b, "CASE-B", "Location B",
        entities=[{"id": "Person-B1", "type": "person", "label": "Person-B1"}],
        events=[{"id": "EVT-B1", "action": "Action B1", "timestamp": "00:01"}],
        video_id=vid_b1,
    )

    # 1. Query Case A with Video 1 -> must NOT return Person-A2, EVT-A2, Person-B1, EVT-B1
    subgraph_a1 = kg.query(investigation_id=inv_a, video_id=vid_a1)
    a1_node_ids = {n["id"] for n in subgraph_a1["nodes"]}
    assert "Person-A1" in a1_node_ids, "Person-A1 must be in Video 1 subgraph"
    assert "Person-A2" not in a1_node_ids, "Person-A2 must NOT leak into Video 1 subgraph"
    assert "Person-B1" not in a1_node_ids, "Person-B1 from Case B must NOT leak into Case A"
    print("  [Pass] Active video A1 isolation verified (no leak from Video A2 or Case B)")

    # 2. Query Case A with Video 2 -> must NOT return Person-A1, EVT-A1
    subgraph_a2 = kg.query(investigation_id=inv_a, video_id=vid_a2)
    a2_node_ids = {n["id"] for n in subgraph_a2["nodes"]}
    assert "Person-A2" in a2_node_ids, "Person-A2 must be in Video 2 subgraph"
    assert "Person-A1" not in a2_node_ids, "Person-A1 must NOT leak into Video 2 subgraph"
    assert "Person-B1" not in a2_node_ids, "Person-B1 must NOT leak into Case A"
    print("  [Pass] Active video A2 isolation verified (no leak from Video A1 or Case B)")

    # 3. Query Case B -> must NOT contain any Case A nodes
    subgraph_b = kg.query(investigation_id=inv_b, video_id=vid_b1)
    b_node_ids = {n["id"] for n in subgraph_b["nodes"]}
    assert "Person-B1" in b_node_ids, "Person-B1 must be in Case B subgraph"
    assert "Person-A1" not in b_node_ids, "Person-A1 must NOT leak into Case B"
    assert "Person-A2" not in b_node_ids, "Person-A2 must NOT leak into Case B"
    print("  [Pass] Investigation-level isolation verified (Case A and Case B are fully partitioned)")


def test_5_query_layer_format():
    print("\n--- Test 5: ReactFlow Payload Formatting ---")
    kg = Neo4jKnowledgeGraphService()
    inv_id = "inv-test-persist-01"
    vid_id = "vid-test-alpha"

    query_res = kg.query(investigation_id=inv_id, video_id=vid_id)
    assert query_res["neo4j_connected"] is True
    assert query_res["graph_engine"] == "Neo4j"
    assert isinstance(query_res["nodes"], list)
    assert isinstance(query_res["edges"], list)

    for n in query_res["nodes"]:
        assert "id" in n
        assert "label" in n
        assert "type" in n
        assert "x" in n and "y" in n, "Nodes must have positioning coordinates for ReactFlow"

    for e in query_res["edges"]:
        assert "id" in e
        assert "source" in e
        assert "target" in e
        assert "relationship" in e

    print(f"  [Pass] Query layer returned {len(query_res['nodes'])} nodes and {len(query_res['edges'])} edges in ReactFlow format")


if __name__ == "__main__":
    print("==================================================================")
    print("   CaseIntel Neo4j Primary Knowledge Graph Integration Tests   ")
    print("==================================================================")
    try:
        test_1_connectivity_and_fallback()
        test_2_graph_persistence_and_hierarchy()
        test_3_idempotency_and_no_duplicates()
        test_4_investigation_and_video_isolation()
        test_5_query_layer_format()
        print("\n==================================================================")
        print(">>> ALL NEO4J PERSISTENCE & INTEGRATION TESTS PASSED (100%)! <<<")
        print("==================================================================")
    except AssertionError as e:
        print(f"\n[FAIL] Test assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
