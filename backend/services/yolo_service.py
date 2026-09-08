"""
CaseIntel — YOLOv11 & ByteTrack Detection and Tracking Service
Performs real frame extraction, YOLOv11 object detection, and ByteTrack
multi-object tracking with persistent entity IDs and trajectories.
"""

import os
import math
import cv2
from typing import Dict, Any, List, Optional, Callable
from ultralytics import YOLO

MODEL_PATH = os.getenv("YOLO_WEIGHTS_PATH", "yolo11n.pt")


class YOLOv11DetectorService:
    """Production YOLOv11 inference and ByteTrack tracking service."""

    def __init__(self, model_path: str = MODEL_PATH):
        self.model_path = model_path
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            self.model = YOLO(self.model_path)
            print(f"[YOLOv11DetectorService] Successfully loaded weights from '{self.model_path}'")
        except Exception as e:
            print(f"[YOLOv11DetectorService] Warning: Failed to load '{self.model_path}': {e}")
            self.model = None

    def detect_frame(self, frame, conf_thresh: float = 0.35) -> List[Dict[str, Any]]:
        """Run YOLO inference on a single numpy image frame without tracking."""
        if self.model is None:
            return []

        h, w = frame.shape[:2]
        results = self.model.predict(source=frame, conf=conf_thresh, verbose=False)
        detections = []

        if not results:
            return detections

        res = results[0]
        boxes = res.boxes
        if boxes is None:
            return detections

        for box in boxes:
            cls_id = int(box.cls[0].item())
            cls_name = self.model.names.get(cls_id, str(cls_id))
            conf = round(float(box.conf[0].item()), 3)
            xyxy = box.xyxy[0].tolist()
            x1, y1, x2, y2 = [round(v, 1) for v in xyxy]

            x_pct = round((x1 / w) * 100, 1) if w > 0 else 0
            y_pct = round((y1 / h) * 100, 1) if h > 0 else 0
            w_pct = round(((x2 - x1) / w) * 100, 1) if w > 0 else 0
            h_pct = round(((y2 - y1) / h) * 100, 1) if h > 0 else 0

            detections.append({
                "class": cls_name,
                "confidence": conf,
                "bbox": [x1, y1, x2, y2],
                "normalized_bbox": [x_pct, y_pct, w_pct, h_pct],
            })

        return detections

    def process_video_with_tracking(
        self,
        video_path: str,
        sample_fps: float = 4.0,
        conf_thresh: float = 0.25,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        max_retained_frames: int = 1200,
    ) -> Dict[str, Any]:
        """
        Extract frames from video and run YOLOv11 + ByteTrack multi-object tracking.
        Maintains persistent entity IDs (e.g. Person-01, Vehicle-01) and trajectory paths.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file '{video_path}' does not exist.")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {
                "valid": False,
                "error": "Failed to open video file via OpenCV.",
                "tracks": [],
                "detections_by_frame": [],
            }

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = round(total_frames / fps, 2) if fps > 0 else 0

        frame_step = max(1, int(fps / sample_fps)) if sample_fps > 0 else int(fps)

        frame_results = []
        tracks_map: Dict[int, Dict[str, Any]] = {}
        detected_classes = set()

        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_step == 0:
                h, w = frame.shape[:2]
                timestamp_sec = round(frame_idx / fps, 2) if fps > 0 else 0
                frame_dets = []

                if progress_callback and total_frames > 0:
                    if frame_idx % (frame_step * 10) == 0 or frame_idx == 0:
                        pct = min(99.0, round((frame_idx / total_frames) * 100.0, 1))
                        progress_callback(pct, frame_idx, total_frames)

                if self.model is not None:
                    try:
                        results = self.model.track(
                            source=frame,
                            tracker="bytetrack.yaml",
                            persist=True,
                            conf=conf_thresh,
                            verbose=False,
                        )
                    except Exception:
                        results = self.model.predict(source=frame, conf=conf_thresh, verbose=False)

                    if results and results[0].boxes is not None:
                        boxes = results[0].boxes
                        TRACKABLE_SECURITY_CLASSES = {
                            "person",
                            "car", "truck", "bus", "motorcycle", "bicycle",
                            "backpack", "handbag", "suitcase",
                            "cell phone", "laptop",
                        }

                        for box in boxes:
                            cls_id = int(box.cls[0].item())
                            cls_name = str(self.model.names.get(cls_id, str(cls_id))).lower()
                            if cls_name not in TRACKABLE_SECURITY_CLASSES:
                                # Skip generic indoor/outdoor objects (couch, tv, chair, potted plant, vase, etc.)
                                continue

                            conf = round(float(box.conf[0].item()), 3)
                            xyxy = box.xyxy[0].tolist()
                            x1, y1, x2, y2 = [round(v, 1) for v in xyxy]

                            x_pct = round((x1 / w) * 100, 1) if w > 0 else 0
                            y_pct = round((y1 / h) * 100, 1) if h > 0 else 0
                            w_pct = round(((x2 - x1) / w) * 100, 1) if w > 0 else 0
                            h_pct = round(((y2 - y1) / h) * 100, 1) if h > 0 else 0

                            # Determine track & entity ID
                            track_id = int(box.id[0].item()) if (box.id is not None and len(box.id) > 0) else None
                            if track_id is not None:
                                if cls_name == "person":
                                    entity_id = f"Person-{track_id:02d}"
                                elif cls_name in ["car", "truck", "bus", "motorcycle", "bicycle"]:
                                    entity_id = f"Vehicle-{track_id:02d}"
                                elif cls_name in ["backpack", "handbag", "suitcase"]:
                                    entity_id = f"Baggage-{track_id:02d}"
                                elif cls_name in ["cell phone", "laptop"]:
                                    entity_id = f"Object-{track_id:02d}"
                                else:
                                    entity_id = f"{cls_name.capitalize()}-{track_id:02d}"
                            else:
                                entity_id = f"{cls_name.capitalize()}-F{frame_idx}"

                            detected_classes.add(cls_name)


                            # Record center point
                            center_x = round(x_pct + (w_pct / 2), 1)
                            center_y = round(y_pct + (h_pct / 2), 1)

                            det_entry = {
                                "track_id": track_id,
                                "entity_id": entity_id,
                                "class": cls_name,
                                "confidence": conf,
                                "bbox": [x1, y1, x2, y2],
                                "normalized_bbox": [x_pct, y_pct, w_pct, h_pct],
                                "center": [center_x, center_y],
                            }
                            frame_dets.append(det_entry)

                            # Update tracks map
                            if track_id is not None:
                                if track_id not in tracks_map:
                                    tracks_map[track_id] = {
                                        "track_id": track_id,
                                        "entity_id": entity_id,
                                        "class": cls_name,
                                        "confidences": [conf],
                                        "first_seen_sec": timestamp_sec,
                                        "last_seen_sec": timestamp_sec,
                                        "trajectory": [],
                                    }
                                else:
                                    tracks_map[track_id]["confidences"].append(conf)
                                    tracks_map[track_id]["last_seen_sec"] = timestamp_sec

                                tracks_map[track_id]["trajectory"].append({
                                    "frame": frame_idx,
                                    "timestamp_sec": timestamp_sec,
                                    "x": x_pct,
                                    "y": y_pct,
                                    "w": w_pct,
                                    "h": h_pct,
                                    "center_x": center_x,
                                    "center_y": center_y,
                                    "confidence": round(float(conf) * 100, 1),
                                })


                if len(frame_results) < max_retained_frames or frame_dets:
                    frame_results.append({
                        "frame": frame_idx,
                        "timestamp_sec": timestamp_sec,
                        "detections": frame_dets,
                    })

            frame_idx += 1

        cap.release()
        if progress_callback and total_frames > 0:
            progress_callback(100.0, total_frames, total_frames)

        # Aggregate tracks summary with transient noise rejection
        tracks_list = []
        for tid, tinfo in tracks_map.items():
            raw_traj = tinfo["trajectory"]
            obs = len(raw_traj)
            dur = round(tinfo["last_seen_sec"] - tinfo["first_seen_sec"], 2)
            avg_conf = round(sum(tinfo["confidences"]) / len(tinfo["confidences"]), 3)
            cls_name = str(tinfo["class"]).lower()

            # Reject ultra-short person noise (< 3 observations and duration < 0.3s, or single frame with low conf)
            if cls_name == "person" and ((obs < 3 and dur < 0.3) or (obs <= 2 and avg_conf < 0.50)):
                continue

            # Reject transient baggage/objects (< 5 observations or duration < 1.0s with low conf)
            if cls_name in ["backpack", "handbag", "suitcase", "cell phone", "laptop"] and (obs < 5 or dur < 1.0) and avg_conf < 0.70:
                continue

            # Reject transient vehicle glitches
            if cls_name in ["car", "truck", "bus", "motorcycle", "bicycle"] and obs < 3 and dur < 0.3 and avg_conf < 0.50:
                continue

            # Downsample trajectory points to ~2 Hz (every 0.5s) for long videos (> 200 points)
            # This maintains fluid video player bounding-box interpolation while keeping memory and DB bounded
            if len(raw_traj) > 200:
                sampled_traj = [raw_traj[0]]
                last_t = raw_traj[0]["timestamp_sec"]
                for pt in raw_traj[1:-1]:
                    if pt["timestamp_sec"] - last_t >= 0.5:
                        sampled_traj.append(pt)
                        last_t = pt["timestamp_sec"]
                sampled_traj.append(raw_traj[-1])
                final_traj = sampled_traj
            else:
                final_traj = raw_traj

            tracks_list.append({
                "track_id": tid,
                "entity_id": tinfo["entity_id"],
                "class": tinfo["class"],
                "avg_confidence": avg_conf,
                "first_seen_sec": tinfo["first_seen_sec"],
                "last_seen_sec": tinfo["last_seen_sec"],
                "observations_count": len(raw_traj),
                "trajectory": final_traj,
            })

        # Stitch & merge fragmented person tracks (occlusions, crouching, pose transitions)
        tracks_list = self._merge_person_tracks(tracks_list, width, height)

        person_tracks = sum(1 for t in tracks_list if t["class"] == "person")
        vehicle_tracks = sum(1 for t in tracks_list if t["class"] in ["car", "truck", "bus", "motorcycle"])

        return {
            "valid": True,
            "fps": fps,
            "width": width,
            "height": height,
            "frame_count": total_frames,
            "duration_seconds": duration,
            "analyzed_frames": len(frame_results),
            "tracks": tracks_list,
            "detections_by_frame": frame_results,
            "summary": {
                "total_tracked_entities": len(tracks_list),
                "total_tracked_persons": person_tracks,
                "total_tracked_vehicles": vehicle_tracks,
                "classes_detected": sorted(list(detected_classes)),
            },
        }

    def _merge_person_tracks(
        self,
        tracks: List[Dict[str, Any]],
        width: int,
        height: int,
    ) -> List[Dict[str, Any]]:
        """
        Merge fragmented person tracklets caused by temporary occlusions (e.g. crouching
        behind furniture or under vehicle hoods), posture changes, or transient detector misclassification.
        Preserves single physical human identity across surveillance scenes while keeping distinct concurrent
        individuals strictly separated.
        """
        person_candidates = []
        other_tracks = []

        for t in tracks:
            cls = str(t.get("class", "")).lower()
            if cls == "person":
                person_candidates.append(t)
            else:
                other_tracks.append(t)

        if not person_candidates:
            return tracks

        # Sort candidate person tracks chronologically by first appearance
        person_candidates.sort(key=lambda x: (x.get("first_seen_sec", 0.0), -(x.get("last_seen_sec", 0.0) - x.get("first_seen_sec", 0.0))))

        merged_persons: List[Dict[str, Any]] = []
        for cand in person_candidates:
            if not merged_persons:
                merged_persons.append(cand)
                continue

            cand_first = cand.get("first_seen_sec", 0.0)
            cand_last = cand.get("last_seen_sec", 0.0)
            cand_traj = cand.get("trajectory", [])
            c_start = cand_traj[0] if cand_traj else {"x": 0.0, "y": 0.0}
            c_end = cand_traj[-1] if cand_traj else {"x": 0.0, "y": 0.0}
            cx_start = c_start.get("center_x", c_start.get("x", 0.0))
            cy_start = c_start.get("center_y", c_start.get("y", 0.0))

            matched_idx = None
            best_score = 999.0

            for idx, existing in enumerate(merged_persons):
                e_first = existing.get("first_seen_sec", 0.0)
                e_last = existing.get("last_seen_sec", 0.0)
                e_traj = existing.get("trajectory", [])
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
                    dists = [
                        math.hypot(
                            e_pts_by_t[t].get("center_x", e_pts_by_t[t].get("x", 0.0)) - c_pts_by_t[t].get("center_x", c_pts_by_t[t].get("x", 0.0)),
                            e_pts_by_t[t].get("center_y", e_pts_by_t[t].get("y", 0.0)) - c_pts_by_t[t].get("center_y", c_pts_by_t[t].get("y", 0.0))
                        )
                        for t in common_ts
                    ]
                    avg_common_dist = sum(dists) / len(dists)

                    # Case A: Duplicate detection / handoff on same body:
                    # Common frames are brief (<= 3 frames) or spatial distance is coincident (< 6.0%)
                    if (len(common_ts) <= 3 and avg_common_dist < 10.0) or avg_common_dist < 6.0:
                        if avg_common_dist < best_score:
                            best_score = avg_common_dist
                            matched_idx = idx
                            continue
                    else:
                        # Persistent simultaneous presence in distinct locations: distinct concurrent persons!
                        continue

                # Check if candidate falls inside an internal gap of existing track
                if e_first <= cand_first and cand_last <= e_last:
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

                        # Condition 1: Short gap (<= 5s), plausible human walking displacement
                        if time_gap <= 5.0 and dist <= max(35.0, 20.0 * time_gap + 15.0):
                            if dist < best_score:
                                best_score = dist
                                matched_idx = idx

                        # Condition 2: Prolonged occlusion inside monitored zone without boundary departure
                        # (e.g. crouching beside/under vehicle, ducking behind wall/furniture)
                        elif not has_departed and time_gap <= 35.0:
                            if dist <= 42.0:
                                if dist < best_score:
                                    best_score = dist
                                    matched_idx = idx

            if matched_idx is not None:
                target = merged_persons[matched_idx]
                existing_ts = {round(p.get("timestamp_sec", 0.0), 2) for p in target["trajectory"]}
                new_pts = [p for p in cand_traj if round(p.get("timestamp_sec", 0.0), 2) not in existing_ts]
                target["trajectory"].extend(new_pts)
                target["trajectory"].sort(key=lambda p: p.get("timestamp_sec", 0.0))
                target["first_seen_sec"] = min(target.get("first_seen_sec", 0.0), cand_first)
                target["last_seen_sec"] = max(target.get("last_seen_sec", 0.0), cand_last)
                target["observations_count"] = len(target["trajectory"])
                conf_a = target.get("avg_confidence", 0.8)
                conf_b = cand.get("avg_confidence", 0.8)
                target["avg_confidence"] = round((conf_a + conf_b) / 2.0, 3)
                target["class"] = "person"
            else:
                merged_persons.append(cand)

        # Standardize entity IDs sequentially (Person-01, Person-02)
        for idx, p in enumerate(merged_persons, start=1):
            p["entity_id"] = f"Person-{idx:02d}"
            p["class"] = "person"

        # Standardize vehicle entity IDs sequentially (Vehicle-01, Vehicle-02)
        vehicles = [t for t in other_tracks if str(t.get("class", "")).lower() in ["car", "truck", "bus", "motorcycle", "bicycle"]]
        for idx, v in enumerate(vehicles, start=1):
            v["entity_id"] = f"Vehicle-{idx:02d}"
            v["class"] = "vehicle"

        # Standardize baggage entity IDs sequentially (Baggage-01, Baggage-02)
        baggage = [t for t in other_tracks if str(t.get("class", "")).lower() in ["backpack", "handbag", "suitcase"]]
        for idx, b in enumerate(baggage, start=1):
            b["entity_id"] = f"Baggage-{idx:02d}"

        # Standardize objects/property entity IDs sequentially (Object-01, Object-02)
        objects = [t for t in other_tracks if str(t.get("class", "")).lower() in ["cell phone", "laptop"]]
        for idx, o in enumerate(objects, start=1):
            cls_lower = str(o.get("class", "")).lower()
            tag = "Phone" if "phone" in cls_lower else "Laptop"
            o["entity_id"] = f"{tag}-{idx:02d}"

        return merged_persons + vehicles + baggage + objects


    def process_video(
        self,
        video_path: str,
        sample_fps: float = 4.0,
        conf_thresh: float = 0.25,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
    ) -> Dict[str, Any]:
        """Runs tracking and detection pipeline on the video."""
        return self.process_video_with_tracking(
            video_path=video_path,
            sample_fps=sample_fps,
            conf_thresh=conf_thresh,
            progress_callback=progress_callback,
        )
