CLI Reference
=============

SciTeX Hub provides a command-line interface for managing projects,
syncing code, interacting with the Git hosting service, deploying apps,
and controlling the MCP server.

Install with:

.. code-block:: bash

   pip install scitex-hub

Global Options
--------------

.. code-block:: bash

   scitex-hub --help                    # Show help
   scitex-hub --help-recursive          # Show all subcommands recursively
   scitex-hub --version                 # Show version

Project Management
------------------

Create and manage SciTeX Hub projects. ``project create`` triggers the
full flow: Gitea repository + Django project + server-side workspace.

.. code-block:: bash

   scitex-hub project create my-research -d "Paper on X"
   scitex-hub project list [--json]
   scitex-hub project delete my-research --yes
   scitex-hub project rename my-research new-name

Three-Way Sync
--------------

SciTeX manages three repositories per project:

- **Local** — your dev machine
- **Gitea** — source of truth (hosted Git)
- **Workspace** — server-side working directory (web UI edits here)

.. code-block:: text

              Gitea
             (source of truth)
            /              \
      push/pull          (server-side git)
      (git)
          /                  \
       Local ------------ Workspace
    (dev machine)  sync-to/from  (server-side)
                    (files)

**Git operations** (committed changes):

.. code-block:: bash

   scitex-hub push              # git push → Gitea
   scitex-hub push origin main  # push specific branch
   scitex-hub pull              # git pull ← Gitea
   scitex-hub pull origin main  # pull specific branch

**File sync** (working tree, Dropbox-style):

.. code-block:: bash

   scitex-hub sync-to                    # local → workspace
   scitex-hub sync-to ywatanabe/my-proj  # explicit repo
   scitex-hub sync-to --dry-run          # preview changes
   scitex-hub sync-from                  # workspace → local
   scitex-hub sync-from --dry-run        # preview changes

Conflict handling: when both sides changed the same file since the last
sync, both versions are kept — the synced version overwrites, and the
other side's version is saved as ``file.conflict-<timestamp>.ext``.

**Status**:

.. code-block:: bash

   scitex-hub sync-status  # show divergence (alias: ss)

Git Hosting (Gitea)
-------------------

Lower-level Gitea operations. For most workflows, use ``push``/``pull``
and ``project create`` instead.

.. code-block:: bash

   scitex-hub gitea list                # List repositories
   scitex-hub gitea clone user/repo     # Clone a repository
   scitex-hub gitea create my-repo      # Create Gitea repo only
   scitex-hub gitea push                # Push changes
   scitex-hub gitea pull                # Pull changes
   scitex-hub gitea search "query"      # Search repos
   scitex-hub gitea fork user/repo      # Fork a repo
   scitex-hub gitea pr create           # Create a pull request
   scitex-hub gitea pr list             # List pull requests
   scitex-hub gitea issue create        # Create an issue
   scitex-hub gitea issue list          # List issues
   scitex-hub gitea login               # Authenticate
   scitex-hub gitea logout              # Remove credentials
   scitex-hub gitea status              # Repo status

App Management
--------------

.. code-block:: bash

   scitex-hub app list                  # List installed apps
   scitex-hub app info <name>           # App details
   scitex-hub app current               # Active app
   scitex-hub app init . --name my_app  # Scaffold new app
   scitex-hub app validate-deps <name>  # Validate dependencies
   scitex-hub app submit <path>         # Submit for review
   scitex-hub app prefs get/update      # User preferences

Cloud SDK
---------

.. code-block:: bash

   # DataStore (JSON CRUD)
   scitex-hub sdk data list|create|get|update|delete|search

   # FileVault (file storage)
   scitex-hub sdk files list|upload|download|delete

   # JobQueue (background compute)
   scitex-hub sdk jobs submit|status|list|cancel

Infrastructure
--------------

.. code-block:: bash

   scitex-hub status                    # Deployment health
   scitex-hub deploy                    # Deploy to production
   scitex-hub setup [--env dev|prod]    # Setup environment
   scitex-hub docker up|down|restart    # Container management
   scitex-hub logs [service]            # View logs
   scitex-hub ssh                       # SSH into cloud instance

MCP Server
----------

.. code-block:: bash

   scitex-hub mcp start                 # Start the MCP server
   scitex-hub mcp list-tools            # List available MCP tools
   scitex-hub mcp doctor                # Diagnose MCP setup

For full MCP documentation, see :doc:`mcp`.

Utilities
---------

.. code-block:: bash

   scitex-hub completion                # Set up shell completion
   scitex-hub list-python-apis          # List all available Python APIs
   scitex-hub dev skills list           # List available skills
   scitex-hub dev skills get <name>     # Show a skill
