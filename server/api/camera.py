import base64
import cv2
from ipaddress import IPv4Address, IPv4Network
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from urllib.parse import quote
import cv2
import time

from services.camera_services.camera_scanner import scan_cameras
from services.camera_services.generate_mjpeg_stream import generate_mjpeg_stream, release_camera
from services.auth_services.auth import get_current_user, get_user_database
from services.camera_services.stream_manager import get_or_start_camera_stream, get_camera_stream

camera_router = APIRouter()
active_cameras = {}
private_networks = (
    IPv4Network("10.0.0.0/8"),
    IPv4Network("172.16.0.0/12"),
    IPv4Network("192.168.0.0/16"),
)

class CameraPasswordRequest(BaseModel):
    password: str | None = None


@camera_router.get("/saved")
def get_saved_cameras(current_user=Depends(get_current_user), user_database=Depends(get_user_database)):
    try:
        response = user_database.table("cameras").select("id, index, name, frame, connection_id").eq("user_id", str(current_user.id)).order("index").execute()
        return response.data
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not load saved cameras") from error

@camera_router.post("/discover/{connection_id}")
def discover_cameras(connection_id: str, request: CameraPasswordRequest, current_user=Depends(get_current_user), user_database=Depends(get_user_database)):
    try:
        # a user cannot scan another user’s saved connection ID since we do 2 .eq(user_id) and .eq(connection_id)
        connection_response = user_database.table("camera_connections").select("id, ipv4, username").eq("id", connection_id).eq("user_id", str(current_user.id)).execute()
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not load camera connection") from error

    if not connection_response.data:
        raise HTTPException(status_code=404, detail="Camera connection not found")

    connection = connection_response.data[0]
    ipv4 = IPv4Address(connection["ipv4"])
    username = connection.get("username")

    if not any(ipv4 in network for network in private_networks):
        raise HTTPException(status_code=400, detail="Saved IPv4 address is not private")

    if bool(username) != bool(request.password):
        raise HTTPException(status_code=400, detail="Camera password is unavailable")

    return scan_cameras(str(ipv4), username, request.password)


@camera_router.post("/refresh/{connection_id}")
def refresh_saved_cameras(connection_id: str, request: CameraPasswordRequest, current_user=Depends(get_current_user), user_database=Depends(get_user_database)):
    """
    The workflow is: Get all connections + all saved camera indexes =>
    """
    # 1. Query all rows of the connection that match the connection id that the request asks for
    try:
        connection_response = user_database.table("camera_connections").select("id, ipv4, username").eq("id", connection_id).eq("user_id", str(current_user.id)).execute()
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not load the saved camera connection") from error

    if not connection_response.data:
        raise HTTPException(status_code=404, detail="Camera connection not found")

    # 2. Since a conection id can store the same info (ipv4, user, pwd) across multiple cameras
    #  => Take only the first row as representative
    connection = connection_response.data[0]

    # 3. If username exists but pwd DNE then this connection can't be accessed
    if connection.get("username") and not request.password:
        raise HTTPException(status_code=400, detail="The camera password is unavailable on this device")

    # 4. Load the saved cameras and extract the indexes
    try:
        saved_response = user_database.table("cameras").select("id, index, name, frame, connection_id").eq("user_id", str(current_user.id)).eq("connection_id", connection_id).order("index").execute()
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not load saved cameras") from error

    if not saved_response.data:
        return []

    # 5. Extract connection's information
    username = connection.get("username")
    authentication = ""

    if username and request.password:
        encoded_username = quote(username, safe="")
        encoded_password = quote(request.password, safe="")
        authentication = f"{encoded_username}:{encoded_password}@"

    camera_stream_pairs = []

    # 6. Start every stream first so they connect concurrently
    for camera in saved_response.data:
        camera_index = camera["index"]
        source = f"rtsp://{authentication}{connection['ipv4']}:554/Streaming/Channels/{camera_index}"
        stream = get_or_start_camera_stream(camera["id"], source)
        camera_stream_pairs.append((camera, stream))

    # 7. Getting the frames
    for camera, stream in camera_stream_pairs:
        wait_start = time.monotonic()
        was_ready = stream.frame_ready.is_set()
        stream_identity = id(stream)

        # Get the first frame
        frame = stream.wait_for_first_frame()

        wait_time = time.monotonic() - wait_start
        print(f"Camera {camera['id']}: stream={stream_identity}, ready_before={was_ready}, wait={wait_time:.2f}s")

        # Keep the previous Supabase preview when no in-memory frame is available
        if frame is None:
            continue

        resized_frame = cv2.resize(frame, (640, 320))
        encoded, buffer = cv2.imencode(".jpg", resized_frame)

        if encoded:
            camera["frame"] = base64.b64encode(buffer).decode("utf-8")

    return saved_response.data


@camera_router.get("/feed/{connection_id}/{camera_id}")
def get_live_feed(camera_id: int, connection_id: str, current_user=Depends(get_current_user), user_database=Depends(get_user_database)):
    try:
        camera_response = user_database.table("cameras").select("id, name").eq("user_id", str(current_user.id)).eq("connection_id", connection_id).eq("id", camera_id).limit(1).execute()
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not load camera") from error

    if not camera_response.data:
        raise HTTPException(status_code=404, detail="Camera not found")

    camera = camera_response.data[0]
    stream = get_camera_stream(camera_id)

    if stream is None:
        raise HTTPException(status_code=409, detail="Camera stream has not been started")

    return StreamingResponse(generate_mjpeg_stream(camera_id, camera["name"], stream), media_type="multipart/x-mixed-replace; boundary=frame")


@camera_router.post("/stop/{camera_index}")
async def stop_camera(camera_index: int, current_user=Depends(get_current_user)):
    user_id = current_user.id

    """Stop the camera stream and release resources"""
    if camera_index in active_cameras:
        del active_cameras[camera_index]
    release_camera(camera_index)
    return {"status": "Camera stopped", "camera_index": camera_index}
