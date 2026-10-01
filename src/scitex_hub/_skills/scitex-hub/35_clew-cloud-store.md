---
description: Validate the authenticated Clew web adapter and private PostgreSQL boundary using synthetic projects before deployment.
---

# Clew Cloud integration

Start with the paper's project skill for research boundaries and use this
workflow for platform integration. Verify current source, running revisions,
and package origins; package version strings alone do not prove deployed code.

The GUI belongs to `scitex_clew._django` and uses `scitex_sdk` host capabilities. Hub supplies generic project/store authorization only; it does not import leaf schemas or verification operations.

The local leaf adapter delegates hashing and DAG verification to `scitex_clew` in
a fresh process for each request. It never changes a shared worker's cwd,
environment, or Clew DB cache. Request parameters cannot supply credentials.
The child checks the tenant login and all twenty physical Clew tables before
reading provenance. Missing configuration is HTTP 503, not an empty success.

Operator settings `SCITEX_STORE_TENANTS` map authenticated Django user PKs to
`tenant_id` (stable UUID), `dsn` (private secret), and `projects` (Django
project PK -> existing Clew scope). Keep credentials in private deployment
configuration. Register the persisted project scope explicitly; do not mint
or infer an owner when importing historical records. `SCITEX_STORE_OWNER`
names the separate NOLOGIN table owner. This requires the companion
`scitex_dev.store` tenant API, which is currently an unreleased local patch.

Owner access is implemented. Collaborator and organization stores remain
unavailable until project capabilities can limit access without borrowing a
full owner login. Public anonymized hash proofs remain public; they do not
expose private project rows. The read API refuses script reruns on GET.

Validate on a disposable local PostgreSQL cluster with
`tests.security.clew_store_settings`. This configuration loads real Django
models, authentication and routes, but omits deployment provisioner signals
and external integrations. The tests cover HTTP -> worker -> current Clew ->
real PostgreSQL, concurrent users, same IDs in different projects, forged
identity, policy weakening, preserved files/Claims, and public proof privacy.
Leaf frontend tests verify tab project identity, root/custom mounts and honest unavailable states. The HTTP suite also runs the leaf plugin and standalone GUI in Chromium on a disposable live test server.

Before deployment, additionally validate PostgreSQL 18, the actual PgBouncer
pool, service-role secret resolution, full deployed middleware/migrations,
and a worker whose filesystem exposes only the authorized project. Current
path checks reject traversal, symlink escapes and foreign recorded paths, but
the process adapter is not an OS filesystem sandbox and does not eliminate
concurrent symlink replacement. No successful local check certifies the live
55432 service. Validate Writer compilation and scientific Claims separately.
