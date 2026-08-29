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
from services.camera_services.camera_credentials import encrypt_camera_password, decrypt_camera_password

camera_router = APIRouter()
active_cameras = {}
private_networks = (
    IPv4Network("10.0.0.0/8"),
    IPv4Network("172.16.0.0/12"),
    IPv4Network("192.168.0.0/16"),
)

# Information required to create or update a camera connection.
class CameraConnectionRequest(BaseModel):
    ipv4: str
    username: str | None = None
    password: str | None = None


@camera_router.get("/")
def get_saved_cameras(current_user=Depends(get_current_user), user_database=Depends(get_user_database)):
    try:
        response = user_database.table("cameras").select("id, index, name, frame, connection_id").eq("user_id", str(current_user.id)).order("index").execute()
        return response.data
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not load saved cameras") from error

@camera_router.post("/connections")
def save_camera_connection(request: CameraConnectionRequest, current_user=Depends(get_current_user), user_database=Depends(get_user_database)):
    # 1. Extracting basic information of a connection (ipv4, username, pwd)
    try:
        ipv4 = IPv4Address(request.ipv4)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IPv4 address")

    # Only allow private household addresses.
    if not any(ipv4 in network for network in private_networks):
        raise HTTPException(status_code=400, detail="IPv4 address must be private")

    if request.username:
        username = request.username.strip()
    else:
        username = None

    # Authentication requires both a username and password.
    if bool(username) != bool(request.password):
        raise HTTPException(status_code=400, detail="Username and password must be provided together")

    # Encrypt the password before it reaches Supabase.
    encrypted_password = encrypt_camera_password(request.password)

    # 2. Store these information on supabase
    try:
        response = user_database.table("camera_connections").upsert({
            "user_id": str(current_user.id),
            "ipv4": str(ipv4),
            "username": username,
            "encrypted_password": encrypted_password,
        }, on_conflict="user_id,ipv4").execute()
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not save camera connection") from error

    if not response.data:
        raise HTTPException(status_code=500, detail="Camera connection was not saved")

    connection = response.data[0]

    # Never return the encrypted password.
    return {
        "id": connection["id"],
        "ipv4": connection["ipv4"],
        "username": connection.get("username"),
    }

# Scan a connection using credentials stored by the backend.
@camera_router.post("/discover/{connection_id}")
def discover_cameras(connection_id: str, current_user=Depends(get_current_user), user_database=Depends(get_user_database)):
    try:
        # a user cannot scan another user’s saved connection ID since we do 2 .eq(user_id) and .eq(connection_id)
        connection_response = user_database.table("camera_connections").select("id, ipv4, username, encrypted_password").eq("id", connection_id).eq("user_id", str(current_user.id)).execute()
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not load camera connection") from error

    if not connection_response.data:
        raise HTTPException(status_code=404, detail="Camera connection not found")

    connection = connection_response.data[0]
    ipv4 = IPv4Address(connection["ipv4"])
    username = connection.get("username")

    try:
        password = decrypt_camera_password(connection.get("encrypted_password"))
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not decrypt camera credentials") from error

    if not any(ipv4 in network for network in private_networks):
        raise HTTPException(status_code=400, detail="Saved IPv4 address is not private")

    if bool(username) != bool(password):
        raise HTTPException(status_code=400, detail="Camera password is unavailable")

    return scan_cameras(str(ipv4), username, password)


@camera_router.post("/refresh/{connection_id}")
def refresh_saved_cameras(connection_id: str, current_user=Depends(get_current_user), user_database=Depends(get_user_database)):
    """
    The workflow is: Get all connections + all saved camera indexes =>
    """
    # 1. Query all rows of the connection that match the connection id that the request asks for
    try:
        connection_response = user_database.table("camera_connections").select("id, ipv4, username, encrypted_password").eq("id", connection_id).eq("user_id", str(current_user.id)).execute()
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not load the saved camera connection") from error

    if not connection_response.data:
        raise HTTPException(status_code=404, detail="Camera connection not found")

    # 2. Since a conection id can store the same info (ipv4, user, pwd) across multiple cameras
    #  => Take only the first row as representative
    connection = connection_response.data[0]

    # 3. If username exists but pwd DNE then this connection can't be accessed
    try:
        password = decrypt_camera_password(connection.get("encrypted_password"))
    except Exception as error:
        raise HTTPException(status_code=500, detail="Could not decrypt camera credentials") from error

    if bool(connection.get("username")) != bool(password):
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

    if username and password:
        encoded_username = quote(username, safe="")
        encoded_password = quote(password, safe="")
        authentication = f"{encoded_username}:{encoded_password}@"

    camera_stream_pairs = []

    # 6. Get the latest frames from each camera
    for camera in saved_response.data:
        camera_id = camera["id"]
        stream = get_camera_stream(camera_id)

        if stream is None:
            camera_index = camera["index"]
            source = f"rtsp://{authentication}{connection['ipv4']}:554/Streaming/Channels/{camera_index}"
            stream = get_or_start_camera_stream(camera["id"], source)
            camera_stream_pairs.append((camera, stream))

        wait_start = time.monotonic()
        was_ready = stream.first_frame_ready.is_set()

        # Get the first frame
        frame = stream.wait_for_first_frame()

        wait_time = time.monotonic() - wait_start
        print(f"Camera {camera['id']}: ready_before={was_ready}, wait={wait_time:.2f}s")

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
