import base64
import socket
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import cv2

# A dictionary that holds connection for a camera index
connected_camera_sources = {}

def get_camera_source(camera_index):
    return connected_camera_sources.get(camera_index, camera_index)


# Open the camera to get its frame
def read_camera(camera_index, ipv4=None, username=None, password=None):
    if ipv4:
        authentication = ""

        if username and password:
            authentication = f"{quote(username, safe='')}:{quote(password, safe='')}@"

        source = f"rtsp://{authentication}{ipv4}:554/Streaming/Channels/{camera_index}"
        cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG, [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000])
    else:
        source = camera_index
        cap = cv2.VideoCapture(source)

    try:
        if not cap.isOpened():
            return None

        success, image = cap.read()

        if not success:
            return None

        image = cv2.resize(image, (640, 320))
        encoded, buffer = cv2.imencode('.jpg', image)

        if not encoded:
            return None

        connected_camera_sources[camera_index] = source
        camera_number = camera_index // 100 if ipv4 else camera_index + 1

        return {
            "index": camera_index,
            "name": f"Camera {camera_number}",
            "frame": base64.b64encode(buffer).decode('utf-8'),
        }
    finally:
        cap.release()



def scan_cameras(ipv4=None, username=None, password=None, camera_indexes=None):
    if ipv4:
        try:
            with socket.create_connection((ipv4, 554), timeout=2):
                pass
        except OSError:
            return []

    if camera_indexes is None:
        camera_indexes = list(range(102, 1003, 100)) if ipv4 else list(range(10))

    if not camera_indexes:
        return []
    
    if not ipv4:
        cameras = [read_camera(camera_index) for camera_index in camera_indexes]
        return [camera for camera in cameras if camera]

    worker_count = min(4, len(camera_indexes))

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        cameras = executor.map(lambda camera_index: read_camera(camera_index, ipv4, username, password), camera_indexes)

    # a camera includes frame, index and name
    return [camera for camera in cameras if camera]