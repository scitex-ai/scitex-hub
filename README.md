<!-- ---
!-- Timestamp: 2025-11-01 16:36:27
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/README.md
!-- --- -->

# SciTeX Cloud

[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/django-5.1-green.svg)](https://djangoproject.com)
[![SLURM](https://img.shields.io/badge/SLURM-24.05-orange.svg)](https://slurm.schedmd.com)
[![Celery](https://img.shields.io/badge/celery-5.4-success.svg)](https://docs.celeryq.dev)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Open-source scientific research platform for researchers and academics.

🌐 **Live**: https://scitex.ai
📦 **Package**: `pip install scitex-cloud`
🔧 **Status**: Alpha (data may be lost)

---

## CLI Package

The `scitex-cloud` package provides CLI tools and MCP server for AI integration.

```bash
# Install
pip install scitex-cloud[mcp]

# CLI Commands
scitex-cloud -h                    # Help
scitex-cloud gitea list            # List repositories
scitex-cloud gitea clone user/repo # Clone repository
scitex-cloud mcp start             # Start MCP server
scitex-cloud mcp list-tools        # List 23 available tools
```

<details>
<summary><b>Python API</b></summary>

```python
import scitex_cloud

# Cloud client for API access
client = scitex_cloud.CloudClient()
client.scholar_search("neural networks")
client.enrich_bibtex("@article{...}")
```

</details>

<details>
<summary><b>MCP Server (AI Integration)</b></summary>

```bash
# Start MCP server (for Claude Desktop/Code)
scitex-cloud mcp start              # stdio (local)
scitex-cloud mcp start -t http      # HTTP (remote)

# Claude Desktop config (~/.config/claude/claude_desktop_config.json):
{
  "mcpServers": {
    "scitex-cloud": {
      "command": "scitex-cloud",
      "args": ["mcp", "start"],
      "env": {"SCITEX_CLOUD_API_KEY": "your-key"}
    }
  }
}
```

**23 MCP Tools Available:**
- `cloud_*` (14): clone, create, list, push, pull, pr, issue, etc.
- `api_*` (9): scholar_search, crossref_search, enrich_bibtex, etc.

</details>

---

## Web Platform Quick Start

<details open>
<summary><b>Docker (Recommended)</b></summary>

```bash
# Clone and navigate
git clone git@github.com:ywatanabe1989/scitex-cloud.git
cd scitex-cloud

# Start development environment
make start

# Access at: http://localhost:8000
# Gitea: http://localhost:3000
```

**Test User:**
- Username: `test-user`
- Password: `Password123!`

</details>

<details>
<summary><b>Local (Without Docker)</b></summary>

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install scitex[web,scholar,writer,dev]

# Configure
cp deployment/dotenvs/dotenv.example .env
# Edit .env with your settings

# Run
python manage.py migrate
python manage.py runserver

# Access at: http://127.0.0.1:8000
```

</details>

---

## Deployment Options

<details open>
<summary><b>Development (Default)</b></summary>

```bash
make start                    # Full setup
make restart                  # Quick restart
make logs                     # View logs
make migrate                  # Run migrations
make shell                    # Django shell
```

</details>

<details>
<summary><b>Production/Home Server</b></summary>

```bash
make ENV=prod start            # Start on production
make ENV=prod status           # Check status
make ENV=prod db-backup        # Backup
```

</details>

**All commands:** `make help` or `make ENV=prod help`

---

## Environment Variables

<details>
<summary><b>Configuration Files</b></summary>

Place `.env` files in `SECRET/` directory (gitignored):
- `SECRET/.env.dev` - Development
- `SECRET/.env.prod` - Production/Home Server

**Required variables:**
```bash
# Django
DJANGO_SCITEX_CLOUD_DJANGO_SECRET_KEY=your-secret-key
DEBUG=True                           # False in production

# Database
SCITEX_CLOUD_POSTGRES_DB=scitex_cloud_dev
SCITEX_CLOUD_POSTGRES_USER=scitex_dev
SCITEX_CLOUD_POSTGRES_PASSWORD=strong-password

# Gitea (optional)
SCITEX_CLOUD_GITEA_URL=http://gitea:3000
SCITEX_CLOUD_GITEA_TOKEN=your-token
```

**Templates available:**
- `deployment/docker/docker_dev/.env.dev.example`
- `deployment/docker/docker_prod/.env.prod.example`

</details>

---

## Common Tasks

<details>
<summary><b>Development</b></summary>

```bash
make start                    # Start dev environment
make migrate                  # Run migrations
make shell                    # Django shell
make logs-web                 # View web logs
make db-shell                 # Database shell
make gitea-token              # Setup Gitea token (dev only)
make recreate-testuser        # Recreate test user (dev only)
```

</details>

<details>
<summary><b>Production Deployment</b></summary>

```bash
make ENV=prod start            # Deploy to production
make ENV=prod migrate          # Run migrations
make ENV=prod db-backup        # Backup database
make ENV=prod verify-health    # Health check
make ENV=prod logs             # View logs
```

</details>

<details>
<summary><b>Testing</b></summary>

```bash
make test                     # Run test suite (dev)
make ENV=prod verify-health    # Health check (production)
```

</details>

---

## Project Structure

<details>
<summary><b>Directory Organization</b></summary>

```
scitex-cloud/
├── apps/                    # Django applications
│   ├── scholar_app/        # Literature discovery
│   ├── writer_app/         # Scientific writing
│   ├── console_app/           # Code analysis
│   ├── viz_app/            # Data visualization
│   ├── project_app/        # Repository management
│   ├── auth_app/           # Authentication
│   ├── public_app/         # Landing page
│   ├── gitea_app/          # Git hosting integration
│   └── dev_app/            # Design system
│
├── deployment/docker/       # Container deployments
│   ├── docker_dev/         # Development
│   ├── docker_prod/        # Production/Home server
│   └── common/             # Shared resources
│
├── SECRET/                  # Environment files (gitignored)
│   ├── .env.dev            # Development secrets
│   └── .env.prod           # Production secrets
│
├── config/                  # Django configuration
├── static/                  # Frontend assets
├── templates/               # Base templates
├── deployment/              # Legacy deployment configs
└── Makefile                 # Environment switcher
```

**Documentation:**
- `deployment/docker/README.md` - Docker setup
- `deployment/docker/docker_dev/README.md` - Dev environment
- `deployment/docker/docker_prod/README.md` - Production deployment

</details>

---

## Architecture

<details>
<summary><b>Tech Stack</b></summary>

**Backend:**
- Django 4.2+
- PostgreSQL (Docker) / SQLite (local)
- Gunicorn (production)

**Frontend:**
- HTML5, CSS3, JavaScript
- Theme-responsive (light/dark modes)
- GitHub-inspired UI

**Infrastructure:**
- Nginx (reverse proxy)
- Gitea (Git hosting)
- Redis (caching + Celery broker)
- Docker Compose (orchestration)
- SLURM (job scheduling)
- Apptainer (HPC containers)
- Celery (async task processing)
- Flower (task monitoring)

**Design:**
- Project-centric (all modules link to projects)
- Three-tier fair resource allocation (Django/Celery/SLURM)
- 100% MIT licensed

</details>

---

## Troubleshooting

<details>
<summary><b>Docker Issues</b></summary>

```bash
make logs                     # Check logs
make rebuild                  # Rebuild containers
make down                     # Stop services
make ENV=dev clean            # Clean up (⚠️ removes volumes)
```

**Port conflicts:**
```bash
sudo lsof -i :8000
make down
```

**Permission denied:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

</details>

<details>
<summary><b>Local Development Issues</b></summary>

```bash
# Port in use
lsof -i :8000

# Reset database
rm data/db/sqlite/scitex_cloud.db
python manage.py migrate

# Fix static files
python manage.py collectstatic

# Permission errors
chmod +x scripts/server/start
```

</details>

---

## Contributing

<details>
<summary><b>How to Contribute</b></summary>

1. Fork repository
2. Create feature branch: `git checkout -b feature/name`
3. Commit: `git commit -m 'feat: Add feature'`
4. Push: `git push origin feature/name`
5. Open Pull Request

**Code Style:**
- Django best practices
- Apps in `apps/XXX_app/` format
- No files in project root
- Theme-responsive CSS
- Environment files in `SECRET/` (never commit)

</details>

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md).

---

<p align="center">
  <a href="https://scitex.ai" target="_blank"><img src="static/shared/images/scitex-icon-navy-inverted.png" alt="SciTeX" width="40"/></a>
  <br>
  AGPL-3.0
</p>

<!-- EOF -->