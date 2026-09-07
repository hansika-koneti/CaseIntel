import cv2, os
from ultralytics import YOLO

model = YOLO('backend/yolo11n.pt')
video_path = 'backend/uploads/vid-a5ad7565_womans-encounter-with-intruder-at-home-SBV-306399481-preview.mp4'

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)

os.makedirs('scratch_detections', exist_ok=True)

# Run on frames 0s, 1s, 2s, 5s, 8s, 10s
for sec in [0, 1, 2, 5, 8, 10]:
    frame_no = int(sec * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    ret, frame = cap.read()
    if ret:
        results = model.predict(frame, conf=0.25, verbose=False)[0]
        vis_frame = frame.copy()
        print(f"\n--- Frame at {sec}s (frame {frame_no}) ---")
        for box in results.boxes:
            cls_id = int(box.cls[0])
            cls_name = model.names[cls_id]
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].tolist()
            print(f"  Detected: {cls_name} ({cls_id}) - Conf: {conf:.2f} - Box: {[round(x,1) for x in xyxy]}")
            if cls_name in ['person', 'cell phone', 'chair']:
                x1, y1, x2, y2 = [int(x) for x in xyxy]
                color = (0, 255, 0) if cls_name == 'person' else (255, 0, 0)
                cv2.rectangle(vis_frame, (x1, y1), (x2, y2), color, 3)
                cv2.putText(vis_frame, f"{cls_name} {conf:.2f}", (x1, max(20, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.imwrite(f"scratch_detections/det_{sec}s.jpg", vis_frame)

cap.release()
