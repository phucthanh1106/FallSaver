import threading
import time
from urllib.parse import quote
import cv2

# ============================================================================
# Global dictionary holding all active camera streams in server memory.
# Structure: { source: CameraStreamInstance }
# ============================================================================
camera_streams = {} # {source: CameraStream}
# Connect each user-specific camera to its shared RTSP source
camera_sources = {} # {camera_id: source}
camera_streams_lock = (
    threading.Lock()
)  # Protects adding/removing items from camera_streams

# CameraStream manages a camera stream and owns its background thread
class CameraStream:
    def __init__(self, source):
        self.source = source

        # Shared frame state
        self.latest_frame = None
        self.latest_frame_time = None
        self.online = False
        self.producer_fps = 0.0

        self.frame_lock = threading.Lock()
        # threading.Event() IS thread-safe out of the box.
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

                produced_frames = 0
                measurement_start = time.monotonic()
                # Second loop is for getting the frames continuously from the open connection
                while not self.stop_event.is_set():
                    success, frame = cap.read()

                    if not success:
                        break

                    with self.frame_lock:
                        self.latest_frame = frame.copy()
                        self.latest_frame_time = time.time()
                        self.online = True

                    # Releasing the lock before you ring the alarm bell ensures the path is completely clear for the main thread as soon as it wakes up.
                    self.frame_ready.set()

                    # Count every frame successfully produced by OpenCV.
                    produced_frames += 1
                    elapsed = time.monotonic() - measurement_start

                    # Update the average producer FPS once per second.
                    if elapsed >= 1:
                        measured_fps = produced_frames / elapsed

                        with self.frame_lock:
                            self.producer_fps = measured_fps

                        produced_frames = 0
                        measurement_start = time.monotonic()
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
                "fps": self.producer_fps,
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

    # Connect this camera row to its physical RTSP source
    with camera_streams_lock:
        stream = camera_streams.get(source)

        if stream and stream.thread and stream.thread.is_alive():
            camera_sources[camera_id] = source
            return stream

        # Remove the stream for this source if its thread is no longer running
        old_stream = camera_streams.pop(source, None)

    # Stop the outdated stream OUTSIDE the lock to avoid blocking other threads during network teardown
    if old_stream:
        old_stream.stop()

    # Create the replacement stream instance with the new connection details
    new_stream = CameraStream(source)

    # Re-acquire lock to safely register the newly created stream
    with camera_streams_lock:
        # Double-check: Handle race condition where another thread might have registered a stream while lock was released
        existing_stream = camera_streams.get(source)

        if existing_stream:
            camera_sources[camera_id] = source
            return existing_stream

        # Register the new stream in the global in-memory store

        camera_streams[source] = new_stream
        camera_sources[camera_id] = source

    # Start the background frame-grabbing thread outside the lock
    new_stream.start()
    return new_stream


def get_camera_stream(camera_id):
    with camera_streams_lock:
        source = camera_sources.get(str(camera_id))
        return camera_streams.get(source)


def stop_camera_stream(camera_id):
    with camera_streams_lock:
        source = camera_sources.pop(str(camera_id), None)
        stream = None

        # Keep the shared stream alive while another camera row uses it
        if source and source not in camera_sources.values():
            stream = camera_streams.pop(source, None)

    if stream:
        stream.stop()


def stop_all_camera_streams():
    with camera_streams_lock:
        streams = list(camera_streams.values())
        camera_streams.clear()
        camera_sources.clear()

    for stream in streams:
        stream.stop()
