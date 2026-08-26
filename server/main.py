from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.camera import camera_router 
from contextlib import asynccontextmanager
from services.camera_services.stream_manager import stop_all_camera_streams
from services.camera_services.start_saved_camera_streams import start_saved_camera_streams
import os

os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"

@asynccontextmanager
async def lifespan(app):
    start_saved_camera_streams()
    yield
    stop_all_camera_streams()

app = FastAPI(lifespan=lifespan)

# Allow your iPhone to talk to your Mac
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include our camera routes (like app.use('/cameras', cameraRoutes))
# This is like mounting middlewares in express: app.use("/api/categories", categoriesRouter);
app.include_router(camera_router, prefix="/api/cameras")

@app.get("/")
async def root():
    return {"message": "Fall Saver Backend is running"}

