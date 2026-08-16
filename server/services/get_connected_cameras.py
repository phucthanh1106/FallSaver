import base64
from urllib.parse import quote

import cv2


connected_camera_sources = {}


def get_camera_source(camera_index):
    return connected_camera_sources.get(camera_index, camera_index)


def get_connected_cameras(ipv4=None, username=None, password=None):
    available = []

    if ipv4:
        camera_indexes = range(102, 1003, 100)
    else:
        camera_indexes = range(10)

    for camera_index in camera_indexes:
        if ipv4:
            authentication = ""
            if username and password:
                authentication = f"{quote(username, safe='')}:{quote(password, safe='')}@"
            source = f"rtsp://{authentication}{ipv4}:554/Streaming/Channels/{camera_index}"
        else:
            source = camera_index

        cap = cv2.VideoCapture(source)

        try:
            if not cap.isOpened():
                continue

            # Read a few frames so the preview is not the camera's first incomplete frame.
            for _ in range(3):
                cap.read()

            success, image = cap.read()
            if not success:
                continue

            image = cv2.resize(image, (640, 320))

            # Convert frame to JPEG
            encoded, buffer = cv2.imencode('.jpg', image)
            if not encoded:
                continue

            connected_camera_sources[camera_index] = source
            camera_number = camera_index // 100 if ipv4 else camera_index + 1
            available.append({
                "index": camera_index,
                "name": f"Camera {camera_number}",
                "frame": base64.b64encode(buffer).decode('utf-8'),
            })
        finally:
            cap.release()

    return available
