# 07 - Operations

## Start/Stop

```bash
make env=dev start
make env=dev stop
make env=dev status
```

## Docker

```bash
docker compose logs -f web
docker compose restart web
docker compose exec web bash
```

## SLURM

```bash
sinfo          # Status
squeue         # Jobs
scancel <id>   # Cancel
```

## Celery

http://localhost:5555

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Container won't start | `docker compose logs <service>` |
| SLURM job stuck | `sudo ./deployment/slurm/fix.sh` |
| Celery tasks stuck | `docker compose restart celery_worker` |
