import cv2
import math
import time
from ultralytics import YOLO
from services.fall_detector import FallDetector
from services.log_fall_events import log_fall_events
from datetime import datetime, timezone, timedelta

# Load the model once
model = YOLO("yolo26n-pose.pt")

# Initialize fall detector
fall_detector = FallDetector(history_size=40, threshold_angle=36, threshold_drop=0.25)

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

    FALL_WINDOW = int(fps * 1.67)
    return prev_time, FALL_WINDOW


# Add fall event tracking
fall_events_time = []


def generate_mjpeg_stream(camera_index):
    """Generator that yields JPEG frames as MJPEG stream with fall detection"""
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print("Camera failed to open")
        return
    
    prev_time = time.time()

    while True:
        success, frame = cap.read()
        if not success:
            break
        
        # Resize frame for performance
        frame = cv2.resize(frame, (640, 480))
        
        # Run fall detection model
        results = model.track(frame, persist=True, device="mps", verbose=False)
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
        prev_time, FALL_WINDOW = show_fps(prev_time, annotated_frame)
        
        # Status tracking for display
        status_text = "OK"
        status_color = (0, 255, 0)
        
        if ids is not None:
            selected_joints = keypoints[:, [5, 6, 11, 12, 15, 16], :]
            joints_conf = kp_conf[:, [5, 6, 11, 12, 15, 16]]
            
            for i, id in enumerate(ids):
                id = int(id.item())
                
                # Calculate body angle
                angle = fall_detector.body_angle(selected_joints[i], joints_conf[i])
                
                # Skip if angle is None (occluded)
                if angle is None:
                    continue
                
                x1, y1, x2, y2 = boxes.xyxy[i]
                
                # Display body angle
                cv2.putText(
                    annotated_frame,
                    f"Angle: {int(angle)}°",
                    (int(x2) - 70, int(y1) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 0, 0),
                    2
                )
                
                # Update history using the detector
                fall_detector.update_history(id, angle, boxes.xywh[i], boxes.conf[i].item())
                
                # Get history
                angles, xywh, conf = fall_detector.get_history(id)
                
                # Detect fall
                if len(angles) >= FALL_WINDOW:
                    angle_change, vertical_drop = fall_detector.fall_metrics(
                        angles[-FALL_WINDOW:],
                        xywh[-FALL_WINDOW:],
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
                    if fall_detector.detect_fall(angles[-FALL_WINDOW:], xywh, conf, FALL_WINDOW):
                        if len(fall_events_time) == 0:
                            fall_events_time.append(datetime.now(timezone.utc).isoformat())
                            log_fall_events(camera_id=camera_index, angle_change=float(angle_change), vertical_drop=float(vertical_drop))
                        else:
                            now = datetime.now(timezone.utc)
                            last_fall = datetime.fromisoformat(fall_events_time[-1])
                            time_diff = now - last_fall
                            # Ensure that falls don't overlap each other 
                            if time_diff.total_seconds() > 2:
                                fall_events_time.append(datetime.now(timezone.utc).isoformat())
                                log_fall_events(camera_id=camera_index, angle_change=float(angle_change), vertical_drop=float(vertical_drop))
                        
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