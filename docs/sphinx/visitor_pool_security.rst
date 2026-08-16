Visitor Pool Security
=====================

The visitor pool provides anonymous, sandboxed access to SciTeX Hub
for users who have not signed up. Four pre-allocated accounts
(``visitor-001`` to ``visitor-004``) are shared in rotation.

This page covers the leak-proof slot-recycling model introduced on
2026-07-07 (visitor-slot isolation audit), which replaced the 2026-03
decorator-based cleanup.

Security invariant
------------------

**Only verified-clean slots are redistributed; failed slots are
quarantined.** A slot is handed to a new visitor only after its
workspace has been wiped, *verified empty*, re-cloned from the
``scitex_minimal`` template, and the clone verified. Any failure in
that pipeline quarantines the slot — it is never allocated again until
``manage.py reconcile_visitor_slots`` re-cleans and re-verifies it.

How allocation is gated
-----------------------

The wipe happens at *release* time (asynchronously, via the
``reset_visitor_slot`` Celery task); allocation never cleans anything
inline. ``PoolAllocator._try_allocate_slot()`` refuses every slot that
is not:

* ``workspace_ready=True`` — wiped + verified since the last visitor,
* ``quarantined=False``,
* passing a synchronous template-marker filesystem check.

With Celery down, released slots simply stay out of circulation; the
pool shrinks and overflow visitors get the shared ``readonly-visitor``
account with ``session["visitor_readonly_reason"]`` set to
``"no_ready_slot"`` (or ``"pool_full"`` when all slots are busy).

The release pipeline
--------------------

Every path that frees a slot — explicit deallocation, the expiry
middleware, the idle sweep, and signup claim — goes through
``slot_lifecycle.release_slot()``:

.. code-block:: text

   release_slot()
       → is_active=False, workspace_ready=False   (out of circulation NOW)
       → enqueue reset_visitor_slot (Celery)
            → WorkspaceManager.reset_visitor_workspace()
                1. delete ALL the visitor's Project rows
                2. wipe the filesystem base dir + VERIFY empty
                   (guarded rmtree: chmod+retry on permission errors)
                3. hard-delete ALL the visitor's Gitea repos + VERIFY zero
                4. clear user-scoped rows (chat, LLM logs, app
                   installs / stars / reviews, dev installs)
                5. create the fresh Project row
                6. clone template + VERIFY the marker
            → success: workspace_ready=True (slot back in the pool)
            → ANY failure: slot QUARANTINED (loud CRITICAL log)

The fresh ``Project`` row is created only *after* the verified wipe —
previously it was created first, so an aborted wipe still produced an
"initialized" slot containing the previous visitor's files.

Gitea repositories
------------------

Visitor repos live at a stable path (``visitor-NNN/default-project``)
across slot rotations, so a repo that survives a best-effort deletion
would be adopted by the next visitor's project — leaking pushed
commits across users. The reset therefore lists and deletes *every*
repo the visitor owns and verifies none remain; additionally the
``create_gitea_repository`` signal refuses adoption of a pre-existing
repo for visitor-owned projects (it hard-deletes and recreates, or
quarantines the slot when deletion fails).

Boot fail-safe
--------------

``deployment/docker/*/entrypoint*.sh`` run at every service start:

.. code-block:: bash

   python manage.py create_visitor_pool       # ensure accounts exist
   python manage.py reconcile_visitor_slots   # quarantine + wipe+verify

``reconcile_visitor_slots`` treats *every* slot (allocated, mid-reset,
or unknown at shutdown) as unverified: all are quarantined, then each
runs the wipe+verify pipeline; only survivors return to circulation.
Until at least one slot verifies clean, visitors are served
``readonly-visitor`` only.

Known gap (tracked)
-------------------

Apptainer/container overlay state is **not** yet wiped by the reset —
scitex-container integration is a follow-up tracked on card
``hub-visitor-slot-isolation-audit``.

Operations
----------

.. code-block:: bash

   # Boot fail-safe / release quarantined slots after re-clean
   python manage.py reconcile_visitor_slots
   python manage.py reconcile_visitor_slots --quarantine-only
   python manage.py reconcile_visitor_slots --visitor 2

   # Hard reset all slots (same wipe+verify pipeline)
   python manage.py reset_visitor_pool

   # Release expired allocations only (reset is enqueued per slot)
   python manage.py reset_visitor_pool --free-expired

   # Pool health (free / total / quarantined / ready)
   make status

Further reading
---------------

* Module README: ``apps/infra/project_app/services/visitor_pool/README.md``
* Architecture overview: ``docs/VISITOR_POOL_ARCHITECTURE.md``
* Lifecycle source: ``apps/infra/project_app/services/visitor_pool/slot_lifecycle.py``
