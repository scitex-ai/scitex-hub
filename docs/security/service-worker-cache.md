# Service-worker cache boundary

`static/shared/sw.js` owns the root-scoped PWA worker served at `/sw.js`.
It intercepts only same-origin GET navigations and public `/static/` requests.
APIs, event streams, media, downloads, unsafe methods and external origins use
the browser's normal request lifecycle.

Navigations always use the network. A network failure or gateway error returns
the restart/retry page, never a previously cached account's HTML. Only successful,
unredirected same-origin static responses explicitly marked `Cache-Control:
public` may enter `scitex-public-static-v2`. Private/no-store policies,
event-stream or HTML content, authenticated requests and `Vary: Cookie`,
`Authorization` or `*` are excluded. A browser filters `Set-Cookie` from
script-visible response headers, so that header is not the authority for
deciding whether content is public.

The current production nginx static policy does not explicitly declare `public`.
Those responses continue to load online but do not populate the worker's offline
cache. Offline static fallback requires that explicit server-side opt-in.

Activation deletes only the known legacy `scitex-v1` cache, which previously
stored private replies even with `Cache-Control: private, no-store` and
`Vary: Cookie`. Other applications' caches are preserved. This removes browser
cache copies; it does not delete server-side user data.

Run the source-backed behavioral controls:

```bash
pytest tests/config/test_service_worker_cache_policy.py
```

After deployment, verify the actual public `/sw.js` response matches the accepted
source. A correct Vite manifest alone does not prove the root-served worker was
updated: `config/pwa.py` prefers its collected static copy. Keep service workers
enabled when checking this behavior; a capture with workers blocked cannot prove
private-cache isolation.
