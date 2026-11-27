# Environment Configuration

Centralized environment files for SciTeX Hub deployment.

## Files

| File | Purpose | Used By |
|------|---------|---------|
| `.env.dev` | Local development | `docker_dev/`, local Django |
| `.env.staging` | Staging server | `docker-compose.staging.yml` |
| `.env.prod` | Production server | `docker_prod/` |
| `.env.example` | Template with placeholders | New deployments |
| `secrets/cloudflared-tunnel-token` | Prod tunnel token, one line; owner 65532, mode 0400 | `docker_prod/` `cloudflared` (compose `secrets:`) |

## Symlinks

```
project_root/.env          -> deployment/docker/envs/.env.dev
docker_dev/.env            -> ../envs/.env.dev
```

## Usage

### Local Development
```bash
make env=dev start
```

### Staging and Production

Follow the [canonical deployment runbook](../../../src/scitex_hub/_skills/scitex-hub/12_deployment-production.md)
for qualified images, reviewed environment selection, targeted recreation and
rollback. The environment files supply configuration to that owning workflow.

### Browser Reload in Development

`SCITEX_HUB_DJANGO_DEBUG` controls the development settings' DEBUG flag.
`SCITEX_HUB_BROWSER_RELOAD_ENABLED` independently controls injection of the
browser reload worker and defaults to `True`. Set it to `False` for a server
started without a file watcher, such as the baked E2E `--noreload` profile.
DEBUG and strict manifest validation remain enabled in that profile. Normal
interactive development keeps reload enabled; production settings do not add
the development reload middleware.

## Creating New Environment

1. Copy `.env.example` to `.env.<environment>`
2. Fill in all required values
3. Generate new secrets:
   ```bash
   python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
   ```

## Security

- Never commit actual `.env.*` files (gitignored)
- Only `.env.example` and `README.md` are tracked
- Rotate secrets regularly in production
