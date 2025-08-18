import sys
import os
import tempfile
import requests
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import ImageClip
from html2image import Html2Image


def download_landing_image(landing_url, output_image_path):
    hti = Html2Image()
    hti.screenshot(url=landing_url, save_as=os.path.basename(output_image_path), size=(1280, 720))
    
    saved_path = os.path.join(os.getcwd(), os.path.basename(output_image_path))
    os.replace(saved_path, output_image_path)
    return output_image_path

def build_video(landing_url, output_path):
    temp_img = os.path.join(tempfile.gettempdir(), "landing.jpg")

    print(f"Fetching landing page image from {landing_url}")
    download_landing_image(landing_url, temp_img)

    print("Creating video...")

    # Create image clip
    landing_img = ImageClip(temp_img).with_duration(10).resized(height=720)


    # Optional: overlay on a background or video clip
    # bg_clip = VideoFileClip("path_to_base_video.mp4").subclip(0, 10)

    # For demo: just use the image as full screen
    final = CompositeVideoClip([landing_img.with_position("center")])

    print(f"Writing final video to: {output_path}")
    final.write_videofile(output_path, codec="libx264", fps=24)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python deck_builder.py <landing_page_url> <output_video_path>")
        sys.exit(1)

    landing_url = sys.argv[1]
    output_path = sys.argv[2]

    build_video(landing_url, output_path)
