import os
import math
from typing import List, Dict, Any
from services.yolo_service import YOLOv11DetectorService

video_path = os.path.join("backend", "test_footage", "ucf_crime_stealing002.mp4")
yolo = YOLOv11DetectorService()

def refine_and_merge_tracks(raw_tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Step 1: Prune transient noise / false-positive detector glitches
    filtered = []
    for t in raw_tracks:
        obs = t.get("observations_count", len(t.get("trajectory", [])))
        dur = round(t.get("last_seen_sec", 0.0) - t.get("first_seen_sec", 0.0), 2)
        avg_conf = t.get("avg_confidence", 0.0)
        cls_name = str(t.get("class", "")).lower()

        # Reject ultra-short transient person tracks (< 3 observations or duration < 0.3s)
        if cls_name == "person":
            if (obs < 3 and dur < 0.3) or (obs <= 2 and avg_conf < 0.50):
                print(f"  [PRUNED NOISE PERSON] Track {t.get('track_id')} (obs={obs}, dur={dur}s, conf={avg_conf})")
                continue

        # Reject transient object/baggage glitches (< 5 observations or duration < 1.0s with conf < 0.70)
        if cls_name in ["backpack", "handbag", "suitcase", "cell phone", "laptop"]:
            if obs < 5 or dur < 1.0:
                print(f"  [PRUNED TRANSIENT OBJECT] Track {t.get('track_id')} {cls_name} (obs={obs}, dur={dur}s, conf={avg_conf})")
                continue

        # Reject transient vehicle glitches
        if cls_name in ["car", "truck", "bus", "motorcycle", "bicycle"]:
            if obs < 3 and dur < 0.3 and avg_conf < 0.50:
                print(f"  [PRUNED TRANSIENT VEHICLE] Track {t.get('track_id')} (obs={obs}, dur={dur}s, conf={avg_conf})")
                continue

        filtered.append(t)

    # Step 2: Separate persons vs non-persons
    persons = [t for t in filtered if str(t.get("class", "")).lower() == "person"]
    others = [t for t in filtered if str(t.get("class", "")).lower() != "person"]

    # Sort persons chronologically
    persons.sort(key=lambda x: (x.get("first_seen_sec", 0.0), -(x.get("last_seen_sec", 0.0) - x.get("first_seen_sec", 0.0))))

    merged_persons: List[Dict[str, Any]] = []

    for cand in persons:
        cand_first = cand.get("first_seen_sec", 0.0)
        cand_last = cand.get("last_seen_sec", 0.0)
        cand_traj = cand.get("trajectory", [])
        c_start = cand_traj[0] if cand_traj else {"x": 0.0, "y": 0.0}
        c_end = cand_traj[-1] if cand_traj else {"x": 0.0, "y": 0.0}
        cx_start = c_start.get("center_x", c_start.get("x", 0.0))
        cy_start = c_start.get("center_y", c_start.get("y", 0.0))

        matched_idx = None
        best_score = 999.0

        for idx, exist in enumerate(merged_persons):
            e_first = exist.get("first_seen_sec", 0.0)
            e_last = exist.get("last_seen_sec", 0.0)
            e_traj = exist.get("trajectory", [])
            e_start = e_traj[0] if e_traj else {"x": 0.0, "y": 0.0}
            e_end = e_traj[-1] if e_traj else {"x": 0.0, "y": 0.0}
            ex_end = e_end.get("center_x", e_end.get("x", 0.0))
            ey_end = e_end.get("center_y", e_end.get("y", 0.0))

            # Check common timestamps
            e_pts_by_t = {round(p.get("timestamp_sec", 0.0), 1): p for p in e_traj}
            c_pts_by_t = {round(p.get("timestamp_sec", 0.0), 1): p for p in cand_traj}
            common_ts = set(e_pts_by_t.keys()) & set(c_pts_by_t.keys())

            # If there are simultaneous overlapping frames
            if common_ts:
                # Calculate distance during simultaneous frames
                dists = [
                    math.hypot(
                        e_pts_by_t[t].get("center_x", e_pts_by_t[t].get("x", 0.0)) - c_pts_by_t[t].get("center_x", c_pts_by_t[t].get("x", 0.0)),
                        e_pts_by_t[t].get("center_y", e_pts_by_t[t].get("y", 0.0)) - c_pts_by_t[t].get("center_y", c_pts_by_t[t].get("y", 0.0))
                    )
                    for t in common_ts
                ]
                avg_common_dist = sum(dists) / len(dists)

                # Case A: Duplicate detection / handoff on same body:
                # Common frames are brief (<= 3 frames / <= 0.8s) OR spatial distance is very small (< 8.0%)
                if (len(common_ts) <= 3 and avg_common_dist < 10.0) or avg_common_dist < 6.0:
                    if avg_common_dist < best_score:
                        best_score = avg_common_dist
                        matched_idx = idx
                        continue
                else:
                    # Persistent simultaneous presence in different locations: distinct concurrent persons!
                    continue

            # Check if candidate falls inside an internal gap of existing track
            if e_first <= cand_first and cand_last <= e_last:
                # Candidate occurred during a gap in existing track!
                # Check spatial distance to surrounding points in existing track
                closest_dist = min(
                    math.hypot(
                        p.get("center_x", p.get("x", 0.0)) - cx_start,
                        p.get("center_y", p.get("y", 0.0)) - cy_start
                    )
                    for p in e_traj
                )
                if closest_dist < 10.0:
                    if closest_dist < best_score:
                        best_score = closest_dist
                        matched_idx = idx
                        continue

            # Non-overlapping: calculate time gap
            overlap_start = max(e_first, cand_first)
            overlap_end = min(e_last, cand_last)
            overlap_dur = max(0.0, overlap_end - overlap_start)

            if overlap_dur == 0:
                time_gap = cand_first - e_last
                if 0.0 <= time_gap <= 35.0:
                    dist = math.hypot(cx_start - ex_end, cy_start - ey_end)
                    
                    # Check if existing person departed at boundary
                    ex_last_pt = e_end.get("x", 50.0)
                    ey_last_pt = e_end.get("y", 50.0)
                    has_departed = (ex_last_pt > 88.0 or ex_last_pt < 10.0 or ey_last_pt > 88.0 or ey_last_pt < 10.0)

                    # Short gap (<= 5s): walking continuity
                    if time_gap <= 5.0 and dist <= max(35.0, 20.0 * time_gap + 15.0):
                        if dist < best_score:
                            best_score = dist
                            matched_idx = idx

                    # Long gap (<= 35s): stationary dwell / occlusion inside monitored zone without boundary departure
                    elif not has_departed and time_gap <= 35.0:
                        if dist <= 32.0:
                            if dist < best_score:
                                best_score = dist
                                matched_idx = idx

        if matched_idx is not None:
            target = merged_persons[matched_idx]
            # Avoid inserting duplicate frames at same timestamp
            existing_ts = {round(p.get("timestamp_sec", 0.0), 2) for p in target["trajectory"]}
            new_pts = [p for p in cand_traj if round(p.get("timestamp_sec", 0.0), 2) not in existing_ts]
            target["trajectory"].extend(new_pts)
            target["trajectory"].sort(key=lambda p: p.get("timestamp_sec", 0.0))
            target["first_seen_sec"] = min(target.get("first_seen_sec", 0.0), cand_first)
            target["last_seen_sec"] = max(target.get("last_seen_sec", 0.0), cand_last)
            target["observations_count"] = len(target["trajectory"])
            target["avg_confidence"] = round((target.get("avg_confidence", 0.8) + cand.get("avg_confidence", 0.8)) / 2.0, 3)
            print(f"  [MERGED] Candidate ({cand_first}s-{cand_last}s) -> Target Person-{matched_idx+1:02d} (New span: {target['first_seen_sec']}s-{target['last_seen_sec']}s)")
        else:
            merged_persons.append(cand)
            print(f"  [NEW PERSON] Track {cand.get('track_id')} ({cand_first}s-{cand_last}s) -> Person-{len(merged_persons):02d}")

    # Renumber sequentially
    for idx, p in enumerate(merged_persons, start=1):
        p["entity_id"] = f"Person-{idx:02d}"
        p["class"] = "person"

    vehicles = [t for t in others if str(t.get("class", "")).lower() in ["car", "truck", "bus", "motorcycle", "bicycle"]]
    for idx, v in enumerate(vehicles, start=1):
        v["entity_id"] = f"Vehicle-{idx:02d}"
        v["class"] = "vehicle"

    baggage = [t for t in others if str(t.get("class", "")).lower() in ["backpack", "handbag", "suitcase"]]
    for idx, b in enumerate(baggage, start=1):
        b["entity_id"] = f"Baggage-{idx:02d}"

    objects = [t for t in others if str(t.get("class", "")).lower() in ["cell phone", "laptop"]]
    for idx, o in enumerate(objects, start=1):
        cls_lower = str(o.get("class", "")).lower()
        tag = "Phone" if "phone" in cls_lower else "Laptop"
        o["entity_id"] = f"{tag}-{idx:02d}"

    return merged_persons + vehicles + baggage + objects

print("Running raw extraction...")
res = yolo.process_video_with_tracking(video_path, sample_fps=4.0, conf_thresh=0.25)
raw_tracks = res.get("tracks", [])

refined = refine_and_merge_tracks(raw_tracks)
print(f"\n==========================================")
print(f"FINAL REFINED ENTITY COUNT: {len(refined)}")
print(f"==========================================")
for t in refined:
    dur = round(t['last_seen_sec'] - t['first_seen_sec'], 2)
    print(f"  [{t['class'].upper()}] {t['entity_id']}: {t['first_seen_sec']}s -> {t['last_seen_sec']}s (dur={dur}s, obs={t['observations_count']}, avg_conf={t['avg_confidence']})")
