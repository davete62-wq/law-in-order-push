// js/api.js — Centralised API helper with in-memory cache
// Automatically detects local testing vs production:
const API_BASE = (
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1" ||
  window.location.protocol === "file:"
)
  ? "http://localhost:8000/api"
  : (window.location.hostname.endsWith("onrender.com")
      ? "/api"
      : "https://YOUR-APP.onrender.com/api");

// ── In-memory cache (key → {data, ts}) ──────────────────────────────
const _cache = {};
const CACHE_TTL = {
  default:       20 * 1000,   // 20 seconds for most lists
  "/auth/me":    60 * 1000,   // 60 seconds – who I am doesn't change often
  "/announcements/":  30 * 1000,
  "/events/":         30 * 1000,
  "/files/":          30 * 1000,
  "/points/rankings": 30 * 1000,
  "/users/":          20 * 1000,
};

function _cacheKey(path) { return path; }
function _ttl(path) {
  for (const k of Object.keys(CACHE_TTL)) {
    if (path.startsWith(k)) return CACHE_TTL[k];
  }
  return CACHE_TTL.default;
}
function _cacheGet(path) {
  const entry = _cache[_cacheKey(path)];
  if (!entry) return null;
  if (Date.now() - entry.ts > _ttl(path)) { delete _cache[_cacheKey(path)]; return null; }
  return entry.data;
}
function _cacheSet(path, data) {
  _cache[_cacheKey(path)] = { data, ts: Date.now() };
}
// Call this after any write (POST/PATCH/DELETE) to bust related caches
function _cacheBust(...prefixes) {
  for (const pre of prefixes) {
    for (const k of Object.keys(_cache)) {
      if (k.startsWith(pre)) delete _cache[k];
    }
  }
}

async function apiFetch(path, options = {}) {
  const url = API_BASE + path;
  const defaults = {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  };
  const cfg = { ...defaults, ...options };
  if (cfg.body && typeof cfg.body !== "string") {
    cfg.body = JSON.stringify(cfg.body);
  }

  // On GET requests, serve from cache while simultaneously refreshing in the background
  const isGet = !cfg.method || cfg.method === "GET";
  if (isGet) {
    const cached = _cacheGet(path);
    if (cached !== null) {
      // Return cache instantly, refresh in background (stale-while-revalidate)
      fetch(url, cfg).then(async r => {
        if (r.ok) _cacheSet(path, await r.json());
      }).catch(() => {});
      return cached;
    }
  }

  const res = await fetch(url, cfg);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || `Error ${res.status}`);
  }
  const data = await res.json();
  if (isGet) _cacheSet(path, data);
  return data;
}

const api = {
  get: (path) => apiFetch(path, { method: "GET" }),

  post: (path, body) => apiFetch(path, { method: "POST", body }).then(r => {
    // Bust cache for the same prefix after a write
    _cacheBust(path.replace(/\/[^/]+$/, "/"), path);
    return r;
  }),

  patch: (path, body) => apiFetch(path, { method: "PATCH", body }).then(r => {
    _cacheBust(path.replace(/\/[^/]+$/, "/"), path);
    return r;
  }),

  delete: (path) => apiFetch(path, { method: "DELETE" }).then(r => {
    _cacheBust(path.replace(/\/[^/]+$/, "/"), path);
    return r;
  }),

  // File upload (multipart — cannot use JSON)
  uploadFile: (path, formData) =>
    fetch(API_BASE + path, {
      method: "POST",
      credentials: "include",
      body: formData,
    }).then(async r => {
      if (!r.ok) {
        const e = await r.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(e.detail);
      }
      _cacheBust("/files/", "/assignments/");
      return r.json();
    }),

  // Manual cache busting for cases where you know what changed
  bustCache: (...prefixes) => _cacheBust(...prefixes),
};
