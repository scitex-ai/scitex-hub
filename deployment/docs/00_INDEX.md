# Deployment Docs

## Index

| # | Doc | About |
|---|-----|-------|
| 01 | [Architecture](./01_ARCHITECTURE_OVERVIEW.md) | System design |
| 02 | [Resource Allocation](./02_FAIR_RESOURCE_ALLOCATION.md) | Quotas |
| 03 | [SLURM](./03_SLURM_SETUP.md) | Job scheduler |
| 04 | [Celery](./04_CELERY_SETUP.md) | Task queue |
| 05 | [Apptainer](./05_APPTAINER_CONTAINERS.md) | User containers |
| 06 | [Docker](./06_DOCKER_SERVICES.md) | Services |
| 07 | [Operations](./07_OPERATIONS_GUIDE.md) | Commands |
| 08 | [Port Proxy](./08_PORT_PROXY.md) | Service access |

## Quick Start

```bash
make env=dev start
make env=dev status
```

## URLs

| Service | URL |
|---------|-----|
| Django | http://localhost:8000 |
| Flower | http://localhost:5555 |
| Gitea | http://localhost:3001 |
