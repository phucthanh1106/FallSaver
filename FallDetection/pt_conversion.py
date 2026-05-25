from ultralytics import YOLO

# Load your custom trained or official PyTorch model
model = YOLO("yolo26s-pose.pt")

# Export to ONNX format
# setting dynamic=True allows the model to handle different video frame sizes smoothly
success = model.export(format="onnx", dynamic=True)

print("Export complete! You should now see 'yolo26n-pose.onnx' in your folder.")