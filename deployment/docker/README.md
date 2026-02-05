# Docker

## Environments

| Env | Usage |
|-----|-------|
| docker_dev | Development |
| docker_prod | Production |
| docker_prod | NAS/Home |

## Quick Start

```bash
make env=dev start
make env=prod start
make env=prod start
```

## Structure

```
docker/
├── docker_dev/   # Development
├── docker_prod/  # Production
├── docker_prod/   # NAS
└── common/       # Shared configs
```
