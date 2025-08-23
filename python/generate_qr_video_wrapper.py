
import os
import argparse
import qrcode
from PIL import Image
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip

def generate_qr_video(wrapper, qr_img_path, landing_url, output_path):
    # Step 1: Generate QR Code
    qr_img = qrcode.make(landing_url).convert("RGB")
    qr_img.save(qr_img_path)
    print(f"[QR] Saved QR code image to: {qr_img_path}")

    # Step 2: Load video
    if not os.path.exists(wrapper):
        raise FileNotFoundError(f"Wrapper video not found at: {wrapper}")

    video_clip = VideoFileClip(wrapper)
    video_clip = video_clip.subclip(0, min(10, video_clip.duration))  # Limit to 10 sec

    # Step 3: Prepare QR overlay
    qr_clip = ImageClip(qr_img_path).set_duration(video_clip.duration)
    qr_clip = qr_clip.resize(height=150).set_pos(("right", "bottom"))

    # Step 4: Overlay QR on video
    final_clip = CompositeVideoClip([video_clip, qr_clip])
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    print(f"[DONE] Final video with QR saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate QR embedded video.")
    parser.add_argument('--wrapper', required=True, help="Path to wrapper video")
    parser.add_argument('--qr', required=True, help="Path to save generated QR image")
    parser.add_argument('--landing', required=True, help="Landing page URL")
    parser.add_argument('--output', required=True, help="Output video path")

    args = parser.parse_args()
    generate_qr_video(args.wrapper, args.qr, args.landing, args.output)
