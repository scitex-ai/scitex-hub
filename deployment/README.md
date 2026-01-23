# Deployment

## Quick Start

```bash
make env=dev start
make env=dev status
```

## Structure

```
deployment/
├── docker/     # Docker configs
├── slurm/      # SLURM setup
├── singularity/# User containers
├── envs/       # Environment templates
├── docs/       # Documentation
└── cron/       # Scheduled tasks (unused)
```

## Environments

| Command | Usage |
|---------|-------|
| `make env=dev start` | Development |
| `make env=prod start` | Production |
| `make env=nas start` | NAS |

## Config

`SECRETS/.env.{dev,prod,nas}`
