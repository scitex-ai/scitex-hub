<!-- ---
!-- Timestamp: 2026-02-13
!-- File: /home/ywatanabe/proj/scitex-cloud/README.md
!-- --- -->

<p align="center">
  <a href="https://scitex.ai">
    <img src="static/shared/images/scitex-logo-blue-cropped.png" alt="SciTeX Cloud" width="400">
  </a>
</p>

<p align="center">
  <a href="https://pypi.org/project/scitex-cloud/"><img src="https://badge.fury.io/py/scitex-cloud.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/scitex-cloud/"><img src="https://img.shields.io/pypi/pyversions/scitex-cloud.svg" alt="Python Versions"></a>
  <a href="https://github.com/ywatanabe1989/scitex-cloud/blob/main/LICENSE"><img src="https://img.shields.io/github/license/ywatanabe1989/scitex-cloud" alt="License"></a>
</p>

<p align="center">
  <a href="https://scitex.ai">scitex.ai</a> · <code>pip install scitex-cloud</code>
</p>

---

**Open-source scientific research platform — web interface for the [scitex](https://github.com/ywatanabe1989/scitex-python) ecosystem.**

Provides Scholar, Writer, Vis, Console, and Hub modules as a Django web application with Docker deployment, plus a pip-installable CLI and MCP server for AI integration.

> **Status**: Alpha (data may be lost)

## Installation

```bash
pip install scitex-cloud              # CLI only
pip install scitex-cloud[mcp]         # CLI + MCP server
pip install scitex-cloud[all]         # Everything
```

## Three Interfaces

<details>
<summary><strong>Python API</strong></summary>

<br>

```python
import scitex_cloud

# Version and health
scitex_cloud.__version__        # "0.8.0-alpha"
scitex_cloud.get_version()      # Version string
scitex_cloud.health_check()     # Service health status
```

</details>

<details>
<summary><strong>CLI Commands</strong></summary>

<br>

```bash
scitex-cloud --help                    # Help
scitex-cloud --help-recursive          # All commands recursively
scitex-cloud --version                 # Version

# Git hosting (Gitea)
scitex-cloud gitea list                # List repositories
scitex-cloud gitea clone user/repo     # Clone repository
scitex-cloud gitea push                # Push changes
scitex-cloud gitea pr create           # Create pull request
scitex-cloud gitea issue create        # Create issue

# Docker management
scitex-cloud docker status             # Container status
scitex-cloud docker logs               # View logs

# MCP server
scitex-cloud mcp start                 # Start MCP server
scitex-cloud mcp list-tools            # List available tools
scitex-cloud mcp doctor                # Diagnose setup
scitex-cloud mcp installation          # Client config instructions

# Utilities
scitex-cloud status                    # Deployment status
scitex-cloud completion                # Shell completion setup
scitex-cloud list-python-apis          # List all Python APIs
```

</details>

<details>
<summary><strong>MCP Tools — 23 tools for AI Agents</strong></summary>

<br>

| Category | Tools | Description |
|----------|-------|-------------|
| cloud | 14 | Git operations (clone, push, pull, PR, issues) |
| api | 9 | Scholar search, CrossRef, BibTeX enrichment |

**Claude Desktop** (`~/.config/claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "scitex-cloud": {
      "command": "scitex-cloud",
      "args": ["mcp", "start"]
    }
  }
}
```

</details>

## Web Platform

<details>
<summary><strong>Quick Start (Docker)</strong></summary>

<br>

```bash
git clone https://github.com/ywatanabe1989/scitex-cloud.git
cd scitex-cloud
make start                    # Development environment

# Access at: http://localhost:8000
# Gitea: http://localhost:3000
# Test user: test-user / Password123!
```

</details>

<details>
<summary><strong>Deployment</strong></summary>

<br>

```bash
make start                    # Development (default)
make ENV=prod start           # Production
make ENV=prod status          # Health check
make ENV=prod db-backup       # Backup database
make help                     # All available commands
```

</details>

<details>
<summary><strong>Configuration</strong></summary>

<br>

`.env` files in `deployment/docker/envs/` (gitignored):

```bash
.env.dev        # Development
.env.prod       # Production
.env.staging    # Staging
.env.example    # Template (tracked)
```

Key variables:
```bash
SCITEX_CLOUD_DJANGO_SECRET_KEY=your-secret-key
SCITEX_CLOUD_POSTGRES_PASSWORD=strong-password
SCITEX_CLOUD_GITEA_TOKEN=your-token
```

</details>

<details>
<summary><strong>Project Structure</strong></summary>

<br>

```
scitex-cloud/
├── apps/                    # Django applications
│   ├── scholar_app/        # Literature discovery
│   ├── writer_app/         # Scientific writing
│   ├── console_app/        # Terminal & code execution
│   ├── vis_app/            # Data visualization
│   ├── hub_app/            # Project hub & file browser
│   ├── project_app/        # Project management
│   ├── clew_app/           # Verification pipeline
│   └── public_app/         # Landing page & tools
│
├── deployment/docker/
│   ├── docker_dev/         # Development compose
│   ├── docker_prod/        # Production compose
│   └── envs/               # .env files (gitignored)
│
├── config/                  # Django settings
├── static/                  # Shared frontend assets
├── src/scitex_cloud/        # pip package (CLI + MCP)
├── tests/                   # Test suite
└── Makefile                 # Thin dispatcher
```

</details>

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md).

---

<p align="center">
  <a href="https://scitex.ai" target="_blank"><img src="static/shared/images/scitex-icon-navy-inverted.png" alt="SciTeX" width="40"/></a>
  <br>
  AGPL-3.0
</p>

<!-- EOF -->
