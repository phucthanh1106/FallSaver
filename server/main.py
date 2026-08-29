from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.camera import camera_router 
from contextlib import asynccontextmanager
from services.camera_services.stream_manager import stop_all_camera_streams
from services.camera_services.start_saved_camera_streams import start_saved_camera_streams
import os

os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:8081,http://127.0.0.1:8081",
    ).split(",")
    if origin.strip()
]

@asynccontextmanager
async def lifespan(app):
    start_saved_camera_streams()
    yield
    stop_all_camera_streams()

app = FastAPI(lifespan=lifespan)

# Browser clients must come from an explicitly configured origin. Native Expo
# requests are not restricted by browser CORS enforcement.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include our camera routes (like app.use('/cameras', cameraRoutes))
# This is like mounting middlewares in express: app.use("/api/categories", categoriesRouter);
app.include_router(camera_router, prefix="/api/cameras")

@app.get("/")
async def root():
    return {"message": "Fall Saver Backend is running"}
