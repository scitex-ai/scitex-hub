# Environment Configuration

Centralized environment files for SciTeX Cloud deployment.

## Files

| File | Purpose | Used By |
|------|---------|---------|
| `.env.dev` | Local development | `docker_dev/`, local Django |
| `.env.staging` | Staging server | `docker-compose.staging.yml` |
| `.env.prod` | Production server | `docker_prod/` |
| `.env.example` | Template with placeholders | New deployments |

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

### Staging Deployment
```bash
./scripts/deploy/rebuild.sh staging
```

### Production Deployment
```bash
./scripts/deploy/rebuild.sh prod
```

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
