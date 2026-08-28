import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from supabase import create_client, Client

# Load the variables from the .env file
load_dotenv()

# Initialize Supabase client
url = os.getenv("SUPABASE_URL")
secret_key = os.getenv("SUPABASE_SECRET_KEY")

# supabase: The name of your variable.
# : is The separator that says, "Hey, I'm about to tell you what type this is."
# Client: The specific Data Type. In this case, it’s a special type defined by the Supabase library.
# =: The standard assignment operator.
supabase: Client = create_client(url, secret_key)

def log_fall_events(camera_id, camera_name, angle_change, vertical_drop):
    try:
        data = {
            "camera_id": camera_id,
            "camera_name": camera_name,
            "angle_change": angle_change,
            "vertical_drop": vertical_drop,
            "fall_detected_at": datetime.now(timezone.utc).isoformat()
        }

        response = supabase.table("fall_events").insert(data).execute()
        print(f"Fall event log: {response}")
        return response
    except Exception as e:
        print(f"Error logging fall event: {e}")
        return None

