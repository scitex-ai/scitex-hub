# Docker

## Environments

| Env | Usage |
|-----|-------|
| docker_dev | Development |
| docker_prod | Production |
| docker_nas | NAS/Home |

## Quick Start

```bash
make env=dev start
make env=prod start
make env=nas start
```

## Structure

```
docker/
├── docker_dev/   # Development
├── docker_prod/  # Production
├── docker_nas/   # NAS
└── common/       # Shared configs
```
