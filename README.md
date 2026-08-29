# FallSaver

FallSaver is a full-stack fall-detection system for household RTSP cameras. It continuously captures camera frames, performs YOLO pose inference through ONNX Runtime, evaluates body movement for possible falls, and exposes authenticated camera previews and live MJPEG feeds to an Expo mobile application.

## Why I Built It

I started this project after my father fell while doing pull-ups at my home in Vietnam, and I had no way of knowing about it immediately since I was studying in the US. FallSaver aims to solve this problem by using Computer Vision to automatically detect falls through household cameras.

## Current Features

- Authenticated Expo and React Native mobile client
- User-scoped camera connections and cameras stored in Supabase
- Encrypted RTSP camera passwords stored by the backend
- Hikvision-compatible RTSP camera discovery and live MJPEG feeds
- Persistent OpenCV capture threads with automatic reconnection
- Separate producer and consumer threads for capture and pose inference
- Latest-frame caching that prevents inference backlogs when capture FPS exceeds inference FPS
- YOLO pose inference from an ONNX model using ONNX Runtime
- Per-person tracking with body-angle and vertical-drop fall metrics
- Automatic startup and graceful shutdown of saved camera streams

## Architecture

```text
Hikvision RTSP camera
        |
        v
OpenCV producer thread ----> latest-frame cache
                                  |
                                  v
                       ONNX Runtime consumer thread
                                  |
                         latest inference result
                                  |
                  +---------------+---------------+
                  |                               |
          FastAPI MJPEG feed              fall-detection logic
                  |
                  v
          Expo mobile client
```

Capture and inference run independently. The producer continuously replaces the cached frame, while the consumer processes the newest available frame. This avoids building a queue of stale frames when inference is slower than the camera stream.

## Technology

**Backend:** Python, FastAPI, OpenCV, Ultralytics YOLO Pose, ONNX Runtime, Supabase, Pydantic, Cryptography

**Mobile:** React Native, Expo, Expo Router, Supabase Auth

**Camera protocol:** RTSP with Hikvision channel paths

## Local Setup

### Backend

1. Create and activate a Python environment.
2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `server/.env.example` to `server/.env` and fill in the backend values.
4. Start FastAPI from the `server` directory:

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Mobile client

1. Copy `client/.env.example` to `client/.env` and configure the public Supabase values and backend URL.
2. Install and start the client:

   ```bash
   cd client
   npm install
   npx expo start
   ```

When the backend runs on another machine, set `EXPO_PUBLIC_API_URL` to that machine's reachable LAN or Tailscale URL instead of `127.0.0.1`.

## Environment and Security

- Never place `SUPABASE_SECRET_KEY` or `CAMERA_ENCRYPTION_KEY` in the Expo client. Every `EXPO_PUBLIC_*` value is bundled into the client and must be considered public.
- The Supabase publishable key is intended for client applications; Row Level Security remains responsible for protecting user data.
- `CAMERA_ENCRYPTION_KEY` encrypts stored RTSP passwords. Back it up securely: replacing it makes existing encrypted passwords unreadable unless they are migrated or entered again.
- Configure browser origins with a comma-separated backend value such as:

  ```text
  ALLOWED_ORIGINS=http://localhost:8081,https://your-web-client.example.com
  ```

## Planned Work

- Store a short pre-fall and post-fall incident video
- Send fall notifications by SMS or push notification
- Add retryable background event processing
- Add metrics for capture FPS, inference latency, reconnects, and camera health
- Benchmark TensorRT and Triton inference on the target NVIDIA GPU
