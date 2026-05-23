Quick Start
===========

Get SciTeX Cloud running in three commands.

Deployment
----------

.. code-block:: bash

   git clone https://github.com/ywatanabe1989/scitex-hub.git
   cd scitex-hub
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

   pip install scitex-hub           # CLI only
   pip install scitex-hub[mcp]      # CLI + MCP server
   pip install scitex-hub[all]      # Everything

Verify:

.. code-block:: bash

   scitex-hub --version
   scitex-hub --help

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
