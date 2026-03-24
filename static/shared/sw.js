/**
 * SciTeX Service Worker — Minimal PWA registration
 *
 * Enables "Add to Home Screen" standalone mode on iOS/Android.
 * Network-first strategy: always fetch from server, fall back to cache.
 */

const CACHE_NAME = "scitex-v1";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(clients.claim());
});

self.addEventListener("fetch", (event) => {
  // Network-first: try server, fall back to cache
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Cache successful GET responses for offline fallback
        if (event.request.method === "GET" && response.status === 200) {
          const clone = response.clone();
          caches
            .open(CACHE_NAME)
            .then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request)),
  );
});
