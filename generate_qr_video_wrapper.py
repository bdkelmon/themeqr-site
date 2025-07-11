
import os
import qrcode
from PIL import Image
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip

# === CONFIGURATION ===
landing_page_url = "https://bdkelmon.github.io/themeqr-site/HappyBirthdayAiden.html"  # Replace with actual landing page URL
qr_output_path = os.path.join(os.getcwd(), "C:\Users\Bdkel\Documents\Themeqr\BirthdayParty-Deck\themeqr_landing_qr.png")

video_path = os.path.join(os.getcwd(), "C:\Users\Bdkel\Documents\Themeqr\BirthdayParty-Deck\BirthdayParty.mp4")
output_video_path = os.path.join(os.getcwd(), "themeqr_video_with_qr.mp4")

# === STEP 1: Generate QR Code ===
qr_img = qrcode.make(landing_page_url).convert("RGB")
qr_img.save(qr_output_path)
print(f"[QR] Saved QR code image to: {qr_output_path}")

# === STEP 2: Load video and QR ===
if not os.path.exists(video_path):
    raise FileNotFoundError(f"Video not found at: {video_path}")

video_clip = VideoFileClip(video_path)
video_clip = video_clip.subclip(0, min(10, video_clip.duration))  # Use first 10 seconds or full length

# === STEP 3: Prepare and resize QR ===
qr_clip = ImageClip(qr_output_path).set_duration(video_clip.duration)
qr_clip = qr_clip.resize(height=150).set_pos(("right", "bottom"))

# === STEP 4: Overlay QR on video ===
final_clip = CompositeVideoClip([video_clip, qr_clip])
final_clip.write_videofile(output_video_path, codec="libx264", audio_codec="aac")

print(f"[DONE] Final video with QR saved to: {output_video_path}")
