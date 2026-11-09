CLI Reference
=============

The ``scitex-hub`` entry point is installed by ``pip install scitex-hub``.
When the SciTeX umbrella is also installed, ``scitex hub`` delegates to this
package. Inspect the help of the installed version before using an operation.

Discover commands
-----------------

.. code-block:: bash

   scitex-hub --version
   scitex-hub --help
   scitex-hub project --help
   scitex-hub workspace --help
   scitex-hub dev --help
   scitex-hub app --help
   scitex-hub mcp --help
   scitex-hub skills --help

These help commands do not create projects, deploy services or start an MCP
server. ``--help-recursive`` prints the registered command tree, including
compatibility routes; use each command's help for arguments and options.
The root ``--json`` option is honored by commands that explicitly support it;
it does not make every command a JSON interface.

Command groups
--------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Command
     - Scope
   * - ``project``
     - Project management
   * - ``push-project`` / ``pull-project``
     - Git synchronization with project repositories
   * - ``workspace``
     - Working-file upload, synchronization and status
   * - ``account`` / ``auth``
     - Account and authentication operations
   * - ``app`` / ``sdk``
     - Hosted app plugins and platform data/file/job operations
   * - ``context``
     - Web app context for agents
   * - ``gitea``
     - Git-hosting operations
   * - ``init`` / ``deploy`` / ``docker``
     - Environment setup and deployment operations
   * - ``status`` / ``logs``
     - Deployment diagnostics
   * - ``mcp`` / ``skills`` / ``docs``
     - Agent interfaces and documentation discovery
   * - ``dev`` / ``dev-preview``
     - Development and preview operations
   * - ``completion``
     - Shell completion

Canonical synchronization routes are ``push-project``, ``pull-project``,
``workspace push``, ``workspace pull`` and ``workspace status``. Older
spellings such as ``sync-to`` are compatibility routes, not the preferred
examples. Inspect the installed help rather than inferring that a scheduled
removal has happened.

Deployment commands can alter services and persistent data. Follow the
source-owned deployment runbook and its dependency, image, backup and rollback
checks; command registration or help output does not qualify a deployment.
Authentication and host configuration remain necessary for remote operations.

Source and validation
---------------------

Command registration is owned by ``scitex_hub._cli.main`` and its imported
command groups. ``tests/config/test_shipped_documentation.py`` checks the
selected help routes against the actual Click parser without invoking their
operation callbacks. It also checks the shipped documentation's version
binding. These checks do not execute synchronization, account, deployment or
remote app operations.

See :doc:`mcp` and :doc:`api/index` for the other package interfaces.
