from flask import Flask, request, jsonify
import os, requests
from dotenv import load_dotenv

load_dotenv()
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")

app = Flask(__name__)

@app.get("/api/giphy-search")
def giphy_search():
    q = request.args.get("q", "funny")
    limit = request.args.get("limit", "24")
    rating = request.args.get("rating", "pg")

    url = "https://api.giphy.com/v1/gifs/search"
    params = {"api_key": GIPHY_API_KEY, "q": q, "limit": limit, "rating": rating}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json().get("data", [])

    items = []
    for g in data:
        images = g.get("images", {})
        downsized = images.get("downsized_medium") or images.get("original") or {}
        thumb = images.get("fixed_width_small_still") or images.get("preview_gif") or downsized
        items.append({
            "provider": "giphy",
            "provider_id": g.get("id"),
            "title": g.get("title") or "",
            "url_web": downsized.get("url"),
            "url_thumb": (thumb.get("url") or downsized.get("url")),
            "width": int(downsized.get("width", 480)),
            "height": int(downsized.get("height", 270)),
            "mime": "image/gif"
        })

    return jsonify({"items": items})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
