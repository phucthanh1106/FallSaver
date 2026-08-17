import base64
import cv2
from ipaddress import IPv4Address, IPv4Network
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.camera_services.get_connected_cameras import get_connected_cameras
from services.camera_services.generate_mjpeg_stream import generate_mjpeg_stream, release_camera
from services.auth_services.auth import get_current_user, get_user_database

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


class SavedCameraScanRequest(BaseModel):
    connection_id: str
    password: str | None = None


@camera_router.get("/scan")
async def get_saved_cameras(current_user=Depends(get_current_user), user_database=Depends(get_user_database)):
    try:
        response = user_database.table("cameras").select("id, index, name, frame, connection_id").eq("user_id", str(current_user.id)).order("index").execute()
        return response.data
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not load saved cameras") from error

@camera_router.post("/scan")
async def scan_network_cameras(connection: CameraScanRequest, current_user=Depends(get_current_user)):
    user_id = current_user.id

    if not any(connection.ipv4 in network for network in private_networks):
        raise HTTPException(status_code=400, detail="Enter a private IPv4 address")

    if bool(connection.username) != bool(connection.password):
        raise HTTPException(status_code=400, detail="Username and password must be entered together")

    return get_connected_cameras(str(connection.ipv4), connection.username, connection.password)


@camera_router.post("/scan/saved")
async def scan_saved_cameras(request: SavedCameraScanRequest, current_user=Depends(get_current_user), user_database=Depends(get_user_database)):
    try:
        connection_response = user_database.table("camera_connections").select("id, ipv4, username").eq("id", request.connection_id).eq("user_id", str(current_user.id)).execute()
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not load the saved camera connection") from error

    if not connection_response.data:
        raise HTTPException(status_code=404, detail="Camera connection not found")

    connection = connection_response.data[0]

    if connection.get("username") and not request.password:
        raise HTTPException(status_code=400, detail="The camera password is unavailable on this device")

    fresh_cameras = get_connected_cameras(connection["ipv4"], connection.get("username"), request.password)
    fresh_frames = {camera["index"]: camera["frame"] for camera in fresh_cameras}

    try:
        saved_response = user_database.table("cameras").select("id, index, name, frame, connection_id").eq("user_id", str(current_user.id)).eq("connection_id", request.connection_id).order("index").execute()
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not load saved cameras") from error

    return [{**camera, "frame": fresh_frames.get(camera["index"], camera["frame"])} for camera in saved_response.data]


@camera_router.get("/feed/{camera_index}")
async def get_camera_def(camera_index: int, current_user=Depends(get_current_user), user_database=Depends(get_user_database)):
    user_id = current_user.id

    try:
        cameras_db = user_database.table("cameras").select("connection_id").eq("user_id", user_id).execute()
        connection_id = cameras_db.data[0]["connection_id"]

        camera_connections = user_database.table("camera_connections").select("ipv4, username, password_secret_id").eq("id", connection_id).execute()
        return
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not load saved camera connections") from error

    # Store camera index as active
    active_cameras[camera_index] = True
    # Stream live MJPEG feed from camera
    return StreamingResponse(generate_mjpeg_stream(camera_index), media_type="multipart/x-mixed-replace; boundary=frame")


@camera_router.post("/stop/{camera_index}")
async def stop_camera(camera_index: int, current_user=Depends(get_current_user)):
    user_id = current_user.id

    """Stop the camera stream and release resources"""
    if camera_index in active_cameras:
        del active_cameras[camera_index]
    release_camera(camera_index)
    return {"status": "Camera stopped", "camera_index": camera_index}
