import base64
import cv2
from ipaddress import IPv4Address, IPv4Network
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.get_connected_cameras import get_connected_cameras
from services.generate_mjpeg_stream import generate_mjpeg_stream, release_camera

camera_router = APIRouter()
active_cameras = {}
private_networks = (
    IPv4Network("10.0.0.0/8"),
    IPv4Network("172.16.0.0/12"),
    IPv4Network("192.168.0.0/16"),
)


class CameraScanRequest(BaseModel):
    ipv4: IPv4Address
    username: str | None = None
    password: str | None = None

@camera_router.get("/scan")
async def scan_usb_ports():
    # Call "controller" logic
    return get_connected_cameras()


@camera_router.post("/scan")
async def scan_network_cameras(connection: CameraScanRequest):
    if not any(connection.ipv4 in network for network in private_networks):
        raise HTTPException(status_code=400, detail="Enter a private IPv4 address")

    if bool(connection.username) != bool(connection.password):
        raise HTTPException(status_code=400, detail="Username and password must be entered together")

    return get_connected_cameras(str(connection.ipv4), connection.username, connection.password)


@camera_router.get("/feed/{camera_index}")
async def get_camera_def(camera_index: int):
    # Store camera index as active
    active_cameras[camera_index] = True
    # Stream live MJPEG feed from camera
    return StreamingResponse(generate_mjpeg_stream(camera_index), media_type="multipart/x-mixed-replace; boundary=frame")


@camera_router.post("/stop/{camera_index}")
async def stop_camera(camera_index: int):
    """Stop the camera stream and release resources"""
    if camera_index in active_cameras:
        del active_cameras[camera_index]
    release_camera(camera_index)
    return {"status": "Camera stopped", "camera_index": camera_index}
