# ADR-0004: PostgreSQL is the only database engine

- **Status:** Accepted
- **Date:** 2026-08-29
- **Driver:** Standing operator directive to eradicate SQLite from the entire
  SciTeX fleet.

## Context

scitex-hub carried SQLite in three unrelated places, and each one cost
something different.

**1. Django's own `DATABASES`.** `settings_shared.py` hardcoded a SQLite
engine, and both `settings_dev.py` and `settings_prod.py` carried an env-gated
branch (`..._USE_SQLITE_DEV` / `..._USE_SQLITE_PROD`) that swapped Django onto
a single local file. The prod one was reachable through the ADR-0001 legacy
`SCITEX_CLOUD_*` alias as well, so a stale environment file could silently
demote production onto a single-file store.

**2. CI ran the entire suite on SQLite.** The three required status checks
(`pytest-matrix-on-ubuntu-py3.11/3.12/3.13`), the security-regression gate and
the release-tag gate all set the SQLite flag because no job declared a
database service. This is the expensive one: every merge-blocking gate was
measuring behaviour against a *different engine than production runs*. Two
migrations in this repo (`scholar_app/0018`, `writer_app/0007`) carry
backend-conditional code and long comments that exist purely because the test
matrix and production disagreed. The tenant-isolation security gate was
proving isolation on the wrong engine.

**3. A hand-rolled per-project database.**
`writer_app/utils/project_db/` (7 files, 851 lines) opened its own
connections, declared its own schema, ran its own ad-hoc migrations, and wrote
one file per project at `{project_root}/scitex/metadata.db`. It is exactly the
per-package database layer the fleet ruling removed, and it had already
accumulated the bugs that predicts — notably a duplicate-detection query
selecting a column its own schema never declared, failing on every call and
being swallowed by a bare `except Exception`.

## Decision

**PostgreSQL is the only supported engine. There is no fallback branch, by
design.** An environment that cannot reach Postgres must fail at connect time
rather than quietly succeed against a different database.

1. `DATABASES` is PostgreSQL in every settings module. The two env escape
   hatches are deleted, not deprecated.
2. Every CI job that runs Django declares a `postgres:16` service container
   and points Django at it — the same image and credentials `e2e-mobile.yml`
   and `screenshots.yml` already used.
3. The flag that gated SQLite *also* forced Celery into eager mode with an
   in-memory broker, because it was really answering "is this a test run".
   That half is kept under an honest name, `SCITEX_HUB_TEST_MODE`. It no
   longer selects a database; CI supplies both independently.
4. `project_db/` is deleted. Its rows move to ordinary Django models
   (`ProjectFigure`, `ProjectTable`, `ProjectFigureLatexReference`).

### Why Django's ORM and not `scitex_dev.store`

The fleet primitive is the right answer when a package needs a store of its
own. This app already has one: a Django `DATABASES["default"]` on the same
PostgreSQL cluster, with migrations, pooling and transactions already wired
up. Every consumer of this data is Django code already inside an ORM context,
and every row is scoped to a `Project` row only the ORM can resolve. Adding
`scitex_dev.store` — with its own DSN, schema and migration path — would have
*added* a second store beside Django's own rather than removing one. The
ruling's target was the hand-rolled layer, and deleting it is what removes it.

Consequently this change adds **no new dependency**, and in particular does not
raise the `scitex-dev` floor.

## Consequences

- The migration is code-only. The per-project index is rebuildable from the
  filesystem by `writer_app.tasks.indexer`, so no data migration was needed and
  no existing database file was read, moved or deleted.
- Table duplicate-detection works for the first time (`ProjectTable.file_size`
  is a new column; its absence was the latent bug above).
- Figure/table search is case-insensitive substring matching instead of the old
  engine's bundled full-text extension. Relevance ranking is gone; substring
  matching returns strictly more rows for the partial-filename queries this
  endpoint actually receives.
- Uniqueness is now `(project, file_path)`. The old file-per-project layout
  made `file_path` alone unique, which would have let one project's re-index
  clobber another's row in a shared table.
- The dev **preview** compose stack gains a small dedicated `postgres:16-alpine`
  container. It previously ran SQLite specifically to avoid a second DB server;
  previewing against a different engine than production was the wrong trade.
- CI is slower: every session now builds a real PostgreSQL test database
  through the full migration set. There is no `--reuse-db` or `--no-migrations`
  in `addopts`; if the matrix gets too slow, that is the knob.

## Scope note: what this ADR does NOT claim

Removing the string from this repository is not the same as scitex-hub having
no dependency on SQLite-backed data. It still reaches, at runtime, several
stores owned by *other* projects that remain file-backed:

- `deployment/docker/openalex_local/` serves a ~284M-work mirror that the
  external `openalex-local` package reads from a mounted file.
- `settings_integrations.py` points at `/data/crossref/crossref.db`, read
  in-process by `scitex_scholar`.
- The third-party `impact-factor` package keeps its own embedded store — which
  is why `scholar_app/views/search/citations.py` needs a `threading.local()`.
- `scitex.clew` keeps its own store per project.

Those are separate projects' data and are out of scope here. They are named so
that a future reader does not mistake "the string is gone from scitex-hub" for
"scitex-hub touches no file-backed database".

## References

- ADR-0001 — the `SCITEX_CLOUD_*` legacy alias that made the prod SQLite gate
  reachable from a stale environment file.
