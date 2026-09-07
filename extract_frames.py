import cv2, os

video_path = 'backend/uploads/vid-a5ad7565_womans-encounter-with-intruder-at-home-SBV-306399481-preview.mp4'
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Video: {video_path}")
print(f"Dimensions: {w}x{h}, FPS: {fps}, Total Frames: {frames}, Duration: {frames/fps:.2f}s")

# Let's check frame 0, frame 60 (2s), frame 150 (5s)
os.makedirs('scratch_frames', exist_ok=True)
for sec in [0, 1, 2, 5, 8, 10]:
    frame_no = int(sec * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    ret, frame = cap.read()
    if ret:
        out_name = f"scratch_frames/frame_{sec}s.jpg"
        cv2.imwrite(out_name, frame)
        print(f"Saved {out_name} (frame {frame_no})")

cap.release()
