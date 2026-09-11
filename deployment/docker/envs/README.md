# Environment Configuration

Centralized environment files for SciTeX Hub deployment.

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

The browser terminal uses one writable Apptainer sandbox on the host. Keep the
large artifact on scratch storage and set its absolute host path in the
untracked `.env.dev`:

```dotenv
SCITEX_HUB_SLURM_CONTAINER_PATH=/absolute/path/on/slurm-host/to/current-sandbox
```

The development Compose stack binds that exact source read-only at the stable
Docker path `/app/singularity/current`. Django validates the container through
that alias, while `srun` receives the original host path. Docker is configured
with `create_host_path: false`, so a typo or missing sandbox fails at startup
instead of silently creating an empty directory. An unset value resolves to a
deliberately nonexistent sentinel for the same fail-closed behavior. The host
source may vary by node; the Docker-side path must not.

Build the writable sandbox from a Hub worktree on scratch storage so the
generated base image, sandbox, and temporary files do not consume the home
filesystem:

```bash
SCITEX_HUB_BUILD_WORKTREE=/scratch/path-you-own/scitex-hub-terminal-image
git worktree add --detach "$SCITEX_HUB_BUILD_WORKTREE" origin/develop
cd "$SCITEX_HUB_BUILD_WORKTREE"
make apptainer-build-base
make apptainer-sandbox
```

Then set `SCITEX_HUB_SLURM_CONTAINER_PATH` to that worktree's
`deployment/singularity/current-sandbox` symlink. Do not substitute a SAC agent
image: the Hub user-terminal image has a separate runtime and security contract.

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
