Visitor Pool Security
=====================

The visitor pool provides anonymous, sandboxed access to SciTeX Cloud
for users who have not signed up. Four pre-allocated accounts
(``visitor-001`` to ``visitor-004``) are shared in rotation.

This page covers the security measures added on 2026-03-24 to prevent
chat history and project files from leaking between consecutive visitors
on the same slot.

Background: the fix
--------------------

Before the fix, a visitor who reused a recycled slot could see the
previous visitor's chat sessions in the UI. The root cause was that
``ChatSession`` records were not deleted on deallocation.

Three layers of protection were added.

Layer 1 — ``@reset_workspace_after``
-------------------------------------

Applied to ``PoolAllocator.deallocate_visitor()``.

After the slot is marked inactive the decorator calls
``WorkspaceManager.reset_visitor_workspace(user)`` immediately.
This is the primary cleanup path for normal session endings (expiry,
sign-up, or explicit logout).

.. code-block:: python

   # apps/infra/project_app/services/visitor_pool/decorators.py

   @reset_workspace_after
   def deallocate_visitor(cls, session): ...

Layer 2 — ``@ensure_clean_workspace``
--------------------------------------

Applied to ``PoolAllocator._try_allocate_slot()``.

Before handing a slot to a new visitor the decorator checks whether the
slot was previously used and, if so, calls the same workspace reset.
This catches edge cases where Layer 1 did not run: server crash, Docker
restart, idle-timeout expiry, or NAS reboot.

.. code-block:: python

   # apps/infra/project_app/services/visitor_pool/decorators.py

   @ensure_clean_workspace
   def _try_allocate_slot(cls, visitor_num, session, pool_size): ...

Layer 3 — ``reset_visitor_pool`` on container restart
------------------------------------------------------

``deployment/docker/docker_prod/entrypoint.sh`` runs the management
command in the background immediately after ``gunicorn`` binds:

.. code-block:: bash

   python manage.py reset_visitor_pool   # wipe all slots
   python manage.py create_visitor_pool  # ensure accounts exist

No state survives a container bounce.

What gets cleared
-----------------

``WorkspaceManager.reset_visitor_workspace(user)`` deletes and
re-creates the following for each visitor account:

* **Project** DB row — deleted then re-created from the
  ``scitex_minimal`` template via ``scitex.template.clone_template()``.
* **Project filesystem** — ``shutil.rmtree`` + fresh template clone.
* **ChatSession / ChatMessage** — deleted by ``_clear_visitor_data()``.
* **LLMUsageLog** — deleted by ``_clear_visitor_data()``.
* **VisitorAllocation** — marked ``is_active=False``.

Pool lifecycle diagram
-----------------------

.. code-block:: text

   Container start
       → reset_visitor_pool        # hard reset all 4 slots
       → create_visitor_pool       # ensure accounts/projects exist

   Visitor arrives
       → @ensure_clean_workspace   # layer 2 safety net
       → allocate_visitor()        # DB lock prevents race conditions

   Visitor uses platform (~1 hour)

   Session ends
       → deallocate_visitor()
       → @reset_workspace_after    # layer 1 immediate cleanup

Operations
----------

.. code-block:: bash

   # Reset all slots (run automatically on restart)
   python manage.py reset_visitor_pool

   # Free expired allocations only (no workspace wipe)
   python manage.py reset_visitor_pool --free-expired

   # Pool health (free / total)
   make status

Further reading
---------------

* Module README: ``apps/infra/project_app/services/visitor_pool/README.md``
* Architecture overview: ``docs/VISITOR_POOL_ARCHITECTURE.md``
* Decorator source: ``apps/infra/project_app/services/visitor_pool/decorators.py``
