# Environment Variables

## Setup

```bash
# Copy template
cp deployment/envs/.env.example SECRETS/.env.dev

# Edit with your values
vim SECRETS/.env.dev
```

## Files

| File | Purpose |
|------|---------|
| `SECRETS/.env.dev` | Development secrets |
| `SECRETS/.env.prod` | Production secrets |
| `deployment/envs/.env.example` | Template |

## Key Variables

- `SCITEX_HUB_DJANGO_SECRET_KEY`
- `SCITEX_HUB_POSTGRES_PASSWORD`
- `ANTHROPIC_API_KEY`
