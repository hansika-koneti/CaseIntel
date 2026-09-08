import os
import sys
import json
from services.yolo_service import YOLOv11DetectorService

video_path = os.path.join("backend", "test_footage", "ucf_crime_stealing002.mp4")
yolo = YOLOv11DetectorService()

print("Running process_video_with_tracking...")
res = yolo.process_video_with_tracking(video_path, sample_fps=4.0, conf_thresh=0.25)
tracks = res.get("tracks", [])

print("\n--- Detailed Person Tracks ---")
for t in tracks:
    if t["class"] == "person":
        traj = t["trajectory"]
        p_start = (round(traj[0]["x"], 1), round(traj[0]["y"], 1))
        p_end = (round(traj[-1]["x"], 1), round(traj[-1]["y"], 1))
        dur = round(t["last_seen_sec"] - t["first_seen_sec"], 2)
        print(f"  {t['entity_id']}: {t['first_seen_sec']}s -> {t['last_seen_sec']}s (dur={dur}s, obs={len(traj)}, avg_conf={t['avg_confidence']}) | start={p_start} | end={p_end}")
