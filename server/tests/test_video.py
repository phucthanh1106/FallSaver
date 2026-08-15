import cv2
import time
from ultralytics import YOLO
from datetime import datetime, timezone, timedelta
import os
import dotenv
from pathlib import Path

from test_fall_detector import FallDetector

# Load environment variables
dotenv.load_dotenv()
THRESHOLD_ANGLE = int(os.getenv("THRESHOLD_ANGLE"))
THRESHOLD_DROP = float(os.getenv("THRESHOLD_DROP"))

# Load the model once
model = YOLO("/Users/tyler/FallSaver/server/weights/yolo26n-pose.onnx", task="pose")
video_path="/Users/tyler/FallSaver/FallDetection/data/cctv/20260722_174929.mp4"
filename = os.path.basename(video_path)
output_path = f"/Users/tyler/FallSaver/FallDetection/data/annotated/{filename}"

def show_fps(prev_time, frame):
    """Show FPS on frame"""
    cur_time = time.time()
    fps = 1 / (cur_time - prev_time)
    prev_time = cur_time

    cv2.putText(
        frame,
        f"FPS: {int(fps)}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    return prev_time


# Add fall event tracking
fall_events_time = []

# Display video with fall detection
cap = cv2.VideoCapture(video_path)
video_fps = cap.get(cv2.CAP_PROP_FPS) or 25
FALL_WINDOW = max(2, int(video_fps * 1.5))
fall_detector = FallDetector(
    history_size=FALL_WINDOW,
    threshold_angle=THRESHOLD_ANGLE,
    threshold_drop=THRESHOLD_DROP,
)
prev_time = time.time()


video_writer = None
# frame_count = 0
# SKIP_FRAMES = 2
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    new_width = 640
    scale = new_width / frame.shape[1]
    new_height = int(frame.shape[0] * scale)

    frame_resized = cv2.resize(
        frame,
        (new_width, new_height),
    )

    # frame_count += 1

    # if frame_count % SKIP_FRAMES == 0:
    #     frame_resized = cv2.resize(frame, (640, 480))
    #     results = model.track(frame_resized, persist=True, conf=0.1, device="cpu", verbose=False)
    #     r = results[0]
    
    results = model.track(frame_resized, persist=True, conf=0.1, device="cpu", verbose=False)
    r = results[0]
    annotated_frame = r.plot()
    
    keypoints = r.keypoints.xy
    kp_conf = r.keypoints.conf
    boxes = r.boxes
    ids = r.boxes.id
    
    prev_time = show_fps(prev_time, annotated_frame)
    
    status_text = "OK"
    status_color = (0, 255, 0)
    
    if ids is not None:
        selected_joints = keypoints[:, [5, 6, 11, 12, 15, 16], :]
        joints_conf = kp_conf[:, [5, 6, 11, 12, 15, 16]]
        
        for i, person_id in enumerate(ids):
            person_id = int(person_id.item())
            angle = fall_detector.body_angle(selected_joints[i], joints_conf[i])
            
            if angle is None:
                continue
            
            x1, y1, x2, y2 = boxes.xyxy[i]

            fall_detector.update_history(
                person_id,
                angle,
                boxes.xywh[i],
                boxes.conf[i].item(),
            )
            angles, xywh, conf = fall_detector.get_history(person_id)

            if len(angles) >= FALL_WINDOW / 4.5:
                recent_angles = angles[-FALL_WINDOW:]
                recent_xywh = xywh[-FALL_WINDOW:]
                angle_change, vertical_drop, case = fall_detector.fall_metrics(
                    recent_angles,
                    recent_xywh,
                    FALL_WINDOW,
                )

                cv2.putText(
                    annotated_frame,
                    f"Angle: {angle_change: .1f}",
                    (int(x2) + 10, int(y2) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.3,
                    (0, 255, 0),
                    2,
                )
                cv2.putText(
                    annotated_frame,
                    f"Vert Drop: {vertical_drop:.2f}",
                    (int(x2) + 10, int(y2) - 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.3,
                    (0, 255, 0),
                    2,
                )
                cv2.putText(
                    annotated_frame,
                    f"Case: {case}",
                    (int(x2) + 10, int(y2) - 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.3,
                    (0, 255, 0),
                    2,
                )

                if fall_detector.detect_fall(
                    recent_angles,
                    recent_xywh,
                    conf,
                    FALL_WINDOW,
                ):
                    angle_change, vertical_drop, case = fall_detector.fall_metrics(angles, xywh, FALL_WINDOW)
                    print(f"FALLLLLLL (ID: {person_id})")
                    print(f"\tAngle Change: {angle_change}, Vert Drop: {vertical_drop}, Case: {case}")
                    status_text = "FALL DETECTED!"
                    status_color = (0, 0, 255)
    
    frame_height, frame_width = annotated_frame.shape[:2]
    text_size = cv2.getTextSize(f"Status: {status_text}", cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
    text_x = frame_width - text_size[0] - 20
    text_y = 50
    
    cv2.putText(annotated_frame, f"Status: {status_text}", (text_x, text_y), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
    

    # Saving the annotated video
    if video_writer is None:
        frame_height, frame_width = annotated_frame.shape[:2]

        video_writer = cv2.VideoWriter(
            output_path,
            cv2.VideoWriter_fourcc(*"mp4v"),
            video_fps,
            (frame_width, frame_height),
        )

        if not video_writer.isOpened():
            raise RuntimeError(f"Could not create video: {output_path}")

    video_writer.write(annotated_frame)
    
    cv2.imshow("Fall Detection", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()

if video_writer is not None:
    video_writer.release()

print(f"Annotated video saved to: {output_path}")

cv2.destroyAllWindows()
