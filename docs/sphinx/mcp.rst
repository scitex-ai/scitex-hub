MCP Server
==========

SciTeX Cloud ships with an `MCP (Model Context Protocol) <https://modelcontextprotocol.io/>`_
server that lets AI agents — Claude, Cursor, and others — interact with the platform
autonomously. AI agents can search literature, manage citations, query project files,
and submit jobs without manual intervention.

Available Tools
---------------

.. list-table::
   :header-rows: 1
   :widths: 15 10 75

   * - Category
     - Count
     - Description
   * - ``cloud``
     - 14
     - Git operations: clone, push, pull, create pull requests, create and list issues
   * - ``api``
     - 9
     - Scholar search, CrossRef lookup, BibTeX enrichment, citation management

Run ``scitex-cloud mcp list-tools`` for the full list of tools with descriptions.

Setup for Claude Desktop
------------------------

Add the following to your Claude Desktop configuration
(``~/.config/claude/claude_desktop_config.json``):

.. code-block:: json

   {
     "mcpServers": {
       "scitex-cloud": {
         "command": "scitex-cloud",
         "args": ["mcp", "start"]
       }
     }
   }

Setup for Claude Code
---------------------

Add the following to your project ``.mcp.json`` (or the global
``~/.claude/.mcp.json``):

.. code-block:: json

   {
     "mcpServers": {
       "scitex-cloud": {
         "command": "scitex-cloud",
         "args": ["mcp", "start"]
       }
     }
   }

Environment Source File (``ENV_SRC``)
--------------------------------------

To pass credentials and configuration to the MCP server without hardcoding
values in the JSON config, use the ``SCITEX_CLOUD_ENV_SRC`` environment variable.
Set it to the path of a shell ``.src`` file that exports the required variables:

.. code-block:: bash

   # ~/.scitex_cloud.src
   export SCITEX_CLOUD_API_BASE_URL=https://scitex.example.com
   export SCITEX_CLOUD_API_TOKEN=your-token-here

Then reference it in your MCP config:

.. code-block:: json

   {
     "mcpServers": {
       "scitex-cloud": {
         "command": "scitex-cloud",
         "args": ["mcp", "start"],
         "env": {
           "SCITEX_CLOUD_ENV_SRC": "/home/user/.scitex_cloud.src"
         }
       }
     }
   }

The server will source the ``.src`` file at startup and make all exported
variables available to the MCP tools.

CLI Commands
------------

.. code-block:: bash

   scitex-cloud mcp start             # Start the MCP server (stdio transport)
   scitex-cloud mcp doctor            # Diagnose setup and connectivity
   scitex-cloud mcp installation      # Print client configuration instructions
   scitex-cloud mcp list-tools        # List all available tools with descriptions
