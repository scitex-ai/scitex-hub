# Gitea Setup

Django-Gitea integration is automatic.

## What Happens Automatically

- Django user created → Gitea user created
- Django project created → Gitea repo created
- Django user deleted → Gitea user deleted

## Config

In `SECRETS/.env.dev`:

```bash
SCITEX_CLOUD_GITEA_URL_DEV=http://gitea:3000
SCITEX_CLOUD_GITEA_TOKEN_DEV=<token>
```

## Generate Token

```bash
docker exec -u git scitex-cloud-dev-gitea-1 gitea admin user generate-access-token \
  --username admin \
  --token-name "django-token" \
  --scopes "write:admin,write:repository,write:user"
```

## Access

http://localhost:3001
