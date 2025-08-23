from flask import Flask, request, jsonify
import os, requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")

@app.get("/api/giphy-search")
def giphy_search():
    try:
        # 0) Basic guards
        if not GIPHY_API_KEY:
            return jsonify({"error": "GIPHY_API_KEY not configured"}), 500

        q = request.args.get("q", "cat")
        limit = request.args.get("limit", "12")
        rating = request.args.get("rating", "pg")

        # 1) Call Giphy with timeout
        params = {
            "api_key": GIPHY_API_KEY,
            "q": q,
            "limit": limit,
            "rating": rating,
        }
        r = requests.get("https://api.giphy.com/v1/gifs/search",
                         params=params, timeout=10)

        # 2) If Giphy errors, surface it so you can see why
        if not r.ok:
            return jsonify({
                "error": "GIPHY request failed",
                "status": r.status_code,
                "giphy_body": safe_text(r)
            }), r.status_code

        j = r.json()
        data = j.get("data", [])

        # 3) Normalize safely (not all items have the same shapes)
        results = []
        for it in data:
            images = it.get("images", {})
            # Prefer downsized_medium, fallback to original
            full = images.get("downsized_medium") or images.get("original") or {}
            # Prefer a small still/preview for grid
            thumb = (images.get("fixed_width_small_still")
                     or images.get("preview_gif")
                     or full)

            results.append({
                "id": it.get("id"),
                "title": it.get("title") or "",
                "url_web": full.get("url"),
                "url_thumb": (thumb or {}).get("url") or full.get("url"),
                "width": int((full.get("width") or 0) or 0) if str(full.get("width", "")).isdigit() else 480,
                "height": int((full.get("height") or 0) or 0) if str(full.get("height", "")).isdigit() else 270,
                "mime": "image/gif",
            })

        return jsonify({"items": results})

    except Exception as e:
        # 4) Last-resort error to see what blew up
        return jsonify({"error": "server_exception", "detail": str(e)}), 500

def safe_text(resp):
    try:
        return resp.text[:2000]  # cap size
    except Exception:
        return "<no-body>"


