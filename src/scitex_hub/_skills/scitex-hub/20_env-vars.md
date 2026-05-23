---
description: |
  [TOPIC] scitex-hub — Environment Variables
  [DETAILS] Environment variables read by scitex-hub at import / runtime. Follow SCITEX_<MODULE>_* convention — see general/10_arch-environment-variables.md..
tags: [scitex-hub-env-vars]
---

# scitex-hub — Environment Variables

## Environment selection

| Variable | Purpose | Default | Type |
|---|---|---|---|
| `SCITEX_HUB_ENV` | Target environment (`dev`, `staging`, `prod`, `onsite`). | `dev` | string |
| `SCITEX_HUB_CONFIG` | Path to YAML config. | bundled | path |
| `SCITEX_HUB_ROOT` | Root directory of the scitex-hub repo (dev). | repo-root | path |
| `SCITEX_HUB_WORKSPACE` / `SCITEX_WORKSPACE` | Active workspace name. | `default` | string |
| `SCITEX_HUB_IS_ON_SITE` | Mark the deployment as on-site (enables on-site tools only). | `false` | bool |
| `SCITEX_HUB_COMPLETE` | Internal sentinel: standalone importable. | unset | bool (presence) |

## URLs / hosts

| Variable | Purpose | Default | Type |
|---|---|---|---|
| `SCITEX_HUB_URL` | Primary cloud URL. | `https://scitex.ai` | URL |
| `SCITEX_HUB_SITE_URL` | Public site URL (may differ from API). | inherits | URL |
| `SCITEX_HUB_DOMAIN` | Allowed domain for cookies / CSRF. | inherits | string |
| `SCITEX_HUB_ALLOWED_HOSTS` | Django `ALLOWED_HOSTS` override. | inherits | string (CSV) |
| `SCITEX_API_URL` | Legacy alias of `SCITEX_HUB_URL`. | inherits | URL |
| `SCITEX_HUB_HTTP_PORT_DEV` | HTTP port used in local dev. | `8000` | int |
| `SCITEX_HUB_MCP_HOST` | MCP daemon host. | `localhost` | string |
| `SCITEX_HUB_MCP_PORT` | MCP daemon port. | `8765` | int |

## Auth / credentials

| Variable | Purpose | Default | Type |
|---|---|---|---|
| `SCITEX_API_TOKEN` | User API token (primary). | `—` | string |
| `SCITEX_HUB_API_KEY` | Service-account API key. | `—` | string |
| `SCITEX_HUB_USERNAME` | Username for SSO / password login. | `—` | string |
| `SCITEX_HUB_WORKSPACE_USER` | Workspace-level user. | inherits | string |
| `SCITEX_HUB_WORKSPACE_PASSWORD` | Workspace-level password. | `—` | string |
| `SCITEX_HUB_DJANGO_SECRET_KEY` | Django `SECRET_KEY`. | generated | string (required in prod) |
| `SCITEX_HUB_DJANGO_SETTINGS_MODULE` | Django settings module path. | `scitex_hub.settings.dev` | string |
| `SCITEX_HUB_POSTGRES_PASSWORD` | Postgres password. | `—` | string |

## Security / SSL

| Variable | Purpose | Default | Type |
|---|---|---|---|
| `SCITEX_HUB_ENABLE_SSL_REDIRECT` | Force HTTPS redirect in Django. | `true` in prod | bool |
| `SCITEX_HUB_FORCE_HTTPS_COOKIES` | Set `Secure` cookie flag. | `true` in prod | bool |

## Gitea integration

| Variable | Purpose | Default | Type |
|---|---|---|---|
| `SCITEX_HUB_GITEA_URL` | Production Gitea URL. | inherits | URL |
| `SCITEX_HUB_GITEA_URL_DEV` | Dev Gitea URL. | `http://localhost:3001` | URL |
| `SCITEX_HUB_GITEA_HTTP_PORT_DEV` | Dev Gitea HTTP port. | `3001` | int |
| `SCITEX_HUB_GITEA_USER` | Gitea login username. | `—` | string |
| `SCITEX_HUB_GITEA_PASSWORD` | Gitea login password. | `—` | string |
| `SCITEX_HUB_GITEA_TOKEN` | Gitea API token (prod). | `—` | string |
| `SCITEX_HUB_GITEA_TOKEN_DEV` | Gitea API token (dev). | `—` | string |

## App context

| Variable | Purpose | Default | Type |
|---|---|---|---|
| `SCITEX_CURRENT_APP` | Active SciTeX app slug (sidebar selection). | unset | string |
| `SCITEX_UI_STATIC` | Static-asset dir. | bundled | path |

## Feature flags

- **opt-in:** `SCITEX_HUB_IS_ON_SITE=true` — limits the tool surface to
  on-site safe operations.
- **opt-out (prod-only):** `SCITEX_HUB_ENABLE_SSL_REDIRECT=false` —
  disables the enforced HTTPS redirect; strongly discouraged outside dev.

## Audit

```bash
grep -rhoE 'SCITEX_[A-Z0-9_]+' $HOME/proj/scitex-hub/src/ | sort -u
```
