# CrossRef Local - Docker Distribution Strategy

**Author**: Claude Code
**Date**: 2025-12-03
**Context**: Official repos have bugs, considering pre-built Docker distribution

## The Problem

### Official Tools Have Issues

```
❌ CrossRef Labs API repos - Bugs
❌ dois2sqlite - Issues
❌ Complex setup - Days of work
❌ Users repeat same problems
```

### Our Situation

✅ You've already done the hard work:
- Fixed bugs in official tools
- Downloaded and converted data
- Added indices
- Validated database

❓ **Question**: Why should every user repeat this painful process?

## The Solution: Pre-Built Docker Image

**Distribute a ready-to-use Docker image with:**
1. Pre-built, indexed CrossRef SQLite database
2. Fixed/patched tools
3. FastAPI server
4. Documentation

### Benefits

| Approach | Setup Time | Disk Space | Bugs |
|----------|-----------|------------|------|
| **DIY** (current) | 3-7 days | 2TB | User encounters bugs |
| **Docker Distribution** | 5 minutes | 400GB | We fixed them |

## Distribution Strategies

### Strategy A: Complete Database Image (Recommended)

**Ship everything in one image**

#### Pros
✅ Zero setup for users
✅ Guaranteed to work
✅ No version conflicts
✅ Immediate usability

#### Cons
❌ Large image size (~400GB compressed)
❌ Bandwidth intensive
❌ Update = re-download entire image

#### Implementation

```dockerfile
# Dockerfile.full
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py database.py models.py config.py ./

# Copy PRE-BUILT database
COPY data/crossref.db /data/crossref.db

# Metadata
LABEL org.opencontainers.image.title="CrossRef Local Database"
LABEL org.opencontainers.image.description="Pre-indexed CrossRef database with FastAPI server"
LABEL org.opencontainers.image.version="2024.12"
LABEL org.opencontainers.image.authors="SciTeX Team"

# Health check
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:3333/health || exit 1

EXPOSE 3333

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3333"]
```

```bash
# Build and push
docker build -f Dockerfile.full -t scitex/crossref-local:2024.12 .
docker tag scitex/crossref-local:2024.12 scitex/crossref-local:latest

# Push to registry
docker push scitex/crossref-local:2024.12
docker push scitex/crossref-local:latest
```

**User Experience**:
```bash
# User just runs:
docker pull scitex/crossref-local:latest
docker run -d -p 3333:3333 scitex/crossref-local:latest

# Done! Working in 5 minutes
```

### Strategy B: Server + Separate Volume (Hybrid)

**Small image + large data volume**

#### Pros
✅ Smaller image (~100MB)
✅ Update server without re-downloading data
✅ More flexible

#### Cons
❌ Two-step setup
❌ User must download data separately
❌ Slightly more complex

#### Implementation

```dockerfile
# Dockerfile.server (lightweight)
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py database.py models.py config.py ./

# Database is mounted at runtime
VOLUME ["/data"]

ENV CROSSREF_DB_PATH=/data/crossref.db

HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:3333/health || exit 1

EXPOSE 3333

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3333"]
```

**Data Distribution**:
```bash
# Option 1: Direct download
wget https://scitex.ai/data/crossref_2024.db.gz
gunzip crossref_2024.db.gz

# Option 2: Docker volume with data
docker volume create crossref-data
# Pre-populate volume (we provide script)
docker run --rm -v crossref-data:/data scitex/crossref-data-loader:2024.12
```

**User Experience**:
```bash
# Step 1: Get data (one time, large download)
docker volume create crossref-data
docker run --rm -v crossref-data:/data scitex/crossref-data-loader:2024.12

# Step 2: Run server (fast, updates easy)
docker run -d \
    -p 3333:3333 \
    -v crossref-data:/data:ro \
    scitex/crossref-local:latest
```

### Strategy C: Tiered Distribution

**Multiple image sizes for different use cases**

```
scitex/crossref-local:sample        # 1GB - Top 10k papers
scitex/crossref-local:subset-2020   # 50GB - 2020-2024
scitex/crossref-local:full          # 400GB - All data
```

#### Benefits
✅ Users choose based on needs
✅ Fast development with sample
✅ Full production with complete

## Recommended Architecture

### Multi-Stage Build with Variants

```dockerfile
# Dockerfile.multi-stage

# Stage 1: Base (common dependencies)
FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py database.py models.py config.py ./

# Stage 2: Sample (development)
FROM base AS sample
COPY data/crossref_sample.db /data/crossref.db
ENV VARIANT=sample

# Stage 3: Subset (testing)
FROM base AS subset
COPY data/crossref_subset_2020.db /data/crossref.db
ENV VARIANT=subset

# Stage 4: Full (production)
FROM base AS full
COPY data/crossref_full.db /data/crossref.db
ENV VARIANT=full

# Default: base without data (external volume)
FROM base AS default
VOLUME ["/data"]
ENV VARIANT=external
```

**Build all variants**:
```bash
# Sample (quick pull for dev)
docker build --target sample -t scitex/crossref-local:sample .

# Subset (for testing)
docker build --target subset -t scitex/crossref-local:subset .

# Full (for production)
docker build --target full -t scitex/crossref-local:full .

# External volume (most flexible)
docker build --target default -t scitex/crossref-local:latest .
```

## Distribution Platforms

### Option 1: Docker Hub (Public/Private)

```bash
# Public (free, unlimited pulls)
docker push scitex/crossref-local:latest

# Users pull
docker pull scitex/crossref-local:latest
```

**Pros**: Free, familiar, widely used
**Cons**: 6-month inactivity deletion, rate limits

### Option 2: GitHub Container Registry

```bash
# Authenticate
echo $CR_PAT | docker login ghcr.io -u USERNAME --password-stdin

# Tag and push
docker tag scitex/crossref-local:latest ghcr.io/scitex/crossref-local:latest
docker push ghcr.io/scitex/crossref-local:latest

# Users pull
docker pull ghcr.io/scitex/crossref-local:latest
```

**Pros**: Integrated with GitHub, free for public repos
**Cons**: Must manage GitHub organization

### Option 3: Self-Hosted Registry (NAS)

```bash
# Run registry on your NAS
docker run -d -p 5000:5000 --name registry \
    -v /mnt/nas_ug/docker-registry:/var/lib/registry \
    registry:2

# Push images
docker tag scitex/crossref-local:latest localhost:5000/crossref-local:latest
docker push localhost:5000/crossref-local:latest

# Users pull (with your NAS URL)
docker pull nas.scitex.ai:5000/crossref-local:latest
```

**Pros**: Full control, no rate limits, can host large images
**Cons**: Bandwidth from your NAS, uptime responsibility

### Recommended: Hybrid Approach

```
Sample → Docker Hub (free, fast)
Subset → GitHub Container Registry (free)
Full   → Self-hosted on NAS (large, controlled)
```

## Legal & Licensing Considerations

### CrossRef Data License

```
CrossRef metadata is licensed under CC0 1.0 Universal
✅ Free to use
✅ Free to redistribute
✅ No attribution required (but encouraged)

Source: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
```

**You CAN legally**:
✅ Redistribute CrossRef data
✅ Create derived databases
✅ Package in Docker images
✅ Offer as a service

**You SHOULD**:
✅ Credit CrossRef in documentation
✅ Note data version and date
✅ Provide update mechanism

### Your Fixes & Additions

```
Your bug fixes and tools:
- Your choice of license (MIT recommended)
- Clearly separate from CrossRef data
- Document what you fixed/added
```

## Implementation Plan

### Phase 1: Prepare Images (1 week)

```bash
# 1. Create sample database (your existing data)
python create_sample.py --size 1GB --output data/crossref_sample.db

# 2. Create subset (if not exist)
python create_subset.py --years 2020-2024 --output data/crossref_subset.db

# 3. Use your full database
cp /mnt/nas_ug/crossref_local/data/crossref.db data/crossref_full.db

# 4. Build all variants
make docker-build-all

# 5. Test locally
make docker-test-all

# 6. Document
make docker-docs
```

### Phase 2: Distribution Setup (2 days)

```bash
# 1. Push to Docker Hub (sample, subset)
docker push scitex/crossref-local:sample
docker push scitex/crossref-local:subset

# 2. Setup self-hosted registry (full)
# On NAS
docker-compose -f docker-registry.yml up -d

# 3. Push full image to NAS registry
docker push nas.scitex.ai:5000/crossref-local:full

# 4. Create documentation
# - Quick start guide
# - API documentation
# - License info
```

### Phase 3: User Documentation (1 day)

```markdown
# docs/CROSSREF_LOCAL_QUICKSTART.md

## Quick Start

### Development (1GB sample)
```bash
docker run -d -p 3333:3333 scitex/crossref-local:sample
curl http://localhost:3333/health
```

### Testing (50GB subset)
```bash
docker run -d -p 3333:3333 scitex/crossref-local:subset
```

### Production (400GB full)
```bash
# One-time data download
docker pull nas.scitex.ai:5000/crossref-local:full

# Run
docker run -d -p 3333:3333 nas.scitex.ai:5000/crossref-local:full
```

### Custom Database
```bash
docker run -d -p 3333:3333 \
    -v /path/to/your/crossref.db:/data/crossref.db:ro \
    scitex/crossref-local:latest
```
```

## Update Strategy

### Monthly Data Updates

```bash
# Build new version
export VERSION=$(date +%Y.%m)
docker build -t scitex/crossref-local:$VERSION .
docker tag scitex/crossref-local:$VERSION scitex/crossref-local:latest

# Push
docker push scitex/crossref-local:$VERSION
docker push scitex/crossref-local:latest
```

### Users Update

```bash
# Pull latest
docker pull scitex/crossref-local:latest

# Restart container
docker-compose restart crossref-local
```

## Makefile Targets

```makefile
# Makefile additions for Docker distribution

.PHONY: docker-build-all docker-test-all docker-push-all

# Build all variants
docker-build-all:
	docker build --target sample -t scitex/crossref-local:sample .
	docker build --target subset -t scitex/crossref-local:subset .
	docker build --target full -t scitex/crossref-local:full .
	docker build --target default -t scitex/crossref-local:latest .

# Test all variants
docker-test-all:
	./scripts/test_docker_variant.sh sample
	./scripts/test_docker_variant.sh subset
	./scripts/test_docker_variant.sh full

# Push to registries
docker-push-all:
	docker push scitex/crossref-local:sample
	docker push scitex/crossref-local:subset
	docker push scitex/crossref-local:latest
	# Full pushed to self-hosted registry separately

# Version tag
docker-tag-version:
	$(eval VERSION := $(shell date +%Y.%m))
	docker tag scitex/crossref-local:full scitex/crossref-local:$(VERSION)
	docker push scitex/crossref-local:$(VERSION)
```

## Testing Before Distribution

```bash
# Test script
# scripts/test_docker_variant.sh

#!/bin/bash
VARIANT=$1

echo "Testing $VARIANT variant..."

# Start container
docker run -d --name test-crossref-$VARIANT \
    -p 3333:3333 \
    scitex/crossref-local:$VARIANT

# Wait for startup
sleep 5

# Health check
curl -f http://localhost:3333/health || exit 1

# Test search
curl "http://localhost:3333/api/search/?doi=10.1038/nature12345" || exit 1

# Test stats
curl http://localhost:3333/api/stats/ || exit 1

# Cleanup
docker stop test-crossref-$VARIANT
docker rm test-crossref-$VARIANT

echo "$VARIANT variant: ✅ PASSED"
```

## Documentation for Users

### README for Docker Hub

```markdown
# CrossRef Local - Fast, Offline Research Paper Metadata

Pre-built, indexed CrossRef database with FastAPI server.

## Quick Start

```bash
# Sample database (1GB) - Development
docker run -d -p 3333:3333 scitex/crossref-local:sample

# Test it
curl http://localhost:3333/health
curl "http://localhost:3333/api/search/?doi=10.1038/nature12345"
```

## Variants

- `sample` - 1GB, 10k papers, instant download
- `subset` - 50GB, 2020-2024, for testing
- `full` - 400GB, all CrossRef data, production
- `latest` - Server only, use with external volume

## Features

✅ 140M+ research papers
✅ Citation graphs
✅ Fast local queries (no API limits)
✅ REST API included
✅ Pre-indexed for performance

## Data Source

CrossRef metadata (CC0 licensed)
Data version: 2024.12
Papers: 140M+
Coverage: 1800s - 2024

## License

- CrossRef data: CC0 1.0 Universal
- Server code: MIT License
- See LICENSE file for details
```

## Next Steps

1. **Confirm your data is ready**:
   ```bash
   ssh nas
   cd /home/ywatanabe/crossref_local/
   ls -lh data/crossref.db
   ```

2. **Document your bug fixes**:
   - What bugs did you encounter?
   - What did you fix?
   - Should we contribute fixes back upstream?

3. **Choose distribution strategy**:
   - Full image (easy) or Server + Volume (flexible)?
   - Which registries to use?

4. **Build and test**:
   - Create Dockerfile(s)
   - Build variants
   - Test thoroughly

5. **Distribute**:
   - Push to registries
   - Document for users
   - Announce availability

---

**Let's check what you have first, then decide on the best distribution approach!**
