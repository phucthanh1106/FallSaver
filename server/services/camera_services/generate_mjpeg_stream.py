import time

import cv2

from services.camera_services.stream_manager import (
    stop_all_camera_streams,
    stop_camera_stream,
)


def generate_mjpeg_stream(camera_id, camera_name, stream):
    """
    Stream the latest completed inference result as MJPEG.

    YOLO inference and fall detection are already performed by CameraStream.
    This generator only draws the cached result, displays stream information,
    encodes the frame, and sends it to the client.
    """
    if stream is None:
        print(f"Camera stream {camera_id} is missing")
        return

    last_result_time = None
    
    while (
        not stream.stop_event.is_set()
        and stream.consumer_thread
        and stream.consumer_thread.is_alive()
    ):
        # These three values belong to the same inference result.
        result, result_time, frame_fall = stream.get_latest_result()

        # No inference has completed yet, or this result was already displayed.
        if result is None or result_time == last_result_time:
            stream.stop_event.wait(0.01)
            continue

        last_result_time = result_time

        # Read capture and inference performance.
        stream_status = stream.get_status()
        producer_fps = stream_status["producer_fps"]
        consumer_fps = stream_status["consumer_fps"]

        # Draw YOLO boxes, tracking IDs, and pose keypoints.
        annotated_frame = result.plot()
        _, frame_width = annotated_frame.shape[:2]

        # Producer FPS
        cv2.putText(
            annotated_frame,
            f"Producer FPS: {producer_fps:.1f}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
        )

        # Consumer FPS
        cv2.putText(
            annotated_frame,
            f"Consumer FPS: {consumer_fps:.1f}",
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
        )

        # Fall status
        if frame_fall:
            status_text = "FALL DETECTED!"
            status_color = (0, 0, 255)
        else:
            status_text = "OK"
            status_color = (0, 255, 0)

        full_status_text = f"Status: {status_text}"

        text_size = cv2.getTextSize(
            full_status_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            2,
        )[0]

        text_x = frame_width - text_size[0] - 20

        cv2.putText(
            annotated_frame,
            full_status_text,
            (text_x, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            status_color,
            2,
        )

        # Encode the annotated frame as JPEG.
        encoded, buffer = cv2.imencode(".jpg", annotated_frame)

        if not encoded:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Content-Length: "
            + str(len(frame_bytes)).encode()
            + b"\r\n\r\n"
            + frame_bytes
            + b"\r\n"
        )


def release_camera(camera_id):
    """
    Backward-compatible wrapper for camera.py.

    camera_id must be the Supabase camera row ID, not the Hikvision channel
    index such as 102 or 202.
    """
    stop_camera_stream(camera_id)


def release_all_cameras():
    """Stop every camera stream managed by stream_manager.py."""
    stop_all_camera_streams()