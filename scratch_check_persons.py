import cv2
from ultralytics import YOLO

cap = cv2.VideoCapture('backend/uploads/vid-5fbf878d_3878245337-preview.mp4')
model = YOLO('backend/models/yolo11n.pt')

frame_idx = 0
person_detections = []
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    if frame_idx % 10 == 0:  # Sample every 10 frames (~0.4s)
        res = model(frame, conf=0.15, verbose=False)[0]
        persons = []
        for b in res.boxes:
            cls_id = int(b.cls[0])
            conf = float(b.conf[0])
            if cls_id == 0:  # person
                xyxy = [round(x, 1) for x in b.xyxy[0].tolist()]
                persons.append((conf, xyxy))
        if persons:
            t = frame_idx / 25.0
            person_detections.append((frame_idx, t, persons))
    frame_idx += 1

print(f"Total sampled frames with person detections: {len(person_detections)}")
for f_idx, t, p_list in person_detections:
    print(f"Frame {f_idx:3d} (t={t:4.2f}s): {p_list}")
