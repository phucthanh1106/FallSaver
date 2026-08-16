import cv2
import time
from datetime import datetime, timezone, timedelta
import os
import dotenv
from ultralytics import YOLO
from services.fall_detector import FallDetector
from services.get_connected_cameras import get_camera_source
from services.log_fall_events import log_fall_events

dotenv.load_dotenv()
THRESHOLD_ANGLE = int(os.getenv("THRESHOLD_ANGLE"))
THRESHOLD_DROP = float(os.getenv("THRESHOLD_DROP"))

# Load the model once
model = YOLO("/Users/tyler/FallSaver/server/weights/yolo26n-pose.pt", task="pose")

# Track active camera instances
active_camera_instances = {}

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


# Track the most recent fall separately for each person on each camera
fall_events_time = {}


def generate_mjpeg_stream(camera_index):
    """Generator that yields JPEG frames as MJPEG stream with fall detection"""
    cap = cv2.VideoCapture(get_camera_source(camera_index))
    
    # Store the camera instance for later release
    active_camera_instances[camera_index] = cap
    
    if not cap.isOpened():
        print("Camera failed to open")

        if camera_index in active_camera_instances:
            del active_camera_instances[camera_index]

        return
    
    # Use the camera FPS to create a fixed 1.5-second detection window
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 25
    fall_window = max(2, int(video_fps * 1.5))
    fall_detector = FallDetector(history_size=fall_window, threshold_angle=THRESHOLD_ANGLE, threshold_drop=THRESHOLD_DROP)
    
    prev_time = time.time()

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        
        # Resize while preserving the original aspect ratio
        new_width = 640
        scale = new_width / frame.shape[1]
        new_height = int(frame.shape[0] * scale)
        frame = cv2.resize(frame, (new_width, new_height))
        
        # Run fall detection model
        results = model.track(frame, persist=True, conf=0.1, device="cpu", verbose=False)
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
                fall_detector.update_history(person_id, angle, boxes.xywh[i], boxes.conf[i].item())
                
                # Get history
                angles, xywh, conf = fall_detector.get_history(person_id)
                
                # Detect fall
                if len(angles) >= fall_window / 4.5:
                    recent_angles = angles[-fall_window:]
                    recent_xywh = xywh[-fall_window:]
                    angle_change, vertical_drop, case = fall_detector.fall_metrics(recent_angles, recent_xywh, fall_window)
                    
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
                    cv2.putText(
                        annotated_frame,
                        f"Case: {case}",
                        (20, 160),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2
                    )
                    
                    is_fall = fall_detector.detect_fall(recent_angles, recent_xywh, conf, fall_window)
                    # Draw fall detection result
                    if is_fall:
                        now = datetime.now(timezone.utc)
                        event_key = (camera_index, person_id)
                        last_fall = fall_events_time.get(event_key)

                        # Ensure that repeated events for the same person do not overlap
                        if last_fall is None or (now - last_fall).total_seconds() > 2:
                            fall_events_time[event_key] = now
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

    cap.release()
    active_camera_instances.pop(camera_index, None)
    fall_detector.info_history.clear()
    for event_key in [key for key in fall_events_time if key[0] == camera_index]:
        fall_events_time.pop(event_key, None)


def release_camera(camera_index):
    """Release a specific camera and clean up resources"""
    if camera_index in active_camera_instances:
        cap = active_camera_instances[camera_index]
        cap.release()
        del active_camera_instances[camera_index]
        print(f"Camera {camera_index} released")


def release_all_cameras():
    """Release all active cameras"""
    for camera_index in list(active_camera_instances.keys()):
        release_camera(camera_index)
