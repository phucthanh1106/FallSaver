import os
from cryptography.fernet import Fernet


# Create the encryption tool using the backend-only key.
encryption_key = os.getenv("CAMERA_ENCRYPTION_KEY")

if not encryption_key:
    raise RuntimeError("CAMERA_ENCRYPTION_KEY is missing")

cipher = Fernet(encryption_key.encode())


# Encrypt an RTSP password before saving it.
def encrypt_camera_password(password):
    if not password:
        return None

    return cipher.encrypt(password.encode()).decode()


# Decrypt a stored RTSP password inside the backend.
def decrypt_camera_password(encrypted_password):
    if not encrypted_password:
        return None

    return cipher.decrypt(encrypted_password.encode()).decode()