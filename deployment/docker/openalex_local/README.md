# `openalex_local/` — OpenAlex Local API container

Serves the local OpenAlex database (284M+ works, FTS5) as an HTTP API on
`:31292`, consumed by `scitex-scholar`'s `OpenAlexLocalEngine` and the standalone
GUI search. Mirrors the sibling `crossref_local/` service.

Unlike `crossref_local/` (which copies its own `server.py`), this image installs
the published `openalex-local[server]` package from PyPI and runs its built-in
`openalex-local relay` FastAPI server. The endpoint contract is
`GET /works?q=<query>&limit=<n>` plus `GET /health`.

## Read-only WAL — tested, and guarded

The DB mount is `:ro` (mandatory — the ~1.43 TB live DB must never be
container-writable). The host `openalex.db` is WAL-mode.

**Empirically tested** (Docker `:ro` mount = exactly this service's mount, run
cold with no other reader): a `:ro` reader opens the DB and returns **correct**
data — *because the `-wal` is checkpointed (0 bytes)*. No `immutable=1` needed.
Both plain `:ro` and `immutable=1` returned identical correct rows.

**But that is a property of the DB's state, not of the mount.** If a writer ever
leaves pending WAL frames when the container starts, a `:ro` reader can fail —
or silently read **stale** data. So `entrypoint.sh` enforces a **fail-loud
guard**: at startup it `stat`s `${OPENALEX_LOCAL_DB}-wal`, and if it is non-empty
it **refuses to start** with a clear message (run
`PRAGMA wal_checkpoint(TRUNCATE)` and restart). This turns an invisible
correctness bug into an obvious startup failure — a note that "the updater must
checkpoint" would only be a prompt someone has to remember; the guard makes it
true.

**Operational requirement:** the updater (the card's planned monthly cron) must
end with `PRAGMA wal_checkpoint(TRUNCATE)`, and this service should restart after
an update, so it never opens against a live `-wal`. The guard enforces it; this
note explains it.

## Other build notes

1. **DB mount source.** The host `openalex-local/data/openalex.db` is a symlink
   into `openalex-local.bak/data/`, which won't resolve inside the container.
   The compose service mounts the **real** directory (`openalex-local.bak/data`)
   — override via `OPENALEX_LOCAL_DB_DIR` in the env file rather than editing
   compose.
2. **Resource cap.** Capped at 1G / 1 cpu like crossref; the NAS is the
   constrained tier-1 box, so an uncapped process is a real risk.
3. **Gold-standard check still pending:** raw `sqlite3 :ro` reads are verified;
   the full relay (FastAPI + FTS5) inside the `:ro` container has not been hit
   yet — build the image and curl `/works` to confirm the FTS path before
   flipping the card.

## Verified so far

The `openalex-local relay` server is proven working against this exact DB (run
directly on the host from an isolated venv with fastapi 0.115.14 +
starlette 0.46.2): `/health` → `database_connected: true`,
`/works?q=hippocampus` → 235,003 hits in 141 ms.
