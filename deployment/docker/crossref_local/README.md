# CrossRef Local API

Fast, offline API server for local CrossRef database (1TB+ SQLite database).

## Architecture

```
┌───────────────────────────────────────────┐
│         NAS: /home/ywatanabe/proj/        │
│                                           │
│  crossref_local/data/crossref.db (1TB+)  │
│         ↓ (read-only volume mount)       │
│  ┌──────────────────────────────┐        │
│  │ Docker: scitex-crossref-local│        │
│  │ FastAPI + Uvicorn            │        │
│  │ Port: 3333                   │        │
│  │ Workers: 4                   │        │
│  └──────────────────────────────┘        │
│         ↓ HTTP API                       │
│  ┌──────────────────────────────┐        │
│  │ Django: scitex-cloud         │        │
│  │ Scholar App                  │        │
│  └──────────────────────────────┘        │
└───────────────────────────────────────────┘
```

## Features

✅ **Fast**: Local SQLite queries (no API rate limits)
✅ **Simple**: Single Docker container
✅ **Lightweight**: ~100MB image (no data included)
✅ **RESTful**: Full OpenAPI/Swagger documentation
✅ **Robust**: Health checks, error handling, logging
✅ **Flexible**: Works with any CrossRef SQLite database

## Quick Start

### Step 1: Explore Your Database

```bash
# Check what you have
cd /home/ywatanabe/proj/scitex-cloud
bash scripts/explore_crossref_local.sh

# Review the analysis
cat crossref_local_analysis.txt
```

### Step 2: Build Docker Image

```bash
cd deployment/docker/crossref_local

# Build
docker build -t scitex-crossref-local:latest .

# Verify build
docker images | grep crossref
```

### Step 3: Run Server

```bash
# Start the API server
docker-compose -f docker-compose.crossref.yml up -d

# Check logs
docker logs -f scitex-crossref-local-nas

# Wait for startup (check health)
curl http://localhost:3333/health
```

### Step 4: Test API

```bash
# Run test script
bash test_api.sh

# Or test manually
curl http://localhost:3333/api/stats/
curl "http://localhost:3333/api/search/?doi=10.1038/nature12345"

# Open interactive docs
open http://localhost:3333/docs
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/docs` | GET | Interactive Swagger UI |
| `/api/search/` | GET | Search papers by DOI/title/year/authors |
| `/api/citations/` | GET | Get citation graph |
| `/api/journal/` | GET | Get journal info |
| `/api/batch/` | POST | Batch DOI lookup |
| `/api/stats/` | GET | Database statistics |

## Usage Examples

### Search by DOI

```bash
curl "http://localhost:3333/api/search/?doi=10.1038/nature12345"
```

Response:
```json
{
  "query": {"doi": "10.1038/nature12345"},
  "results": [{
    "doi": "10.1038/nature12345",
    "title": "Paper Title",
    "authors": ["Author One", "Author Two"],
    "year": 2023,
    "journal": "Nature"
  }],
  "total": 1,
  "returned": 1
}
```

### Search by Title

```bash
curl "http://localhost:3333/api/search/?title=deep+learning&year=2015&limit=10"
```

### Get Citation Graph

```bash
curl "http://localhost:3333/api/citations/?doi=10.1038/nature12345&depth=2&include_references=true&include_citations=true"
```

Response:
```json
{
  "center_doi": "10.1038/nature12345",
  "nodes": [
    {
      "doi": "10.1038/nature12345",
      "title": "Center Paper",
      "year": 2023
    },
    {
      "doi": "10.1016/...",
      "title": "Citing Paper",
      "year": 2024
    }
  ],
  "edges": [
    {
      "source": "10.1016/...",
      "target": "10.1038/nature12345",
      "type": "cites"
    }
  ],
  "total_nodes": 2,
  "total_edges": 1
}
```

### Batch Lookup

```bash
curl -X POST "http://localhost:3333/api/batch/" \
  -H "Content-Type: application/json" \
  -d '["10.1038/nature12345", "10.1126/science.1234567"]'
```

## Configuration

Environment variables (in `docker-compose.crossref.yml`):

```yaml
environment:
  # Database
  - CROSSREF_DB_PATH=/data/crossref.db

  # Server
  - LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
  - WORKERS=4               # Number of worker processes
  - HOST=0.0.0.0
  - PORT=3333

  # Performance
  - ENABLE_QUERY_CACHE=true
  - CACHE_TTL_SECONDS=3600
  - MAX_SEARCH_RESULTS=100
  - MAX_BATCH_SIZE=100
  - MAX_CITATION_DEPTH=3
```

## Troubleshooting

### Container won't start

```bash
# Check if database file exists
ls -lh /home/ywatanabe/proj/crossref_local/data/

# Check Docker logs
docker logs scitex-crossref-local-nas

# Verify volume mount
docker inspect scitex-crossref-local-nas | grep -A 10 Mounts
```

### Database not found

```bash
# Check the CROSSREF_DB_PATH in docker-compose.yml
# Make sure it points to actual .db file inside /data/

# If your database has a different name:
environment:
  - CROSSREF_DB_PATH=/data/your_database_name.db
```

### Slow queries

```bash
# Check if indices exist in your database
sqlite3 /home/ywatanabe/proj/crossref_local/data/crossref.db << EOF
SELECT name FROM sqlite_master WHERE type='index';
EOF

# If no indices, add them (see docs/CROSSREF_DATA_SETUP_WORKFLOW.md)

# Increase workers
environment:
  - WORKERS=8  # More workers for concurrent requests
```

### Memory issues

```bash
# Reduce workers or increase memory limit
deploy:
  resources:
    limits:
      memory: 4G  # Increase if needed
    reservations:
      memory: 1G
```

## Integration with Django

See `docs/CROSSREF_DOCKER_ARCHITECTURE.md` for Django integration guide.

Quick example:

```python
# apps/scholar_app/integrations/crossref_local_client.py
import requests

class CrossRefLocalClient:
    def __init__(self):
        self.api_url = "http://crossref-local:3333"

    def search_by_doi(self, doi: str):
        response = requests.get(
            f"{self.api_url}/api/search/",
            params={"doi": doi}
        )
        data = response.json()
        return data["results"][0] if data["results"] else None
```

## Monitoring

### Health Checks

```bash
# Manual check
curl http://localhost:3333/health | jq

# Docker health status
docker ps | grep crossref

# Continuous monitoring
watch -n 10 'curl -s http://localhost:3333/health | jq'
```

### Logs

```bash
# Follow logs
docker logs -f scitex-crossref-local-nas

# Last 100 lines
docker logs --tail 100 scitex-crossref-local-nas

# With timestamps
docker logs -t scitex-crossref-local-nas
```

### Performance Metrics

```bash
# Database stats
curl http://localhost:3333/api/stats/ | jq

# Container stats
docker stats scitex-crossref-local-nas

# Disk usage
docker exec scitex-crossref-local-nas du -sh /data
```

## Development

### Local Testing (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set database path
export CROSSREF_DB_PATH=/home/ywatanabe/proj/crossref_local/data/crossref.db

# Run server
python server.py

# Or with uvicorn
uvicorn server:app --reload --host 0.0.0.0 --port 3333
```

### Updating the Code

```bash
# Rebuild image after code changes
docker-compose -f docker-compose.crossref.yml build

# Restart service
docker-compose -f docker-compose.crossref.yml restart crossref-local

# Or full restart
docker-compose -f docker-compose.crossref.yml down
docker-compose -f docker-compose.crossref.yml up -d
```

## Production Deployment

### Add to Main docker-compose.yml

```yaml
# In deployment/docker/docker_nas/docker-compose.yml

services:
  # ... existing services ...

  crossref-local:
    build: ../crossref_local/
    container_name: scitex-crossref-local-nas
    expose:
      - "3333"  # Only exposed to internal network
    volumes:
      - /home/ywatanabe/proj/crossref_local/data:/data:ro
    environment:
      - CROSSREF_DB_PATH=/data/crossref.db
      - WORKERS=8
      - LOG_LEVEL=WARNING
    restart: unless-stopped
    networks:
      - scitex-network

  django:
    depends_on:
      - crossref-local
    environment:
      - CROSSREF_LOCAL_API_URL=http://crossref-local:3333
```

### Start Everything Together

```bash
cd deployment/docker/docker_nas
docker-compose up -d

# Verify all services
docker-compose ps
```

## License

- Code: MIT License
- CrossRef Data: CC0 1.0 Universal (Public Domain)

## Support

For issues or questions:
- Check logs: `docker logs scitex-crossref-local-nas`
- Review docs: `docs/CROSSREF_*.md`
- Test API: `bash test_api.sh`

## Next Steps

1. ✅ Built and tested API
2. → Integrate with Django Scholar app
3. → Implement impact factor calculation
4. → Add Connected Papers visualization
5. → Deploy to production

See `docs/CROSSREF_LOCAL_INTEGRATION_PLAN.md` for complete roadmap.
