import os
import argparse
import qrcode
from PIL import Image
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip

def generate_qr_video(wrapper, qr_img_path, landing_url, output_path, duration=10):
    # Step 1: Generate QR Code
    qr_img = qrcode.make(landing_url).convert("RGB")
    qr_img.save(qr_img_path)
    print(f"[QR] Saved QR code image to: {qr_img_path}")

    # Step 2: Load wrapper (video or image)
    if not os.path.exists(wrapper):
        raise FileNotFoundError(f"Wrapper file not found at: {wrapper}")

    # Check if wrapper is an image or video based on file extension
    image_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
    file_ext = os.path.splitext(wrapper)[1].lower()

    if file_ext in image_extensions:
        # Handle image: Create a static clip with specified duration
        base_clip = ImageClip(wrapper).set_duration(duration)
    else:
        # Handle video: Load and limit to specified duration
        base_clip = VideoFileClip(wrapper)
        base_clip = base_clip.subclip(0, min(duration, base_clip.duration))

    # Step 3: Prepare QR overlay
    qr_clip = ImageClip(qr_img_path).set_duration(base_clip.duration)
    qr_clip = qr_clip.resize(height=150).set_pos(("right", "bottom"))

    # Step 4: Overlay QR on base clip (video or image)
    final_clip = CompositeVideoClip([base_clip, qr_clip])
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    print(f"[DONE] Final video with QR saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate QR embedded video.")
    parser.add_argument('--wrapper', required=True, help="Path to wrapper video or image")
    parser.add_argument('--qr', required=True, help="Path to save generated QR image")
    parser.add_argument('--landing', required=True, help="Landing page URL")
    parser.add_argument('--output', required=True, help="Output video path")
    parser.add_argument('--duration', type=float, default=10, help="Duration for image wrapper (seconds)")

    args = parser.parse_args()
    generate_qr_video(args.wrapper, args.qr, args.landing, args.output, args.duration)
