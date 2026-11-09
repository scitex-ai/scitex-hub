Three-Way Sync
==============

SciTeX Hub manages three copies of each project's repository:

.. list-table::
   :header-rows: 1

   * - Location
     - Purpose
     - Who edits
   * - **Local** (dev machine)
     - Development, testing
     - Developer (editor, CLI)
   * - **Gitea** (source of truth)
     - Hosted Git, PRs, issues
     - Nobody directly — receives pushes
   * - **Workspace** (server-side)
     - Web UI editing, running apps
     - Users via browser (Writer, FigRecipe, etc.)

Architecture
------------

.. code-block:: text

              Gitea
             (source of truth)
            /              \
      push/pull          (server-side git)
      (committed)
          /                  \
       Local ------------ Workspace
    (dev machine)  sync-to/from  (server-side)
                    (working files)

Two mechanisms:

- **push/pull** — standard ``git push``/``git pull`` for committed changes
- **sync-to/sync-from** — file-level sync for uncommitted working tree changes

Commands
--------

.. code-block:: bash

   # Git operations (committed changes)
   scitex-hub push [remote] [branch]
   scitex-hub pull [remote] [branch]

   # File sync (working tree, Dropbox-style)
   scitex-hub sync-to [repo] [--dry-run]
   scitex-hub sync-from [repo] [--dry-run]

   # Status
   scitex-hub sync-status [repo]   # alias: ss

Conflict Handling
-----------------

When both local and workspace have changed the same file since the last
sync, both versions are preserved:

.. list-table::
   :header-rows: 1

   * - Scenario
     - Action
   * - Only one side changed
     - Overwrite the stale copy
   * - Both sides changed
     - Sync the "winner" + save the other as ``.conflict-<timestamp>``
   * - Neither changed
     - Skip (already in sync)

Example:

.. code-block:: text

   data/config.yaml                              ← synced version
   data/config.conflict-20260324T120000.yaml     ← other side's version

The user must manually review and delete the ``.conflict-*`` file.

State Tracking
--------------

A ``.scitex-sync-state.json`` file stores SHA-256 checksums from the last
successful sync. This enables change detection on the next sync.

Typical Workflows
-----------------

**Developer edits locally, wants to see changes in workspace:**

.. code-block:: bash

   # Edit files locally...
   scitex-hub sync-to          # files appear in workspace immediately
   # Verify in browser...
   scitex-hub push             # commit and push to Gitea when ready

**User edits in web UI, developer wants the changes:**

.. code-block:: bash

   scitex-hub sync-from        # pull workspace files to local
   # If conflicts: resolve .conflict-* files manually
   scitex-hub push             # push resolved version to Gitea

**On the workspace server:**

``sync-to`` and ``sync-from`` detect that you're on the workspace and
show an error with a hint:

.. code-block:: text

   You're already on the workspace.
   Did you mean: scitex cloud push

Implementation
--------------

- ``src/scitex_hub/_cli/sync.py`` — CLI commands
- ``src/scitex_hub/_cli/_sync_engine.py`` — Conflict-aware sync engine
- Remote file listing via SSH + ``find`` + ``sha256sum``
- Per-file transfer via ``scp``
