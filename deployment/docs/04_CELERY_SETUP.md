# 04 - Celery

Async task queue for I/O tasks.

## Use For

- AI API calls
- Paper search
- PDF processing
- LaTeX compilation

## Monitor

http://localhost:5555 (Flower)

## Restart

```bash
docker compose restart celery_worker
```

## Config

`config/celery.py`
`config/settings/settings_shared.py`
