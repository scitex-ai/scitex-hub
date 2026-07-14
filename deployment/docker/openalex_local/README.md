# `openalex_local/` — OpenAlex Local API container

Serves the local OpenAlex database (284M+ works, FTS5) as an HTTP API on
`:31292`, consumed by `scitex-scholar`'s `OpenAlexLocalEngine` and the standalone
GUI search. Mirrors the sibling `crossref_local/` service.

Unlike `crossref_local/` (which copies its own `server.py`), this image installs
the published `openalex-local[server]` package from PyPI and runs its built-in
`openalex-local relay` FastAPI server. The endpoint contract is
`GET /works?q=<query>&limit=<n>` plus `GET /health`.

## Build-test checklist (verify before relying on prod)

1. **Read-only WAL open.** The DB mount is `:ro` (mandatory — the ~1.43 TB live
   DB must never be container-writable). The host `openalex.db` is WAL-mode with
   live `-shm`/`-wal` sidecars. Opening a WAL database on a read-only mount can
   fail (`attempt to write a readonly database`) because WAL needs to touch
   `-shm`. If `/health` reports `database_connected: false` or the container
   crashes on first query, `openalex-local` needs to open with
   `?immutable=1`/`mode=ro`, or the deployment needs a checkpointed
   (WAL-collapsed) copy. This is the single most likely build issue.
2. **DB mount source.** The host `openalex-local/data/openalex.db` is a symlink
   into `openalex-local.bak/data/`, which won't resolve inside the container.
   The compose service therefore mounts the **real** directory
   (`openalex-local.bak/data`) — override via `OPENALEX_LOCAL_DB_DIR` in the env
   file rather than editing compose.
3. **Resource cap.** Capped at 1G / 1 cpu like crossref; the NAS is the
   constrained tier-1 box, so an uncapped process is a real risk.

## Verified so far

The `openalex-local relay` server itself is proven working against this exact DB
(run directly on the host from an isolated venv with fastapi 0.115.14 +
starlette 0.46.2): `/health` → `database_connected: true`,
`/works?q=hippocampus` → 235,003 hits in 141 ms. What is NOT yet build-tested is
this **containerized `:ro`** path — items 1–2 above.
