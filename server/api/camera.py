import base64
import cv2
from ipaddress import IPv4Address, IPv4Network
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.camera_services.camera_scanner import scan_cameras
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
def scan_network_cameras(connection: CameraScanRequest, current_user=Depends(get_current_user)):
    user_id = current_user.id

    if not any(connection.ipv4 in network for network in private_networks):
        raise HTTPException(status_code=400, detail="Enter a private IPv4 address")

    if bool(connection.username) != bool(connection.password):
        raise HTTPException(status_code=400, detail="Username and password must be entered together")

    return scan_cameras(str(connection.ipv4), connection.username, connection.password)


@camera_router.post("/scan/saved")
def scan_saved_cameras(request: SavedCameraScanRequest, current_user=Depends(get_current_user), user_database=Depends(get_user_database)):
    # 1. Query all rows of the connection that match the connection id that the request asks for
    try:
        connection_response = user_database.table("camera_connections").select("id, ipv4, username").eq("id", request.connection_id).eq("user_id", str(current_user.id)).execute()
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not load the saved camera connection") from error

    # 2. Handle the cases when that connection id DNE
    if not connection_response.data:
        raise HTTPException(status_code=404, detail="Camera connection not found")

    # 3. Since a conection id can store the same info (ipv4, user, pwd) across multiple cameras
    #  => Take only the first row as representative
    connection = connection_response.data[0]

    # 4. If username exists but pwd DNE then this connection can't be accessed
    if connection.get("username") and not request.password:
        raise HTTPException(status_code=400, detail="The camera password is unavailable on this device")

    # 5. Load the saved cameras and extract the indexes
    try:
        saved_response = user_database.table("cameras").select("id, index, name, frame, connection_id").eq("user_id", str(current_user.id)).eq("connection_id", request.connection_id).order("index").execute()
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not load saved cameras") from error

    camera_indexes = [camera["index"] for camera in saved_response.data]

    if not camera_indexes:
        return []

    # 6. Now we have the camera connection and saved camera indexes => Query fresh frames 
    fresh_cameras = scan_cameras(connection["ipv4"], connection.get("username"), request.password, camera_indexes)

    if not fresh_cameras:
        raise HTTPException(status_code=503, detail="Camera network is unavailable")

    # 6. Create a dictionary that stores camera index as key and the new frame as value
    fresh_frames = {camera["index"]: camera["frame"] for camera in fresh_cameras}

    # 8. Based on the old cameras, get the indexes of them and then if that index in fresh_frames
    # => Replace the old frame to the new one
    cameras_with_latest_frames = []

    for camera in saved_response.data:
        camera_index = camera["index"]

        if camera_index in fresh_frames:
            camera["frame"] = fresh_frames[camera_index]

        cameras_with_latest_frames.append(camera)

    return cameras_with_latest_frames


@camera_router.get("/feed/{camera_index}")
def get_camera_def(camera_index: int, current_user=Depends(get_current_user), user_database=Depends(get_user_database)):
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
