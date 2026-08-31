import cv2
import time
from datetime import datetime, timezone, timedelta
import os
import dotenv
from services.fall_services.fall_detector import FallDetector
from services.fall_services.log_fall_events import log_fall_events
from services.camera_services.stream_manager import get_camera_stream


dotenv.load_dotenv()
THRESHOLD_ANGLE = int(os.getenv("THRESHOLD_ANGLE"))
THRESHOLD_DROP = float(os.getenv("THRESHOLD_DROP"))

# Track active camera instances
active_camera_instances = {}

def generate_mjpeg_stream(camera_id, camera_name, stream):
    """Generator that yields JPEG frames as MJPEG stream with fall detection"""
    if stream is None: 
        print("Camera stream is missing")
        return
    
    # Read completed YOLO results from the background inference thread
    fall_detector = None
    fall_window = None
    prev_time = time.time()
    last_result_time = None

    try:
        while stream.consumer_thread and stream.consumer_thread.is_alive():
            # Get the latest result and the frame that produced it
            r, result_time, frame_fall = stream.get_latest_result()

            # Wait when inference has not completed or this result was already used
            if r is None or result_time == last_result_time:
                time.sleep(0.01)
                continue

            # Wait for the first reliable inference FPS measurement
            stream_status = stream.get_status()
            producer_fps = stream_status["producer_fps"]
            consumer_fps = stream_status["consumer_fps"]

            if consumer_fps <= 0:
                time.sleep(0.01)
                continue

            # Create one detector using the actual inference rate
            if fall_detector is None:
                fall_window = max(2, int(consumer_fps * 1.5))
                fall_detector = FallDetector(history_size=fall_window, threshold_angle=THRESHOLD_ANGLE, threshold_drop=THRESHOLD_DROP)

            last_result_time = result_time

            # Draw boxes and keypoints from the cached YOLO result
            annotated_frame = r.plot()
            
            # Get detection data
            keypoints = r.keypoints.xy
            kp_conf = r.keypoints.conf
            boxes = r.boxes
            ids = r.boxes.id
            
            # Get frame dimensions for top-right positioning
            frame_height, frame_width = annotated_frame.shape[:2]
            
            # Show the camera capture FPS on the first line
            cv2.putText(
                annotated_frame,
                f"Producer FPS: {producer_fps:.1f}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1
            )

            # Show the YOLO inference FPS on the second line
            cv2.putText(
                annotated_frame,
                f"Consumer FPS: {consumer_fps:.1f}",
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1
            )
            
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
                        
                        is_fall = fall_detector.detect_fall(recent_angles, recent_xywh, conf, fall_window)
                        # Draw fall detection result
                        if is_fall:
                            print("FALLLLLLLL")
                            status_text = "FALL DETECTED!"
                            status_color = (0, 0, 255)
            
            # Display status at top-right
            text_size = cv2.getTextSize(f"Status: {status_text}", cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
            text_x = frame_width - text_size[0] - 20
            text_y = 50
            
            cv2.putText(
                annotated_frame,
                f"Status: {status_text}",
                (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                status_color,
                2
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
    finally:
        # The stream may close before the first result arrives
        if fall_detector is not None:
            fall_detector.info_history.clear()


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
