// File: /api/tenor-search.js
// Runtime: Node.js on Vercel (Next.js API route)
// Env var required: TENOR_API_KEY
//
// Usage:
//   GET /api/tenor-search?q=funny cats&limit=12&media_filter=minimal&pos=XXXX
//
// Notes:
// - Uses Tenor v2 API: https://tenor.googleapis.com/v2/search
// - Returns simplified objects (id, title, preview, gif, mp4, tinygif, tinymp4, nanomp4, shareUrl, dims, duration)
// - Supports CORS + OPTIONS preflight

const TENOR_ENDPOINT = "https://tenor.googleapis.com/v2/search";
const CLIENT_KEY = "themeqr"; // identifies your app in Tenor analytics (safe to expose)

function setCors(res) {
  res.setHeader("Access-Control-Allow-Origin", "*"); // tighten for prod domains
  res.setHeader("Access-Control-Allow-Methods", "GET,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
}

function badRequest(res, msg, code = 400) {
  setCors(res);
  res.status(code).json({ ok: false, error: msg });
}

function mapResult(item) {
  // Tenor v2 returns media_formats with keys like: gif, mp4, tinygif, tinymp4, nanomp4, webm, etc.
  // Each format has: url, dims [w,h], duration, size
  const mf = item.media_formats || {};
  const pick = (k) => (mf[k] && mf[k].url) ? { url: mf[k].url, dims: mf[k].dims, duration: mf[k].duration } : null;

  // Choose a preview image/gif (prefer tinygif > gif)
  const preview =
    (mf.tinygif && mf.tinygif.url) ? mf.tinygif.url :
    (mf.gif && mf.gif.url) ? mf.gif.url :
    null;

  return {
    id: item.id,
    title: item.content_description || "",
    // media:
    preview,                             // handy for thumbnail display
    gif: pick("gif"),
    mp4: pick("mp4"),
    tinygif: pick("tinygif"),
    tinymp4: pick("tinymp4"),
    nanomp4: pick("nanomp4"),
    webm: pick("webm"),
    // meta:
    shareUrl: item.itemurl || item.url || null,
    created: item.created,               // ISO time
  };
}

export default async function handler(req, res) {
  setCors(res);

  if (req.method === "OPTIONS") {
    return res.status(204).end();
  }
  if (req.method !== "GET") {
    return badRequest(res, "Method not allowed", 405);
  }

  const apiKey = process.env.TENOR_API_KEY;
  if (!apiKey) {
    return badRequest(res, "TENOR_API_KEY is not configured on the server", 500);
  }

  // Inputs
  const q = (req.query.q || "").toString().trim();
  const limit = Math.min(Math.max(parseInt(req.query.limit || "20", 10) || 20, 1), 50); // clamp 1..50
  const pos = (req.query.pos || "").toString().trim();      // pagination cursor from previous response
  const mediaFilter = (req.query.media_filter || "minimal").toString().trim(); // "basic" | "minimal" | "tinygif" etc.
  const country = (req.query.country || "").toString().trim(); // optional, e.g., "US"
  const locale = (req.query.locale || "").toString().trim();   // optional, e.g., "en_US"
  const random = (req.query.random || "").toString().trim();   // optional: "true" or "1" to randomize

  if (!q) {
    return badRequest(res, "Missing required query parameter: q");
  }

  // Build Tenor request
  const params = new URLSearchParams();
  params.set("key", apiKey);
  params.set("client_key", CLIENT_KEY);
  params.set("q", q);
  params.set("limit", String(limit));
  params.set("media_filter", mediaFilter);  // "minimal" is efficient for GIF/MP4 urls
  if (pos) params.set("pos", pos);
  if (country) params.set("country", country);
  if (locale) params.set("locale", locale);
  if (random === "true" || random === "1") params.set("random", "true");

  // Optional: ar_range or contentfilter can be added if you want to constrain aspect ratios or safety
  // params.set("ar_range", "all");          // "all" | "wide" | "standard" | "tall"
  // params.set("contentfilter", "high");    // "off" | "low" | "medium" | "high"

  // Fetch with timeout
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12_000);

  let r;
  try {
    r = await fetch(`${TENOR_ENDPOINT}?${params.toString()}`, {
      method: "GET",
      signal: controller.signal,
      headers: {
        "Accept": "application/json",
      },
    });
  } catch (e) {
    clearTimeout(timeout);
    return badRequest(res, `Network error contacting Tenor: ${e?.message || e}`, 502);
  } finally {
    clearTimeout(timeout);
  }

  if (!r.ok) {
    const text = await r.text().catch(() => "");
    return badRequest(res, `Tenor API error (${r.status}): ${text || r.statusText}`, 502);
  }

  let data;
  try {
    data = await r.json();
  } catch {
    return badRequest(res, "Invalid JSON from Tenor", 502);
  }

  // Shape response
  const results = Array.isArray(data.results) ? data.results.map(mapResult) : [];
  const next = data.next || null; // pass back Tenor pagination cursor

  // Bubble up Tenor rate-limit info if present
  const rl = {
    limit: r.headers.get("x-ratelimit-limit"),
    remaining: r.headers.get("x-ratelimit-remaining"),
    reset: r.headers.get("x-ratelimit-reset"),
  };

  res.status(200).json({
    ok: true,
    q,
    count: results.length,
    next,          // pass this back as ?pos= to paginate
    results,
    rateLimit: rl,
  });
}
