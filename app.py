# app.py

from flask import Flask, request, render_template, jsonify, send_from_directory, redirect
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

# Cloudinary setup
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Supabase setup
# IMPORTANT: Ensure these environment variables are set in your Render deployment.
# Do NOT hardcode sensitive keys directly in the code.
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://hvfqdrfdefgfqbfdikpn.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh2ZnFkcmZkZWZnZnFiZmRpa3BuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTIxOTA4MjgsImV4cCI6MjA2Nzc2NjgyOH0.nG8rzVCQR6J8XxbTaiC9zOUjFu7fi-4oRVY-D61NCJU")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Define the path to your HTML template for the editor
# Ensure 'themeqr-site' is a subfolder containing 'index_template.html'
TEMPLATE_PATH = os.path.join(app.root_path, 'themeqr-site', 'index_template.html')

# Define a fixed ID for the demo QR's dynamic redirect in Supabase.
# This ID will be used to store and retrieve the current landing URL for 'themeqr.com/go'.
DEMO_DECK_ID = "demo_qr_redirect"

# Ensure 'static' directory exists for storing generated QR codes
if not os.path.exists(app.static_folder):
    os.makedirs(app.static_folder)

@app.route('/')
def home():
    """Renders the main editor page."""
    # Make sure 'editor.html' exists in your 'templates' folder
    return render_template('editor.html')

@app.route('/reset_index', methods=['POST'])
def reset_index():
    """Resets the index.html file to its original template."""
    try:
        # Copies the original template to /tmp/index.html
        shutil.copyfile(TEMPLATE_PATH, '/tmp/index.html')
        print("✅ index.html reset to template.")
        return jsonify(success=True)
    except Exception as e:
        print(f"❌ Error resetting index.html: {str(e)}")
        return jsonify(success=False, error=str(e))

@app.route('/index.html')
def serve_updated_index():
    """Serves the potentially updated index.html from the /tmp directory."""
    # This assumes that update_index or reset_index has written to /tmp/index.html
    return send_from_directory('/tmp', 'index.html')

@app.route('/change_qr_landing', methods=['POST'])
def change_qr_landing():
    """
    Updates the target landing URL for the demo QR code in Supabase.
    This URL is what 'themeqr.com/go' will redirect to.
    """
    try:
        print("📥 Incoming POST to /change_qr_landing")
        data = request.get_json()
        print(f"📦 Data received: {data}")

        new_landing = data.get('landing')
        if not new_landing or not new_landing.startswith("http"):
            print("❌ Invalid landing URL provided.")
            return jsonify(success=False, error="Invalid URL format"), 400

        # Upsert (update or insert) the landing URL for the DEMO_DECK_ID in Supabase.
        # 'on_conflict' ensures that if a row with DEMO_DECK_ID already exists, it's updated.
        response = supabase.table('qr_decks').upsert(
            {'id': DEMO_DECK_ID, 'landing_url': new_landing},
            on_conflict='id'
        ).execute()

        if response.error:
            print(f"❌ Supabase error updating landing URL: {response.error.message}")
            return jsonify(success=False, error=response.error.message), 500

        print(f"✅ Supabase updated for {DEMO_DECK_ID} to {new_landing}.")
        return jsonify(success=True)

    except Exception as e:
        print(f"❌ Exception during /change_qr_landing: {str(e)}")
        return jsonify(success=False, error=str(e)), 500

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    """
    Generates a QR code image for the fixed URL 'https://themeqr.com/go'
    and makes it available for the frontend to display.
    """
    try:
        data = request.get_json()
        link_to_encode = data.get('link') # This should be "https://themeqr.com/go"

        if not link_to_encode:
            return jsonify(success=False, error="Missing link to encode."), 400

        # Define the filename for the QR code image that the frontend will display
        qr_filename = 'demo_themeqr_go_qr.png'
        qr_path = os.path.join(app.static_folder, qr_filename)

        # Generate the QR code image
        qr_img = qrcode.make(link_to_encode).convert("RGB")
        qr_img.save(qr_path)

        # Return the URL of the generated QR code image relative to the static folder
        qr_url = f"/static/{qr_filename}"
        print(f"✅ QR code generated for '{link_to_encode}' at '{qr_url}'")
        return jsonify(success=True, qr_url=qr_url)

    except Exception as e:
        print(f"❌ Error generating QR code: {e}")
        return jsonify(success=False, error=str(e)), 500

@app.route('/update_index', methods=['POST'])
def update_index():
    """
    Updates the index.html with a new video URL, overlaying a QR code on the video.
    This route is for the video overlay functionality, separate from the dynamic QR redirect.
    """
    data = request.get_json()
    wrapper = data.get('wrapper') # URL of the wrapper video
    landing = data.get('landing') # Landing page for the QR code to be overlaid on video

    print("🔁 Received wrapper:", wrapper)
    print("🔁 Received landing page:", landing)

    if not wrapper or not landing:
        return jsonify(success=False, error="Missing wrapper or landing URL."), 400

    try:
        # 1. Generate QR for the video overlay
        qr_path = "/tmp/themeqr_landing_qr_video_overlay.png" # Unique name for this QR
        qr_img = qrcode.make(landing).convert("RGB")
        qr_img.save(qr_path)
        print(f"✅ QR for video overlay generated at {qr_path}")

        # 2. Download wrapper video
        wrapper_temp_path = f"/tmp/{uuid.uuid4()}.mp4"
        print(f"Downloading wrapper from {wrapper} to {wrapper_temp_path}")
        with requests.get(wrapper, stream=True) as r:
            r.raise_for_status()
            with open(wrapper_temp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print("✅ Wrapper video downloaded.")

        # 3. Overlay QR on video
        # Ensure moviepy is installed and its dependencies are met in your Render environment
        video_clip = VideoFileClip(wrapper_temp_path).subclip(0, 10) # Using first 10 seconds
        # Resize QR and position it (e.g., bottom right)
        qr_clip = ImageClip(qr_path).set_duration(video_clip.duration).resize(height=150).set_pos(("right", "bottom"))
        final_clip = CompositeVideoClip([video_clip, qr_clip])

        final_output_path = "/tmp/final_themeqr_video.mp4"
        print(f"Compositing video and QR. Output to {final_output_path}")
        final_clip.write_videofile(final_output_path, codec="libx264", audio_codec="aac")
        print("✅ Final video with QR overlay created.")

        # 4. Upload video to Cloudinary
        cloud_result = cloudinary.uploader.upload_large(
            final_output_path,
            resource_type="video",
            folder="themeqr/wrappers" # Organize uploads in a specific folder
        )
        cloud_url = cloud_result['secure_url']
        print(f"🌐 Uploaded to Cloudinary: {cloud_url}")

        # 5. Inject new video URL into index_template.html
        print(f"📁 Looking for template at: {TEMPLATE_PATH}")
        with open(TEMPLATE_PATH, "r") as template:
            content = template.read()

        # Replace a specific placeholder video URL in your template with the new Cloudinary URL
        # Make sure the placeholder string exactly matches what's in your index_template.html
        updated_html = content.replace(
            'src="https://res.cloudinary.com/themeqr-test/video/upload/v1752014993/themeqr/wrappers/obsg01o6dfzl6du5bsaa.mp4"',
            f'src="{cloud_url}"'
        )

        with open("/tmp/index.html", "w") as f:
            f.write(updated_html)
        print("✅ index.html successfully written to /tmp with new video URL.")
        return jsonify(success=True, video_url=cloud_url)

    except Exception as e:
        print(f"❌ Error in update_index: {str(e)}")
        return jsonify(success=False, error=str(e))

@app.route('/go')
def redirect_to_landing():
    """
    Redirects to the current landing URL associated with the DEMO_DECK_ID.
    This is the endpoint that the 'themeqr.com/go' QR code will point to.
    """
    try:
        # Fetch the current landing URL for the DEMO_DECK_ID from Supabase
        response = supabase.table('qr_decks').select("landing_url").eq("id", DEMO_DECK_ID).single().execute()

        if response.error:
            # If no entry is found for DEMO_DECK_ID, redirect to a default fallback URL
            print(f"❌ Supabase fetch error for DEMO_DECK_ID: {response.error.message}. Redirecting to default.")
            return redirect("https://themeqr.com", code=302)

        landing_url = response.data["landing_url"]
        print(f"✅ Redirecting /go to: {landing_url}")
        return redirect(landing_url, code=302)

    except Exception as e:
        # Catch any other exceptions during the redirect process and fall back
        print(f"❌ Exception in /go redirect: {e}. Redirecting to default.")
        return redirect("https://themeqr.com", code=302)

if __name__ == '__main__':
    # Get the port from environment variable, default to 5000 for local development
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
