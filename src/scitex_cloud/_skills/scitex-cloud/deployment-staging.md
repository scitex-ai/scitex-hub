---
description: Deploy SciTeX Cloud to staging — sync versions, build Docker, verify.
---

# Deploy to Staging

## Prerequisites
- Ensure scitex packages are latest and synchronized (`scitex dev versions list --json`)
- If scitex version was bumped locally, MUST be released to PyPI before Docker build
  (Dockerfile.prod installs from PyPI, not local source)

## Step 1: Sync versions
```bash
scitex dev versions list --json
scitex dev versions sync --confirm --host nas
```

## Step 2: Verify Dockerfile pins correct version
```bash
grep 'scitex\[all\]==' ~/proj/scitex-cloud/deployment/docker/Dockerfile.prod
```

## Step 3: Sync NAS repo
```bash
ssh nas "cd ~/proj/scitex-cloud && git -C ~/proj/scitex-cloud pull origin develop"
```

## Step 4: Build staging container
```bash
ssh nas "cd ~/proj/scitex-cloud/deployment/docker/docker_staging && docker compose build --no-cache"
```

## Step 5: Start staging
```bash
ssh nas "cd ~/proj/scitex-cloud/deployment/docker/docker_staging && docker compose up -d"
```

## Step 6: Verify
- Check staging URL
- Run smoke tests
- Verify all apps load
