from ultralytics import YOLO
import cv2 
import math
import time
from collections import defaultdict, deque

# Some variables
model = YOLO("yolo26n-pose.pt") # load an official model
cap = cv2.VideoCapture("FallDetection/data/random videos/fall17.mp4")
# cap = cv2.VideoCapture(0)
prev_time = time.time()

# --------------------------------------------Helpfer function to show FPS--------------------------------------------
def show_fps(prev_time, frame):
    # FPS calculation
    cur_time = time.time()
    fps = 1 / (cur_time - prev_time)
    prev_time = cur_time

    # draw FPS on screen
    cv2.putText(
        frame,
        f"FPS: {int(fps)}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0,255,0),
        2
    )

    return prev_time

# --------------------------------------------Helpfer function to show fall metrics--------------------------------------------
def fall_metrics(angles, xywh):
    # Detecting fall using velocity drop and change of body angle
    y_centers = [frame[1].item() for frame in xywh[-FALL_WINDOW:]]
    max_y = max(y_centers)
    min_y = min(y_centers)
    initial_h = xywh[-FALL_WINDOW:][0][3].item()
    initial_w = xywh[-FALL_WINDOW:][0][2].item()
    last_h = xywh[-1][3].item()
    last_w = xywh[-1][2].item()

    angle_change = max(angles) - min(angles)

    # max_y should be when the person completely fell onto the floor/surface
    if y_centers.index(max_y) > y_centers.index(min_y):  
        # First standing position then laying  
        if initial_h > initial_w:
            # Handle the normal laying position case
            if last_w > last_h: 
                vertical_drop = (max_y  - min_y) / initial_h
            # Handle the final position of person that results in a vertical bounding box 
            # Situation for fall15.mp4 when the whole body line is a straight line that makes a 90 degree angle to the frame
            else:
                # angle_change = 90
                ave_h = (initial_h + last_h) / 2
                vertical_drop = (max_y  - min_y) / ave_h
        # First laying position then keep laying  
        else:
            # Handle the case when person switches from lying to standing
            if initial_h / initial_w - last_h / last_w < -0.5 or last_h / last_w > 1:
                vertical_drop = 0
            # Handle the case when person falling in a horizontal posture
            # Situation for fall16.mp4 when the whole body line is a horizontal line that makes a 180 degree angle to the frame
            else:
                vertical_drop = (max_y  - min_y) / initial_h
    # This case means that the vertical change is upward not downward as in a fall
    else:
        vertical_drop = -(max_y - min_y) / initial_h

    return angle_change, vertical_drop


# --------------------------------------------Calculating body's angle--------------------------------------------
def body_angle(key_joints, conf):
    #  key_joints = [l_shoulder, r_shoulder, l_hip, r_hip, l_ankle, r_ankle]
    upper_avg_x = (key_joints[0][0] + key_joints[1][0]) / 2
    upper_avg_y = (key_joints[0][1] + key_joints[1][1]) / 2

    # Handle the case when the lower parts are all occluded
    if conf[2] < 0.1 and conf[3] < 0.1 and conf[4] < 0.25 and conf[5] < 0.25:
        return None
    # ankles are occluded
    elif conf[4] < 0.2 and conf[5] < 0.2:
        return None
    # hips are occluded
    elif conf[2] < 0.2 and conf[3] < 0.2:
        lower_avg_x = (key_joints[4][0] + key_joints[5][0]) / 2
        lower_avg_y = (key_joints[4][1] + key_joints[5][1]) / 2
    else:
        lower_avg_x = (key_joints[4][0] + key_joints[5][0]) / 2
        lower_avg_y = (key_joints[4][1] + key_joints[5][1]) / 2
    
    return math.degrees(math.atan2(abs(upper_avg_y-lower_avg_y), (abs(upper_avg_x-lower_avg_x))))

#------------------------------Detect stationary------------------------------
# def is_person_stationary(xywh, angles, stationary_window, movement_thresh, angle_thresh):
#     # Not enough data
#     if len(xywh) < stationary_window or len(angles) < stationary_window:
#         return False

#     recent_boxes = xywh[-stationary_window:]
#     recent_angles = angles[-stationary_window:]

#     # --- 1. Measure center movement ---
#     centers = [(b[0].item(), b[1].item()) for b in recent_boxes]

#     total_movement = 0
#     for i in range(1, len(centers)):
#         dx = centers[i][0] - centers[i-1][0]
#         dy = centers[i][1] - centers[i-1][1]
#         dist = math.sqrt(dx*dx + dy*dy)
#         total_movement += dist

#     avg_movement = total_movement / (stationary_window - 1)

#     # Normalize movement by body size (important!)
#     avg_height = sum([b[3].item() for b in recent_boxes]) / stationary_window
#     normalized_movement = avg_movement / avg_height

#     # --- 2. Measure angle stability ---
#     angle_variation = max(recent_angles) - min(recent_angles)

#     # --- 3. Decide ---
#     if normalized_movement < movement_thresh and angle_variation < angle_thresh:
#         return True

#     return False

# --------------------------------------------Detecting fall--------------------------------------------
def fall_detection(angles, xywh, conf, threshold_angle, threshold_drop):
    # If not really a person, skip
    # if conf < 0.15:
    #     return False
    case = "Case"

    # Detecting fall using velocity drop and change of body angle
    y_centers = [frame[1].item() for frame in xywh[-FALL_WINDOW:]]
    max_y = max(y_centers)
    min_y = min(y_centers)
    initial_h = xywh[-FALL_WINDOW:][0][3].item()
    initial_w = xywh[-FALL_WINDOW:][0][2].item()
    last_h = xywh[-1][3].item()
    last_w = xywh[-1][2].item()

    angle_change = max(angles) - min(angles)

    # max_y should be when the person completely fell onto the floor/surface
    if y_centers.index(max_y) > y_centers.index(min_y):  
        # First standing position then laying  
        if initial_h / initial_w > 1:
            # Handle the normal laying position case
            if last_w > last_h: 
                case = "Case 1"
                vertical_drop = (max_y  - min_y) / initial_h
            # Handle the final position of person that results in a vertical bounding box => either falling or just sitting down
            # Situation for fall15.mp4 when the whole body line is a straight line that makes a 90 degree angle to the frame
            else:
                # if conf < 0.5:
                #     angle_change = 90
                angle_change += 5
                ave_h = (initial_h + last_h) / 2
                vertical_drop = (max_y  - min_y) / ave_h
                case = "Case 2"
        # First laying position then keep laying  
        else:
            # Handle the case when person switches from lying to standing
            # if initial_h / initial_w - last_h / last_w < -0.5 or last_h / last_w > 1:
            if last_h / last_w > 1:
                vertical_drop = 0
                case = "Case 3"
            # Handle the case when person falling in a horizontal posture
            # Situation for fall16.mp4 when the whole body line is a horizontal line that makes a 180 degree angle to the frame
            else:
                vertical_drop = (max_y  - min_y) / initial_h - 0.1
                case = "Case 4"
                angle_change = 90
    # This case means that the vertical change is upward not downward as in a fall
    else:
        vertical_drop = -(max_y - min_y) / initial_h

    if angles[-1] > 50:
        return False

    if angle_change >= threshold_angle and vertical_drop >= threshold_drop:
        print(f'Angle : {angle_change:.1f}, Vert Drop: {vertical_drop:.2f}')
        print(case)
        return True
    
    return False




# Predict with the model 
FALL_WINDOW = 18 # Determine how many frames a fall should last
HISTORY = 40
info_history = defaultdict(lambda: {
    "angles": deque(maxlen=HISTORY),
    "xywh": deque(maxlen=HISTORY),
    "conf": deque(maxlen=HISTORY),
}) # Store the information for every person that's being tracked

while True:
    # Getting the information from the frame
    success, img = cap.read()
    if not success:
        print("Camera is not working properly")
        break
    results = model.track(img, persist=True, device="mps", verbose=False)
    r = results[0]     # Getting all the info for each frame coming out from the camera

    # Extracting certain information from the frame
    annotated_frame = r.plot() # Draw the frame
    keypoints = r.keypoints.xy
    kp_conf = r.keypoints.conf
    boxes = r.boxes
    ids = r.boxes.id
    
    # Get frame dimensions for top-right positioning
    frame_height, frame_width = annotated_frame.shape[:2]
    
    if ids is None:
        cv2.imshow("Webcam", annotated_frame)
        if cv2.waitKey(1) == ord('q'):
            break
        continue

    # Showing fps to the screen
    prev_time = show_fps(prev_time, annotated_frame)

    # Collecting the keypoints of people's bodies that we assume to stay still and are crucial to detect fall
    selected_joints = keypoints[:, [5,6,11,12,15,16], :] # [l_shoulder, r_shoulder, l_hip, r_hip, l_ankle, r_ankle]
    joints_conf = kp_conf[:, [5,6,11,12,15,16]]
    
    # Status tracking for display
    status_text = "OK"
    status_color = (0, 255, 0)
    
    # Storing information
    for i, id in enumerate(ids):
        id = int(id.item())
        angle = body_angle(selected_joints[i], joints_conf[i])

        if angle is None:
            continue

        # Keep track of angle of the bounding box
        x1,y1,x2,y2 = boxes.xyxy[i]
        cv2.putText(annotated_frame, str(int(angle)), (int(x2)-70, int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,0,0), 3)

        # Updating the history across people
        info_history[id]["angles"].append(angle)
        info_history[id]["xywh"].append(boxes.xywh[i])
        info_history[id]["conf"] = boxes.conf[i].item()

        angles = list(info_history[id]["angles"])
        xywh = list(info_history[id]["xywh"])
        conf = float(info_history[id]["conf"])

        # Keep track of fall metrics
        angle_change, vertical_drop = fall_metrics(
            angles[-FALL_WINDOW:], 
            xywh[-FALL_WINDOW:]
        )

        cv2.putText(
            annotated_frame,
            f"Angle Change: {angle_change:.1f}",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0,255,0),
            2
        )

        cv2.putText(
            annotated_frame,
            f"Vert Drop: {vertical_drop:.2f}",
            (20, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0,255,0),
            2
        )

        # Start detecting
        if fall_detection(angles[-FALL_WINDOW:], xywh, conf, 36, 0.25):
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

    # Showing the webcam and turn it off when q is pressed
    cv2.imshow("Webcam", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    
cap.release()
cv2.destroyAllWindows()