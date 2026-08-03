# status.scitex.ai — Cloudflare Worker

Public status page for SciTeX, served at <https://status.scitex.ai/>.

## Why this does not live on the NAS

A status page hosted on the machine it reports on is unreachable exactly when it
is needed. `status.scitex.ai` therefore runs as a Cloudflare Worker at the edge:
it keeps answering when every SciTeX origin is down, which is the entire point of
having it.

This was an explicit operator decision (2026-08-03): *"scitex.ai が止まると全部
止まるというのは良くない"*, and *"できるだけシンプルに、安定性が一番です"*.

The same reasoning is why `https://scitex.ai/server-status/` is **not** a
substitute — that page is served by the Django app on the NAS, so it dies with
the thing it monitors.

## Design constraints, and why each one is here

- **No KV, no cron, no build step, no dependencies.** Probes run per request and
  are edge-cached for 60 s. One moving part is the maximum this is allowed to
  have; every added component is another thing that can fail silently and make
  the status page lie.
- **A table, not cards.** The operator asked for legibility over looks. The state
  word (`稼働中` / `停止`) is the largest element on each row.
- **Always HTTP 200**, including when services are down. A monitoring page that
  itself returns an error status is indistinguishable from a broken page.
- **A redirect is healthy.** `scitex.ai/` 302s to `/landing/`; only 5xx and
  transport failures count as down.

## Layout

| Path | Purpose |
|------|---------|
| `worker.js` | The entire Worker. Module syntax, `export default { fetch }`. |
| `deploy.sh` | Uploads `worker.js` and ensures the route exists. Idempotent. |

## Endpoints

| Path | Returns |
|------|---------|
| `/` | The HTML status table. |
| `/api/status` | JSON: `{ok, checked_at, services[]}`, CORS-open. |

`/api/status` doubles as the independence check: it is a path only the Worker can
serve, so a valid JSON response proves the page is not coming from the NAS.

## Deploying

```bash
./deploy.sh          # dry run: shows what would be uploaded
./deploy.sh --apply  # upload + ensure route
```

Credentials come from the operator's shell secret files; `deploy.sh` sources them
and never echoes their values. See the script header for the exact paths.

## Gotcha that cost a deploy

Cloudflare resolves module names from the multipart part's **filename**, not the
form field name. `curl -F "worker.js=@some-other-name.js"` uploads a part whose
filename is `some-other-name.js` and fails with
`Uncaught Error: No such module: worker.js`. Pass `;filename=worker.js`
explicitly — `deploy.sh` does.

## Adding a service

Append to `TARGETS` in `worker.js` and redeploy. Keep the list short: this page
answers "is SciTeX up", not "what is every component doing".

## Related

- Tunnel ingress carries a stale `status.sctiex.ai` rule (note the typo) pointing
  at `http://nginx:80`. The Worker route matches ahead of the tunnel so it is
  inert, but it should be deleted.
