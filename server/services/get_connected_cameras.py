import cv2
import base64 
# Base64 is a binary-to-text encoding scheme 
# that converts binary data (like images or executable files) into a sequence of 64 printable ASCII characters

def get_connected_cameras():
    available = []

    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            # Let the camera warm up a little bit so the frame looks better
            for _ in range(10):
                cap.read()
            
            # Now capture the "real" frame
            success, img = cap.read()

            if success:
                img = cv2.resize(img, (640, 320))
                # Convert frame to JPEG
                _, buffer = cv2.imencode('.jpg', img)

                # Encode to Base64 string
                frame_base64 = base64.b64encode(buffer).decode('utf-8')

                available.append({
                    "index": i, 
                    "name": f'Camera {i + 1}',
                    "frame": frame_base64, 
                })
            cap.release()
    return available