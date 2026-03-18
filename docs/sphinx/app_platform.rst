App Platform
============

SciTeX Cloud ships a first-class **app platform** that lets third-party apps
integrate into the workspace alongside built-in tools.  The platform handles
registration, isolation, data persistence, job queuing, and developer
tooling so apps can focus on domain logic.

.. note::

   This page describes what the **platform** provides.
   For the developer-facing workflow — scaffolding, manifest schema,
   frontend integration — see the
   `App Developer Guide <https://github.com/ywatanabe1989/scitex-cloud/blob/main/docs/APP_DEVELOPER_GUIDE.md>`_
   and the ``scitex-app`` package documentation.

---

Workspace Layout
----------------

Every app renders as a **partial template** loaded by AJAX into the
right-most column of the three-column workspace::

   ┌─────────────┬──────────────────┬────────────────┐
   │  AI Pane    │  Worktree/Files  │  Module (app)  │
   └─────────────┴──────────────────┴────────────────┘

Apps never render a full HTML page.  The platform supplies the outer
chrome — tab bar, layout, resizers, file tree, file viewer, and AI chat.

---

Platform Services
-----------------

All services are accessible under ``/platform/api/``.
Session authentication is required; include ``X-CSRFToken`` on all writes.

DataStore
~~~~~~~~~

Structured, schema-typed key/value records scoped per app.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Endpoint
     - Description
   * - ``GET|POST /platform/api/data/<app>/<schema>/``
     - List records or create a new one
   * - ``GET|PUT|DELETE /platform/api/data/<app>/<schema>/<uuid>/``
     - Retrieve, update, or delete a record
   * - ``POST /platform/api/data/<app>/<schema>/search/``
     - Filter records by field values

FileVault
~~~~~~~~~

File storage scoped to each app.  Paths are relative to the app's
private storage root; apps cannot escape their own namespace.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Endpoint
     - Description
   * - ``GET /platform/api/files/<app>/``
     - List stored files
   * - ``GET /platform/api/files/<app>/<path>``
     - Read file content
   * - ``PUT /platform/api/files/<app>/<path>``
     - Write or overwrite a file
   * - ``DELETE /platform/api/files/<app>/<path>``
     - Delete a file

JobQueue
~~~~~~~~

Asynchronous background task execution.  Jobs report progress
incrementally so frontends can poll or stream status.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Endpoint
     - Description
   * - ``POST /platform/api/jobs/<app>/submit/``
     - Submit a job: ``{"task": "name", "args": {...}}``
   * - ``GET /platform/api/jobs/<app>/``
     - List all jobs for the app
   * - ``GET /platform/api/jobs/<app>/<uuid>/``
     - Poll status: ``{"status": "running|done|failed", "progress": 0–100}``
   * - ``POST /platform/api/jobs/<app>/<uuid>/cancel/``
     - Request cancellation

ScitexBridge
~~~~~~~~~~~~

Call any public function in the ``scitex`` Python package directly from
the browser without writing custom Django views.

.. code-block:: text

   POST /platform/api/scitex/<module>/<function>/

Example — load a CSV file:

.. code-block:: text

   POST /platform/api/scitex/io/load/
   {"path": "experiment/results.csv"}

Available modules mirror the ``scitex`` package namespaces: ``io``,
``plt``, ``stats``, and so on.

ExternalAPI
~~~~~~~~~~~

Proxy to external services registered by the platform administrator
(CrossRef, OpenAlex, custom institutional APIs, etc.).

.. code-block:: text

   GET|POST /platform/api/external/<api_name>/

RealtimeHub
~~~~~~~~~~~

WebSocket channels for live collaboration and streaming job output.
Apps subscribe to a channel keyed by ``app_slug`` and ``project_id``;
the platform handles routing and authentication.

.. code-block:: text

   ws://<host>/ws/app/<app_slug>/<project_id>/

FrontendKit
~~~~~~~~~~~

Pre-built TypeScript/React components provided by ``scitex-ui``:

- ``DataTableManager`` — spreadsheet with selection, editing, and CSV import
- ``WorkspacePanelResizer`` — drag-to-resize panels with ``data-h-resizer``
- ``AppSandbox`` — Shadow DOM wrapper enforcing CSS isolation
- ``PlatformContext`` — React context populated by ``GET /platform/api/context/``

Install via ``scitex-ui`` (npm) and import from ``@scitex/ui``.

---

App Registration
----------------

Built-in Apps
~~~~~~~~~~~~~

Built-in apps ship inside the ``scitex-cloud`` repository.  They are
listed in ``_BUILTIN_MANIFEST_PATHS`` in ``apps/infra/workspace_app/registry.py``
and are loaded unconditionally at startup.

External (pip-installed) Apps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Third-party apps declare themselves through a Python entry point:

.. code-block:: toml

   # pyproject.toml
   [project.entry-points."scitex_modules"]
   my_app = "my_app:get_module_config"

The platform calls ``discover_external_modules()`` at startup and
registers any apps found via this mechanism.  No code changes to
``scitex-cloud`` are required.

Context Bootstrap
~~~~~~~~~~~~~~~~~

Apps call ``GET /platform/api/context/`` on load to receive:

- Active project (owner, slug, permissions)
- Current user info
- List of enabled module names

---

Dev Install Workflow
--------------------

The dev install path lets an individual developer test their app in the
live workspace **without** going through the store review process.  Only
the installing user sees the tab.

.. code-block:: text

   POST /apps/store/api/dev/install/
   Content-Type: application/json
   {"owner": "alice", "repo": "my-app"}

Response:

.. code-block:: text

   {"success": true, "module_name": "dev__alice__my-app", "label": "My App"}

What the platform does:

1. Checks Gitea access for the authenticated user.
2. Calls ``validate_dev_repo()`` — the repository must contain a
   ``templates/`` directory and a valid ``manifest.json``.
3. Creates a ``DevInstallation`` record.
4. The tab appears on next page load under the name
   ``dev__<owner>__<repo>``.

Additional dev-install endpoints:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Endpoint
     - Action
   * - ``POST /apps/store/api/dev/<owner>/<repo>/uninstall/``
     - Soft-delete (hides tab)
   * - ``POST /apps/store/api/dev/<owner>/<repo>/reinstall/``
     - Re-enable after soft-delete
   * - ``GET  /apps/store/api/dev/url/?project_id=<repo>``
     - Resolve workspace URL for the installed app

---

App Submission and Review
-------------------------

When an app is ready for wider distribution it is submitted through the
store:

1. **Publish** the app to a Gitea repository accessible to the platform.
2. **Submit** via ``POST /apps/store/api/submit/`` — the platform reads
   ``manifest.json``, validates the privilege declarations, and creates a
   ``StoreSubmission`` record.
3. **Review** — a platform administrator audits the manifest, privilege
   list, and dependency declarations.
4. **Approve** — sets ``StoreSubmission.status = "approved"``.  The app
   becomes available to all users via the store UI.
5. **Install** — users install from the store; no per-user Gitea access
   check is required after approval.

The review focuses on:

- Declared ``privileges`` match actual API usage.
- No undeclared ``system`` or ``node`` dependencies.
- ``license`` field is present and OSI-compatible (or flagged for review).
- No calls to platform-internal endpoints outside ``/platform/api/``.

---

Separation of Concerns
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Layer
     - Responsibility
   * - ``scitex-cloud`` (this project)
     - Platform APIs, workspace layout, registry, isolation enforcement,
       store, review workflow, built-in apps
   * - ``scitex-app`` (pip package)
     - Developer CLI (``scitex-cloud app init``), manifest schema
       validation, scaffold templates, local dev server integration
   * - ``scitex-ui`` (npm package)
     - Shared TypeScript/React UI components, Shadow DOM isolation,
       resizer, data table, platform context hook
   * - Third-party app
     - Domain logic only — ``manifest.json``, a partial template,
       optionally a React/Vite frontend

Django code in ``scitex-cloud`` is intentionally a **thin wrapper**.
Business logic lives in the ``scitex`` Python package and is exposed to
apps via ScitexBridge, not re-implemented per-app.

---

Reference
---------

- `App Developer Guide <https://github.com/ywatanabe1989/scitex-cloud/blob/main/docs/APP_DEVELOPER_GUIDE.md>`_ — full manifest schema, scaffold CLI, and frontend integration
- `figrecipe <https://github.com/ywatanabe1989/figrecipe>`_ — reference implementation
- `scitex-app <https://pypi.org/project/scitex-app/>`_ — developer CLI package
- `scitex-ui <https://www.npmjs.com/package/@scitex/ui>`_ — shared UI components
