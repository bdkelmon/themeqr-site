import os
import shutil
import uuid
import cloudinary
import cloudinary.uploader
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
import qrcode
import requests
from flask import Flask, request, render_template, jsonify, send_from_directory, redirect, session, flash, url_for
from flask_cors import CORS
from datetime import datetime, timezone
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("SUPABASE_URL or SUPABASE_KEY not set")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Cloudinary setup
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your-secret-key")
CORS(app)

DEMO_DECK_ID = "71f42d9b-fe22-4085-87f0-944ab85ac07e"
TEMPLATE_PATH = os.path.join(app.root_path, 'themeqr-site', 'index_template.html')
if not os.path.exists(app.static_folder):
    os.makedirs(app.static_folder)

@app.route("/")
def index():
    return render_template("index.html", user=session.get("user"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            session["user"] = response.user.__dict__
            session["session"] = response.session.__dict__ if response.session else None
            flash("Logged in successfully!", "success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"Login failed: {str(e)}", "error")
            return render_template("login.html")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            response = supabase.auth.sign_up({"email": email, "password": password})
            user_data = response.user.__dict__
            # Store only serializable user data
            session["user"] = {
                "id": user_data.get("id"),
                "email": user_data.get("email"),
                "created_at": user_data.get("created_at")
            }
            session["session"] = response.session.__dict__ if response.session else None
            flash("Sign-up successful! Please check your email to confirm.", "success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"Sign-up failed: {str(e)}", "error")
            return render_template("signup.html")
    return render_template("signup.html")

@app.route("/logout")
def logout():
    try:
        supabase.auth.sign_out()
        session.pop("user", None)
        session.pop("session", None)
        flash("Logged out successfully!", "success")
        return redirect(url_for("index"))
    except Exception as e:
        flash(f"Logout failed: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        email = request.form.get("email")
        if not email:
            flash("Email is required.", "error")
            return render_template("reset_password.html")
        try:
            # Send password reset email via Supabase
            supabase.auth.reset_password_for_email(email)
            flash("Password reset email sent! Please check your email.", "success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"Failed to send password reset email: {str(e)}", "error")
            return render_template("reset_password.html")
    return render_template("reset_password.html")

@app.route("/google-login")
def google_login():
    try:
        response = supabase.auth.sign_in_with_oauth({"provider": "google"})
        return redirect(response.url)
    except Exception as e:
        flash(f"Google login failed: {str(e)}", "error")
        return redirect(url_for("login"))

@app.route("/auth/callback")
def auth_callback():
    try:
        session_data = supabase.auth.get_session()
        if session_data:
            session["user"] = session_data.user.__dict__
            session["session"] = session_data.__dict__
            flash("Logged in with Google successfully!", "success")
        else:
            flash("Authentication failed.", "error")
        return redirect(url_for("index"))
    except Exception as e:
        flash(f"Authentication failed: {str(e)}", "error")
        return redirect(url_for("login"))

@app.route("/birthday")
def birthday():
    return app.send_static_file("birthday/video1.mp4")

@app.route("/tech")
def tech():
    return app.send_static_file("tech/video2.mp4")

@app.route('/test_supabase')
def test_supabase():
    try:
        response = supabase.table('decks').select('*').execute()
        if response.error:
            return jsonify({"error": response.error.message}), 500
        return jsonify({"data": response.data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

async def get_or_create_user_vault(user_id: str):
    try:
        response = supabase.table('vaults').select('id').eq('user_id', user_id).single().execute()
        if response.data:
            print(f"✅ Found existing vault for user {user_id}: {response.data['id']}")
            return response.data['id']
        elif response.error and response.error.code == 'PGRST116':
            print(f"ℹ️ No vault found for user {user_id}. Creating a new one...")
            insert_response = supabase.table('vaults').insert({
                'user_id': user_id,
                'vault_name': f"Vault for {user_id[:8]}",
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).execute()
            if insert_response.error:
                print(f"❌ Error creating vault for user {user_id}: {insert_response.error.message}")
                return None
            print(f"✅ Created new vault for user {user_id}: {insert_response.data[0]['id']}")
            return insert_response.data[0]['id']
        else:
            print(f"❌ Supabase error checking vault for user {user_id}: {response.error.message}")
            return None
    except Exception as e:
        print(f"❌ Exception in get_or_create_user_vault: {str(e)}")
        return None

@app.route('/editor')
def serve_qr_landing_editor():
    print(f"Serving qr_landing_editor.html. Supabase URL: {SUPABASE_URL}")
    return render_template('qr_landing_editor.html', 
                          supabase_url=os.getenv('SUPABASE_URL'),
                          supabase_key=os.getenv('SUPABASE_KEY'))

@app.route('/reset_index', methods=['POST'])
def reset_index():
    try:
        shutil.copyfile(TEMPLATE_PATH, '/tmp/index.html')
        print("✅ index.html reset to template.")
        return jsonify(success=True)
    except Exception as e:
        print(f"❌ Error resetting index.html: {str(e)}")
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
        if not new_landing or (not new_landing.startswith("http://") and not new_landing.startswith("https://")):
            print("❌ Invalid landing URL format.")
            return jsonify(success=False, error="Invalid URL format."), 400
        response = supabase.table('decks').update({'landing_url': new_landing}).eq('id', DEMO_DECK_ID).execute()
        if not response.data:
            print(f"⚠️ No row found for ID: {DEMO_DECK_ID}.")
            return jsonify(success=False, error="Deck ID not found."), 404
        print(f"✅ Supabase updated for {DEMO_DECK_ID} to {new_landing}.")
        return jsonify(success=True)
    except Exception as e:
        print(f"❌ Exception during /change_qr_landing: {str(e)}")
        return jsonify(success=False, error=str(e)), 500

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    try:
        data = request.get_json()
        link_to_encode = data.get('link')
        if not link_to_encode:
            return jsonify(success=False, error="Missing link to encode."), 400
        temp_qr_filename = f"temp_qr_{uuid.uuid4()}.png"
        temp_qr_path = os.path.join("/tmp", temp_qr_filename)
        qr_img = qrcode.make(link_to_encode).convert("RGB")
        qr_img.save(temp_qr_path)
        print(f"✅ Temporary QR code generated at '{temp_qr_path}'")
        cloud_result = cloudinary.uploader.upload(temp_qr_path, folder="themeqr/qrcodes_dynamic_demo")
        cloud_url = cloud_result['secure_url']
        print(f"🌐 Uploaded QR to Cloudinary: {cloud_url}")
        os.remove(temp_qr_path)
        print(f"🗑️ Cleaned up temporary file: {temp_qr_path}")
        return jsonify(success=True, qr_url=cloud_url)
    except Exception as e:
        print(f"❌ Error generating QR code: {e}")
        return jsonify(success=False, error=str(e)), 500

@app.route('/update_index', methods=['POST'])
def update_index():
    data = request.get_json()
    wrapper = data.get('wrapper')
    landing = data.get('landing')
    print(f"🔁 Received wrapper: {wrapper}")
    print(f"🔁 Received landing: {landing}")
    if not wrapper or not landing:
        return jsonify(success=False, error="Missing wrapper or landing URL."), 400
    try:
        qr_path = "/tmp/themeqr_landing_qr_video_overlay.png"
        qr_img = qrcode.make(landing).convert("RGB")
        qr_img.save(qr_path)
        print(f"✅ QR generated at {qr_path}")
        wrapper_temp_path = f"/tmp/{uuid.uuid4()}.mp4"
        print(f"Downloading wrapper to {wrapper_temp_path}")
        with requests.get(wrapper, stream=True) as r:
            r.raise_for_status()
            with open(wrapper_temp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print("✅ Wrapper video downloaded.")
        video_clip = VideoFileClip(wrapper_temp_path).subclip(0, 10)
        qr_clip = ImageClip(qr_path).set_duration(video_clip.duration).resize(height=150).set_pos(("right", "bottom"))
        final_clip = CompositeVideoClip([video_clip, qr_clip])
        final_output_path = "/tmp/final_themeqr_video.mp4"
        print(f"Compositing video. Output to {final_output_path}")
        final_clip.write_videofile(final_output_path, codec="libx264", audio_codec="aac")
        print("✅ Final video created.")
        cloud_result = cloudinary.uploader.upload_large(
            final_output_path, resource_type="video", folder="themeqr/wrappers")
        cloud_url = cloud_result['secure_url']
        print(f"🌐 Uploaded to Cloudinary: {cloud_url}")
        with open(TEMPLATE_PATH, "r") as template:
            content = template.read()
        updated_html = content.replace(
            'src="https://res.cloudinary.com/themeqr-test/video/upload/v1752014993/themeqr/wrappers/obsg01o6dfzl6du5bsaa.mp4"',
            f'src="{cloud_url}"'
        )
        with open("/tmp/index.html", "w") as f:
            f.write(updated_html)
        print("✅ index.html updated.")
        return jsonify(success=True, video_url=cloud_url)
    except Exception as e:
        print(f"❌ Error in update_index: {str(e)}")
        return jsonify(success=False, error=str(e))

@app.route('/go')
def redirect_to_landing():
    try:
        response = supabase.table('decks').select("landing_url").eq("id", DEMO_DECK_ID).single().execute()
        if response.error:
            print(f"❌ Supabase fetch error: {response.error.message}")
            return redirect("https://themeqr.com", code=302)
        landing_url = response.data["landing_url"]
        print(f"✅ Redirecting /go to: {landing_url}")
        return redirect(landing_url, code=302)
    except Exception as e:
        print(f"❌ Exception in /go: {e}")
        return redirect("https://themeqr.com", code=302)

@app.route('/api/vaults/<string:user_id>', methods=['GET'])
async def get_user_vault_and_decks(user_id):
    try:
        vault_id = await get_or_create_user_vault(user_id)
        if not vault_id:
            return jsonify({"error": "Could not retrieve or create vault."}), 500
        response = supabase.table('decks').select('*').eq('vault_id', vault_id).order('created_at', desc=True).execute()
        if response.error:
            print(f"❌ Supabase error fetching decks: {response.error.message}")
            return jsonify({"error": response.error.message}), 500
        decks = response.data
        return jsonify({"vault_id": vault_id, "decks": decks}), 200
    except Exception as e:
        print(f"❌ Exception in get_user_vault_and_decks: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/vaults/<string:vault_id>/decks', methods=['POST'])
def create_deck_in_vault(vault_id):
    data = request.get_json()
    user_id = data.get('user_id')
    deck_name = data.get('deck_name')
    landing_url = data.get('landing_url')
    if not user_id or not deck_name or not landing_url:
        return jsonify({"error": "User ID, deck name, and landing page required"}), 400
    if not landing_url.startswith('http://') and not landing_url.startswith('https://'):
        return jsonify({"error": "Landing page must be a valid URL starting with http:// or https://"}), 400
    try:
        vault_check_response = supabase.table('vaults').select('id').eq('id', vault_id).eq('user_id', user_id).single().execute()
        if not vault_check_response.data:
            return jsonify({"error": "Vault not found or does not belong to this user."}), 403
        response = supabase.table('decks').insert({
            'vault_id': vault_id,
            'deck_name': deck_name,
            'landing_url': landing_url,
            'qr_code': '',
            'wrapper': '',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }).execute()
        if response.error:
            print(f"❌ Supabase error creating deck: {response.error.message}")
            return jsonify({"error": response.error.message}), 500
        new_deck = response.data[0]
        return jsonify(new_deck), 201
    except Exception as e:
        print(f"❌ Exception in create_deck_in_vault: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/decks/<string:deck_id>', methods=['PUT'])
def update_deck(deck_id):
    data = request.get_json()
    user_id = data.get('user_id')
    landing_url = data.get('landing_url')
    deck_name = data.get('deck_name')
    if not user_id or not landing_url:
        return jsonify({"error": "User ID and landing page required"}), 400
    if not landing_url.startswith('http://') and not landing_url.startswith('https://'):
        return jsonify({"error": "Landing page must be a valid URL starting with http:// or https://"}), 400
    try:
        deck_response = supabase.table('decks').select('vault_id').eq('id', deck_id).single().execute()
        if not deck_response.data:
            return jsonify({"error": "Deck not found."}), 404
        deck_vault_id = deck_response.data['vault_id']
        vault_check_response = supabase.table('vaults').select('id').eq('id', deck_vault_id).eq('user_id', user_id).single().execute()
        if not vault_check_response.data:
            return jsonify({"error": "You do not have permission to update this deck."}), 403
        update_data = {
            'landing_url': landing_url,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        if deck_name:
            update_data['deck_name'] = deck_name
        response = supabase.table('decks').update(update_data).eq('id', deck_id).execute()
        if response.error:
            print(f"❌ Supabase error updating deck: {response.error.message}")
            return jsonify({"error": response.error.message}), 500
        if not response.data:
            return jsonify({"error": "Deck not found or nothing to update."}), 404
        return jsonify({"message": "Deck updated successfully", "deck": response.data[0]}), 200
    except Exception as e:
        print(f"❌ Exception in update_deck: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
   # port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
   # from dotenv import load_dotenv 
   # load_dotenv()  # Load environment variables from .env file 
    app.run(debug=True, port=5000)