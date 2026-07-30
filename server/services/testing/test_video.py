import cv2
import time
from ultralytics import YOLO
from datetime import datetime, timezone, timedelta
import os
from pathlib import Path

from fall_detector import FallDetector

# Load the model once
model = YOLO("/Users/tyler/FallSaver/server/weights/yolo26n-pose.onnx", task="pose")
video_path="/Users/tyler/FallSaver/FallDetection/data/shorten_fall_video/IMG_3832.MOV"
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


def generate_mjpeg_stream(path):
    """Generator that yields JPEG frames as MJPEG stream with fall detection"""
    cap = cv2.VideoCapture(path)
    
    
    if not cap.isOpened():
        print("Camera failed to open")
        return
    
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 25
    FALL_WINDOW = max(2, int(video_fps * 1.5))
    fall_detector = FallDetector(
        history_size=FALL_WINDOW,
        threshold_angle=40,
        threshold_drop=0.3,
    )
    prev_time = time.time()

    while True:
        success, frame = cap.read()
        if not success:
            break
        
        # Resize frame for performance
        frame = cv2.resize(frame, (640, 480))
        
        # Run fall detection model
        results = model.track(frame, persist=True, conf=0.05, device="mps", verbose=False)
        r = results[0]
        
        # Draw bounding boxes and keypoints
        annotated_frame = r.plot()
        
        # Get detection data
        keypoints = r.keypoints.xy
        kp_conf = r.keypoints.conf
        boxes = r.boxes
        ids = r.boxes.id
        
        # Get frame dimensions for top-right positioning
        frame_height, frame_width = annotated_frame.shape[:2]
        
        # Show FPS
        prev_time = show_fps(prev_time, annotated_frame)
        
        # Status tracking for display
        status_text = "OK"
        status_color = (0, 255, 0)
        
        if ids is not None:
            selected_joints = keypoints[:, [5, 6, 11, 12, 15, 16], :]
            joints_conf = kp_conf[:, [5, 6, 11, 12, 15, 16]]
            
            for i, person_id in enumerate(ids):
                person_id = int(person_id.item())
                
                # Calculate body angle
                angle = fall_detector.body_angle(selected_joints[i], joints_conf[i])
                
                # Skip if angle is None (occluded)
                if angle is None:
                    continue
                
                x1, y1, _, _ = boxes.xyxy[i]
                
                # Display body angle
                cv2.putText(
                    annotated_frame,
                    f"Angle: {int(angle)}",
                    (int(x1), int(y1) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 0, 0),
                    2
                )
                
                # Update history using the detector
                fall_detector.update_history(
                    person_id,
                    angle,
                    boxes.xywh[i],
                    boxes.conf[i].item(),
                )
                
                # Get history
                angles, xywh, conf = fall_detector.get_history(person_id)
                
                # Detect fall
                if len(angles) >= FALL_WINDOW:
                    recent_angles = angles[-FALL_WINDOW:]
                    recent_xywh = xywh[-FALL_WINDOW:]
                    angle_change, vertical_drop, case = fall_detector.fall_metrics(
                        recent_angles,
                        recent_xywh,
                        FALL_WINDOW
                    )
                    
                    # Display metrics
                    cv2.putText(
                        annotated_frame,
                        f"Angle Change: {angle_change:.1f}°",
                        (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2
                    )
                    cv2.putText(
                        annotated_frame,
                        f"Vert Drop: {vertical_drop:.2f}",
                        (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2
                    )
                    
                    # Draw fall detection result
                    if fall_detector.detect_fall(recent_angles, recent_xywh, conf, FALL_WINDOW):
                        if len(fall_events_time) == 0:
                            fall_events_time.append(datetime.now(timezone.utc).isoformat())
                        else:
                            now = datetime.now(timezone.utc)
                            last_fall = datetime.fromisoformat(fall_events_time[-1])
                            time_diff = now - last_fall
                            # Ensure that falls don't overlap each other 
                            if time_diff.total_seconds() > 2:
                                fall_events_time.append(datetime.now(timezone.utc).isoformat())
                        
                        status_text = "FALL"
                        status_color = (0, 0, 255)
        
        # Display status at top-right
        text_size = cv2.getTextSize(f"Status: {status_text}", cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
        text_x = frame_width - text_size[0] - 20
        text_y = 50
        
        cv2.putText(
            annotated_frame,
            f"Status: {status_text}",
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            status_color,
            3
        )
        
        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        if not ret:
            continue
        
        # Yield frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'Content-length: ' + str(len(buffer)).encode() + b'\r\n\r\n'
               + buffer.tobytes() + b'\r\n')

# Display video with fall detection
cap = cv2.VideoCapture(video_path)
video_fps = cap.get(cv2.CAP_PROP_FPS) or 25
FALL_WINDOW = max(2, int(video_fps * 1.5))
fall_detector = FallDetector(
    history_size=FALL_WINDOW,
    threshold_angle=40,
    threshold_drop=0.28,
)
prev_time = time.time()



video_writer = None
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    results = model.track(frame, persist=True, conf=0.1, device="cpu", verbose=False)
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
                    0.7,
                    (0, 255, 0),
                    2,
                )
                cv2.putText(
                    annotated_frame,
                    f"Vert Drop: {vertical_drop:.2f}",
                    (int(x2) + 10, int(y2) - 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )
                cv2.putText(
                    annotated_frame,
                    f"Case: {case}",
                    (int(x2) + 10, int(y2) - 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
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
