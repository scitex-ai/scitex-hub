CLI Reference
=============

SciTeX Cloud provides a command-line interface for managing projects,
syncing code, interacting with the Git hosting service, deploying apps,
and controlling the MCP server.

Install with:

.. code-block:: bash

   pip install scitex-cloud

Global Options
--------------

.. code-block:: bash

   scitex-cloud --help                    # Show help
   scitex-cloud --help-recursive          # Show all subcommands recursively
   scitex-cloud --version                 # Show version

Project Management
------------------

Create and manage SciTeX Cloud projects. ``project create`` triggers the
full flow: Gitea repository + Django project + server-side workspace.

.. code-block:: bash

   scitex-cloud project create my-research -d "Paper on X"
   scitex-cloud project list [--json]
   scitex-cloud project delete my-research --yes
   scitex-cloud project rename my-research new-name

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

   scitex-cloud push              # git push → Gitea
   scitex-cloud push origin main  # push specific branch
   scitex-cloud pull              # git pull ← Gitea
   scitex-cloud pull origin main  # pull specific branch

**File sync** (working tree, Dropbox-style):

.. code-block:: bash

   scitex-cloud sync-to                    # local → workspace
   scitex-cloud sync-to ywatanabe/my-proj  # explicit repo
   scitex-cloud sync-to --dry-run          # preview changes
   scitex-cloud sync-from                  # workspace → local
   scitex-cloud sync-from --dry-run        # preview changes

Conflict handling: when both sides changed the same file since the last
sync, both versions are kept — the synced version overwrites, and the
other side's version is saved as ``file.conflict-<timestamp>.ext``.

**Status**:

.. code-block:: bash

   scitex-cloud sync-status  # show divergence (alias: ss)

Git Hosting (Gitea)
-------------------

Lower-level Gitea operations. For most workflows, use ``push``/``pull``
and ``project create`` instead.

.. code-block:: bash

   scitex-cloud gitea list                # List repositories
   scitex-cloud gitea clone user/repo     # Clone a repository
   scitex-cloud gitea create my-repo      # Create Gitea repo only
   scitex-cloud gitea push                # Push changes
   scitex-cloud gitea pull                # Pull changes
   scitex-cloud gitea search "query"      # Search repos
   scitex-cloud gitea fork user/repo      # Fork a repo
   scitex-cloud gitea pr create           # Create a pull request
   scitex-cloud gitea pr list             # List pull requests
   scitex-cloud gitea issue create        # Create an issue
   scitex-cloud gitea issue list          # List issues
   scitex-cloud gitea login               # Authenticate
   scitex-cloud gitea logout              # Remove credentials
   scitex-cloud gitea status              # Repo status

App Management
--------------

.. code-block:: bash

   scitex-cloud app list                  # List installed apps
   scitex-cloud app info <name>           # App details
   scitex-cloud app current               # Active app
   scitex-cloud app init . --name my_app  # Scaffold new app
   scitex-cloud app check-deps <name>     # Check dependencies
   scitex-cloud app submit <path>         # Submit for review
   scitex-cloud app prefs get/set         # User preferences

Cloud SDK
---------

.. code-block:: bash

   # DataStore (JSON CRUD)
   scitex-cloud sdk data list|create|get|update|delete|search

   # FileVault (file storage)
   scitex-cloud sdk files list|upload|download|delete

   # JobQueue (background compute)
   scitex-cloud sdk jobs submit|status|list|cancel

Infrastructure
--------------

.. code-block:: bash

   scitex-cloud status                    # Deployment health
   scitex-cloud deploy                    # Deploy to production
   scitex-cloud setup [--env dev|prod]    # Setup environment
   scitex-cloud docker up|down|restart    # Container management
   scitex-cloud logs [service]            # View logs
   scitex-cloud ssh                       # SSH into cloud instance

MCP Server
----------

.. code-block:: bash

   scitex-cloud mcp start                 # Start the MCP server
   scitex-cloud mcp list-tools            # List available MCP tools
   scitex-cloud mcp doctor                # Diagnose MCP setup

For full MCP documentation, see :doc:`mcp`.

Utilities
---------

.. code-block:: bash

   scitex-cloud completion                # Set up shell completion
   scitex-cloud list-python-apis          # List all available Python APIs
   scitex-cloud skills list               # List available skills
   scitex-cloud skills get <name>         # Show a skill
