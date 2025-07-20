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
from datetime import datetime, timezone

# Cloudinary setup
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://hvfqdrfdefgfqbfdikpn.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh2ZnFkcmZkZWZnZnFiZmRpa3BuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTIxOTA4MjgsImV4cCI6MjA2Nzc2NjgyOH0.nG8rzVCQR6J8XxbTaiC9C_D61NCJU") # Ensure this is correct
supabase: Client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

TEMPLATE_PATH = os.path.join(app.root_path, 'themeqr-site', 'index_template.html')
#--DEMO_DECK_ID = "demo_qr_redirect" changed to a real deck ID 
DEMO_DECK_ID = "71f42d9b-fe22-4085-87f0-944ab85ac07e"
if not os.path.exists(app.static_folder):
    os.makedirs(app.static_folder)

# --- Helper Function for Vault Management ---
async def get_or_create_user_vault(user_id: str):
    """
    Fetches a user's vault. If it doesn't exist, creates a default one.
    Returns the vault ID or None if an error occurs.
    """
    try:
        # Try to fetch the existing vault for the user

        if response.data:
            print(f"✅ Found existing vault for user {user_id}: {response.data['id']}")
            return response.data['id']
        elif response.error and response.error.code == 'PGRST116': # No rows found
            # If no vault found, create a new one
            print(f"ℹ️ No vault found for user {user_id}. Creating a new one...")
            insert_response = supabase.table('vaults').insert({
                'user_id': user_id,
                'vault_name': f"Vault for {user_id[:8]}", # Default name
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

# --- Existing Routes ---
@app.route('/')
def home():
    return render_template('qr_landing_editor.html')

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
        if not new_landing or not new_landing.startswith("http") or not new_landing.startswith("https"):
            print("❌ Invalid landing URL provided.")
            return jsonify(success=False, error="Invalid URL format"), 400

        response = supabase.table('decks').upsert(
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
    try:
        data = request.get_json()
        link_to_encode = data.get('link')

        if not link_to_encode:
            return jsonify(success=False, error="Missing link to encode."), 400

        temp_qr_filename = f"temp_qr_{uuid.uuid4()}.png"
        temp_qr_path = os.path.join("/tmp", temp_qr_filename)

        qr_img = qrcode.make(link_to_encode).convert("RGB")
        qr_img.save(temp_qr_path)
        print(f"✅ Temporary QR code generated for '{link_to_encode}' at '{temp_qr_path}'")

        cloud_result = cloudinary.uploader.upload(
            temp_qr_path,
            folder="themeqr/qrcodes_dynamic_demo"
        )
        cloud_url = cloud_result['secure_url']
        print(f"🌐 Uploaded QR to Cloudinary: {cloud_url}")

        os.remove(temp_qr_path)
        print(f"🗑️ Cleaned up temporary file: {temp_qr_path}")

        return jsonify(success=True, qr_url=cloud_url)

    except Exception as e:
        print(f"❌ Error generating or uploading QR code: {e}")
        return jsonify(success=False, error=str(e)), 500

@app.route('/update_index', methods=['POST'])
def update_index():
    data = request.get_json()
    wrapper = data.get('wrapper')
    landing = data.get('landing')

    print("🔁 Received wrapper:", wrapper)
    print("🔁 Received landing page:", landing)

    if not wrapper or not landing:
        return jsonify(success=False, error="Missing wrapper or landing URL."), 400

    try:
        qr_path = "/tmp/themeqr_landing_qr_video_overlay.png"
        qr_img = qrcode.make(landing).convert("RGB")
        qr_img.save(qr_path)
        print(f"✅ QR for video overlay generated at {qr_path}")

        wrapper_temp_path = f"/tmp/{uuid.uuid4()}.mp4"
        print(f"Downloading wrapper from {wrapper} to {wrapper_temp_path}")
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
        print(f"Compositing video and QR. Output to {final_output_path}")
        final_clip.write_videofile(final_output_path, codec="libx264", audio_codec="aac")
        print("✅ Final video with QR overlay created.")

        cloud_result = cloudinary.uploader.upload_large(
            final_output_path,
            resource_type="video",
            folder="themeqr/wrappers"
        )
        cloud_url = cloud_result['secure_url']
        print(f"🌐 Uploaded to Cloudinary: {cloud_url}")

        print(f"📁 Looking for template at: {TEMPLATE_PATH}")
        with open(TEMPLATE_PATH, "r") as template:
            content = template.read()

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
    try:
        response = supabase.table('decks').select("landing_url").eq("id", DEMO_DECK_ID).single().execute()

        if response.error:
            print(f"❌ Supabase fetch error for DEMO_DECK_ID: {response.error.message}. Redirecting to default.")
            return redirect("https://themeqr.com", code=302)

        landing_url = response.data["landing_url"]
        print(f"✅ Redirecting /go to: {landing_url}")
        return redirect(landing_url, code=302)

    except Exception as e:
        print(f"❌ Exception in /go redirect: {e}. Redirecting to default.")
        return redirect("https://themeqr.com", code=302)


# --- NEW API Endpoints for ThemeQR Vault (Supabase Integration) ---

@app.route('/api/vaults/<string:user_id>', methods=['GET'])
async def get_user_vault_and_decks(user_id):
    """
    Fetches the user's vault and all associated decks.
    If no vault exists for the user, it creates one.
    """
    try:
        vault_id = await get_or_create_user_vault(user_id)
        if not vault_id:
            return jsonify({"error": "Could not retrieve or create user vault."}), 500

        # Fetch decks associated with this vault_id
        response = supabase.table('decks').select('*').eq('vault_id', vault_id).order('created_at', desc=True).execute()

        if response.error:
            print(f"❌ Supabase error fetching decks for vault {vault_id}: {response.error.message}")
            return jsonify({"error": response.error.message}), 500

        decks = response.data
        return jsonify({"vault_id": vault_id, "decks": decks}), 200

    except Exception as e:
        print(f"❌ Exception in get_user_vault_and_decks: {str(e)}")
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500


@app.route('/api/vaults/<string:vault_id>/decks', methods=['POST'])
def create_deck_in_vault(vault_id):
    """
    Creates a new deck within a specific vault.
    Requires 'user_id', 'deck_name', and 'landing_url' in the request body.
    """
    data = request.get_json()
    user_id = data.get('user_id') # For verification
    deck_name = data.get('deck_name')
    landing_url = data.get('landing_url')

    if not user_id or not deck_name or not landing_url:
        return jsonify({"error": "User ID, deck name, and landing page are required"}), 400

    if not landing_url.startswith('http://') and not landing_url.startswith('https://'):
        return jsonify({"error": "Landing page must be a valid URL starting with http:// or https://"}), 400

    try:
        # Verify that the vault_id belongs to the user_id
        vault_check_response = supabase.table('vaults').select('id').eq('id', vault_id).eq('user_id', user_id).single().execute()
        if not vault_check_response.data:
            return jsonify({"error": "Vault not found or does not belong to this user."}), 403 # Forbidden

        # Insert new deck
        response = supabase.table('decks').insert({
            'vault_id': vault_id,
            'deck_name': deck_name,
            'landing_url': landing_url,
            'qr_code': '', # Placeholder
            'wrapper': '', # Placeholder
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }).execute()

        if response.error:
            print(f"❌ Supabase error creating deck in vault {vault_id}: {response.error.message}")
            return jsonify({"error": response.error.message}), 500

        new_deck = response.data[0]
        return jsonify(new_deck), 201

    except Exception as e:
        print(f"❌ Exception in create_deck_in_vault: {str(e)}")
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500

@app.route('/api/decks/<string:deck_id>', methods=['PUT'])
def update_deck(deck_id):
    """
    Updates an existing deck's landing page.
    Requires 'user_id' and 'landing_url' in the request body.
    Also verifies ownership via vault.
    """
    data = request.get_json()
    user_id = data.get('user_id') # For verification
    landing_url = data.get('landing_url')
    deck_name = data.get('deck_name') # Optional: allow updating name too

    if not user_id or not landing_url:
        return jsonify({"error": "User ID and landing page are required"}), 400

    if not landing_url.startswith('http://') and not landing_url.startswith('https://'):
        return jsonify({"error": "Landing page must be a valid URL starting with http:// or https://"}), 400

    try:
        # First, get the deck and its associated vault_id
        deck_response = supabase.table('decks').select('vault_id').eq('id', deck_id).single().execute()
        if not deck_response.data:
            return jsonify({"error": "Deck not found."}), 404
        
        deck_vault_id = deck_response.data['vault_id']

        # Then, verify that the vault_id belongs to the user_id
        vault_check_response = supabase.table('vaults').select('id').eq('id', deck_vault_id).eq('user_id', user_id).single().execute()
        if not vault_check_response.data:
            return jsonify({"error": "You do not have permission to update this deck."}), 403 # Forbidden

        update_data = {
            'landing_url': landing_url,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        if deck_name:
            update_data['deck_name'] = deck_name

        response = supabase.table('decks').update(update_data).eq('id', deck_id).execute()

        if response.error:
            print(f"❌ Supabase error updating deck {deck_id}: {response.error.message}")
            return jsonify({"error": response.error.message}), 500

        if not response.data:
            return jsonify({"error": "Deck not found or nothing to update."}), 404

        return jsonify({"message": "Deck updated successfully", "deck": response.data[0]}), 200

    except Exception as e:
        print(f"❌ Exception in update_deck: {str(e)}")
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
