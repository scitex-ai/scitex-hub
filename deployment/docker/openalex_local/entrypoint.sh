#!/usr/bin/env bash
# Fail-loud WAL guard for the read-only OpenAlex relay.
#
# The DB is mounted read-only (:ro). A read-only reader CANNOT apply pending
# WAL frames, so if the mounted DB has a non-empty -wal, serving it would give
# stale/inconsistent reads WITHOUT any error — the service would report healthy
# while quietly returning wrong data. Refuse to start instead: convert an
# invisible correctness bug into an obvious startup failure.
#
# The check is conservative: ANY non-zero -wal refuses, even if some frames are
# already applied-but-not-truncated. `PRAGMA wal_checkpoint(TRUNCATE)` zeroes it.
set -euo pipefail

DB="${OPENALEX_LOCAL_DB:-/data/openalex.db}"
WAL="${DB}-wal"

if [ ! -f "$DB" ]; then
    echo "FATAL: OpenAlex DB not found at $DB — is the read-only volume mounted?" >&2
    exit 1
fi

wal_bytes=0
if [ -f "$WAL" ]; then
    wal_bytes="$(stat -c %s "$WAL" 2>/dev/null || echo 0)"
fi

if [ "$wal_bytes" -gt 0 ]; then
    echo "FATAL: $WAL has $wal_bytes bytes of pending WAL frames." >&2
    echo "A read-only reader cannot safely apply them and would serve stale/inconsistent data." >&2
    echo "Fix: run 'PRAGMA wal_checkpoint(TRUNCATE);' against $DB with a writable connection, then restart this service." >&2
    exit 1
fi

echo "openalex-relay: WAL clean (${wal_bytes} bytes pending); starting relay on ${OPENALEX_LOCAL_HOST:-0.0.0.0}:${OPENALEX_LOCAL_PORT:-31292}"
exec openalex-local relay \
    --host "${OPENALEX_LOCAL_HOST:-0.0.0.0}" \
    --port "${OPENALEX_LOCAL_PORT:-31292}"
