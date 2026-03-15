Quick Start
===========

Get SciTeX Cloud running in three commands.

Deployment
----------

.. code-block:: bash

   git clone https://github.com/ywatanabe1989/scitex-cloud.git
   cd scitex-cloud
   make start

This pulls Docker images, builds containers, runs migrations, and creates a test user.

Access at:

- **Django**: http://localhost:8000
- **Gitea**: http://localhost:3000
- **Test user**: ``test-user`` / ``Password123!``

CLI-Only Install
----------------

Use the CLI and MCP server without Docker:

.. code-block:: bash

   pip install scitex-cloud           # CLI only
   pip install scitex-cloud[mcp]      # CLI + MCP server
   pip install scitex-cloud[all]      # Everything

Verify:

.. code-block:: bash

   scitex-cloud --version
   scitex-cloud --help

Common Operations
-----------------

.. code-block:: bash

   make start                    # Start development environment
   make stop                     # Stop all services
   make restart                  # Restart services
   make status                   # Health check
   make logs                     # View logs
   make help                     # All available commands

For full CLI reference, see :doc:`cli`.
For MCP server setup, see :doc:`mcp`.
