# CrossRef Local - Quick Start on NAS

**Goal**: Get the CrossRef Local API running on your NAS in ~30 minutes

## Your Setup

```
NAS: /home/ywatanabe/proj/
├── crossref_local/         ← Your 1TB+ CrossRef database
│   ├── data/               ← Database files here
│   ├── dois2sqlite/
│   ├── impact_factor/
│   └── labs-data-file-api/
├── scitex-cloud/           ← Django application
└── scitex-code/            ← Python package
```

## Step-by-Step Testing

### 1. Explore Your Database (5 minutes)

**SSH to NAS and run:**

```bash
cd /home/ywatanabe/proj/scitex-cloud

# Explore what you have
bash scripts/explore_crossref_local.sh

# Review the output
cat crossref_local_analysis.txt
```

**Look for:**
- ✓ Database file location
- ✓ Table names (works, references, journals, etc.)
- ✓ Row counts
- ✓ Indices (if any)
- ✓ Sample data

**Save this info** - you'll need it for Docker configuration.

### 2. Build Docker Image (5 minutes)

```bash
cd /home/ywatanabe/proj/scitex-cloud/deployment/docker/crossref_local

# Build the image
docker build -t scitex-crossref-local:latest .

# Verify
docker images | grep crossref-local
# Should show: scitex-crossref-local:latest (~100MB)
```

### 3. Configure Database Path (2 minutes)

**Edit** `docker-compose.crossref.yml`:

```yaml
# Find this line in volumes section:
- /home/ywatanabe/proj/crossref_local/data:/data:ro

# And this in environment:
- CROSSREF_DB_PATH=/data/crossref.db
#                        ^^^^^^^^^^^^
#                        Replace with your actual database filename
```

**If your database file is named differently:**
1. From Step 1, find the actual .db file name
2. Update CROSSREF_DB_PATH to match

Example:
```yaml
# If database is: crossref_local/data/crossref_2024.db
- CROSSREF_DB_PATH=/data/crossref_2024.db
```

### 4. Start the API Server (2 minutes)

```bash
# Start in background
docker-compose -f docker-compose.crossref.yml up -d

# Check if running
docker ps | grep crossref-local

# Watch logs (wait for "Application startup complete")
docker logs -f scitex-crossref-local-nas

# Press Ctrl+C to exit logs
```

**Expected output:**
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Connected to database: /data/crossref.db
INFO:     Database contains 140,123,456 papers
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:3333
```

### 5. Test the API (5 minutes)

```bash
# Quick test
curl http://localhost:3333/health

# Should return:
# {
#   "status": "healthy",
#   "database_connected": true,
#   "total_papers": 140123456,
#   ...
# }

# Run full test suite
bash test_api.sh

# All tests should pass with ✓
```

### 6. Try Some Queries (10 minutes)

```bash
# Get database stats
curl http://localhost:3333/api/stats/ | jq

# Search by DOI (replace with actual DOI from your database)
curl "http://localhost:3333/api/search/?doi=10.1038/nature12345" | jq

# Search by title
curl "http://localhost:3333/api/search/?title=deep%20learning&limit=5" | jq

# Search by year
curl "http://localhost:3333/api/search/?year=2020&limit=5" | jq

# Get citation graph (if references table exists)
curl "http://localhost:3333/api/citations/?doi=10.1038/nature12345&depth=1" | jq
```

### 7. Interactive Documentation

**Open in browser:**
```
http://YOUR_NAS_IP:3333/docs
```

- Try queries interactively
- See all available endpoints
- Test parameters

## Troubleshooting

### Problem: Container exits immediately

```bash
# Check logs for error
docker logs scitex-crossref-local-nas

# Common issues:
# 1. Database file not found
#    → Check CROSSREF_DB_PATH matches actual file
# 2. Permission denied
#    → Check file permissions: ls -l /home/ywatanabe/proj/crossref_local/data/
```

**Fix database path:**
```bash
# Find actual database files
ls -lh /home/ywatanabe/proj/crossref_local/data/*.db

# Update docker-compose.crossref.yml with correct filename
# Then restart
docker-compose -f docker-compose.crossref.yml restart
```

### Problem: No data returned from searches

```bash
# Check what's actually in the database
docker exec scitex-crossref-local-nas sqlite3 /data/crossref.db << EOF
.tables
SELECT COUNT(*) FROM works;
SELECT * FROM works LIMIT 3;
EOF
```

**If table is empty or named differently:**
1. Check `crossref_local_analysis.txt` from Step 1
2. Database may need to be built/imported
3. See `docs/CROSSREF_DATA_SETUP_WORKFLOW.md` for data import

### Problem: Slow queries

```bash
# Check if indices exist
docker exec scitex-crossref-local-nas sqlite3 /data/crossref.db << EOF
SELECT name FROM sqlite_master WHERE type='index';
EOF

# If no indices, see:
# docs/CROSSREF_DATA_SETUP_WORKFLOW.md (Step 4: Add Indices)
```

## What You've Achieved

✅ **Docker API server running**
✅ **Accessing your 1TB+ CrossRef database**
✅ **Fast local queries (no API limits)**
✅ **RESTful API with OpenAPI docs**

## Next Steps

### Option A: Integrate with Django (Recommended)

```bash
cd /home/ywatanabe/proj/scitex-cloud

# Create Django client
# See: docs/CROSSREF_DOCKER_ARCHITECTURE.md
# File: apps/scholar_app/integrations/crossref_local_client.py
```

**Quick test from Django:**
```bash
docker exec -it scitex-django-nas python manage.py shell

>>> from apps.scholar_app.integrations.crossref_local_client import CrossRefLocalClient
>>> client = CrossRefLocalClient("http://crossref-local:3333")
>>> paper = client.search_by_doi("10.1038/nature12345")
>>> print(paper)
```

### Option B: Improve Database (If needed)

**If your database has no indices or incomplete data:**

1. Check current state from Step 1 output
2. Follow: `docs/CROSSREF_DATA_SETUP_WORKFLOW.md`
3. Add indices (4-8 hours for full database)
4. Import missing data if needed

**Run in background:**
```bash
# Add indices
nohup python add_indices.py --database /home/ywatanabe/proj/crossref_local/data/crossref.db > logs/indices.log 2>&1 &

# Monitor progress
tail -f logs/indices.log
```

### Option C: Add to Main docker-compose

**For production deployment:**

1. Edit `/home/ywatanabe/proj/scitex-cloud/deployment/docker/docker_nas/docker-compose.yml`
2. Add crossref-local service (see README.md Production section)
3. Restart entire stack:
   ```bash
   cd deployment/docker/docker_nas
   docker-compose down
   docker-compose up -d
   ```

## Experiments to Try

### Experiment 1: Impact Factor Calculation

**Goal**: Calculate journal impact factors from citation data

```bash
# Check if citation data exists
curl http://localhost:3333/api/stats/ | jq '.has_citations'

# If true, try citation graph
curl "http://localhost:3333/api/citations/?doi=YOUR_DOI&depth=2" | jq

# Next: Implement impact factor calculation
# See: docs/CROSSREF_LOCAL_INTEGRATION_PLAN.md (Phase 2)
```

### Experiment 2: Search Performance

**Benchmark local vs API:**

```bash
# Local (should be <100ms)
time curl "http://localhost:3333/api/search/?doi=10.1038/nature12345"

# Compare with public API
time curl "https://api.crossref.org/works/10.1038/nature12345"

# Local is much faster! ⚡
```

### Experiment 3: Connected Papers

**Find related papers:**

```bash
# Get citation network for a paper
curl "http://localhost:3333/api/citations/?doi=YOUR_DOI&depth=2&include_references=true&include_citations=true" | jq

# Analyze:
# - How many papers cite it?
# - How many papers does it cite?
# - What's the citation network structure?

# Next: Build visualization (D3.js)
# See: docs/CROSSREF_LOCAL_INTEGRATION_PLAN.md (Phase 4)
```

## Monitoring

```bash
# Container status
docker ps | grep crossref-local

# Logs (follow)
docker logs -f scitex-crossref-local-nas

# Health check
watch -n 10 'curl -s http://localhost:3333/health | jq'

# Stats
curl http://localhost:3333/api/stats/ | jq

# Performance
docker stats scitex-crossref-local-nas
```

## Stopping the Server

```bash
# Stop
docker-compose -f docker-compose.crossref.yml stop

# Remove
docker-compose -f docker-compose.crossref.yml down

# Restart
docker-compose -f docker-compose.crossref.yml restart
```

## Summary

**You now have:**
- ✅ Working CrossRef Local API server
- ✅ Accessing 1TB+ database via HTTP
- ✅ No data copying (volume mount)
- ✅ Fast queries (<100ms)
- ✅ RESTful API with docs
- ✅ Ready for Django integration

**Time to complete:** ~30 minutes
**Image size:** ~100MB
**Data movement:** 0 bytes (no copying!)

## Questions or Issues?

1. Check logs: `docker logs scitex-crossref-local-nas`
2. Review analysis: `cat crossref_local_analysis.txt`
3. Test API: `bash test_api.sh`
4. Read docs: `deployment/docker/crossref_local/README.md`

## Documentation

- **Architecture**: `docs/CROSSREF_DOCKER_ARCHITECTURE.md`
- **Data Setup**: `docs/CROSSREF_DATA_SETUP_WORKFLOW.md`
- **Integration Plan**: `docs/CROSSREF_LOCAL_INTEGRATION_PLAN.md`
- **API Docs**: http://localhost:3333/docs (when running)

---

**Ready to start?** SSH to your NAS and run Step 1!

```bash
ssh your-nas
cd /home/ywatanabe/proj/scitex-cloud
bash scripts/explore_crossref_local.sh
```
