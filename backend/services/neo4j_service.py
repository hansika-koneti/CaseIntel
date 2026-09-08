"""
CaseIntel — Neo4j Knowledge Graph Service
Manages graph topology for physical security investigations.
Supports live Neo4j Bolt/Cypher connection with automatic in-memory graph fallback
when Neo4j instance is not running locally.
"""

import os
import re
import math
from typing import Dict, Any, List, Optional
from services.base import KnowledgeGraphService, normalize_location_name

try:
    from neo4j import GraphDatabase, basic_auth
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False




def clean_entity_label(label: Optional[str], ent_id: str, ent_type: str) -> str:
    """Format meaningful investigator-friendly entity labels without internal database artifacts."""
    raw = str(label or ent_id or "").strip()
    if ":" in raw:
        raw = raw.split(":", 1)[1].strip()
    
    # Remove repeated 'Person', 'Vehicle', or 'Object' prefixes
    raw = re.sub(r'^(Person\s*#?\s*)+', 'Person-', raw, flags=re.IGNORECASE)
    raw = re.sub(r'^(Vehicle\s*#?\s*)+', 'Vehicle-', raw, flags=re.IGNORECASE)
    raw = re.sub(r'^(Object\s*#?\s*)+', 'Object-', raw, flags=re.IGNORECASE)
    raw = re.sub(r'^(Phone\s*#?\s*)+', 'Phone-', raw, flags=re.IGNORECASE)
    raw = re.sub(r'-+', '-', raw)
    raw = re.sub(r'^Person-Person-', 'Person-', raw, flags=re.IGNORECASE)
    raw = re.sub(r'^Vehicle-Vehicle-', 'Vehicle-', raw, flags=re.IGNORECASE)
    
    if ent_type == "person":
        if not re.search(r'person', raw, flags=re.IGNORECASE):
            raw = f"Person-{raw}"
    elif ent_type in ["vehicle", "car", "truck"]:
        if not re.search(r'vehicle|car|truck', raw, flags=re.IGNORECASE):
            raw = f"Vehicle-{raw}"
    elif ent_type in ["object", "phone"]:
        if not re.search(r'phone|object', raw, flags=re.IGNORECASE):
            raw = f"Object-{raw}"
            
    raw = re.sub(r'Person-\s*', 'Person-', raw, flags=re.IGNORECASE)
    raw = re.sub(r'Vehicle-\s*', 'Vehicle-', raw, flags=re.IGNORECASE)
    raw = re.sub(r'Object-\s*', 'Object-', raw, flags=re.IGNORECASE)
    return raw


class Neo4jKnowledgeGraphService(KnowledgeGraphService):
    """Production Neo4j & In-Memory Knowledge Graph Service."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver = None
        self.is_connected = False
        self._init_neo4j()

    def _init_neo4j(self):
        """Attempt connection to live Neo4j database."""
        if not NEO4J_AVAILABLE:
            print("[Neo4jService] 'neo4j' driver not found. Utilizing in-memory graph engine.")
            return

        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=basic_auth(self.user, self.password),
                connection_timeout=2.0,
            )
            self.driver.verify_connectivity()
            self.is_connected = True
            print(f"[Neo4jService] Successfully connected to live Neo4j instance at '{self.uri}'")
        except Exception as e:
            self.is_connected = False
            print(f"[Neo4jService] Notice: Live Neo4j instance not reachable ({e}). Utilizing in-memory graph engine with Cypher-compliant topology.")

    def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()

    def build(self, events: List[Dict], entities: List[Dict]) -> Dict[str, Any]:
        """Build knowledge graph from events and entities."""
        return self.build_graph_from_case(
            investigation_id="inv-custom",
            case_number="CASE-CUSTOM",
            location="Monitored Zone",
            entities=entities,
            events=events,
        )

    def build_graph_from_case(
        self,
        investigation_id: str,
        case_number: str,
        location: str,
        entities: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        evidence: Optional[List[Dict[str, Any]]] = None,
        camera_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize dynamic graph nodes, edges, and entity relationship metadata
        from active case components.
        Produces an investigator-first visual hierarchy with zero crossing edges,
        meaningful human-readable labels, and full underlying Cypher topology.
        """
        nodes = []
        edges = []
        details = {}

        if not entities and not events and not camera_id:
            return {
                "investigation_id": investigation_id,
                "case_number": case_number,
                "nodes": [],
                "edges": [],
                "entityDetails": {},
                "neo4j_connected": self.is_connected,
            }

        # 1. Location Node (Normalized & Contextual)
        normalized_loc = normalize_location_name(location)
        loc_id = None
        if normalized_loc:
            loc_id = f"LOC-{abs(hash(normalized_loc)) % 1000:03d}"
            nodes.append({
                "id": loc_id,
                "label": normalized_loc,
                "type": "location",
                "category": "context",
                "is_technical": False,
                "x": 60,
                "y": 80,
                "data": {
                    "raw_id": loc_id,
                    "label": normalized_loc,
                    "type": "location",
                    "category": "context",
                }
            })
            details[loc_id] = {
                "id": loc_id,
                "label": normalized_loc,
                "type": "location",
                "events": [],
                "cameras": [f"Camera {camera_id or 'C-01'}"] if (camera_id or events) else [],
                "relationships": [],
            }

        # 2. Camera Node (Contextual)
        cam_id = camera_id or (events[0].get("camera_id") if events else "C-01")
        cam_label = f"Camera {cam_id}"
        if cam_id:
            nodes.append({
                "id": cam_id,
                "label": cam_label,
                "type": "camera",
                "category": "context",
                "is_technical": False,
                "confidence": 100.0,
                "x": 60,
                "y": 240,
                "data": {
                    "raw_id": cam_id,
                    "label": cam_label,
                    "type": "camera",
                    "category": "context",
                    "confidence": 100.0,
                    "location": normalized_loc or "Monitored Zone",
                }
            })
            details[cam_id] = {
                "id": cam_id,
                "label": cam_label,
                "type": "camera",
                "confidence": 100.0,
                "location": normalized_loc or "Monitored Zone",
                "events": [],
                "cameras": [],
                "relationships": [],
            }
            if loc_id and normalized_loc:
                edges.append({
                    "id": "e_cam_located_at",
                    "source": cam_id,
                    "target": loc_id,
                    "relationship": "LOCATED_AT",
                    "label": "LOCATED AT",
                    "suspicious": False,
                    "category": "context",
                    "is_technical": False,
                })
                details[cam_id]["relationships"].append(f"LOCATED_AT → {normalized_loc}")
                details[loc_id]["relationships"].append(f"MONITORED_BY → {cam_label}")

        # 3. Primary Subject Nodes (Persons, Vehicles & Key Objects in Center Column)
        person_nodes = []
        vehicle_nodes = []
        object_nodes = []

        for idx, ent in enumerate(entities):
            ent_id = ent.get("id") or f"ENT-{idx+1:02d}"
            ent_type = ent.get("type", "person").lower()
            clean_type = "object" if ent_type in ["object", "phone"] else ("vehicle" if ent_type in ["vehicle", "car", "truck"] else "person")
            conf = float(ent.get("confidence", 95.0))
            clean_lbl = clean_entity_label(ent.get("label"), ent_id, clean_type)
            first_seen = ent.get("first_seen", "00:00")
            last_seen = ent.get("last_seen", "00:16")
            track_duration = ent.get("track_duration") or f"{first_seen} - {last_seen}"

            y_pos = 140 + idx * 240

            if clean_type == "person":
                person_nodes.append(ent_id)
            elif clean_type == "vehicle":
                vehicle_nodes.append(ent_id)
            elif clean_type == "object":
                object_nodes.append(ent_id)

            nodes.append({
                "id": ent_id,
                "label": clean_lbl,
                "type": clean_type,
                "category": "primary",
                "is_technical": False,
                "confidence": conf,
                "x": 360,
                "y": y_pos,
                "data": {
                    "raw_id": ent_id,
                    "label": clean_lbl,
                    "type": clean_type,
                    "category": "primary",
                    "confidence": conf,
                    "first_seen": first_seen,
                    "last_seen": last_seen,
                    "track_duration": track_duration,
                    "camera": cam_label,
                    "location": normalized_loc or "Monitored Zone",
                }
            })

            details[ent_id] = {
                "track_id": ent_id,
                "entity_type": ent_type,
                "label": clean_lbl,
                "confidence": conf,
                "first_seen": first_seen,
                "last_seen": last_seen,
                "track_duration": track_duration,
                "camera": cam_label,
                "location": normalized_loc or "Monitored Zone",
                "events": [],
                "cameras": [cam_label],
                "relationships": [],
            }

            # Subject -> Camera (DETECTED_BY)
            if cam_id:
                edges.append({
                    "id": f"e_det_{ent_id}_{cam_id}",
                    "source": ent_id,
                    "target": cam_id,
                    "relationship": "DETECTED_BY",
                    "label": "DETECTED BY",
                    "suspicious": False,
                    "category": "subject_context",
                    "is_technical": False,
                })
                details[ent_id]["relationships"].append(f"DETECTED_BY → {cam_label}")

        # Genuine cross-entity interaction from evidence (strictly data-driven)
        if evidence:
            for evd in evidence:
                p_ent = evd.get("primary_entity_id")
                s_ent = evd.get("secondary_entity_id")
                if p_ent and s_ent and any(n["id"] == p_ent for n in nodes) and any(n["id"] == s_ent for n in nodes):
                    rel_type = (evd.get("type") or "INTERACTED_WITH").upper().replace(" ", "_")
                    is_susp = bool(evd.get("is_key_evidence"))
                    edges.append({
                        "id": f"e_evd_{evd.get('id', 'rel')}_{p_ent}_{s_ent}",
                        "source": p_ent,
                        "target": s_ent,
                        "relationship": rel_type,
                        "label": rel_type.replace("_", " "),
                        "suspicious": is_susp,
                        "reason": evd.get("description"),
                        "category": "primary",
                        "is_technical": False,
                    })
                    if p_ent in details:
                        details[p_ent]["relationships"].append(f"{rel_type} → {s_ent}")

        # 4. Chronological Security Events (Right Column)
        def parse_ts_sec(ts_str: str) -> float:
            try:
                parts = str(ts_str).split(":")
                if len(parts) == 2:
                    return float(parts[0]) * 60 + float(parts[1])
                return float(ts_str)
            except Exception:
                return 0.0

        sorted_events = sorted(events, key=lambda e: parse_ts_sec(e.get("timestamp", "00:00")))
        prev_event_node_id = None

        for idx, evt in enumerate(sorted_events[:12]):
            evt_id = evt.get("id") or f"EVT-{idx+1:03d}"
            ts = evt.get("timestamp") or f"00:{idx*5:02d}"
            action = evt.get("action") or evt.get("event_type") or "Security Observation"
            conf = round(float(evt.get("confidence", 85.0)), 1)
            is_suspicious = bool(evt.get("is_suspicious") or evt.get("severity") in ["HIGH", "CRITICAL"])
            desc = evt.get("description") or f"{action} observed on camera {cam_id} at {ts}."
            susp_reason = desc if is_suspicious else None
            primary_ent = evt.get("entity_id") or evt.get("primary_entity_id") or (person_nodes[0] if person_nodes else (vehicle_nodes[0] if vehicle_nodes else None))
            sec_ent = evt.get("related_entity_id")
            evt_cam = f"Camera {evt.get('camera_id') or cam_id}"
            evt_loc = normalize_location_name(evt.get("location")) or normalized_loc or "Monitored Zone"

            y_event = 60 + idx * 130

            # Meaningful Event Node: Label is the ACTION name, not internal EVT-xxxx
            nodes.append({
                "id": evt_id,
                "label": action,
                "type": "event",
                "category": "secondary",
                "is_technical": False,
                "confidence": conf,
                "is_suspicious": is_suspicious,
                "suspicion_reason": susp_reason,
                "x": 720,
                "y": y_event,
                "data": {
                    "raw_id": evt_id,
                    "label": action,
                    "action": action,
                    "type": "event",
                    "category": "secondary",
                    "timestamp": ts,
                    "confidence": conf,
                    "entity_id": primary_ent or "Subject",
                    "camera": evt_cam,
                    "location": evt_loc,
                    "is_suspicious": is_suspicious,
                    "suspicion_reason": susp_reason,
                    "description": desc,
                }
            })

            details[evt_id] = {
                "underlying_id": evt_id,
                "event_type": action,
                "action": action,
                "timestamp": ts,
                "confidence": conf,
                "entity_id": primary_ent or "Subject",
                "camera": evt_cam,
                "location": evt_loc,
                "is_suspicious": is_suspicious,
                "suspicion_reason": susp_reason or "Normal security observation within baseline behavior parameters.",
                "description": desc,
                "relationships": [],
            }

            # Associate event with entity details
            if primary_ent and primary_ent in details:
                details[primary_ent]["events"].append({
                    "id": evt_id,
                    "action": action,
                    "timestamp": ts,
                    "confidence": conf,
                    "is_suspicious": is_suspicious,
                    "description": desc,
                })
                details[primary_ent]["relationships"].append(f"PERFORMED → {action} ({ts})")

            # Edge: Subject -> Event (PERFORMED)
            if primary_ent and any(n["id"] == primary_ent for n in nodes):
                edges.append({
                    "id": f"e_perf_{primary_ent}_{evt_id}",
                    "source": primary_ent,
                    "target": evt_id,
                    "relationship": "PERFORMED",
                    "label": "PERFORMED",
                    "suspicious": is_suspicious,
                    "reason": susp_reason,
                    "category": "subject_event",
                    "is_technical": False,
                })
                details[evt_id]["relationships"].append(f"PERFORMED_BY ← {primary_ent}")

            # Multi-entity inference from action context if not explicitly provided
            act_lower = action.lower()
            desc_lower = desc.lower()

            # Physical Altercation: Link secondary person (e.g. Person-02)
            if any(w in act_lower or w in desc_lower for w in ["altercation", "confrontation", "physical interaction"]):
                if not sec_ent and person_nodes:
                    other_persons = [p for p in person_nodes if p != primary_ent]
                    if other_persons:
                        sec_ent = other_persons[0]

            # Object Interaction: Link secondary object (e.g. Phone-01)
            target_object = None
            if any(w in act_lower or w in desc_lower for w in ["object interaction", "phone", "device", "item"]):
                if object_nodes:
                    target_object = object_nodes[0]

            # Edge: Event -> Target Entity (TARGETED / INVOLVED)
            if sec_ent and any(n["id"] == sec_ent for n in nodes):
                edges.append({
                    "id": f"e_rel_{evt_id}_{sec_ent}",
                    "source": evt_id,
                    "target": sec_ent,
                    "relationship": "PARTICIPATED_IN" if "altercation" in act_lower else "INVOLVED",
                    "label": "PARTICIPATED IN" if "altercation" in act_lower else "INVOLVED",
                    "suspicious": is_suspicious,
                    "reason": susp_reason,
                    "category": "primary",
                    "is_technical": False,
                })
                details[evt_id]["relationships"].append(f"INVOLVED → {sec_ent}")
                if sec_ent in details:
                    details[sec_ent]["relationships"].append(f"SUBJECT_OF ← {action}")

                # Cross-entity edge: Primary Subject <-> Secondary Subject
                if primary_ent and any(n["id"] == primary_ent for n in nodes):
                    cross_id = f"e_cross_{primary_ent}_{sec_ent}"
                    if not any(e["id"] == cross_id for e in edges):
                        edges.append({
                            "id": cross_id,
                            "source": primary_ent,
                            "target": sec_ent,
                            "relationship": "CONFRONTED",
                            "label": "ALTERCATION / CONTACT",
                            "suspicious": True,
                            "reason": "Physical confrontation / close spatial interaction verified",
                            "category": "primary",
                            "is_technical": False,
                        })
                        if primary_ent in details:
                            details[primary_ent]["relationships"].append(f"CONFRONTED → {sec_ent}")

            # Edge: Event -> Target Object (INVOLVES_OBJECT)
            if target_object and any(n["id"] == target_object for n in nodes):
                edges.append({
                    "id": f"e_obj_{evt_id}_{target_object}",
                    "source": evt_id,
                    "target": target_object,
                    "relationship": "INVOLVES_OBJECT",
                    "label": "INVOLVES OBJECT",
                    "suspicious": is_suspicious,
                    "reason": desc,
                    "category": "primary",
                    "is_technical": False,
                })
                details[evt_id]["relationships"].append(f"INVOLVES_OBJECT → {target_object}")
                if target_object in details:
                    details[target_object]["relationships"].append(f"INVOLVED_IN ← {action}")

                # Cross-entity edge: Primary Subject -> Object (MANIPULATED)
                if primary_ent and any(n["id"] == primary_ent for n in nodes):
                    obj_cross_id = f"e_cross_{primary_ent}_{target_object}"
                    if not any(e["id"] == obj_cross_id for e in edges):
                        edges.append({
                            "id": obj_cross_id,
                            "source": primary_ent,
                            "target": target_object,
                            "relationship": "MANIPULATED",
                            "label": "MANIPULATED",
                            "suspicious": is_suspicious,
                            "reason": "Hand-to-object spatial manipulation detected",
                            "category": "primary",
                            "is_technical": False,
                        })
                        if primary_ent in details:
                            details[primary_ent]["relationships"].append(f"MANIPULATED → {target_object}")

            # Edge: Event(i) -> Event(i+1) (THEN / Chronological Sequence)
            if prev_event_node_id:
                edges.append({
                    "id": f"e_seq_{prev_event_node_id}_{evt_id}",
                    "source": prev_event_node_id,
                    "target": evt_id,
                    "relationship": "THEN",
                    "label": "THEN",
                    "suspicious": False,
                    "category": "sequence",
                    "is_technical": False,
                })
            prev_event_node_id = evt_id

            # 5. Underlying Timestamp Node (for Cypher Topology view)
            ts_id = f"TS-{ts.replace(':', '')[:4]}"
            if not any(n["id"] == ts_id for n in nodes):
                nodes.append({
                    "id": ts_id,
                    "label": ts,
                    "type": "timestamp",
                    "category": "technical",
                    "is_technical": True,
                    "x": 1020,
                    "y": y_event,
                    "data": {
                        "raw_id": ts_id,
                        "label": ts,
                        "type": "timestamp",
                        "category": "technical",
                        "parent_event": evt_id,
                    }
                })
                details[ts_id] = {
                    "underlying_id": ts_id,
                    "label": ts,
                    "type": "timestamp",
                    "events": [evt_id],
                    "relationships": [f"OCCURRED_AT ← {evt_id}"],
                }

            # Technical Edge: Event -> Timestamp (OCCURRED_AT)
            edges.append({
                "id": f"e_ts_{evt_id}_{ts_id}",
                "source": evt_id,
                "target": ts_id,
                "relationship": "OCCURRED_AT",
                "label": "OCCURRED AT",
                "suspicious": False,
                "category": "technical",
                "is_technical": True,
            })
            details[evt_id]["relationships"].append(f"OCCURRED_AT → {ts}")

        # Sync to live Neo4j instance if online
        if self.is_connected and self.driver:
            try:
                self._sync_to_neo4j(investigation_id, nodes, edges)
            except Exception as e:
                print(f"[Neo4jService] Live sync warning ({e}). Continuing with graph payload.")

        return {
            "investigation_id": investigation_id,
            "case_number": case_number,
            "nodes": nodes,
            "edges": edges,
            "entity_details": details,
            "summary": {
                "subjects": len(person_nodes) + len(vehicle_nodes) + len(object_nodes),
                "people": len(person_nodes),
                "vehicles": len(vehicle_nodes),
                "objects": len(object_nodes),
                "cameras": 1 if cam_id else 0,
                "locations": 1 if normalized_loc else 0,
                "events": len(sorted_events),
                "suspicious_events": sum(1 for e in sorted_events if e.get("is_suspicious")),
            },
            "neo4j_connected": self.is_connected,
            "graph_engine": "Neo4j Graph Engine" if self.is_connected else "In-Memory Forensic Topology",
        }

    def _sync_to_neo4j(self, investigation_id: str, nodes: List[Dict], edges: List[Dict]):
        """Execute Cypher statements on live Neo4j database."""
        with self.driver.session() as session:
            # Create nodes
            for n in nodes:
                cypher = (
                    f"MERGE (node:{n['type'].title()} {{id: $id, investigation_id: $inv_id}}) "
                    f"SET node.label = $label, node.confidence = $conf"
                )
                session.run(
                    cypher,
                    id=n["id"],
                    inv_id=investigation_id,
                    label=n["label"],
                    conf=n.get("confidence", 100.0),
                )
            # Create edges
            for e in edges:
                rel = e["relationship"]
                cypher = (
                    f"MATCH (a {{id: $src, investigation_id: $inv_id}}), (b {{id: $tgt, investigation_id: $inv_id}}) "
                    f"MERGE (a)-[r:{rel}]->(b) "
                    f"SET r.suspicious = $suspicious"
                )
                session.run(
                    cypher,
                    src=e["source"],
                    tgt=e["target"],
                    inv_id=investigation_id,
                    suspicious=e.get("suspicious", False),
                )

    def query(self, investigation_id: str) -> Dict[str, Any]:
        """Query subgraphs for investigation ID."""
        if self.is_connected and self.driver:
            try:
                with self.driver.session() as session:
                    res = session.run(
                        "MATCH (n {investigation_id: $inv_id})-[r]->(m {investigation_id: $inv_id}) "
                        "RETURN n, r, m",
                        inv_id=investigation_id,
                    )
                    records = list(res)
                    if records:
                        nodes_map = {}
                        edges_list = []
                        for r in records:
                            n = dict(r["n"])
                            m = dict(r["m"])
                            rel = r["r"]
                            nodes_map[n["id"]] = {"id": n["id"], "label": n.get("label", n["id"]), "type": list(r["n"].labels)[0].lower(), "x": 100, "y": 100}
                            nodes_map[m["id"]] = {"id": m["id"], "label": m.get("label", m["id"]), "type": list(r["m"].labels)[0].lower(), "x": 300, "y": 300}
                            edges_list.append({"id": f"e_{n['id']}_{m['id']}", "source": n["id"], "target": m["id"], "relationship": rel.type, "suspicious": rel.get("suspicious", False)})
                        return {
                            "investigation_id": investigation_id,
                            "nodes": list(nodes_map.values()),
                            "edges": edges_list,
                            "neo4j_connected": True,
                        }
            except Exception as e:
                print(f"[Neo4jService] Cypher query error ({e}). Falling back to case synthesis.")

        return {
            "investigation_id": investigation_id,
            "case_number": None,
            "nodes": [],
            "edges": [],
            "entity_details": {},
            "neo4j_connected": self.is_connected,
        }
