import os
import shutil
import uuid
import cloudinary
import cloudinary.uploader
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
import qrcode
import requests
from flask import Flask, request, render_template, g, jsonify, make_response, send_from_directory, redirect, session, flash, url_for
from flask_cors import CORS
from datetime import datetime, timezone
from supabase import create_client
from dotenv import load_dotenv
import json
import tempfile
from traceback import format_exc
import subprocess, shlex
from PIL import Image as _PILImage
# ---- Pillow 10+ compatibility shim (MoviePy still expects ANTIALIAS/BICUBIC/BILINEAR)
if hasattr(_PILImage, "Resampling"):
    # Only patch if missing (Pillow >=10 removed these attributes)
    _PILImage.ANTIALIAS = getattr(_PILImage, "ANTIALIAS", _PILImage.Resampling.LANCZOS)
    _PILImage.BICUBIC   = getattr(_PILImage, "BICUBIC",   _PILImage.Resampling.BICUBIC)
    _PILImage.BILINEAR  = getattr(_PILImage, "BILINEAR",  _PILImage.Resampling.BILINEAR)


# Load environment variables
load_dotenv()

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("SUPABASE_URL or SUPABASE_KEY not set")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__, template_folder='themeqr-site/templates', static_folder='themeqr-site')
app.secret_key = os.getenv("FLASK_SECRET_KEY")

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

def get_or_create_user_vault(user_id):
    try:
        response = supabase.table('vaults').select('id').eq('user_id', user_id).single().execute()
        if response.data:
            return response.data['id']
        elif response.error and response.error.code == 'PGRST116':
            insert_response = supabase.table('vaults').insert({
                'user_id': user_id,
                'vault_name': f"Vault for {user_id[:8]}",
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).execute()
            if insert_response.error:
                print(f"Error creating vault: {insert_response.error.message}")
                return None
            return insert_response.data[0]['id']
        else:
            print(f"Supabase error: {response.error.message}")
            return None
    except Exception as e:
        print(f"Error in get_or_create_user_vault: {str(e)}")
        return None

@app.route("/manager")
def manager():
    print(f"Serving theme_applier.html via /manager. Supabase URL: {os.getenv('SUPABASE_URL')}")
    if not g.user or not g.user.get('id'):
        flash("Please log in to manage themes and decks.", "warning")
        return redirect(url_for('login'))
    
    user = g.user
    vault_id = get_or_create_user_vault(user['id'])
    if not vault_id:
        flash("Could not retrieve or create a vault. Please contact support.", "error")
        return redirect(url_for('index'))
    
    print(f"Assigned vault_id: {vault_id}")
    return render_template('theme_applier.html',
                          supabase_url=os.getenv('SUPABASE_URL'),
                          supabase_key=os.getenv('SUPABASE_KEY'),
                          user=user,
                          vault_id=vault_id)

@app.before_request
def load_user():
    g.user = None  # Initialize g.user
    if 'access_token' in session:
        try:
            response = supabase.auth.get_user(session['access_token'])
            if response and response.user:
                g.user = {
                    'id': response.user.id,
                    'email': response.user.email,
                    'created_at': response.user.created_at
                    # Add other fields as needed
                }
            else:
                print("No user data in response")
        except Exception as e:
            print(f"Error loading user: {e}")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if response.user:
                session['access_token'] = response.session.access_token
                session['refresh_token'] = response.session.refresh_token  # Store refresh token
                session.permanent = True
                flash("Logged in successfully!", "success")
                return redirect(url_for('serve_qr_landing_editor'))  # Redirect to editor
            else:
                flash("Invalid email or password.", "error")
                return redirect(url_for('login'))
        except Exception as e:
            flash(f"Login failed: {str(e)}", "error")
            return redirect(url_for('login'))
    return render_template('login.html')
     

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
        print(f"Signing out at {datetime.now()}")
        if supabase.auth.get_session():
            supabase.auth.sign_out(),
            session.pop('user', None)
        print(f"Sign-out completed at {datetime.now()}")
        response = make_response(redirect("https://www.themeqr.com/"))
        response.set_cookie('user', '', expires=0, path='/')
        return response
    except Exception as e:
        print(f"Sign-out error: {str(e)} at {datetime.now()}")
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

@app.route("/reset-password-confirm", methods=["GET", "POST"])
def reset_password_confirm():
    if request.method == "POST":
        new_password = request.form.get("password")
        if not new_password:
            flash("Password is required.", "error")
            return render_template("reset_password_confirm.html")
        try:
            supabase.auth.update_user({"password": new_password})
            flash("Password updated successfully! Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Failed to update password: {str(e)}", "error")
            return render_template("reset_password_confirm.html")
    access_token = request.args.get("access_token")
    token_type = request.args.get("type")
    if not access_token or token_type != "recovery":
        flash("Invalid or missing recovery token.", "error")
        return redirect(url_for("login"))
    try:
        supabase.auth.verify_otp({"type": "recovery", "token": access_token})
        return render_template("reset_password_confirm.html")
    except Exception as e:
        flash(f"Invalid or expired recovery token: {str(e)}", "error")
        return redirect(url_for("login"))

@app.route('/login/apple', methods=['POST'])
def apple_login():
    token = request.json.get('token')
    # Validate Apple token (requires client secret from Apple Developer)
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get('https://appleid.apple.com/auth/token', headers=headers)
    if response.status_code == 200:
        session['user'] = {'email': response.json().get('email')}
        return jsonify({'success': True})
    return jsonify({'success': False})

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

def get_or_create_user_vault(user_id):
    try:
        # Check if vault exists
        response = supabase.table('vaults').select('id').eq('user_id', user_id).execute()
        if response.data and len(response.data) > 0:
            print(f"Found existing vault: {response.data[0]['id']}")
            return response.data[0]['id']
        
        # If no vault found, create a new one
        insert_response = supabase.table('vaults').insert({
            'user_id': user_id,
            'vault_name': f"Vault for {user_id[:8]}",
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }).execute()
        if insert_response.data and len(insert_response.data) > 0:
            print(f"Created new vault: {insert_response.data[0]['id']}")
            return insert_response.data[0]['id']
        elif insert_response.error:
            print(f"Error creating vault: {insert_response.error.message}")
            return None
        else:
            print("Unexpected insert response: No data or error")
            return None
    except Exception as e:
        print(f"Error in get_or_create_user_vault: {str(e)}")
        return None

from urllib.parse import urlparse, urlunparse
import re

def strip_query(u: str) -> str:
    p = urlparse(u)
    return urlunparse((p.scheme, p.netloc, p.path, '', '', ''))

def qr_local_path_from_url(qr_url: str, static_root: str) -> str | None:
    try:
        p = urlparse(qr_url)
        if p.path.startswith('/static/'):
            fname = os.path.basename(p.path)
            return os.path.join(static_root, fname)
    except Exception:
        pass
    return None

def cloudinary_direct_video_url(cld_url: str) -> str:
    """
    If given a Cloudinary *player* URL, raise. If given a direct video url, return it.
    You can extend this to map player->direct by extracting public_id if needed.
    """
    p = urlparse(cld_url)
    host = p.netloc.lower()
    if 'player.cloudinary.com' in host:
        raise ValueError("Theme wrapper_url is a Cloudinary *player* URL. Store a direct video URL (res.cloudinary.com/.../video/upload/...mp4).")
    return cld_url

def compose_ffmpeg(wrapper_fp: str, qr_fp: str, out_fp: str, max_duration: int = 10) -> None:
    """
    Overlay QR (bottom-right) with ffmpeg.
    Optimized for low-CPU/RAM and to avoid gunicorn timeouts.
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found on PATH")

    # Downscale base to <=720p to keep encode cheap.
    # Scale QR to ~1/6 of base height. 20px margin.
    # Shorten to max_duration, drop audio, use veryfast + crf 30, single thread.
    filter_complex = (
    # Downscale base to <=720p, keep AR, then force even dims
    "[0:v]scale='min(iw,720)':'-2':force_original_aspect_ratio=decrease,"
    "scale=trunc(iw/2)*2:trunc(ih/2)*2[base];"

    # Scale QR relative to base height (~1/6 of base height)
    "[1][base]scale2ref=w=-1:h=ih/6[qr][b];"

    # Overlay bottom-right with 20px margin
    "[b][qr]overlay=W-w-20:H-h-20"

    # Ensure final frame is even (handles any odd result after overlay)
    ",pad=ceil(iw/2)*2:ceil(ih/2)*2"
  )

    cmd = [
        "ffmpeg", "-y",
        "-hide_banner", "-loglevel", "error",
        "-i", wrapper_fp,
        "-i", qr_fp,
        "-t", str(max_duration),
        "-filter_complex", filter_complex,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "30",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-threads", "1",
        "-an",                 # remove if you need audio
        out_fp,
    ]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=55,        # keep under typical 60s gunicorn timeout
        )
    except subprocess.TimeoutExpired as te:
        raise RuntimeError(f"ffmpeg timed out at ~{te.timeout}s")

    if proc.returncode != 0:
        # Surface the last part of stderr so we can see why
        err = proc.stderr.decode("utf-8", "ignore")
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}): {err[-2000:]}")

    if not os.path.exists(out_fp) or os.path.getsize(out_fp) == 0:
        raise RuntimeError("ffmpeg produced an empty output file")

@app.route('/apply_theme', methods=['POST'])
def apply_theme():
    data = request.get_json()
    deck_id = data.get('deck_id')
    theme_id = data.get('theme_id')
    qr_url = data.get('qr_url')

    if not deck_id or not theme_id or not qr_url:
        return jsonify({'success': False, 'error': 'Missing deck_id, theme_id, or qr_url'}), 400

    tmp_wrapper = tmp_qr = out_path = None
    try:
        # 1) Fetch theme + deck
        theme_resp = supabase.table('themes').select('wrapper_url, landing_url').eq('id', theme_id).single().execute()
        if not theme_resp.data:
            raise ValueError('Theme not found')
        deck_resp = supabase.table('decks').select('vault_id, deck_name').eq('id', deck_id).single().execute()
        if not deck_resp.data:
            raise ValueError('Deck not found')

        wrapper_url = cloudinary_direct_video_url(theme_resp.data['wrapper_url'])
        landing_url = theme_resp.data['landing_url']
        qr_url_clean = strip_query(qr_url)

        # 2) Download wrapper
        tmp_wrapper = os.path.join(tempfile.gettempdir(), f'{uuid.uuid4()}.mp4')
        app.logger.info(f"[apply_theme] Downloading wrapper: {wrapper_url}")
        with requests.get(wrapper_url, stream=True, timeout=180, headers={"User-Agent": "themeqr/1.0"}) as r:
            r.raise_for_status()
            with open(tmp_wrapper, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
        if os.path.getsize(tmp_wrapper) == 0:
            raise RuntimeError("Downloaded wrapper is empty")

        # 3) Get QR (local vs remote)
        qr_local = qr_local_path_from_url(qr_url_clean, app.static_folder)
        if qr_local and os.path.exists(qr_local):
            tmp_qr = qr_local
            app.logger.info(f"[apply_theme] Using local QR: {tmp_qr}")
        else:
            tmp_qr = os.path.join(tempfile.gettempdir(), f'{uuid.uuid4()}.png')
            app.logger.info(f"[apply_theme] Downloading QR: {qr_url_clean}")
            with requests.get(qr_url_clean, stream=True, timeout=60, headers={"User-Agent": "themeqr/1.0"}) as r:
                r.raise_for_status()
                with open(tmp_qr, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=256*1024):
                        if chunk:
                            f.write(chunk)
        if not os.path.exists(tmp_qr) or os.path.getsize(tmp_qr) == 0:
            raise RuntimeError("QR file not found/empty")

        # 4) Compose via ffmpeg (faster & lower memory than MoviePy)
        out_path = os.path.join(tempfile.gettempdir(), f'{uuid.uuid4()}_wrapper_out.mp4')
        app.logger.info("[apply_theme] Composing with ffmpeg…")
        compose_ffmpeg(tmp_wrapper, tmp_qr, out_path, max_duration=10)

        # 5) Upload to Cloudinary
        app.logger.info("[apply_theme] Uploading to Cloudinary…")
        cloud_res = cloudinary.uploader.upload_large(
            out_path,
            resource_type="video",
            folder="themeqr/wrappers",
            public_id=f"{deck_id}_wrapper",
            overwrite=True
        )
        new_wrapper_url = cloud_res['secure_url']

        # 6) Update deck
        app.logger.info(f"[apply_theme] Updating deck {deck_id} with wrapper and landing_url")
        upd = supabase.table('decks').update({
            'wrapper': new_wrapper_url,
            'landing_url': landing_url,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', deck_id).execute()
        if not upd.data:
            raise RuntimeError('Failed to update deck row')

        return jsonify({'success': True, 'new_wrapper_url': new_wrapper_url})

    except Exception as e:
        app.logger.error("[apply_theme] ERROR: %s", e)
        app.logger.error(format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        for p in (tmp_wrapper,):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except: pass
        # Only delete tmp_qr if it was downloaded; leave local QR alone
        try:
            if tmp_qr and tmp_qr.startswith(tempfile.gettempdir()) and os.path.exists(tmp_qr):
                os.remove(tmp_qr)
        except: pass
        try:
            if out_path and os.path.exists(out_path):
                os.remove(out_path)
        except: pass

def compose(wrapper_fp, qr_fp, out_fp, max_duration=10):
    """
    Overlay the QR image onto the bottom-right of the base video
    and write the result to out_fp.
    """
    try:
        base_clip = VideoFileClip(wrapper_fp)

        if base_clip.duration and base_clip.duration > max_duration:
            base_clip = base_clip.subclip(0, max_duration)

        bw, bh = base_clip.size
        target_h = int(min(bw, bh) / 12)

        qr_clip = (
            ImageClip(qr_fp)
            .set_duration(base_clip.duration)
            .resize(height=target_h)
            .set_pos(("right", "bottom"))
        )

        final = CompositeVideoClip([base_clip, qr_clip])
        final.write_videofile(
            out_fp,
            codec="libx264",
            audio_codec="aac",
            threads=1,
            preset="ultrafast",
            bitrate="2000k"
        )
    except Exception as e:
        raise RuntimeError(f"Compose failed: {e}")

@app.route('/apply_theme_to_deck', methods=['POST'])
def apply_theme_to_deck():
    data = request.get_json()
    theme_id = data.get('theme_id')
    deck_id = data.get('deck_id')

    try:
        # Fetch the theme to ensure it exists
        theme_response = supabase.table('themes').select('*').eq('id', theme_id).execute()
        if not theme_response.data:
            return jsonify({'success': False, 'error': 'Theme not found'}), 404

        # Update the deck with the theme_id
        response = supabase.table('decks').update({
            'theme_id': theme_id
        }).eq('id', deck_id).execute()

        if response.data:
            return jsonify({'success': True, 'message': 'Theme applied to deck successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to update deck'}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/editor')
def serve_qr_landing_editor():
    print(f"Serving qr_landing_editor.html. Supabase URL: {SUPABASE_URL}")
    vault_id = None
    try:
        if g.user and g.user.get('id'):
            vault_id = get_or_create_user_vault(g.user['id'])
            print(f"Assigned vault_id for user {g.user['id']}: {vault_id}")
        else:
            print("No user or user ID found in g.user")
        # Get tokens from session
        access_token = session.get('access_token', '')
        refresh_token = session.get('refresh_token', '')
        return render_template(
            'qr_landing_editor.html',
            user=g.user,
            supabase_url=SUPABASE_URL,
            supabase_key=SUPABASE_KEY,
            vault_id=vault_id,
            access_token=access_token,  # Pass access token
            refresh_token=refresh_token  # Pass refresh token
        )
    except Exception as e:
        print(f"Error in serve_qr_landing_editor: {str(e)}")
        return "An internal error occurred. Please try again later.", 500

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
        deck_id = data.get('deck_id')

        if not new_landing or (not new_landing.startswith("http://") and not new_landing.startswith("https://")):
            print("❌ Invalid landing URL format.")
            return jsonify(success=False, error="Invalid URL format."), 400

        # Determine the deck_id to use
        target_deck_id = deck_id if deck_id else DEMO_DECK_ID
        print(f"🔧 Updating deck_id: {target_deck_id} with landing_url: {new_landing}")

        response = supabase.table('decks').update({'landing_url': new_landing}).eq('id', target_deck_id).execute()
        if not response.data:
            print(f"⚠️ No row found for ID: {target_deck_id}.")
            return jsonify(success=False, error="Deck ID not found."), 404

        print(f"✅ Supabase updated for {target_deck_id} to {new_landing}.")
        return jsonify(success=True, qr_url=f"https://themeqr-backend.onrender.com/static/{target_deck_id}_qr.png")
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
@app.route('/go.html')
def redirect_to_landing():
    try:
        print(f"⚠️ Start of the /go.html route {datetime.now()}")
        deck_id = request.args.get('id')
        if not deck_id:
            print("⚠️ No id parameter provided, using DEMO_DECK_ID")
            deck_id = "71f42d9b-fe22-4085-87f0-944ab85ac07e"  # Fallback to DEMO_DECK_ID
        response = supabase.table('decks').select("landing_url").eq("id", deck_id).single().execute()
        if response.error:
            print(f"❌ Supabase fetch error: {response.error.message}")
            return redirect("https://themeqr.com", code=302)
        landing_url = response.data["landing_url"]
        print(f"✅ Redirecting /go to: {landing_url} for deck_id {deck_id} at {datetime.now()}")
        return redirect(landing_url, code=302)
    except Exception as e:
        print(f"❌ Exception in /go: {e} at {datetime.now()}")
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
    port = int(os.environ.get('PORT',10000))
    app.run(host='0.0.0.0', port=port, debug=True)
  
   # from dotenv import load_dotenv 
   # load_dotenv()  # Load environment variables from .env file 
