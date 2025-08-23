
from dotenv import load_dotenv
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Load credentials from .env
load_dotenv()

cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure = True
)

# Local paths (update with your actual file paths)
qr_path = "themeqr_landing_qr.png"
video_path = "C:/Users/Bdkel/Documents/Themeqr/themeqr_video_with_qr.mp4"

# Upload QR code image
qr_upload = cloudinary.uploader.upload(
    qr_path,
    folder="themeqr/qr_codes"
)
qr_cloud_url = qr_upload['secure_url']
print("✅ QR Code uploaded:", qr_cloud_url)

# Upload video with QR
video_upload = cloudinary.uploader.upload(
    video_path,
    resource_type="video",
    folder="themeqr/wrappers"
)
video_cloud_url = video_upload['secure_url']
print("✅ QR Video uploaded:", video_cloud_url)
