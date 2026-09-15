/**
 * SciTeX Service Worker — Minimal PWA registration
 *
 * Enables "Add to Home Screen" standalone mode on iOS/Android.
 * Network-first strategy: always fetch from server, fall back to cache.
 */

const CACHE_NAME = "scitex-v1";

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

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(clients.claim());
});

self.addEventListener("fetch", (event) => {
  const isPage = event.request.mode === "navigate";
  // Network-first: try server, fall back to cache
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (isPage && response.status >= 502 && response.status <= 504) {
          return retryPage();
        }
        // Cache successful GET responses for offline fallback
        if (event.request.method === "GET" && response.status === 200) {
          const clone = response.clone();
          caches
            .open(CACHE_NAME)
            .then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() =>
        caches.match(event.request).then((cached) => cached || (isPage ? retryPage() : Response.error())),
      ),
  );
});
