# NAS

Home server with Cloudflare Tunnel.

## Start

```bash
make env=nas start
```

## Access

- Public: https://scitex.ai (via Cloudflare)
- Local: http://nas-ip:8000

## Cloudflare Setup

1. Create tunnel at https://dash.cloudflare.com
2. Add token to `SECRETS/.env.nas`

## Commands

```bash
make env=nas status
make env=nas logs
make env=nas restart
```
