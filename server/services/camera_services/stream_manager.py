import threading
import time
from urllib.parse import quote
import cv2
from pathlib import Path
import dotenv
from ultralytics import YOLO
import os
import onnxruntime as ort


# ============================================================================
# YOLO & ONNX
# ============================================================================
print(ort.get_available_providers())
dotenv.load_dotenv()
THRESHOLD_ANGLE = int(os.getenv("THRESHOLD_ANGLE"))
THRESHOLD_DROP = float(os.getenv("THRESHOLD_DROP"))

MODEL_PATH = Path(__file__).resolve().parents[2] / "weights" / "yolo26n-pose.onnx"

# ============================================================================
# Global dictionary holding all active camera streams in server memory.
# Structure: { source: CameraStreamInstance }
# ============================================================================
camera_streams = {} # {source: CameraStream}
camera_sources = {} # {camera_id: source}

camera_streams_lock = (
    threading.Lock()
)  # Protects adding/removing items from camera_streams

# CameraStream manages a camera stream and owns its background thread
class CameraStream:
    def __init__(self, source):
        self.source = source

        # YOLO
        self.model = YOLO(str(MODEL_PATH), task="pose")

        # Shared frame state
        self.latest_frame = None
        self.latest_frame_time = None # It helps consumers determine whether the frame changed.
        self.latest_result = None
        self.latest_result_time = None
        self.online = False
        self.producer_fps = 0.0
        self.consumer_fps = 0.0

        # Protect frame data and result shared between both threads
        self.frame_lock = threading.Lock() 
        self.result_lock = threading.Lock() 

        # threading.Event() IS thread-safe out of the box.
        self.first_frame_ready = threading.Event() # Has this camera ever produced its first frame?
        self.inference_ready = threading.Event() # Has a new frame arrived for YOLO?
        self.stop_event = threading.Event() # Has this stream stopped?

        # Keep capture and inference threads separate
        self.producer_thread = None
        self.consumer_thread = None

    def start(self):
        """Starts the background stream threads."""
        if not self.producer_thread or not self.producer_thread.is_alive():
            self.producer_thread = threading.Thread(target=self._run, daemon=True)
            self.producer_thread.start()

        if not self.consumer_thread or not self.consumer_thread.is_alive():
            self.consumer_thread = threading.Thread(target=self._run_inference, daemon=True)
            self.consumer_thread.start()

    def _run(self):
        """Infinite loop pulling frames continuously to keep OpenCV buffers clear."""
        while not self.stop_event.is_set():  # First while loop is for opening the connection and maintaining that connection

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

                produced_frames = 0
                producer_fps_start = time.monotonic()
                while not self.stop_event.is_set(): # Second loop is for getting the frames continuously from the open connection
                    success, frame = cap.read()

                    if not success:
                        break

                    with self.frame_lock:
                        self.latest_frame = frame.copy()
                        self.latest_frame_time = time.time()
                        self.online = True

                    # Releasing the lock before you ring the alarm bell ensures the path is completely clear for the main thread as soon as it wakes up.
                    self.first_frame_ready.set()
                    self.inference_ready.set() # Tell the YOLO thread that a newer frame is available

                    # Count every frame successfully produced by OpenCV.
                    produced_frames += 1
                    elapsed = time.monotonic() - producer_fps_start

                    # Update the average producer FPS once per second.
                    if elapsed >= 1:
                        measured_fps = produced_frames / elapsed

                        with self.frame_lock:
                            self.producer_fps = measured_fps

                        produced_frames = 0
                        producer_fps_start = time.monotonic()
            except Exception:
                self._set_offline()
            finally:
                # Always release the previous OpenCV connection
                if cap is not None:
                    cap.release()

                # Mark the source offline whenever its connection ends
                self._set_offline()

                # Wait before attempting another connection
                if not self.stop_event.is_set():
                    self.stop_event.wait(2)

    # Continuously process only the newest available camera frame
    def _run_inference(self):
        last_frame_time = None

        processed_results = 0
        results_fps_start = time.monotonic()
        while not self.stop_event.is_set():
            # Sleep efficiently until the producer captures another frame
            if not self.inference_ready.wait(timeout=1):
                continue

            self.inference_ready.clear()

            # Copy the newest raw frame without holding the lock during YOLO
            with self.frame_lock:
                if self.latest_frame is None or self.latest_frame_time == last_frame_time:
                    continue

                frame = self.latest_frame.copy()
                frame_time = self.latest_frame_time

            try:
                # Resize the frame before inference
                new_width = 640
                scale = new_width / frame.shape[1]
                new_height = int(frame.shape[0] * scale)
                frame = cv2.resize(frame, (new_width, new_height))

                # Run YOLO in the consumer thread 
                results = self.model.track(frame, persist=True, conf=0.1, device="cpu", verbose=False)

                # Cache the newest completed inference result
                with self.result_lock:
                    self.latest_result = results[0]
                    self.latest_result_time = frame_time

                last_frame_time = frame_time

                # Count every frame successfully processed by YOLO.
                processed_results += 1
                elapsed = time.monotonic() - results_fps_start

                # Update the average producer FPS once per second.
                if elapsed >= 1:
                    measured_fps = processed_results / elapsed

                    with self.frame_lock:
                        self.consumer_fps = measured_fps

                    processed_results = 0
                    results_fps_start = time.monotonic()
            except Exception as error:
                print(f"YOLO inference failed: {error}")
                self.stop_event.wait(1)   

    def _set_offline(self):
        with self.frame_lock:
            self.online = False

    def get_latest_frame(self):
        with self.frame_lock:
            if self.latest_frame is None:
                return None

            return self.latest_frame.copy()

    def get_latest_result(self):
        with self.result_lock:
            return self.latest_result, self.latest_result_time

    def get_status(self):
        with self.frame_lock:
            return {
                "online": self.online,
                "latest_frame_time": self.latest_frame_time, 
                "producer_fps": self.producer_fps,
                "consumer_fps": self.consumer_fps,
            }
        
    def wait_for_first_frame(self, timeout=5):
        self.first_frame_ready.wait(timeout)
        return self.get_latest_frame()

    def stop(self):
        self.stop_event.set()

        # Tells the current (main) thread to pause and wait (7s) for the background thread to finish and exit 
        # before moving on to the next line of code.
        if self.producer_thread and self.producer_thread.is_alive():
            self.producer_thread.join(timeout=7)

        if self.consumer_thread and self.consumer_thread.is_alive():
            self.consumer_thread.join(timeout=7)


# ============================================================================
# Helper Functions to interact with the streams from FastAPI routes
# ============================================================================
def get_or_start_camera_stream(camera_id, source):
    camera_id = str(camera_id)

    # Connect this camera row to its physical RTSP source
    with camera_streams_lock:
        stream = camera_streams.get(source)

        if stream and stream.producer_thread and stream.producer_thread.is_alive():
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
