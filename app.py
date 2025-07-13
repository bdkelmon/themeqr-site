from flask import Flask, request, render_template, jsonify, send_from_directory
import shutil
import os
import subprocess
import uuid
import cloudinary
import cloudinary.uploader
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
import qrcode
import requests

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)
app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def home():
    return render_template('editor.html')

@app.route('/reset_index', methods=['POST'])
def reset_index():
    try:
        shutil.copyfile('index_template.html', '/tmp/index.html')
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e))

@app.route('/index.html')
def serve_updated_index():
    return send_from_directory('/tmp', 'index.html')

@app.route('/update_index', methods=['POST'])
def update_index():
    data = request.get_json()
    wrapper = data['wrapper']
    landing = data['landing']

    try:
        # 1. Generate QR
        qr_path = "/tmp/themeqr_landing_qr.png"
        qr_img = qrcode.make(landing).convert("RGB")
        qr_img.save(qr_path)

        # 2. Download wrapper video from URL to /tmp
        wrapper_temp_path = f"/tmp/{uuid.uuid4()}.mp4"
        with requests.get(wrapper, stream=True) as r:
            r.raise_for_status()
            with open(wrapper_temp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        # 3. Overlay QR on video
        video_clip = VideoFileClip(wrapper_temp_path).subclip(0, 10)
        qr_clip = ImageClip(qr_path).set_duration(video_clip.duration).resize(height=150).set_pos(("right", "bottom"))
        final_clip = CompositeVideoClip([video_clip, qr_clip])

        final_output_path = "/tmp/final_themeqr_video.mp4"
        final_clip.write_videofile(final_output_path, codec="libx264", audio_codec="aac")

        # 4. Upload final video to Cloudinary
        cloud_result = cloudinary.uploader.upload_large(
            final_output_path,
            resource_type="video",
            folder="themeqr/wrappers"
        )
        cloud_url = cloud_result['secure_url']

        # 5. Inject new video URL into HTML template
        with open("index_template.html", "r") as template:
            content = template.read()

        updated_html = content.replace(
            'src="https://res.cloudinary.com/themeqr-test/video/upload/v1752014993/themeqr/wrappers/obsg01o6dfzl6du5bsaa.mp4"',
            f'src="{cloud_url}"'
        )

        with open("/tmp/index.html", "w") as f:
            f.write(updated_html)

        return jsonify(success=True, video_url=cloud_url)

    except Exception as e:
        return jsonify(success=False, error=str(e))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)



