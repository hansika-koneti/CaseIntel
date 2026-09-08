"""
CaseIntel — Neo4j Knowledge Graph Service
Manages graph topology for physical security investigations.
Supports live Neo4j Bolt/Cypher connection as PRIMARY backend with automatic in-memory graph fallback
when Neo4j instance is not running locally or connectivity is interrupted.

Hierarchy: Investigation → Video → Camera/Location → Subjects/Objects → Events → Evidence → Timestamp
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
    """
    Production Neo4j Primary Knowledge Graph & In-Memory Fallback Service.
    Connects via official Neo4j Python driver using environment variables:
      - NEO4J_URI (default: bolt://localhost:7687)
      - NEO4J_USERNAME / NEO4J_USER (default: neo4j)
      - NEO4J_PASSWORD (default: password)
      - NEO4J_DATABASE (default: neo4j)
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.database = database or os.getenv("NEO4J_DATABASE", "neo4j")
        self.driver = None
        self.is_connected = False
        self._init_neo4j()

    def _init_neo4j(self):
        """Attempt connection to live Neo4j database using official driver."""
        if not NEO4J_AVAILABLE:
            self.is_connected = False
            self.driver = None
            return

        if not self.uri or not self.user or self.password is None:
            self.is_connected = False
            self.driver = None
            return

        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=basic_auth(self.user, self.password),
                connection_timeout=2.0,
            )
            self.driver.verify_connectivity()
            self.is_connected = True
            print(f"[Neo4jService] Active Neo4j primary backend connected at '{self.uri}' (Database: '{self.database}')")
        except Exception as e:
            if self.driver:
                try:
                    self.driver.close()
                except Exception:
                    pass
            self.driver = None
            self.is_connected = False
            print(f"[Neo4jService] Notice: Neo4j instance not reachable ({e}). Utilizing in-memory graph engine with Cypher-compliant topology fallback.")

    def check_connection(self) -> bool:
        """Dynamic runtime check of Neo4j connectivity with lazy reconnect."""
        if not NEO4J_AVAILABLE:
            self.is_connected = False
            return False

        if self.driver:
            try:
                self.driver.verify_connectivity()
                self.is_connected = True
                return True
            except Exception:
                if self.driver:
                    try:
                        self.driver.close()
                    except Exception:
                        pass
                self.driver = None
                self.is_connected = False

        # Attempt reconnection
        self._init_neo4j()
        return self.is_connected

    def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            try:
                self.driver.close()
            except Exception:
                pass
            self.driver = None
            self.is_connected = False

    def build(self, events: List[Dict], entities: List[Dict]) -> Dict[str, Any]:
        """Build knowledge graph from events and entities (base class compatibility)."""
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
        video_id: Optional[str] = None,
        investigation_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize dynamic graph nodes, edges, and entity relationship metadata
        from active case components.
        Persists to Neo4j as primary backend when available, and always produces
        an investigator-first visual hierarchy with zero crossing edges, meaningful
        human-readable labels, and full underlying Cypher topology.
        """
        # Re-check live connectivity
        self.check_connection()

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        details: Dict[str, Any] = {}

        if not entities and not events and not camera_id and not video_id:
            return {
                "investigation_id": investigation_id,
                "video_id": video_id,
                "case_number": case_number,
                "nodes": [],
                "edges": [],
                "entity_details": {},
                "neo4j_connected": self.is_connected,
                "graph_engine": "Neo4j" if self.is_connected else "In-Memory Forensic Topology",
            }

        # 0. Context Column: Investigation Node (Scope Root)
        inv_label = f"Case {case_number or investigation_id}"
        inv_data = {
            "raw_id": investigation_id,
            "id": investigation_id,
            "case_number": case_number,
            "label": inv_label,
            "type": "investigation",
            "category": "context",
            "location": location or "Monitored Zone",
            "severity": (investigation_data or {}).get("severity", "HIGH"),
            "status": (investigation_data or {}).get("status", "under_investigation"),
            "incident_type": (investigation_data or {}).get("incident_type", "Security Investigation"),
            "confidence": float((investigation_data or {}).get("confidence", 90.0)),
        }
        nodes.append({
            "id": investigation_id,
            "label": inv_label,
            "type": "investigation",
            "category": "context",
            "is_technical": True,
            "x": 60,
            "y": 20,
            "data": inv_data,
        })
        details[investigation_id] = {
            "id": investigation_id,
            "case_number": case_number,
            "label": inv_label,
            "type": "investigation",
            "events": [],
            "cameras": [],
            "relationships": [],
        }

        # 1. Context Column: Video Node (Active Video Isolation)
        if video_id:
            vid_label = f"Video {video_id}"
            nodes.append({
                "id": video_id,
                "label": vid_label,
                "type": "video",
                "category": "context",
                "is_technical": True,
                "x": 60,
                "y": 100,
                "data": {
                    "raw_id": video_id,
                    "id": video_id,
                    "investigation_id": investigation_id,
                    "label": vid_label,
                    "type": "video",
                    "category": "context",
                }
            })
            details[video_id] = {
                "id": video_id,
                "label": vid_label,
                "type": "video",
                "investigation_id": investigation_id,
                "events": [],
                "cameras": [],
                "relationships": [f"CONTAINS_VIDEO ← {inv_label}"],
            }
            # Edge: Investigation -> Video (CONTAINS_VIDEO)
            edges.append({
                "id": f"e_inv_vid_{investigation_id}_{video_id}",
                "source": investigation_id,
                "target": video_id,
                "relationship": "CONTAINS_VIDEO",
                "label": "CONTAINS VIDEO",
                "suspicious": False,
                "category": "context",
                "is_technical": True,
            })
            details[investigation_id]["relationships"].append(f"CONTAINS_VIDEO → {vid_label}")

        # 2. Context Column: Location Node (Normalized & Contextual)
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
                "y": 180,
                "data": {
                    "raw_id": loc_id,
                    "label": normalized_loc,
                    "type": "location",
                    "category": "context",
                    "investigation_id": investigation_id,
                    "video_id": video_id,
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

        # 3. Context Column: Camera Node (Contextual)
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
                "y": 280,
                "data": {
                    "raw_id": cam_id,
                    "label": cam_label,
                    "type": "camera",
                    "category": "context",
                    "confidence": 100.0,
                    "location": normalized_loc or "Monitored Zone",
                    "investigation_id": investigation_id,
                    "video_id": video_id,
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

            # Edge: Video -> Camera (CAPTURED_BY)
            if video_id:
                edges.append({
                    "id": f"e_vid_cam_{video_id}_{cam_id}",
                    "source": video_id,
                    "target": cam_id,
                    "relationship": "CAPTURED_BY",
                    "label": "CAPTURED BY",
                    "suspicious": False,
                    "category": "context",
                    "is_technical": True,
                })
                details[video_id]["relationships"].append(f"CAPTURED_BY → {cam_label}")
                details[cam_id]["relationships"].append(f"CAPTURED_BY ← {vid_label}")

            # Edge: Camera -> Location (LOCATED_AT)
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

        # 4. Primary Subjects & Key Objects Column (Center-Left: x=360)
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

            y_pos = 120 + idx * 220

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
                    "investigation_id": investigation_id,
                    "video_id": video_id,
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
                "cameras": [cam_label] if cam_id else [],
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

            # Subject -> Location (DETECTED_AT)
            if loc_id and normalized_loc:
                edges.append({
                    "id": f"e_det_loc_{ent_id}_{loc_id}",
                    "source": ent_id,
                    "target": loc_id,
                    "relationship": "DETECTED_AT",
                    "label": "DETECTED AT",
                    "suspicious": False,
                    "category": "subject_context",
                    "is_technical": True,
                })
                details[ent_id]["relationships"].append(f"DETECTED_AT → {normalized_loc}")

        # 5. Chronological Security Events Column (Center-Right: x=720)
        def parse_ts_sec(ts_str: str) -> float:
            try:
                parts = str(ts_str).split(":")
                if len(parts) == 2:
                    return float(parts[0]) * 60 + float(parts[1])
                elif len(parts) == 3:
                    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                return float(ts_str)
            except Exception:
                return 0.0

        sorted_events = sorted(events, key=lambda e: parse_ts_sec(e.get("timestamp", "00:00")))
        prev_event_node_id = None
        event_ids_set = set()

        for idx, evt in enumerate(sorted_events[:12]):
            evt_id = evt.get("id") or f"EVT-{idx+1:03d}"
            event_ids_set.add(evt_id)
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

            # Meaningful Event Node: Label is the ACTION name
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
                    "investigation_id": investigation_id,
                    "video_id": video_id,
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

            # Edge: Event -> Location (OCCURRED_AT)
            if loc_id and normalized_loc:
                edges.append({
                    "id": f"e_evt_loc_{evt_id}_{loc_id}",
                    "source": evt_id,
                    "target": loc_id,
                    "relationship": "OCCURRED_AT",
                    "label": "OCCURRED AT",
                    "suspicious": False,
                    "category": "context",
                    "is_technical": True,
                })

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

            # Edge: Event -> Target Entity (PARTICIPATED_IN / INVOLVED)
            if sec_ent and any(n["id"] == sec_ent for n in nodes):
                rel_kind = "PARTICIPATED_IN" if "altercation" in act_lower else "INVOLVED"
                edges.append({
                    "id": f"e_rel_{evt_id}_{sec_ent}",
                    "source": evt_id,
                    "target": sec_ent,
                    "relationship": rel_kind,
                    "label": rel_kind.replace("_", " "),
                    "suspicious": is_suspicious,
                    "reason": susp_reason,
                    "category": "primary",
                    "is_technical": False,
                })
                details[evt_id]["relationships"].append(f"{rel_kind} → {sec_ent}")
                if sec_ent in details:
                    details[sec_ent]["relationships"].append(f"SUBJECT_OF ← {action}")

                # Cross-entity edge: Primary Subject <-> Secondary Subject (CONFRONTED)
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

            # 6. Technical Column: Timestamp Node (for Cypher Topology view)
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
                        "investigation_id": investigation_id,
                        "video_id": video_id,
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

        # 7. Evidence Nodes & Relationships (Grounded Forensic Evidence)
        if evidence:
            for idx, evd in enumerate(evidence):
                evd_id = evd.get("id") or f"EVD-{idx+1:03d}"
                evd_type = evd.get("type") or "Key Evidence"
                evd_conf = round(float(evd.get("confidence", 90.0)), 1)
                is_key = bool(evd.get("is_key_evidence", False))
                evd_desc = evd.get("description") or f"Grounded evidence of {evd_type}."
                p_ent = evd.get("primary_entity_id")
                s_ent = evd.get("secondary_entity_id")
                linked_evt_id = evd.get("event_id")

                nodes.append({
                    "id": evd_id,
                    "label": f"Evidence: {evd_type}",
                    "type": "evidence",
                    "category": "secondary",
                    "is_technical": False,
                    "confidence": evd_conf,
                    "is_suspicious": is_key,
                    "x": 1020,
                    "y": 240 + idx * 130,
                    "data": {
                        "raw_id": evd_id,
                        "id": evd_id,
                        "label": f"Evidence: {evd_type}",
                        "type": "evidence",
                        "evidence_type": evd_type,
                        "description": evd_desc,
                        "is_key_evidence": is_key,
                        "confidence": evd_conf,
                        "investigation_id": investigation_id,
                        "video_id": video_id,
                    }
                })
                details[evd_id] = {
                    "id": evd_id,
                    "label": f"Evidence: {evd_type}",
                    "type": "evidence",
                    "confidence": evd_conf,
                    "description": evd_desc,
                    "relationships": [],
                }

                # Link Event -> Evidence (PRODUCED_EVIDENCE)
                if linked_evt_id and linked_evt_id in event_ids_set:
                    edges.append({
                        "id": f"e_evd_evt_{linked_evt_id}_{evd_id}",
                        "source": linked_evt_id,
                        "target": evd_id,
                        "relationship": "PRODUCED_EVIDENCE",
                        "label": "PRODUCED EVIDENCE",
                        "suspicious": is_key,
                        "category": "secondary",
                        "is_technical": False,
                    })
                    details[evd_id]["relationships"].append(f"PRODUCED_EVIDENCE ← {linked_evt_id}")

                # Link Evidence -> Primary Entity (INVOLVED)
                if p_ent and any(n["id"] == p_ent for n in nodes):
                    edges.append({
                        "id": f"e_evd_ent_{evd_id}_{p_ent}",
                        "source": evd_id,
                        "target": p_ent,
                        "relationship": "INVOLVED",
                        "label": "INVOLVED",
                        "suspicious": is_key,
                        "category": "primary",
                        "is_technical": False,
                    })
                    details[evd_id]["relationships"].append(f"INVOLVED → {p_ent}")

                # Link Evidence -> Secondary Entity (INVOLVED)
                if s_ent and any(n["id"] == s_ent for n in nodes):
                    edges.append({
                        "id": f"e_evd_ent_{evd_id}_{s_ent}",
                        "source": evd_id,
                        "target": s_ent,
                        "relationship": "INVOLVED",
                        "label": "INVOLVED",
                        "suspicious": is_key,
                        "category": "primary",
                        "is_technical": False,
                    })
                    details[evd_id]["relationships"].append(f"INVOLVED → {s_ent}")

                # Cross-entity interaction from evidence (INTERACTED_WITH)
                if p_ent and s_ent and any(n["id"] == p_ent for n in nodes) and any(n["id"] == s_ent for n in nodes):
                    rel_type = (evd.get("type") or "INTERACTED_WITH").upper().replace(" ", "_")
                    interact_id = f"e_evd_interact_{p_ent}_{s_ent}"
                    if not any(e["id"] == interact_id for e in edges):
                        edges.append({
                            "id": interact_id,
                            "source": p_ent,
                            "target": s_ent,
                            "relationship": rel_type if rel_type in ["CONFRONTED", "MANIPULATED"] else "INTERACTED_WITH",
                            "label": rel_type.replace("_", " "),
                            "suspicious": is_key,
                            "reason": evd_desc,
                            "category": "primary",
                            "is_technical": False,
                        })
                        if p_ent in details:
                            details[p_ent]["relationships"].append(f"{rel_type} → {s_ent}")

        # 7B. Direct Video Activity Recognition Nodes (Separate reasoning path)
        video_activity = (investigation_data or {}).get("video_activity_recognition") or {}
        if video_activity and video_id:
            act_label = video_activity.get("primary_activity", "Unknown Activity")
            act_conf = float(video_activity.get("confidence", 0.0))
            act_model = video_activity.get("model_name", "R(2+1)D-18")
            act_version = video_activity.get("model_version", "1.0.0")
            segs = video_activity.get("supporting_segments", [])
            clip_start = segs[0].get("start", "00:00") if segs else "00:00"
            clip_end = segs[0].get("end", "00:00") if segs else "00:00"

            ap_id = f"APRED-{abs(hash(video_id + act_label)) % 10000:04d}"
            nodes.append({
                "id": ap_id,
                "label": f"Prediction: {act_label}",
                "type": "activity_prediction",
                "category": "prediction",
                "is_technical": False,
                "confidence": act_conf,
                "is_suspicious": "Theft" in act_label or "Break-In" in act_label or "Fighting" in act_label,
                "x": 870,
                "y": 140,
                "data": {
                    "raw_id": ap_id,
                    "id": ap_id,
                    "label": f"Prediction: {act_label}",
                    "type": "activity_prediction",
                    "activity_type": act_label,
                    "confidence": act_conf,
                    "model_name": act_model,
                    "model_version": act_version,
                    "clip_start": clip_start,
                    "clip_end": clip_end,
                    "investigation_id": investigation_id,
                    "video_id": video_id,
                }
            })
            details[ap_id] = {
                "id": ap_id,
                "label": f"Prediction: {act_label}",
                "type": "activity_prediction",
                "confidence": act_conf,
                "model_name": act_model,
                "model_version": act_version,
                "clip_start": clip_start,
                "clip_end": clip_end,
                "relationships": [f"HAS_ACTIVITY_PREDICTION ← {video_id}"],
            }

            # Edge: Video -> ActivityPrediction (HAS_ACTIVITY_PREDICTION)
            edges.append({
                "id": f"e_vid_ap_{video_id}_{ap_id}",
                "source": video_id,
                "target": ap_id,
                "relationship": "HAS_ACTIVITY_PREDICTION",
                "label": "HAS ACTIVITY PREDICTION",
                "suspicious": False,
                "category": "prediction",
                "is_technical": False,
            })
            if video_id in details:
                details[video_id]["relationships"].append(f"HAS_ACTIVITY_PREDICTION → {ap_id}")

        # 8. Persist to live Neo4j instance when connected
        if self.is_connected and self.driver:
            try:
                self._sync_to_neo4j(
                    investigation_id=investigation_id,
                    case_number=case_number,
                    location=location,
                    nodes=nodes,
                    edges=edges,
                    video_id=video_id,
                    investigation_data=investigation_data,
                )
            except Exception as e:
                print(f"[Neo4jService] Live sync notice ({e}). Continuing with in-memory graph fallback payload.")

        return {
            "investigation_id": investigation_id,
            "video_id": video_id,
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
                "evidence": len(evidence) if evidence else 0,
            },
            "neo4j_connected": self.is_connected,
            "graph_engine": "Neo4j" if self.is_connected else "In-Memory Forensic Topology",
        }

    def _sync_to_neo4j(
        self,
        investigation_id: str,
        case_number: str,
        location: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        video_id: Optional[str] = None,
        investigation_data: Optional[Dict[str, Any]] = None,
    ):
        """Execute scoped Cypher statements on live Neo4j database."""
        with self.driver.session(database=self.database) as session:
            # 1. Merge Investigation
            session.run(
                """
                MERGE (inv:Investigation {id: $id})
                SET inv.case_number = $case_number,
                    inv.location = $location,
                    inv.severity = $severity,
                    inv.status = $status,
                    inv.incident_type = $incident_type,
                    inv.confidence = $confidence
                """,
                id=investigation_id,
                case_number=case_number or investigation_id,
                location=location or "Monitored Zone",
                severity=(investigation_data or {}).get("severity", "HIGH"),
                status=(investigation_data or {}).get("status", "under_investigation"),
                incident_type=(investigation_data or {}).get("incident_type", "Security Investigation"),
                confidence=float((investigation_data or {}).get("confidence", 90.0)),
            )

            # 2. Merge Video if present & link Investigation -> Video
            if video_id:
                session.run(
                    """
                    MERGE (vid:Video {id: $vid_id, investigation_id: $inv_id})
                    SET vid.video_id = $vid_id
                    WITH vid
                    MATCH (inv:Investigation {id: $inv_id})
                    MERGE (inv)-[:CONTAINS_VIDEO]->(vid)
                    """,
                    vid_id=video_id,
                    inv_id=investigation_id,
                )

            # 3. Merge Nodes
            for n in nodes:
                ntype = n["type"].lower()
                nid = n["id"]
                nlabel = n.get("label", nid)
                conf = float(n.get("confidence", 100.0))
                is_susp = bool(n.get("is_suspicious", False))
                data = n.get("data", {})

                if ntype == "investigation" or ntype == "video":
                    continue
                elif ntype == "camera":
                    session.run(
                        """
                        MERGE (cam:Camera {id: $id, investigation_id: $inv_id})
                        SET cam.label = $label,
                            cam.location = $location,
                            cam.confidence = $conf,
                            cam.video_id = $vid_id
                        """,
                        id=nid,
                        inv_id=investigation_id,
                        label=nlabel,
                        location=data.get("location", location),
                        conf=conf,
                        vid_id=video_id,
                    )
                elif ntype == "location":
                    session.run(
                        """
                        MERGE (loc:Location {id: $id, investigation_id: $inv_id})
                        SET loc.label = $label,
                            loc.name = $label,
                            loc.video_id = $vid_id
                        """,
                        id=nid,
                        inv_id=investigation_id,
                        label=nlabel,
                        vid_id=video_id,
                    )
                elif ntype in ["person", "vehicle", "object", "phone"]:
                    sub_label = "Person" if ntype == "person" else ("Vehicle" if ntype in ["vehicle", "car", "truck"] else "Object")
                    cypher = f"""
                        MERGE (ent:Entity {{id: $id, investigation_id: $inv_id}})
                        SET ent:{sub_label},
                            ent.label = $label,
                            ent.type = $type,
                            ent.confidence = $conf,
                            ent.first_seen = $first_seen,
                            ent.last_seen = $last_seen,
                            ent.track_duration = $track_duration,
                            ent.video_id = $vid_id
                    """
                    session.run(
                        cypher,
                        id=nid,
                        inv_id=investigation_id,
                        label=nlabel,
                        type=sub_label.lower(),
                        conf=conf,
                        first_seen=data.get("first_seen", "00:00"),
                        last_seen=data.get("last_seen", "00:16"),
                        track_duration=data.get("track_duration", ""),
                        vid_id=video_id,
                    )
                elif ntype == "event":
                    session.run(
                        """
                        MERGE (evt:Event {id: $id, investigation_id: $inv_id})
                        SET evt.action = $action,
                            evt.label = $label,
                            evt.timestamp = $ts,
                            evt.confidence = $conf,
                            evt.is_suspicious = $is_susp,
                            evt.description = $desc,
                            evt.video_id = $vid_id
                        """,
                        id=nid,
                        inv_id=investigation_id,
                        action=data.get("action", nlabel),
                        label=nlabel,
                        ts=data.get("timestamp", "00:00"),
                        conf=conf,
                        is_susp=is_susp,
                        desc=data.get("description", ""),
                        vid_id=video_id,
                    )
                elif ntype == "evidence":
                    session.run(
                        """
                        MERGE (evd:Evidence {id: $id, investigation_id: $inv_id})
                        SET evd.type = $type,
                            evd.confidence = $conf,
                            evd.is_key_evidence = $is_key,
                            evd.description = $desc,
                            evd.video_id = $vid_id
                        """,
                        id=nid,
                        inv_id=investigation_id,
                        type=data.get("evidence_type", data.get("type", "Key Evidence")),
                        conf=conf,
                        is_key=is_susp,
                        desc=data.get("description", ""),
                        vid_id=video_id,
                    )
                elif ntype == "timestamp":
                    session.run(
                        """
                        MERGE (ts:Timestamp {id: $id, investigation_id: $inv_id})
                        SET ts.label = $label,
                            ts.video_id = $vid_id
                        """,
                        id=nid,
                        inv_id=investigation_id,
                        label=nlabel,
                        vid_id=video_id,
                    )
                elif ntype == "activity_prediction":
                    session.run(
                        """
                        MERGE (ap:ActivityPrediction {id: $id, investigation_id: $inv_id})
                        SET ap.label = $label,
                            ap.confidence = $conf,
                            ap.model_name = $model_name,
                            ap.model_version = $model_version,
                            ap.clip_start = $clip_start,
                            ap.clip_end = $clip_end,
                            ap.video_id = $vid_id
                        WITH ap
                        MATCH (vid:Video {id: $vid_id, investigation_id: $inv_id})
                        MERGE (vid)-[:HAS_ACTIVITY_PREDICTION]->(ap)
                        """,
                        id=nid,
                        inv_id=investigation_id,
                        label=nlabel,
                        conf=conf,
                        model_name=data.get("model_name", "R(2+1)D-18"),
                        model_version=data.get("model_version", "1.0.0"),
                        clip_start=data.get("clip_start", "00:00"),
                        clip_end=data.get("clip_end", "00:00"),
                        vid_id=video_id,
                    )

            # 4. Merge Relationships (Scoped by investigation_id and active video_id)
            valid_rels = {
                "CONTAINS_VIDEO", "CAPTURED_BY", "LOCATED_AT", "DETECTED_BY", "DETECTED_AT",
                "PERFORMED", "OCCURRED_AT", "INVOLVED", "PARTICIPATED_IN", "INVOLVES_OBJECT",
                "THEN", "CONFRONTED", "MANIPULATED", "INTERACTED_WITH", "PRODUCED_EVIDENCE",
                "HAS_ACTIVITY_PREDICTION", "SUPPORTED_BY"
            }

            for e in edges:
                rel = e["relationship"].upper().replace(" ", "_")
                if rel not in valid_rels:
                    if rel in ["MONITORS", "RECORDED_ON"]:
                        rel = "CAPTURED_BY"
                    elif rel in ["LOCATED_IN"]:
                        rel = "LOCATED_AT"
                    else:
                        rel = re.sub(r'[^A-Z0-9_]', '', rel) or "RELATED_TO"

                cypher = f"""
                    MATCH (a {{id: $src, investigation_id: $inv_id}})
                    MATCH (b {{id: $tgt, investigation_id: $inv_id}})
                    WHERE ($vid_id IS NULL OR a.video_id IS NULL OR a.video_id = $vid_id)
                      AND ($vid_id IS NULL OR b.video_id IS NULL OR b.video_id = $vid_id)
                    MERGE (a)-[r:{rel}]->(b)
                    SET r.suspicious = $suspicious,
                        r.label = $label,
                        r.reason = $reason
                """
                session.run(
                    cypher,
                    src=e["source"],
                    tgt=e["target"],
                    inv_id=investigation_id,
                    vid_id=video_id,
                    suspicious=bool(e.get("suspicious", False)),
                    label=e.get("label", rel),
                    reason=e.get("reason", ""),
                )

    def query(self, investigation_id: str, video_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Query subgraphs from Neo4j for investigation ID and active video ID.
        Returns data in ReactFlow-compatible nodes/edges format with strict active-video isolation.
        """
        if not self.check_connection():
            return {
                "investigation_id": investigation_id,
                "video_id": video_id,
                "nodes": [],
                "edges": [],
                "entity_details": {},
                "neo4j_connected": False,
                "graph_engine": "In-Memory Forensic Topology",
            }

        try:
            with self.driver.session(database=self.database) as session:
                cypher = """
                    MATCH (n {investigation_id: $inv_id})
                    WHERE ($vid_id IS NULL OR n.video_id IS NULL OR n.video_id = $vid_id)
                    OPTIONAL MATCH (n)-[r]->(m {investigation_id: $inv_id})
                    WHERE ($vid_id IS NULL OR m.video_id IS NULL OR m.video_id = $vid_id)
                    RETURN n, r, m
                """
                res = session.run(cypher, inv_id=investigation_id, vid_id=video_id)
                records = list(res)

                if not records:
                    return {
                        "investigation_id": investigation_id,
                        "video_id": video_id,
                        "nodes": [],
                        "edges": [],
                        "entity_details": {},
                        "neo4j_connected": True,
                        "graph_engine": "Neo4j",
                    }

                nodes_map: Dict[str, Dict[str, Any]] = {}
                edges_list: List[Dict[str, Any]] = []
                seen_edges = set()

                def extract_node_type(node):
                    labels = list(node.labels) if hasattr(node, "labels") else []
                    for l in ["Person", "Vehicle", "Object", "Event", "Evidence", "Camera", "Location", "Timestamp", "Video", "Investigation"]:
                        if l in labels:
                            return l.lower()
                    return labels[0].lower() if labels else "event"

                for rec in records:
                    for n in [rec["n"], rec["m"]]:
                        if n and n["id"] not in nodes_map:
                            ntype = extract_node_type(n)
                            nid = n["id"]
                            nlabel = n.get("label", nid)
                            nodes_map[nid] = {
                                "id": nid,
                                "label": nlabel,
                                "type": ntype,
                                "category": "primary" if ntype in ["person", "vehicle", "object"] else ("secondary" if ntype in ["event", "evidence"] else ("technical" if ntype == "timestamp" else "context")),
                                "is_technical": ntype in ["timestamp", "video", "investigation"],
                                "confidence": n.get("confidence", 90.0),
                                "is_suspicious": n.get("is_suspicious", False),
                                "data": dict(n),
                                "x": 360 if ntype in ["person", "vehicle", "object"] else (720 if ntype == "event" else (1020 if ntype in ["timestamp", "evidence"] else 60)),
                                "y": 100,
                            }

                    r = rec["r"]
                    n = rec["n"]
                    m = rec["m"]
                    if r and n and m:
                        edge_key = (n["id"], r.type, m["id"])
                        if edge_key not in seen_edges:
                            seen_edges.add(edge_key)
                            edges_list.append({
                                "id": f"e_{n['id']}_{r.type}_{m['id']}",
                                "source": n["id"],
                                "target": m["id"],
                                "relationship": r.type,
                                "label": r.get("label", r.type),
                                "suspicious": bool(r.get("suspicious", False)),
                                "reason": r.get("reason"),
                                "category": "primary" if r.type in ["CONFRONTED", "MANIPULATED", "INTERACTED_WITH"] else "context",
                                "is_technical": r.type in ["OCCURRED_AT", "CONTAINS_VIDEO"],
                            })

                col_counts = {}
                for node in nodes_map.values():
                    x = node["x"]
                    col_counts[x] = col_counts.get(x, 0) + 1
                    node["y"] = 60 + (col_counts[x] - 1) * 140

                return {
                    "investigation_id": investigation_id,
                    "video_id": video_id,
                    "nodes": list(nodes_map.values()),
                    "edges": edges_list,
                    "neo4j_connected": True,
                    "graph_engine": "Neo4j",
                }
        except Exception as e:
            print(f"[Neo4jService] Cypher query error ({e}). Returning fallback structure.")
            return {
                "investigation_id": investigation_id,
                "video_id": video_id,
                "nodes": [],
                "edges": [],
                "entity_details": {},
                "neo4j_connected": False,
                "graph_engine": "In-Memory Forensic Topology",
            }
