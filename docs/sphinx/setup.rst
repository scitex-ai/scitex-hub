Setup Guide
===========

Deploy SciTeX Cloud anywhere: local development, home server, or cloud.

What You Get
------------

SciTeX Cloud is a self-hostable research platform. One ``make start`` gives you:

- **Scholar** — Literature search across CrossRef, PubMed, arXiv, and OpenAlex. BibTeX management and citation tracking.
- **Writer** — LaTeX manuscript editor with BibTeX integration, figure/table management, and IMRAD templates.
- **Vis** — Data visualization and interactive figure editing.
- **Console** — Web-based terminal for running Python and Bash in isolated containers.
- **Hub** — Project file browser with GitHub-style ``/username/project/`` URLs.
- **Research Tools** — Statistics, PDF manipulation, citation scraping, and more.
- **MCP Server** — 23 tools for AI agents (Claude, Cursor, etc.) to search literature, manage citations, generate figures, and run statistics.

Optional local databases for offline paper search:

- **CrossRef Local** — 167M+ papers in a local SQLite database with citation graph analysis.
- **OpenAlex Local** — 284M+ scholarly works with full-text search, abstracts, and impact factors.

Prerequisites
-------------

- **OS**: Linux, macOS, or Windows (WSL2)
- **Docker**: 24.0+ with Docker Compose v2
- **Python**: 3.11+ (for CLI-only install)
- **Git**: 2.30+
- **RAM**: 4 GB minimum (8 GB recommended)
- **Disk**: 10 GB free

Quick Start (Development)
-------------------------

Three commands to get running:

.. code-block:: bash

   git clone https://github.com/ywatanabe1989/scitex-cloud.git
   cd scitex-cloud
   make start

This pulls Docker images, builds containers, runs migrations, and creates a test user.

Access at:

- **Django**: http://localhost:8000
- **Gitea**: http://localhost:3000
- **Test user**: ``test-user`` / ``Password123!``

Step-by-Step Development Setup
------------------------------

1. **Clone the repository**

.. code-block:: bash

   git clone https://github.com/ywatanabe1989/scitex-cloud.git
   cd scitex-cloud

2. **Create environment file**

.. code-block:: bash

   cp deployment/docker/envs/.env.example deployment/docker/envs/.env.dev

3. **Configure key variables**

Edit ``.env.dev`` and set at minimum:

.. code-block:: bash

   # Generate a secret key
   SCITEX_CLOUD_DJANGO_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')

   # Database password (any strong password)
   SCITEX_CLOUD_POSTGRES_PASSWORD=your-dev-password

4. **Start services**

.. code-block:: bash

   make start              # Development environment (default)
   make status             # Verify all services are running

5. **Verify**

.. code-block:: bash

   # Open in browser
   open http://localhost:8000

   # Or check health endpoint
   curl http://localhost:8000/healthz/

Production Setup
----------------

For deploying on a home server, NAS, or VPS.

1. **Same prerequisites** plus:

   - A domain name (e.g., ``scitex.example.com``)
   - Cloudflare account (optional, for tunnel/CDN)

2. **Create production environment**

.. code-block:: bash

   cp deployment/docker/envs/.env.example deployment/docker/envs/.env.prod

3. **Configure production variables**

.. code-block:: bash

   # Required changes for production
   SCITEX_CLOUD_DJANGO_SETTINGS_MODULE=config.settings.settings_prod
   DEBUG=False
   SCITEX_CLOUD_DOMAIN=scitex.example.com
   SCITEX_CLOUD_SITE_URL=https://scitex.example.com
   SCITEX_CLOUD_ALLOWED_HOSTS=scitex.example.com

   # Strong passwords
   SCITEX_CLOUD_DJANGO_SECRET_KEY=<generate-new-secret>
   SCITEX_CLOUD_POSTGRES_PASSWORD=<strong-db-password>

   # SSL
   SCITEX_CLOUD_ENABLE_SSL_REDIRECT=true
   SCITEX_CLOUD_FORCE_HTTPS_COOKIES=true

4. **Start production services**

.. code-block:: bash

   make ENV=prod start
   make ENV=prod status

5. **Expose to internet** (optional)

For Cloudflare Tunnel setup, see ``deployment/docs/09_CLOUDFLARE_TUNNEL.md``.

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

MCP server for AI agents:

.. code-block:: bash

   scitex-cloud mcp start             # Start MCP server
   scitex-cloud mcp doctor            # Diagnose setup
   scitex-cloud mcp installation      # Client config instructions

Configuration Reference
-----------------------

All environment variables use the ``SCITEX_CLOUD_`` prefix.

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Variable
     - Required
     - Description
   * - ``SCITEX_CLOUD_DJANGO_SECRET_KEY``
     - Yes
     - Django secret key (generate unique per deployment)
   * - ``SCITEX_CLOUD_POSTGRES_PASSWORD``
     - Yes
     - PostgreSQL database password
   * - ``SCITEX_CLOUD_DOMAIN``
     - Prod
     - Your domain (e.g., ``scitex.example.com``)
   * - ``SCITEX_CLOUD_SITE_URL``
     - Prod
     - Full URL (e.g., ``https://scitex.example.com``)
   * - ``SCITEX_CLOUD_ALLOWED_HOSTS``
     - Prod
     - Comma-separated allowed hostnames
   * - ``SCITEX_CLOUD_ENABLE_SSL_REDIRECT``
     - Prod
     - Set ``true`` for HTTPS
   * - ``SCITEX_CLOUD_GITEA_TOKEN_DEV``
     - No
     - Gitea API token for Git integration

Full template: ``deployment/docker/envs/.env.example`` (268 variables).

Common Commands
---------------

.. code-block:: bash

   # Lifecycle
   make start                    # Start development
   make stop                     # Stop all services
   make restart                  # Restart services
   make status                   # Health check

   # Database
   make db-migrate               # Run migrations
   make db-shell                 # PostgreSQL shell
   make db-backup                # Backup database

   # Logs and debugging
   make logs                     # View all logs
   make shell                    # Django shell

   # Production
   make ENV=prod start           # Start production
   make ENV=prod status          # Production health check
   make ENV=prod db-backup       # Backup production database

   # Help
   make help                     # Available commands

Architecture
------------

SciTeX Cloud runs as a set of Docker containers:

::

   +------------------+     +------------------+
   |   Django (8000)  |---->|  PostgreSQL (DB)  |
   +------------------+     +------------------+
          |
          +---->  Redis (cache/broker)
          |
          +---->  Gitea (3000) - Git hosting
          |
          +---->  Celery (workers) - Async tasks
          |
          +---->  Umami (3300) - Privacy analytics

Optional local databases (mounted as read-only volumes):

::

   +---------------------------+     +---------------------------+
   |  CrossRef Local (31291)   |     |  OpenAlex Local (8083)    |
   |  167M+ papers, FTS5       |     |  284M+ works, abstracts   |
   +---------------------------+     +---------------------------+

Troubleshooting
---------------

**Port already in use**

.. code-block:: bash

   # Check what's using port 8000
   lsof -i :8000
   # Or change the port in .env
   SCITEX_CLOUD_HTTP_PORT_DEV=8080

**Docker permission denied**

.. code-block:: bash

   # Add user to docker group
   sudo usermod -aG docker $USER
   # Log out and back in

**Database migration errors**

.. code-block:: bash

   make db-migrate               # Re-run migrations
   make db-reset                 # Reset database (destroys data)

**Container won't start**

.. code-block:: bash

   make logs                     # Check error messages
   make rebuild                  # Rebuild from scratch

**WSL2-specific issues**

.. code-block:: bash

   # Ensure Docker Desktop WSL integration is enabled
   # Settings > Resources > WSL Integration > Enable for your distro
