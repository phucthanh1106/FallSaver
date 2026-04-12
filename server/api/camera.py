import base64
import cv2
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from services.get_connected_cameras import get_connected_cameras
from services.generate_mjpeg_stream import generate_mjpeg_stream

camera_router = APIRouter()

@camera_router.get("/scan")
async def scan_usb_ports():
    # Call "controller" logic
    return get_connected_cameras()


@camera_router.get("/feed/{camera_index}")
async def get_camera_def(camera_index: int):
    # Stream live MJPEG feed from camera
    return StreamingResponse(generate_mjpeg_stream(camera_index), media_type="multipart/x-mixed-replace; boundary=frame")