import cv2
import math
import time
from ultralytics import YOLO
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque


class FallDetector:
    """Handles all fall detection logic"""
    
    def __init__(self, history_size=40, threshold_angle=36, threshold_drop=0.25):
        self.HISTORY = history_size
        self.THRESHOLD_ANGLE = threshold_angle
        self.THRESHOLD_DROP = threshold_drop
        
        self.info_history = defaultdict(lambda: {
            "angles": deque(maxlen=self.HISTORY),
            "xywh": deque(maxlen=self.HISTORY),
            "conf": deque(maxlen=self.HISTORY),
        })
    
    def body_angle(self, key_joints, conf):
        """Calculate body angle from keypoints"""
        # key_joints = [l_shoulder, r_shoulder, l_hip, r_hip, l_ankle, r_ankle]
        upper_avg_x = (key_joints[0][0] + key_joints[1][0]) / 2
        upper_avg_y = (key_joints[0][1] + key_joints[1][1]) / 2

        # Handle the case when the lower parts are all occluded
        if conf[2] < 0.1 and conf[3] < 0.1 and conf[4] < 0.25 and conf[5] < 0.25:
            return None
        
        # Ankles visible - use them
        if conf[4] > 0.2 and conf[5] > 0.2:
            lower_avg_x = (key_joints[4][0] + key_joints[5][0]) / 2
            lower_avg_y = (key_joints[4][1] + key_joints[5][1]) / 2
        # Hips visible - use them
        elif conf[2] > 0.2 and conf[3] > 0.2:
            lower_avg_x = (key_joints[2][0] + key_joints[3][0]) / 2
            lower_avg_y = (key_joints[2][1] + key_joints[3][1]) / 2
        else: 
            # return None
            lower_avg_x = (key_joints[4][0] + key_joints[5][0]) / 2
            lower_avg_y = (key_joints[4][1] + key_joints[5][1]) / 2
        
        return math.degrees(math.atan2(abs(upper_avg_y - lower_avg_y), abs(upper_avg_x - lower_avg_x)))

    def fall_metrics(self, angles, xywh, fall_window):
        """Calculate fall metrics"""
        y_centers = [frame[1].item() for frame in xywh[-fall_window:]]
        max_y = max(y_centers)
        min_y = min(y_centers)
        initial_h = xywh[-fall_window:][0][3].item()
        initial_w = xywh[-fall_window:][0][2].item()
        last_h = xywh[-1][3].item()
        last_w = xywh[-1][2].item()

        angle_change = max(angles) - min(angles)

        # max_y should be when the person completely fell onto the floor/surface
        if y_centers.index(max_y) > y_centers.index(min_y):  
            # First standing position then laying  
            if initial_h / initial_w > 1:
                # Handle the normal laying position case
                if last_w > last_h: 
                    vertical_drop = (max_y - min_y) / initial_h
                # Handle the final position of person that results in a vertical bounding box
                else:
                    angle_change += 5
                    ave_h = (initial_h + last_h) / 2
                    vertical_drop = (max_y - min_y) / ave_h
            # First laying position then keep laying  
            else:
                # Handle the case when person switches from lying to standing
                if last_h / last_w > 1 or initial_h / initial_w - last_h / last_w < -0.5:
                    vertical_drop = 0
                # Handle the case when person falling in a horizontal posture
                else:
                    vertical_drop = (max_y - min_y) / initial_h - 0.05
                    angle_change = 90
        # This case means that the vertical change is upward not downward as in a fall
        else:
            vertical_drop = -(max_y - min_y) / initial_h

        return angle_change, vertical_drop

    def detect_fall(self, angles, xywh, conf, fall_window):
        # Reject if standing posture (high angle means upright)
        if angles[-1] > 60:
            return False
        
        # Use fall_metrics to calculate angle_change and vertical_drop
        angle_change, vertical_drop = self.fall_metrics(angles, xywh, fall_window)

        return angle_change >= self.THRESHOLD_ANGLE and vertical_drop >= self.THRESHOLD_DROP

    def update_history(self, person_id, angle, xywh, conf):
        """Update history for a person"""
        self.info_history[person_id]["angles"].append(angle)
        self.info_history[person_id]["xywh"].append(xywh)
        self.info_history[person_id]["conf"] = conf
    
    def get_history(self, person_id):
        """Get history for a person"""
        angles = list(self.info_history[person_id]["angles"])
        xywh = list(self.info_history[person_id]["xywh"])
        conf = float(self.info_history[person_id]["conf"])
        return angles, xywh, conf

# Load the model once
model = YOLO("/Users/tyler/FallSaver/server/yolo26n-pose.onnx", task="pose")

# Initialize fall detector
fall_detector = FallDetector(history_size=70, threshold_angle=35, threshold_drop=0.25)

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

    FALL_WINDOW = int(fps * 1.1)
    return prev_time, FALL_WINDOW


# Add fall event tracking
fall_events_time = []


def generate_mjpeg_stream(path):
    """Generator that yields JPEG frames as MJPEG stream with fall detection"""
    cap = cv2.VideoCapture(path)
    
    
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
        results = model.track(frame, persist=True, device="cpu", verbose=False)
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
cap = cv2.VideoCapture("/Users/tyler/FallSaver/FallDetection/data/random videos/fall7.mp4")
prev_time = time.time()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    results = model.track(frame, persist=True, device="cpu", verbose=False)
    r = results[0]
    annotated_frame = r.plot()
    
    keypoints = r.keypoints.xy
    kp_conf = r.keypoints.conf
    boxes = r.boxes
    ids = r.boxes.id
    
    prev_time, FALL_WINDOW = show_fps(prev_time, annotated_frame)
    
    status_text = "OK"
    status_color = (0, 255, 0)
    
    if ids is not None:
        selected_joints = keypoints[:, [5, 6, 11, 12, 15, 16], :]
        joints_conf = kp_conf[:, [5, 6, 11, 12, 15, 16]]
        
        for i, id in enumerate(ids):
            id = int(id.item())
            angle = fall_detector.body_angle(selected_joints[i], joints_conf[i])
            
            if angle is None:
                continue
            
            fall_detector.update_history(id, angle, boxes.xywh[i], boxes.conf[i].item())
            angles, xywh, conf = fall_detector.get_history(id)

            # angle_change, vertical_drop = fall_detector.fall_metrics(
            #     angles[-FALL_WINDOW:], xywh[-FALL_WINDOW:], FALL_WINDOW
            # )
            
            # # Display metrics on frame
            # cv2.putText(annotated_frame, f"Angle Change: {angle_change:.1f}°", (20, 80),
            #             cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            # cv2.putText(annotated_frame, f"Vertical Drop: {vertical_drop:.2f}", (20, 120),
            #             cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if len(angles) >= FALL_WINDOW / 1.4:
                if fall_detector.detect_fall(angles[-FALL_WINDOW:], xywh, conf, FALL_WINDOW):
                    status_text = "FALL DETECTED!"
                    status_color = (0, 0, 255)
    
    frame_height, frame_width = annotated_frame.shape[:2]
    text_size = cv2.getTextSize(f"Status: {status_text}", cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
    text_x = frame_width - text_size[0] - 20
    text_y = 50
    
    cv2.putText(annotated_frame, f"Status: {status_text}", (text_x, text_y), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
    
    cv2.imshow("Fall Detection", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()