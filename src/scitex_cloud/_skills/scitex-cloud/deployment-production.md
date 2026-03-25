---
description: Deploy SciTeX Cloud to production — zero-downtime build, swap, verify.
---

# Deploy to Production

**WARNING: This affects the live site (scitex.ai). Confirm with user before proceeding.**

## Prerequisites
- Staging MUST be deployed and verified first (see `deployment-staging.md`)
- Ensure scitex version is released to PyPI
- Ensure Dockerfile.prod pins correct scitex version

## Step 1: Sync NAS repo
```bash
ssh nas "cd ~/proj/scitex-cloud && git -C ~/proj/scitex-cloud pull origin develop"
```

## Step 2: Build prod image (zero downtime — prod stays running during build)
```bash
ssh nas "cd ~/proj/scitex-cloud/deployment/docker/docker_prod && nohup docker compose build --no-cache > /tmp/prod-build.log 2>&1 &"
```

## Step 3: Monitor build
```bash
ssh nas "tail -f /tmp/prod-build.log"
```

## Step 4: Swap to new image
```bash
ssh nas "cd ~/proj/scitex-cloud/deployment/docker/docker_prod && docker compose up -d"
```

## Step 5: Verify production
- Check https://scitex.ai
- Verify all apps responsive
- Check logs for errors
