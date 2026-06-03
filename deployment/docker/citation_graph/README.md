# Citation Graph API

FastAPI service for citation network analysis on **port 3334**.

## Overview

Provides citation graph analysis using the local CrossRef database:
- Build citation networks with similarity scoring
- Find related papers
- Get paper summaries with citation counts
- In-memory caching for fast repeated queries

## Port Allocation

| Service           | Port  | Purpose                   |
|-------------------|-------|---------------------------|
| CrossRef Local    | 31291  | Paper metadata & search   |
| **Citation Graph** | **3334** | **Citation network analysis** |
| (future services) | 3335+ | Reserved                  |

## Quick Start

### 1. Install Dependencies

```bash
# Install scitex-code (required for citation graph module)
cd ~/proj/scitex-code
pip install -e .

# Install API dependencies
cd ~/proj/scitex-hub/deployment/docker/citation_graph
pip install -r requirements.txt
```

### 2. Start Server

```bash
# Default: port 3334
python server.py

# Custom port
PORT=3334 python server.py

# Custom database
CROSSREF_DB_PATH=/path/to/crossref.db python server.py
```

### 3. Test API

```bash
# Health check
curl http://localhost:3334/health

# Build citation network
curl "http://localhost:3334/api/network/?doi=10.1038/s41586-020-2008-3&top_n=20"

# Get related papers
curl "http://localhost:3334/api/related/?doi=10.1038/s41586-020-2008-3&limit=10"

# Get paper summary
curl "http://localhost:3334/api/paper/?doi=10.1038/s41586-020-2008-3"

# Cache stats
curl http://localhost:3334/api/cache/stats/
```

## API Endpoints

### 1. Build Citation Network

**`GET /api/network/`**

Build complete citation network with similarity scoring.

**Parameters**:
- `doi` (required): Seed paper DOI
- `top_n` (default: 20, max: 100): Number of related papers
- `weight_coupling` (default: 2.0): Bibliographic coupling weight
- `weight_cocitation` (default: 2.0): Co-citation weight
- `weight_direct` (default: 1.0): Direct citation weight
- `no_cache` (default: false): Bypass cache

**Example**:
```bash
curl "http://localhost:3334/api/network/?doi=10.1038/s41586-020-2008-3&top_n=20"
```

**Response**:
```json
{
  "seed": "10.1038/s41586-020-2008-3",
  "nodes": [
    {
      "doi": "10.1038/s41586-020-2008-3",
      "title": "A new coronavirus associated with human respiratory disease in China",
      "year": 2020,
      "authors": ["Fan Wu", "Su Zhao", "Bin Yu"],
      "similarity_score": 100.0
    },
    ...
  ],
  "edges": [
    {
      "source": "10.1038/s41586-020-2008-3",
      "target": "10.1016/j.cell.2020.02.052",
      "edge_type": "cites",
      "weight": 1.0
    },
    ...
  ],
  "total_nodes": 21,
  "total_edges": 45,
  "parameters": {
    "top_n": 20,
    "weight_coupling": 2.0,
    "weight_cocitation": 2.0,
    "weight_direct": 1.0
  },
  "cached": false,
  "build_time_seconds": 28.5
}
```

**Performance**: ~30s uncached, <50ms cached

---

### 2. Get Related Papers

**`GET /api/related/`**

Get list of similar papers (lightweight, no full network).

**Parameters**:
- `doi` (required): Paper DOI
- `limit` (default: 10, max: 50): Maximum results
- `no_cache` (default: false): Bypass cache

**Example**:
```bash
curl "http://localhost:3334/api/related/?doi=10.1038/s41586-020-2008-3&limit=10"
```

**Response**:
```json
{
  "doi": "10.1038/s41586-020-2008-3",
  "related": [
    {
      "doi": "10.1016/j.cell.2020.02.052",
      "title": "SARS-CoV-2 Cell Entry Depends on ACE2 and TMPRSS2...",
      "year": 2020,
      "authors": ["Markus Hoffmann", "Hannah Kleine-Weber"],
      "similarity_score": 85.5,
      "relationship": "similar"
    },
    ...
  ],
  "count": 10,
  "cached": true
}
```

**Performance**: ~15s uncached, <50ms cached

---

### 3. Get Paper Summary

**`GET /api/paper/`**

Get paper metadata with citation counts.

**Parameters**:
- `doi` (required): Paper DOI

**Example**:
```bash
curl "http://localhost:3334/api/paper/?doi=10.1038/s41586-020-2008-3"
```

**Response**:
```json
{
  "doi": "10.1038/s41586-020-2008-3",
  "title": "A new coronavirus associated with human respiratory disease in China",
  "year": 2020,
  "authors": ["Fan Wu", "Su Zhao", "Bin Yu"],
  "abstract": "Emerging infectious diseases...",
  "journal": "Nature",
  "citation_count": 12500,
  "reference_count": 42
}
```

**Performance**: <5s

---

### 4. Health Check

**`GET /health`**

Service health and database status.

**Example**:
```bash
curl http://localhost:3334/health
```

**Response**:
```json
{
  "status": "healthy",
  "database_path": "/home/ywatanabe/proj/crossref_local/data/crossref.db",
  "database_accessible": true,
  "cache_enabled": true,
  "cache_size": 42,
  "version": "1.0.0"
}
```

---

### 5. Cache Management

**`GET /api/cache/stats/`** - Get cache statistics

```bash
curl http://localhost:3334/api/cache/stats/
```

**Response**:
```json
{
  "size": 42,
  "max_size": 1000,
  "hits": 156,
  "misses": 45,
  "hit_rate": 77.61,
  "ttl": 3600
}
```

**`POST /api/cache/clear/`** - Clear cache

```bash
curl -X POST http://localhost:3334/api/cache/clear/
```

---

## Configuration

Environment variables (see `config.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | 0.0.0.0 | Bind address |
| `PORT` | 3334 | Port number |
| `CROSSREF_DB_PATH` | ~/proj/crossref_local/data/crossref.db | Database path |
| `CACHE_ENABLED` | true | Enable caching |
| `CACHE_TTL_SECONDS` | 3600 | Cache TTL (1 hour) |
| `CACHE_MAX_SIZE` | 1000 | Max cached items |
| `LOG_LEVEL` | INFO | Logging level |
| `CORS_ENABLED` | true | Enable CORS |
| `CORS_ORIGINS` | * | Allowed origins |

**Example**:
```bash
PORT=3334 \
CACHE_TTL_SECONDS=7200 \
CROSSREF_DB_PATH=/data/crossref.db \
python server.py
```

---

## Citation Graph Algorithm

The service uses three similarity metrics:

1. **Bibliographic Coupling**: Papers that cite many of the same references
   - Weight: 2.0 (default)
   - Measures shared context

2. **Co-citation**: Papers that are frequently cited together
   - Weight: 2.0 (default)
   - Indicates related work

3. **Direct Citations**: Papers directly connected by citations
   - Weight: 1.0 (default)
   - Ensures key papers are included

**Combined Score**:
```
similarity = (coupling * w_c) + (cocitation * w_co) + (direct * w_d)
```

Top N papers by similarity are included in the network.

---

## Integration with Services

### Use with CrossRef Local (Port 31291)

```python
import requests

# Get paper metadata from CrossRef Local
paper = requests.get(
    "http://localhost:31291/api/search/",
    params={"doi": "10.1038/s41586-020-2008-3"}
).json()

# Build citation network from Citation Graph
network = requests.get(
    "http://localhost:3334/api/network/",
    params={"doi": paper["results"][0]["doi"], "top_n": 20}
).json()

print(f"Network: {network['total_nodes']} nodes, {network['total_edges']} edges")
```

### Frontend Integration (D3.js/vis.js)

```javascript
// Fetch network data
const response = await fetch(
  'http://localhost:3334/api/network/?doi=10.1038/s41586-020-2008-3&top_n=20'
);
const network = await response.json();

// Render with D3.js
const graph = {
  nodes: network.nodes.map(n => ({
    id: n.doi,
    label: n.title,
    size: n.similarity_score
  })),
  edges: network.edges.map(e => ({
    source: e.source,
    target: e.target
  }))
};

// D3 force-directed graph...
```

---

## Performance Tips

1. **Enable caching**: Reduces response time from ~30s to <50ms
   ```bash
   CACHE_ENABLED=true CACHE_TTL_SECONDS=3600 python server.py
   ```

2. **Reduce `top_n`**: Smaller networks are faster
   ```bash
   curl "http://localhost:3334/api/network/?doi=...&top_n=10"  # ~15s
   ```

3. **Adjust weights**: Lower weights = faster (less computation)
   ```bash
   curl "http://localhost:3334/api/network/?doi=...&weight_coupling=1.0"
   ```

4. **Use `/api/related/` for lists**: Lightweight, no full graph structure

5. **Database on SSD**: Improves query performance

---

## Troubleshooting

### Service Unavailable (503)

**Error**: "Service unhealthy: database not found"

**Solution**:
```bash
# Check database path
ls -lh ~/proj/crossref_local/data/crossref.db

# Set explicit path
CROSSREF_DB_PATH=/path/to/crossref.db python server.py
```

---

### Import Error

**Error**: "ModuleNotFoundError: No module named 'scitex.scholar.citation_graph'"

**Solution**:
```bash
cd ~/proj/scitex-code
pip install -e .
```

---

### Slow Performance

**Symptom**: Requests taking >60s

**Solutions**:
1. Enable caching (see config)
2. Reduce `top_n` parameter
3. Check database on SSD/NVMe
4. Add database indexes (see CrossRef database docs)

---

## API Documentation

Interactive API docs available when server is running:

- **Swagger UI**: http://localhost:3334/docs
- **ReDoc**: http://localhost:3334/redoc

---

## Architecture

```
Request Flow:

Client → FastAPI (server.py)
           ↓
       Service Layer (service.py) [+ Cache]
           ↓
       CitationGraphBuilder (scitex-code)
           ↓
       CrossRef Database (SQLite)
```

---

## Files

```
citation_graph/
├── server.py           # FastAPI application
├── service.py          # Business logic + caching
├── models.py           # Pydantic models
├── config.py           # Configuration
├── requirements.txt    # Dependencies
└── README.md           # This file
```

---

## Comparison: Django vs FastAPI

| Feature | Django (Port 8000) | FastAPI (Port 3334) |
|---------|-------------------|---------------------|
| Framework | Django REST | FastAPI |
| Purpose | Full scholar app | Citation graph only |
| Caching | Django cache | In-memory LRU |
| Deployment | Integrated | Standalone microservice |
| Auto docs | DRF browsable | Swagger + ReDoc |

**Use FastAPI (3334)** for:
- Standalone citation graph service
- Lightweight microservice architecture
- Direct API access without Django overhead

**Use Django (8000)** for:
- Full scholar application
- Integrated with other scholar features
- Unified authentication/authorization

---

## Next Steps

1. **Production deployment**: Docker container + systemd
2. **Rate limiting**: Add throttling middleware
3. **Authentication**: API keys or OAuth
4. **Monitoring**: Prometheus metrics
5. **Frontend**: D3.js visualization interface

---

## Support

For issues:
1. Check logs for errors
2. Test `/health` endpoint
3. Verify database path and scitex-code installation
4. Check GitHub issues
