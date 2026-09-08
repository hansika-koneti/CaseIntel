import cv2, torch, time, numpy as np
import torchvision.models.video as vmodels
from torchvision.models.video import R2Plus1D_18_Weights

cap = cv2.VideoCapture('backend/test_footage/ucf_crime_stealing002.mp4')
frames = []
for _ in range(16):
    ret, f = cap.read()
    if ret:
        f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
        frames.append(cv2.resize(f, (112, 112)))
cap.release()

weights = R2Plus1D_18_Weights.DEFAULT
transforms = weights.transforms()
# frames np array is (16, 112, 112, 3). Convert to (16, 3, 112, 112)
tensor_frames = torch.from_numpy(np.array(frames)).permute(0, 3, 1, 2)
transformed = transforms(tensor_frames) # returns (C, T, H, W) or (T, C, H, W)
print('Transformed shape:', transformed.shape)
# R2Plus1D expects (B, C, T, H, W)
if transformed.ndim == 4 and transformed.shape[0] != 3 and transformed.shape[1] == 3:
    # (T, C, H, W) -> (C, T, H, W)
    transformed = transformed.permute(1, 0, 2, 3)
clip = transformed.unsqueeze(0)
print('Clip batch shape:', clip.shape)

m = vmodels.r2plus1d_18(weights=weights)
m.eval()

t1 = time.time()
with torch.no_grad():
    out = m(clip)
t2 = time.time()

probs = torch.softmax(out, dim=1)[0]
top5_probs, top5_indices = torch.topk(probs, 5)
categories = weights.meta['categories']

print(f'Inference time (16-frame clip): {t2 - t1:.3f}s')
print('Top 5 raw predictions:')
for p, idx in zip(top5_probs, top5_indices):
    print(f'  {categories[idx]}: {p.item()*100:.2f}%')
