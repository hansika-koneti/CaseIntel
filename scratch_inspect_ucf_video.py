import cv2
import os
from ultralytics import YOLO

video_path = os.path.join("backend", "test_footage", "ucf_crime_stealing002.mp4")
model = YOLO("yolo11n.pt")
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)

print(f"Inspecting detections across {video_path} (FPS={fps})...")
frame_idx = 0
dets_by_sec = {}

step = max(1, int(fps / 4))
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    if frame_idx % step == 0:
        sec = round(frame_idx / fps, 1)
        res = model.track(source=frame, tracker="bytetrack.yaml", persist=True, conf=0.20, verbose=False)
        boxes = res[0].boxes
        if boxes is not None and len(boxes) > 0:
            frame_items = []
            for b in boxes:
                cls_id = int(b.cls[0].item())
                cname = model.names[cls_id]
                tid = int(b.id[0].item()) if (b.id is not None and len(b.id) > 0) else None
                conf = round(float(b.conf[0].item()), 2)
                xyxy = [round(x, 1) for x in b.xyxy[0].tolist()]
                frame_items.append((cname, tid, conf, xyxy))
            dets_by_sec[sec] = frame_items
    frame_idx += 1
cap.release()

track_timeline = {}
for sec, items in dets_by_sec.items():
    for cname, tid, conf, xyxy in items:
        if cname not in track_timeline:
            track_timeline[cname] = {}
        if tid not in track_timeline[cname]:
            track_timeline[cname][tid] = {"first": sec, "last": sec, "count": 0, "confs": [], "boxes": []}
        t = track_timeline[cname][tid]
        t["last"] = sec
        t["count"] += 1
        t["confs"].append(conf)
        t["boxes"].append(xyxy)

for cname, tracks in track_timeline.items():
    print(f"\n=== Class: {cname} ===")
    for tid, info in sorted(tracks.items(), key=lambda x: (x[1]["first"], x[0] if x[0] is not None else 999)):
        avg_c = round(sum(info["confs"]) / len(info["confs"]), 2)
        print(f"  Track ID {tid}: seen {info['first']}s -> {info['last']}s (frames={info['count']}, avg_conf={avg_c}, first_box={info['boxes'][0]}, last_box={info['boxes'][-1]})")
