# 02 - Resource Allocation

## Per-User Limits

| Resource | Limit |
|----------|-------|
| SLURM jobs | 10 concurrent |
| AI requests | 10/min |
| API requests | 1000/day |

## SLURM Partitions

| Partition | Max Time |
|-----------|----------|
| express | 1 hour |
| normal | 24 hours |
| long | 7 days |

## When Limit Exceeded

| System | Behavior |
|--------|----------|
| SLURM | Job queued |
| Celery | Retry after delay |
| Django | HTTP 429 |
