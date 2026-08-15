import os

# Tell FFmpeg to drop delays, lower probe time, and use UDP
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|buffer_size;1048576|max_delay;500000"
)

import cv2
import getpass

username = input("DVR username: ")
password = getpass.getpass("DVR password: ")

url = (
    f"rtsp://{username}:{password}"
    "@192.168.1.9:554/Streaming/channels/602"
)

cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

if not cap.isOpened():
    print("Could not connect to the camera.")
    raise SystemExit

print("Connected. Press q to stop.")

while True:
    success, frame = cap.read()

    if not success:
        print("Could not read a frame.")
        break

    cv2.imshow("Hikvision Camera", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
