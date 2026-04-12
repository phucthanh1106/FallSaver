# FallSaver

A real-time fall detection system that monitors camera feeds and detects when people fall.

## 📖 Story

I started this project because my father fell while doing pull-ups at home in Vietnam, and I had no way of knowing about it immediately since I was studying in the US. FallSaver aims to solve this problem by using AI to automatically detect falls through household cameras.

## ✨ What This Project Does

- **Detects Falls in Real-Time**: Uses YOLO pose estimation to analyze body position and angle
- **Monitors Multiple Cameras**: Support for USB cameras connected to your network
- **Live Stream Display**: View camera feeds directly from your phone
- **Logs Fall Events**: Stores fall detection data in Supabase for later review
- **Person Tracking**: Tracks individual people across frames to improve accuracy

## 🛠️ Tech Stack

**Backend:**
- Python with FastAPI for the REST API
- OpenCV for video frame processing
- YOLOv8 for pose estimation (detects body keypoints)
- Supabase for cloud database to store fall events

**Frontend:**
- React Native with Expo for mobile app
- WebView for displaying live camera streams



