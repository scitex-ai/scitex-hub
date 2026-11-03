/**
 * SciTeX Service Worker — Minimal PWA registration
 *
 * Enables "Add to Home Screen" standalone mode on iOS/Android.
 * Cache only public same-origin static assets. Private pages and API replies
 * must never survive logout or be replayed for another account.
 */

const CACHE_NAME = "scitex-public-static-v2";
const LEGACY_PRIVATE_CACHE = "scitex-v1";

// A standalone PWA has no reload button, so a gateway error page would strand the user.
const RETRY_PAGE = `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SciTeX</title><style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
font-family:system-ui,sans-serif;background:#f7f6f3;color:#1a2a40;text-align:center}
@media (prefers-color-scheme:dark){body{background:#0e121a;color:#e6e9ef}}
p{margin:.4em 1em}button{margin-top:1em;padding:.6em 1.4em;font-size:16px;border:0;
border-radius:999px;background:#1a2a40;color:#fff}</style></head><body><div>
<p><strong>SciTeX is restarting…</strong></p><p>再起動中です。自動で再接続します。</p>
<button onclick="location.reload()">Retry</button></div>
<script>setTimeout(function(){location.reload()},5000)</script></body></html>`;

function retryPage() {
  return new Response(RETRY_PAGE, {
    status: 503,
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  });
}

function explicitlyPublic(policy) {
  // Extension values may contain commas or the word "public" inside quotes.
  let directive = "";
  let quoted = false;
  let escaped = false;
  for (const character of policy + ",") {
    if (character === "," && !quoted) {
      if (directive.trim().toLowerCase() === "public") return true;
      directive = "";
    } else {
      directive += character;
      if (escaped) escaped = false;
      else if (quoted && character === "\\") escaped = true;
      else if (character === '"') quoted = !quoted;
    }
  }
  return false;
}

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  // The old worker cached private responses, including no-store API replies.
  // Remove only that known legacy cache; other applications own their caches.
  event.waitUntil(caches.delete(LEGACY_PRIVATE_CACHE).then(() => clients.claim()));
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (
    request.method !== "GET" || url.origin !== self.location.origin ||
    request.headers.has("Authorization")
  ) return;
  const isPage = request.mode === "navigate";
  const isStatic = url.pathname.startsWith("/static/");
  const isEventStream = (request.headers.get("Accept") || "")
    .toLowerCase().includes("text/event-stream");
  // APIs, event streams, downloads and media use the browser's normal request
  // lifecycle. In particular, never retain a cloned live API response stream.
  if ((!isPage && !isStatic) || isEventStream) return;
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (isPage && response.status >= 502 && response.status <= 504) {
          return retryPage();
        }
        const policy = response.headers.get("Cache-Control") || "";
        const contentType = (response.headers.get("Content-Type") || "").toLowerCase();
        const vary = response.headers.get("Vary") || "";
        const finalURL = response.url ? new URL(response.url) : null;
        if (
          !isPage && response.status === 200 &&
          !response.redirected && finalURL?.origin === self.location.origin &&
          finalURL.pathname.startsWith("/static/") && explicitlyPublic(policy) &&
          !/no-store|private/i.test(policy) &&
          !contentType.includes("text/event-stream") &&
          !contentType.includes("text/html") &&
          !response.headers.has("Set-Cookie") &&
          !/(?:^|,)\s*(?:\*|cookie|authorization)\s*(?:,|$)/i.test(vary)
        ) {
          const clone = response.clone();
          event.waitUntil(
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone)).catch(() => {}),
          );
        }
        return response;
      })
      .catch(async () => {
        if (isPage) return retryPage();
        const cache = await caches.open(CACHE_NAME);
        return (await cache.match(request)) || Response.error();
      }),
  );
});
