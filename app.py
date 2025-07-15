from flask import Flask, request, render_template, jsonify, send_from_directory
from supabase import create_client, Client
import shutil
import os
import uuid
import cloudinary
import cloudinary.uploader
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
import qrcode
import requests
from flask_cors import CORS

# Cloudniary setup
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Supabase setup
SUPABASE_URL = os.getenv("https://hvfqdrfdefgfqbfdikpn.supabase.co")
SUPABASE_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh2ZnFkcmZkZWZnZnFiZmRpa3BuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTIxOTA4MjgsImV4cCI6MjA2Nzc2NjgyOH0.nG8rzVCQR6J8XxbTaiC9zOUjFu7fi-4oRVY-D61NCJU")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
TEMPLATE_PATH = os.path.join(app.root_path, 'themeqr-site', 'index_template.html')

@app.route('/')
def home():
    return render_template('editor.html')

@app.route('/reset_index', methods=['POST'])
def reset_index():
    try:
        shutil.copyfile(TEMPLATE_PATH, '/tmp/index.html')
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e))

@app.route('/index.html')
def serve_updated_index():
    return send_from_directory('/tmp', 'index.html')

@app.route('/change_qr_landing', methods=['POST'])
def change_qr_landing():
    try:
        print("📥 Incoming POST to /change_qr_landing")
        data = request.get_json()
        print(f"📦 Data received: {data}")

        new_landing = data.get('landing')
        if not new_landing or not new_landing.startswith("http"):
            print("❌ Invalid landing URL provided.")
            return jsonify(success=False, error="Invalid URL format")

        # Save new QR code
        qr_path = os.path.join(app.static_folder, 'themeqr_demo_qr.png')
        print(f"🖨️ Saving QR to: {qr_path}")
        qr_img = qrcode.make(new_landing).convert("RGB")
        qr_img.save(qr_path)

        print("✅ QR successfully saved.")
        return jsonify(success=True)

    except Exception as e:
        print("❌ Exception during /change_qr_landing:", str(e))
        return jsonify(success=False, error=str(e)), 500
        
@app.route('/update_index', methods=['POST'])
def update_index():
    data = request.get_json()
    wrapper = data['wrapper']
    landing = data['landing']

    print("🔁 Received wrapper:", wrapper)
    print("🔁 Received landing page:", landing)

    try:
        # 1. Generate QR
        qr_path = "/tmp/themeqr_landing_qr.png"
        qr_img = qrcode.make(landing).convert("RGB")
        qr_img.save(qr_path)

        # 2. Download wrapper video
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

        # 4. Upload video to Cloudinary
        cloud_result = cloudinary.uploader.upload_large(
            final_output_path,
            resource_type="video",
            folder="themeqr/wrappers"
        )
        cloud_url = cloud_result['secure_url']
        print(f"🌐 Uploaded to Cloudinary: {cloud_url}")

        # 5. Inject new video URL into index_template.html
        print(f"📁 Looking for template at: {TEMPLATE_PATH}")
        with open(TEMPLATE_PATH, "r") as template:
            content = template.read()

        updated_html = content.replace(
            'src="https://res.cloudinary.com/themeqr-test/video/upload/v1752014993/themeqr/wrappers/obsg01o6dfzl6du5bsaa.mp4"',
            f'src="{cloud_url}"'
        )

        with open("/tmp/index.html", "w") as f:
            f.write(updated_html)

        print("✅ index.html successfully written to /tmp")
        return jsonify(success=True, video_url=cloud_url)

    except Exception as e:
        print("❌ Error in update_index:", str(e))
        return jsonify(success=False, error=str(e))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# 5. Get the most recent deck
@app.route('/go')
def qr_redirect():
    try:
        # Get the most recent deck for now
        response = supabase.table('qr_decks').select('*').order('created_at', desc=True).limit(1).execute()
        if response.data and len(response.data) > 0:
            deck = response.data[0]
            landing_url = deck.get('landing_url')
            if landing_url:
                print(f"🔁 Redirecting to: {landing_url}")
                return redirect(landing_url, code=302)
        return "No deck found or missing landing URL", 404
    except Exception as e:
        print(f"❌ Redirect Error: {e}")
        return "Error processing QR redirect", 500


