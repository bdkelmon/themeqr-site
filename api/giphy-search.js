// api/giphy-search.js
export default async function handler(req, res) {
  const q = req.query.q || '';
  if (!q) return res.status(400).json({ error: 'Missing q' });

  // Call GIPHY (server-side)
  const apiKey = process.env.GIPHY_API_KEY; // set in Vercel Project Settings → Environment Variables
  const url = `https://api.giphy.com/v1/gifs/search?api_key=${apiKey}&q=${encodeURIComponent(q)}&limit=5&rating=g`;

  const r = await fetch(url);
  if (!r.ok) {
    const text = await r.text();
    return res.status(502).json({ error: 'Upstream error', detail: text.slice(0,200) });
  }

  const data = await r.json();

  // (optional) reshape to your frontend’s expected shape
  const items = (data.data || []).map(d => ({
    id: d.id,
    title: d.title || '',
    url_web: d.url,
    url_thumb: d.images?.fixed_width_small?.url || d.images?.downsized?.url || '',
    width: Number(d.images?.fixed_width_small?.width || 200),
    height: Number(d.images?.fixed_width_small?.height || 200),
  }));

  res.status(200).json({ items });
}
