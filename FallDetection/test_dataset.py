from ultralytics import YOLO
import cv2 
import os
import math

# Some variables 
data_path = "FallDetection/data/laying_dataset/images"
model = YOLO("yolo11n-pose.pt") # load an official model
joints_xy = []

def body_angle(l_shoulder, r_shoulder, l_ankle, r_ankle):
    shoulder_avg_x = (l_shoulder[0] + r_shoulder[0]) / 2
    shoulder_avg_y = (l_shoulder[1] + r_shoulder[1]) / 2
    ankle_avg_x = (l_ankle[0] + r_ankle[0]) / 2
    ankle_avg_y = (l_ankle[1] + r_ankle[1]) / 2

    return math.degrees(math.atan(abs(shoulder_avg_y - ankle_avg_y) / abs(shoulder_avg_x-ankle_avg_x)))

# Load every image from the laying dataset and get info
for filename in os.listdir(data_path):
    path = os.path.join(data_path, filename)
    cap = cv2.VideoCapture(path)
    success, img = cap.read()
    
    if not success:
        break
    
    h_img, w_img, _ = img.shape
    results = model.track(img, verbose=False)
    r = results[0]
    
    # Shape: (num_people, 17, 2)
    for person in r.keypoints.xy:
        for i, joint in enumerate(person):
            x = int(joint[0])
            y = int(joint[1])
            joints_xy.append((x,y))

    angle = body_angle(joints_xy[5], joints_xy[6], joints_xy[15], joints_xy[16])

    print(f'{filename}: {angle}')
    print("\n")
    
    joints_xy = []
    
    








