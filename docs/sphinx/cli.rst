CLI Reference
=============

SciTeX Cloud provides a command-line interface for managing your deployment,
interacting with the Git hosting service, and controlling the MCP server.

Install with:

.. code-block:: bash

   pip install scitex-cloud

Global Options
--------------

.. code-block:: bash

   scitex-cloud --help                    # Show help
   scitex-cloud --help-recursive          # Show all subcommands recursively
   scitex-cloud --version                 # Show version

Status
------

.. code-block:: bash

   scitex-cloud status                    # Show deployment status

Git Hosting (Gitea)
-------------------

Manage repositories hosted in the integrated Gitea instance.

.. code-block:: bash

   scitex-cloud gitea list                # List repositories
   scitex-cloud gitea clone user/repo     # Clone a repository
   scitex-cloud gitea push                # Push changes
   scitex-cloud gitea pr create           # Create a pull request
   scitex-cloud gitea issue create        # Create an issue

Docker Management
-----------------

.. code-block:: bash

   scitex-cloud docker status             # Show container status
   scitex-cloud docker logs               # View container logs

MCP Server
----------

.. code-block:: bash

   scitex-cloud mcp start                 # Start the MCP server
   scitex-cloud mcp list-tools            # List available MCP tools
   scitex-cloud mcp doctor                # Diagnose MCP setup
   scitex-cloud mcp installation          # Show client configuration instructions

For full MCP documentation, see :doc:`mcp`.

Utilities
---------

.. code-block:: bash

   scitex-cloud completion                # Set up shell completion
   scitex-cloud list-python-apis          # List all available Python APIs
