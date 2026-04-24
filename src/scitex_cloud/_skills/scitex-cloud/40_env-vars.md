---
name: scitex-cloud-env-vars
description: Environment variables read by scitex-cloud at import / runtime. Follow SCITEX_<MODULE>_* convention — see general/10_arch-environment-variables.md.
---

# scitex-cloud — Environment Variables

## Environment selection

| Variable | Purpose | Default | Type |
|---|---|---|---|
| `SCITEX_CLOUD_ENV` | Target environment (`dev`, `staging`, `prod`, `onsite`). | `dev` | string |
| `SCITEX_CLOUD_CONFIG` | Path to YAML config. | bundled | path |
| `SCITEX_CLOUD_ROOT` | Root directory of the scitex-cloud repo (dev). | repo-root | path |
| `SCITEX_CLOUD_WORKSPACE` / `SCITEX_WORKSPACE` | Active workspace name. | `default` | string |
| `SCITEX_CLOUD_IS_ON_SITE` | Mark the deployment as on-site (enables on-site tools only). | `false` | bool |
| `SCITEX_CLOUD_COMPLETE` | Internal sentinel: standalone importable. | unset | bool (presence) |

## URLs / hosts

| Variable | Purpose | Default | Type |
|---|---|---|---|
| `SCITEX_CLOUD_URL` | Primary cloud URL. | `https://scitex.ai` | URL |
| `SCITEX_CLOUD_SITE_URL` | Public site URL (may differ from API). | inherits | URL |
| `SCITEX_CLOUD_DOMAIN` | Allowed domain for cookies / CSRF. | inherits | string |
| `SCITEX_CLOUD_ALLOWED_HOSTS` | Django `ALLOWED_HOSTS` override. | inherits | string (CSV) |
| `SCITEX_API_URL` | Legacy alias of `SCITEX_CLOUD_URL`. | inherits | URL |
| `SCITEX_CLOUD_HTTP_PORT_DEV` | HTTP port used in local dev. | `8000` | int |
| `SCITEX_CLOUD_MCP_HOST` | MCP daemon host. | `localhost` | string |
| `SCITEX_CLOUD_MCP_PORT` | MCP daemon port. | `8765` | int |

## Auth / credentials

| Variable | Purpose | Default | Type |
|---|---|---|---|
| `SCITEX_API_TOKEN` | User API token (primary). | `—` | string |
| `SCITEX_CLOUD_API_KEY` | Service-account API key. | `—` | string |
| `SCITEX_CLOUD_USERNAME` | Username for SSO / password login. | `—` | string |
| `SCITEX_CLOUD_WORKSPACE_USER` | Workspace-level user. | inherits | string |
| `SCITEX_CLOUD_WORKSPACE_PASSWORD` | Workspace-level password. | `—` | string |
| `SCITEX_CLOUD_DJANGO_SECRET_KEY` | Django `SECRET_KEY`. | generated | string (required in prod) |
| `SCITEX_CLOUD_DJANGO_SETTINGS_MODULE` | Django settings module path. | `scitex_cloud.settings.dev` | string |
| `SCITEX_CLOUD_POSTGRES_PASSWORD` | Postgres password. | `—` | string |

## Security / SSL

| Variable | Purpose | Default | Type |
|---|---|---|---|
| `SCITEX_CLOUD_ENABLE_SSL_REDIRECT` | Force HTTPS redirect in Django. | `true` in prod | bool |
| `SCITEX_CLOUD_FORCE_HTTPS_COOKIES` | Set `Secure` cookie flag. | `true` in prod | bool |

## Gitea integration

| Variable | Purpose | Default | Type |
|---|---|---|---|
| `SCITEX_CLOUD_GITEA_URL` | Production Gitea URL. | inherits | URL |
| `SCITEX_CLOUD_GITEA_URL_DEV` | Dev Gitea URL. | `http://localhost:3001` | URL |
| `SCITEX_CLOUD_GITEA_HTTP_PORT_DEV` | Dev Gitea HTTP port. | `3001` | int |
| `SCITEX_CLOUD_GITEA_USER` | Gitea login username. | `—` | string |
| `SCITEX_CLOUD_GITEA_PASSWORD` | Gitea login password. | `—` | string |
| `SCITEX_CLOUD_GITEA_TOKEN` | Gitea API token (prod). | `—` | string |
| `SCITEX_CLOUD_GITEA_TOKEN_DEV` | Gitea API token (dev). | `—` | string |

## App context

| Variable | Purpose | Default | Type |
|---|---|---|---|
| `SCITEX_CURRENT_APP` | Active SciTeX app slug (sidebar selection). | unset | string |
| `SCITEX_UI_STATIC` | Static-asset dir. | bundled | path |

## Feature flags

- **opt-in:** `SCITEX_CLOUD_IS_ON_SITE=true` — limits the tool surface to
  on-site safe operations.
- **opt-out (prod-only):** `SCITEX_CLOUD_ENABLE_SSL_REDIRECT=false` —
  disables the enforced HTTPS redirect; strongly discouraged outside dev.

## Audit

```bash
grep -rhoE 'SCITEX_[A-Z0-9_]+' $HOME/proj/scitex-cloud/src/ | sort -u
```
