import os
import tempfile
from dotenv import load_dotenv
import streamlit as st
import cloudinary
import cloudinary.uploader

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

ALLOWED_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}

st.set_page_config(page_title="Upload Video to Cloudinary", page_icon="🎥", layout="centered")
st.title("🎥 Upload Video to Cloudinary")

folder = st.text_input("Optional Cloudinary folder (e.g. themeqr/wrappers)", value="")
file = st.file_uploader("Pick a video", type=[e.lstrip(".") for e in ALLOWED_EXTS])

if st.button("Upload", type="primary", disabled=file is None):
    if file is None:
        st.error("Please choose a file.")
    else:
        # Validate extension
        _, ext = os.path.splitext(file.name)
        ext = ext.lower()
        if ext not in ALLOWED_EXTS:
            st.error(f"Unsupported file type: {ext}")
        else:
            # Save to temp
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(file.read())
                tmp_path = tmp.name

            # Build a safe public_id stem
            base = os.path.splitext(os.path.basename(file.name))[0]
            # keep it simple; Cloudinary will sanitize, but we'll trim length
            public_id = base[:80] or "video"

            with st.spinner("Uploading to Cloudinary…"):
                try:
                    res = cloudinary.uploader.upload_large(
                        tmp_path,
                        resource_type="video",
                        folder=(folder.strip() or None),
                        public_id=public_id,
                    )
                except Exception as e:
                    st.error(f"Upload failed: {e}")
                else:
                    st.success("Upload complete!")
                    st.write("**Secure URL:**")
                    st.write(res["secure_url"])
                    st.video(res["secure_url"])
                finally:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
