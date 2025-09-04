// api/giphy-search.js
export default async function handler(req, res) {
    
    try {
    const q = (req.query?.q || "").trim();
    if (!q) return res.status(400).json({ error: "Missing q" });

    const apiKey = process.env.GIPHY_API_KEY;
    if (!apiKey) {
      // Most common 502 cause on Vercel: env var not set or not redeployed
      return res.status(500).json({ error: "GIPHY_API_KEY is not set on the server" });
    }

    const url =
      `https://api.giphy.com/v1/gifs/search?api_key=${apiKey}` +
      `&q=${encodeURIComponent(q)}&limit=5&rating=g`;

    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) {
      const text = await r.text();
      // Return 502 but *with* upstream detail so you can see why in Network tab
      return res.status(502).json({ error: "Upstream error", status: r.status, detail: text.slice(0, 500) });
    }

    const data = await r.json();

    // Keep your reshape, but return both shapes so the frontend can read either
    const items = (data.data || []).map((d) => ({
      id: d.id,
      title: d.title || "",
      url_web: d.url,
      url_thumb: d.images?.fixed_width_small?.url || d.images?.downsized?.url || "",
      width: Number(d.images?.fixed_width_small?.width || 200),
      height: Number(d.images?.fixed_width_small?.height || 200),
    }));

    // Return both for now to avoid breaking your existing UI
    return res.status(200).json({ items, data: data.data || [] });
  } catch (err) {
    return res.status(500).json({ error: "Server error", detail: String(err) });
  }
}
