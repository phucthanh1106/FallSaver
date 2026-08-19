let cameraConnection = null;

export function getCameraConnection() {
    return cameraConnection;
}

export function setCameraConnection(connection) {
    cameraConnection = connection;
}

export function clearCameraConnection() {
    cameraConnection = null;
}
