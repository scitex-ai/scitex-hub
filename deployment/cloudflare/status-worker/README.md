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
  word is the largest element on each row.
- **English by default; Japanese only via an explicit `?lang=ja`.** Deliberately
  NOT negotiated from `Accept-Language`: this page is edge-cached, and a response
  varying by request header is cached per-variant only if the CDN honours `Vary`,
  which is not reliable for HTML. Measured 2026-08-03 — with negotiation in place,
  a request carrying no `Accept-Language` was served `<html lang="ja">` from cache.
  A status page showing the wrong language to whoever misses the cache is worse
  than one needing a query parameter, so the URL is the single source of truth.
- **Declared service list, filled by checks.** A failing check renders its row as
  down; it never removes the row. A service that vanishes from the table would
  make the page read as "no problems", which is the one failure mode a status
  page must not have.
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
serve, so a valid JSON response proves the page is not coming from the NAS. It
also reports `upstream_available`, i.e. whether the hub's own status API answered.

`UPSTREAM_API` (`https://scitex.ai/api/status/`) does not exist yet. It is fetched
optionally and the page renders fully without it, reporting its absence rather
than hiding it — a stale internal reading presented as current is worse than none.
When the hub ships that endpoint, its flat key/value pairs appear under Internal
metrics with no change needed here.

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

## Why CrossRef is not listed

CrossRef Local has no public hostname **by design**. It runs in-process inside
django in `db` mode — the settings read the SQLite file at
`/data/crossref/crossref.db` directly — so there is no HTTP service to probe, and
`/server-status/` reporting it HEALTHY is correct.

`crossref.scitex.ai` existed anyway, pointing at `http://crossref:3333`. Two
things were wrong with it: no `crossref` container was ever declared by the live
compose (`deployment/docker/docker_prod/docker-compose.yml`; it is declared only
in the dormant `docker-compose.prod.yml`), and django expects port **31291**, not
3333. The hostname returned 502 from the day it was created. DNS record and
ingress rule were removed on 2026-08-03 rather than left as a permanently-red row.

OpenAlex is the opposite case: the container was running and healthy on 31292 with
no hostname at all, so `openalex.scitex.ai` was published.

## Related

- The stale `status.sctiex.ai` ingress rule (note the typo) was removed at the same
  time. It never had a DNS record, and the Worker route matches ahead of the tunnel
  regardless.
- Two prod compose files have drifted; the dormant one is a copy source that
  silently diverges. Card:
  `hub-two-prod-compose-files-drift-crossref-never-deployed-20260803`.
