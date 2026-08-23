import threading
import time
from urllib.parse import quote
import cv2

# ============================================================================
# Global dictionary holding all active camera streams in server memory.
# Structure: { camera_id: CameraStreamInstance }
# ============================================================================
camera_streams = {}
camera_streams_lock = (
    threading.Lock()
)  # Protects adding/removing items from camera_streams

# CameraStream manages a camera stream and owns its background thread
class CameraStream:
    def __init__(self, camera_id, source):
        self.camera_id = str(camera_id)
        self.source = source

        # Shared frame state
        self.latest_frame = None
        self.latest_frame_time = None
        self.online = False
        self.fps = 15 # Fall back if OpenCV cannot detect the FPS

        self.frame_lock = threading.Lock()
        self.frame_ready = threading.Event() # this event means this camera has produced at least one frame
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        """Starts the background stream thread."""
        if self.thread and self.thread.is_alive():
            return

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        """Infinite loop pulling frames continuously to keep OpenCV buffers clear."""
        # First while loop is for opening the connection and maintaining that connection
        connection_start = time.monotonic()

        while not self.stop_event.is_set():
            cap = None

            try:
                cap = cv2.VideoCapture(
                    self.source,
                    cv2.CAP_FFMPEG,
                    [
                        cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
                        3000,
                        cv2.CAP_PROP_READ_TIMEOUT_MSEC,
                        3000,
                    ],
                )

                if not cap.isOpened():
                    self._set_offline()
                    # pauses the thread for up to 2 seconds, then continues to the next line if no stop request
                    self.stop_event.wait(2)
                    continue

                detected_fps = cap.get(cv2.CAP_PROP_FPS)

                with self.frame_lock:
                    if detected_fps and 1 <= detected_fps <= 120:
                        self.fps = detected_fps
                    else:
                        self.fps = 25.0

                # Second loop is for getting the frames continuously from the open connection
                while not self.stop_event.is_set():
                    success, frame = cap.read()

                    if not success:
                        break

                    with self.frame_lock:
                        self.latest_frame = frame.copy()
                        self.latest_frame_time = time.time()
                        self.online = True

                    self.frame_ready.set()
            except Exception:
                self._set_offline()
            finally:
                if cap is not None:
                    cap.release()

            self._set_offline()

            if not self.stop_event.is_set():
                self.stop_event.wait(2)

    def _set_offline(self):
        with self.frame_lock:
            self.online = False

    def get_latest_frame(self):
        with self.frame_lock:
            if self.latest_frame is None:
                return None

            return self.latest_frame.copy()

    def get_status(self):
        with self.frame_lock:
            return {
                "online": self.online,
                "latest_frame_time": self.latest_frame_time,
                "fps": self.fps,
            }
        
    def wait_for_first_frame(self, timeout=5):
        self.frame_ready.wait(timeout)
        return self.get_latest_frame()

    def stop(self):
        self.stop_event.set()

        # Tells the current (main) thread to pause and wait (7s) for the background thread to finish and exit 
        # before moving on to the next line of code.
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=7)


# ============================================================================
# Helper Functions to interact with the streams from FastAPI routes
# ============================================================================
def get_or_start_camera_stream(camera_id, source):
    camera_id = str(camera_id)

    # Acquire lock to safely inspect and update the global streams dictionary
    with camera_streams_lock:
        stream = camera_streams.get(camera_id)

        # Cache hit: If a stream already exists with the exact same RTSP source/credentials, reuse it
        if stream and stream.source == source and stream.thread and stream.thread.is_alive():
            return stream

        # Cache invalidation: Stream exists but its source/credentials changed, so remove it from the map
        if stream:
            del camera_streams[camera_id]

    # Stop the outdated stream OUTSIDE the lock to avoid blocking other threads during network teardown
    if stream:
        stream.stop()

    # Create the replacement stream instance with the new connection details
    new_stream = CameraStream(camera_id, source)

    # Re-acquire lock to safely register the newly created stream
    with camera_streams_lock:
        # Double-check: Handle race condition where another thread might have registered a stream while lock was released
        existing_stream = camera_streams.get(camera_id)

        if existing_stream:
            return existing_stream

        # Register the new stream in the global in-memory store
        camera_streams[camera_id] = new_stream

    # Start the background frame-grabbing thread outside the lock
    new_stream.start()
    return new_stream


def get_camera_stream(camera_id):
    with camera_streams_lock:
        return camera_streams.get(str(camera_id))


def stop_camera_stream(camera_id):
    with camera_streams_lock:
        stream = camera_streams.pop(str(camera_id), None)

    if stream:
        stream.stop()


def stop_all_camera_streams():
    with camera_streams_lock:
        streams = list(camera_streams.values())
        camera_streams.clear()

    for stream in streams:
        stream.stop()
