from ultralytics import YOLO
import cv2 
import os
import math
from collections import defaultdict, deque


# Some variables 
model = YOLO("yolo26m-pose.pt") # load an official model
WINDOW = 50
info_history = defaultdict(lambda: {
    "angles": deque(maxlen=WINDOW),
    "xywh": deque(maxlen=WINDOW),
    "conf": deque(maxlen=WINDOW)
}) # Store the information for every person that's being tracked

def body_angle(key_joints):
    upper_avg_x = (key_joints[0][0] + key_joints[1][0]) / 2
    upper_avg_y = (key_joints[0][1] + key_joints[1][1]) / 2

    # Handle the case when the ankle are occluded
    if key_joints[4] == () or key_joints[5] == ():
        lower_avg_x = (key_joints[2][0] + key_joints[3][0]) / 2
        lower_avg_y = (key_joints[2][1] + key_joints[3][1]) / 2
    else: 
        lower_avg_x = (key_joints[4][0] + key_joints[5][0]) / 2
        lower_avg_y = (key_joints[4][1] + key_joints[5][1]) / 2


    # Handle the case when divide by 0
    epsilon = 0
    if abs(upper_avg_x-lower_avg_x) == 0:
        epsilon = 0.0001
    
    return math.degrees(math.atan(abs(upper_avg_y - lower_avg_y) / (abs(upper_avg_x-lower_avg_x) + epsilon)))


# Load every image from the laying dataset and get info
def show_image(img_path): 
    cap = cv2.VideoCapture(img_path)

    success, img = cap.read()
    results = model.track(img, verbose=False)
    r = results[0]

    
    annotated_frame = r.plot()
    keypoints = r.keypoints.xy
    boxes = r.boxes
    ids = boxes.id

    selected_joints = keypoints[:, [5,6,11,12,15,16], :] # [l_shoulder, r_shoulder, l_hip, r_hip, l_ankle, r_ankle]
    
    for i, id in enumerate(ids):
        id = int(id.item())
        info_history[id]["angles"].append(body_angle(selected_joints[i]))
        info_history[id]["xywh"].append(boxes.xywh[i].tolist())
        info_history[id]["conf"].append(boxes.conf[i].item())
    
    print(f'{os.path.basename(img_path)}: {info_history}')
    print("\n")

    cv2.imshow(os.path.basename(img_path), annotated_frame)
    cv2.waitKey(0)
    cap.release()
    cv2.destroyAllWindows()

# Running the method:
path = "FallDetection/data/laying_dataset/images/laying91.png"
# path = "FallDetection/data/random images/standing91.png"
show_image(path)
    








