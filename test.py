import os

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"

import cv2
import getpass


username = input("DVR username: ")
password = getpass.getpass("DVR password: ")

url = (
    f"rtsp://{username}:{password}"
    "@192.168.1.9:554/Streaming/channels/601"
)

cap = cv2.VideoCapture(url)

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
