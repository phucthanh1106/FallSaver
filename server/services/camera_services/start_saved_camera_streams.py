import os
from urllib.parse import quote
from supabase import create_client
from services.camera_services.stream_manager import get_or_start_camera_stream
from services.camera_services.camera_credentials import decrypt_camera_password


# Load saved cameras and start their capture threads when FastAPI starts.
def start_saved_camera_streams():
    url = os.getenv("SUPABASE_URL")
    secret_key = os.getenv("SUPABASE_SECRET_KEY")

    try:
        # Use the trusted backend client because no user is logged in at startup.
        database = create_client(url, secret_key)

        # Find connections that point to this household camera system.
        connections = database.table("camera_connections").select("id, ipv4, username, encrypted_password").execute().data

        if not connections:
            print("Camera startup skipped: no saved connections")
            return

        # Load cameras belonging to those connections.
        connection_ids = [connection["id"] for connection in connections] # Save all existed ids of connections in a list
        cameras = database.table("cameras").select("id, index, connection_id").in_("connection_id", connection_ids).execute().data # Find all cameras with existed connections
        connections_by_id = {connection["id"]: connection for connection in connections}

        # Start every capture thread without waiting for its first frame.
        streams = set()
        for camera in cameras:
            connection = connections_by_id[camera["connection_id"]]
            password = decrypt_camera_password(connection.get("encrypted_password"))
            ipv4 = connection.get("ipv4")
            username = connection.get("username")
            authentication = ""

            if username and password:
                authentication = f"{quote(username, safe='')}:{quote(password, safe='')}@"
            elif username:
                continue

            source = f"rtsp://{authentication}{ipv4}:554/Streaming/Channels/{camera['index']}"
            stream = get_or_start_camera_stream(camera["id"], source)
            streams.add(stream)

        print(f"Started {len(streams)} camera streams")
    except Exception as error:
        print(f"Could not start saved camera streams: {error}")