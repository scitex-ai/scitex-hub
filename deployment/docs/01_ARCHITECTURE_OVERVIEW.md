# 01 - Architecture

## Components

| Component | Purpose |
|-----------|---------|
| Django | Web app |
| PostgreSQL | Database |
| Redis | Cache + Celery broker |
| SLURM | Heavy compute jobs |
| Celery | Async I/O tasks |
| Apptainer | User containers |
| Gitea | Git server |

## Task Routing

| Task Type | System |
|-----------|--------|
| Heavy compute (>30s) | SLURM |
| Async I/O (API calls) | Celery |
| Quick (<1s) | Django |

## Data Flow

```
Browser → Django → SLURM/Celery → Result → Django → Browser
```
