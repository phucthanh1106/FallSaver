from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.camera import camera_router 

app = FastAPI()

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