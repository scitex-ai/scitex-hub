<!-- ---
!-- Timestamp: 2025-12-06 17:25:00
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/DEV_VS_NAS.md
!-- --- -->

# Dev vs NAS Environment Configuration

## Quick Reference

| Setting               | Dev                  | NAS                                  |
|-----------------------|----------------------|--------------------------------------|
| **HTTP Port**         | 8000 (direct Django) | 80 (nginx + Cloudflare)              |
| **Domain**            | 127.0.0.1            | scitex.ai                            |
| **HTTPS Cookies**     | false                | true                                 |
| **Database**          | scitex_cloud_dev     | scitex_cloud_nas                     |
| **Cloudflare Tunnel** | none                 | configured                           |
| **Gitea URL**         | 127.0.0.1:3000       | gitea:3000 (Docker internal)         |
| **SLURM Host**        | ywata-note-win       | DXP480TPLUS-994                      |
| **SCITEX_DIR**        | /app/.scitex/        | /volume1/docker/scitex-data/.scitex/ |
| **Visitor Pool**      | 4                    | 16                                   |


## Git SSH Access

| Environment | Command                                                |
|-------------|--------------------------------------------------------|
| **NAS**     | `git clone git@scitex.ai:username/repo.git`            |
| **Dev**     | `git clone ssh://git@127.0.0.1:2222/username/repo.git` |

NAS uses Cloudflare Tunnel to route SSH (port 22) to Gitea container (internal port 2222).

## Architecture Differences

| Aspect              | Dev                                | NAS                              |
|---------------------|------------------------------------|---------------------------------|
| **Dockerfile**      | Single-stage, includes dev tools   | Multi-stage, optimized for size |
| **Container user**  | root                               | scitex (UID 1000)               |
| **SLURM UID**       | Uses host's UID 1000 user          | Requires 'scitex' user on host  |
| **Django command**  | `runserver` (hot reload)           | `daphne` (production ASGI)      |
| **Code mounting**   | Live mount for hot reload          | Built into image                |
| **scitex-code**     | Mounted from local directory       | Installed from PyPI             |
| **Nginx**           | None (direct Django:8000)          | nginx:alpine reverse proxy      |
| **Cloudflare**      | None                               | cloudflared container           |
| **CrossRef**        | NAS via LAN (169.254.11.50:8000)   | Local container (crossref:3333) |
| **Celery workers**  | 4                                  | 8                               |
| **Network subnet**  | 172.20.0.0/16                      | default bridge                  |

## Exposed Ports

| Port | Dev | NAS | Purpose                       |
|------|-----|-----|-------------------------------|
| 8000 | Yes | No  | Django (internal in NAS)      |
| 2200 | Yes | Yes | SSH gateway for workspaces    |
| 2222 | Yes | Yes | Gitea SSH (git clone/push)    |
| 5678 | Yes | No  | Debug (debugpy/pdb)           |
| 5173 | Yes | No  | Vite HMR                      |
| 80   | No  | Yes | nginx (via Cloudflare)        |

Note: In NAS, port 2222 is exposed to internet via Cloudflare Tunnel as port 22, enabling `git@scitex.ai`.

## Services

| Service     | Dev | NAS | Notes                        |
|-------------|-----|-----|------------------------------|
| django      | Yes | Yes | runserver vs daphne          |
| postgres    | Yes | Yes | Query logging in dev         |
| redis       | Yes | Yes | Debug logging in dev         |
| celery      | Yes | Yes | 4 vs 8 concurrency           |
| celery-beat | Yes | Yes | Scheduler                    |
| flower      | Yes | Yes | Celery monitoring            |
| gitea       | Yes | Yes | Git server                   |
| nginx       | No  | Yes | Reverse proxy                |
| cloudflared | No  | Yes | Cloudflare tunnel            |
| crossref    | No  | Yes | Local CrossRef API mirror    |

## Scholar Configuration

| Setting      | Dev                          | NAS                          |
|--------------|------------------------------|------------------------------|
| Cache        | enabled                      | enabled                      |
| Workers      | 8                            | 8                            |
| Mode         | parallel                     | parallel                     |
| Debug        | true                         | false                        |
| PDF Parallel | 8                            | 16                           |
| CrossRef API | 169.254.11.50:8000 (NAS LAN) | crossref:3333 (local Docker) |

### Search Engine Order (default.yaml)

Priority for searching (first to last):
1. URL (extract DOI from URL)
2. CrossRefLocal (local mirror, fastest)
3. Semantic_Scholar
4. CrossRef (public API)
5. OpenAlex
6. PubMed
7. arXiv

### Metadata Merge Priority

When merging results from multiple engines, higher priority wins:
- URL: 6 (highest)
- CrossRefLocal: 5
- CrossRef: 4
- OpenAlex: 3
- Semantic_Scholar: 2
- PubMed/arXiv: 1

Dev connects directly to NAS CrossRef via LAN ($IP_NAS_UG:8000) for full-featured search (DOI + title + authors + year). Port 3333 is DOI-only.

## Resource Quotas

| Setting           | Dev | NAS |
|-------------------|-----|-----|
| Max Queued Jobs   | 8   | 16  |
| Visitor Pool Size | 4   | 16  |

## Dev-Only Features

- **Hot reload**: Live code changes without restart
- **Debug port (5678)**: Remote debugging with debugpy/pdb
- **Vite HMR (5173)**: Frontend hot module replacement
- **Postgres query logging**: All queries logged to stderr
- **Redis debug logging**: Verbose cache operations
- **Volume caching**: uv_cache, playwright_cache for faster rebuilds

## Dev Dependencies on NAS

Dev requires NAS on the same LAN for:

- **CrossRef API**: Direct connection to 169.254.11.50:3333 (NAS CrossRef container)
- **SLURM**: Terminal/compute features (if SLURM is on NAS)

Fully local (no NAS needed):

- **Core Django, Writer, Gitea**: Fully functional

## File Locations

- Dev env: `SECRET/.env.dev`
- NAS env: `SECRET/.env.nas`
- Dev Docker: `deployment/docker/docker_dev/`
- NAS Docker: `deployment/docker/docker_nas/`

<!-- EOF -->