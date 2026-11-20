---
description: |
  [TOPIC] Clew Cloud store
  [DETAILS] Validate the installed GUI and authenticated project-store capability before deployment.
tags: [scitex-hub-clew-cloud-store]
---

# Clew Cloud integration

Clew owns its Django app, schemas, operations, templates and built JavaScript.
Hub supplies generic SDK project, storage, store and API-key identity capabilities.
The installed leaf preserves the `clew_app` label, registration table and initial
migration identity. Removing the duplicate Hub app does not migrate registry data.

The qualified GUI floor is Clew 0.36.2 with SDK 0.3.25 and Dev 0.66.0. Live Paper
0.5.2 supplies the installed manuscript, graph, review and owned-asset routes;
the host's existing resolver and login boundary apply to every resource. Those
resource reads preserve the tab's project without changing remembered navigation.

Configure `SCITEX_HUB_STORE_TENANT_SECRETS` in private deployment configuration.
It is a JSON object keyed by authenticated Django user PK. Each entry contains a
stable `tenant_id` UUID, secret `dsn`, and `projects` mapping Django project PKs to
explicit Clew project scopes. `SCITEX_HUB_STORE_OWNER_ROLE` names the separate
NOLOGIN owner (default `scitex_cloud_owner`). Django's internal setting includes
`SECRET` so its settings reporter redacts the complete credential mapping.
Credentials and owner identity never come from request parameters.

Provision a new tenant namespace explicitly through Dev 0.66.0 or later and the
owning leaf's schemas. Provisioning must use a separate administration connection;
request processes use only the restricted tenant LOGIN. Read requests do not
provision schemas, migrate historical records or select a fleet default DSN.
Historical data and persisted project scopes require a separately reviewed import.

Hub currently grants private stores only to the authenticated project's individual
owner. Collaborators and organization projects return unavailable until store
capabilities can restrict access at project level. Invalid or absent configuration
returns HTTP 503 rather than an empty success. API keys use Hub's existing active,
unexpired key authority and existing `api`/`*` permission. Keys limited to
`publish`, `mcp`, or an empty scope list do not authorize private project reads.
Public hash proofs remain anonymous and omit private
metadata. Registration badges do not assert rerun success or scientific validity.

Run `tests.security.test_clew_tenant_store` and `tests.security.test_clew_store_auth`
with `tests.security.clew_store_settings` and an explicit disposable local
`SCITEX_CLEW_TEST_ADMIN_DSN`. The fixture refuses managed/default database ports,
omits provisioner signals and external services, and creates synthetic users,
projects and tenant namespaces. Required checks include real HTTP/PG concurrency,
policy weakening, foreign project/path denial, API-key expiry, unchanged claims,
preserved registration identity, and Chromium plugin/standalone desktop/mobile.
Run the diagram rendering controls against the installed leaf's static assets too.

Before serving deployment, qualify the actual PostgreSQL version and pool,
service-role configuration, middleware and migration plan, installed artifact
origins, rollback image and persistent mounts. The request worker isolates cwd,
environment and Clew's cached store in a fresh process. It is not an operating
system filesystem sandbox; deployed workers still need project-bound filesystem
access. Local synthetic checks alone do not establish deployed Cloud acceptance.
