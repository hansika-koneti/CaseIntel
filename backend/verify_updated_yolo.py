import os
from services.yolo_service import YOLOv11DetectorService

video_path = os.path.join(os.path.dirname(__file__), "test_footage", "ucf_crime_stealing002.mp4")
yolo = YOLOv11DetectorService()
res = yolo.process_video_with_tracking(video_path, sample_fps=4.0, conf_thresh=0.25)
print("Persons count:", res["summary"]["total_tracked_persons"])
for t in res["tracks"]:
    if t["class"] == "person":
        dur = round(t["last_seen_sec"] - t["first_seen_sec"], 2)
        print(f"  [{t['class'].upper()}] {t['entity_id']}: {t['first_seen_sec']}s -> {t['last_seen_sec']}s (dur={dur}s, obs={t['observations_count']}, conf={t['avg_confidence']})")
