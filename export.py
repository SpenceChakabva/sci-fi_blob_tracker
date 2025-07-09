import cv2
import numpy as np
import time
import os
import random
import subprocess
import tempfile
from math import sin

# === CONFIG ===
video_folder = "input"  # Folder containing the video file
video_path = os.path.join(video_folder, "test1.mp4")
image_folder = "img_e"  # Folder containing 1.jpg to 8.jpg
output_folder = "output"  # Folder to save final output video
os.makedirs(output_folder, exist_ok=True)

final_output = os.path.join(output_folder, "output_with_audio.mp4")
target_fps = 30
window_size = (800, 600)
head_img_size = 70

# === TEMP FILES ===
audio_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".aac").name
video_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name

# Extract audio from original video
subprocess.call([
    "ffmpeg", "-i", video_path, "-vn", "-acodec", "copy", audio_temp, "-y"
])

# Load overlay images
overlay_images = []
for i in range(1, 9):
    path = os.path.join(image_folder, f"{i}.jpg")
    img = cv2.imread(path)
    if img is not None:
        overlay_images.append(cv2.resize(img, (head_img_size, head_img_size)))

cap = cv2.VideoCapture(video_path)
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out_video = cv2.VideoWriter(video_temp, fourcc, target_fps, window_size)

# Blob detector params
params = cv2.SimpleBlobDetector_Params()
params.filterByColor = False
params.filterByArea = True
params.minArea = 70
params.maxArea = 3000
params.filterByCircularity = True
params.minCircularity = 0.4
params.filterByConvexity = False
params.filterByInertia = False
blob_detector = cv2.SimpleBlobDetector_create(params)

# Initialize variables for frame processing
start_time = time.time()
prev_frame_time = 0
frame_delay = 1.0 / target_fps
prev_gray = None

# Main processing loop
while True:
    current_time = time.time()
    if current_time - prev_frame_time < frame_delay:
        continue
    prev_frame_time = current_time

    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, window_size)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(frame, -1, kernel)
    gray = cv2.cvtColor(sharpened, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), 0)

    if prev_gray is None:
        prev_gray = blurred
        continue

    
    frame_diff = cv2.absdiff(blurred, prev_gray)
    prev_gray = blurred
    _, motion_mask = cv2.threshold(frame_diff, 20, 255, cv2.THRESH_BINARY)
    kernel_morph = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, kernel_morph)
    motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_CLOSE, kernel_morph)
    keypoints = blob_detector.detect(motion_mask)

    # Glitch effect
    for i in range(0, frame.shape[0], 20):
        if random.random() < 0.07:
            shift = random.randint(-15, 15)
            b, g, r = cv2.split(frame[i:i+10])
            b = np.roll(b, shift, axis=1)
            g = np.roll(g, -shift, axis=1)
            r = np.roll(r, shift // 2, axis=1)
            glitch_slice = cv2.merge([b, g, r])
            frame[i:i+10] = cv2.addWeighted(frame[i:i+10], 0.7, glitch_slice, 0.3, 0)

    positions = [tuple(np.round(kp.pt).astype(int)) for kp in keypoints]
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            cv2.line(frame, positions[i], positions[j], (255, 255, 255), 1, cv2.LINE_AA)

    for idx, (x, y) in enumerate(positions):
        size = 10
        cv2.rectangle(frame, (x - size, y - size), (x + size, y + size), (255, 255, 255), 1)
        cv2.putText(frame, f"ID:{idx}", (x + 12, y - 12), cv2.FONT_HERSHEY_PLAIN, 1, (255, 255, 255), 1)

    if positions and overlay_images:
        elapsed = time.time() - start_time
        head_x, head_y = positions[0]
        img = random.choice(overlay_images)
        ih, iw = img.shape[:2]
        x1, y1 = head_x - iw // 2, head_y - ih // 2
        x2, y2 = x1 + iw, y1 + ih
        if 0 <= x1 < frame.shape[1] - iw and 0 <= y1 < frame.shape[0] - ih:
            roi = frame[y1:y2, x1:x2]
            frame[y1:y2, x1:x2] = cv2.addWeighted(roi, 0.3, img, 0.7, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 1)

    # Add timestamp
    cv2.imshow("Sci-fi Blob Tracker - Exported", frame)
    out_video.write(frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
out_video.release()
cv2.destroyAllWindows()

# Merge video and audio
subprocess.call([
    "ffmpeg", "-i", video_temp, "-i", audio_temp, "-c:v", "copy", "-c:a", "aac", "-strict", "experimental", final_output, "-y"
])

# Clean up temporary files
os.remove(video_temp)
os.remove(audio_temp)
print(f"✅ Exported video with audio saved as: {final_output}")
