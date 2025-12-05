<!-- ---
!-- Timestamp: 2025-12-06 09:02:41
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-cloud/docs/LOCAL_CROSSREF.md
!-- --- -->

# Local CrossRef Database & Citation Graph Services

## Overview

SciTeX uses a **local CrossRef database mirror** with 167M+ works and 47M+ citations for fast, offline paper metadata and citation network analysis.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    scitex.ai (HTTPS)                     │
│                    Django Application                     │
├─────────────────────────────────────────────────────────┤
│  Scholar App                                             │
│  ├─ Paper Search (CrossRefLocal engine)                 │
│  ├─ Citation Graph API (Django REST)                    │
│  └─ PDF Processing                                       │
└─────────────────────────────────────────────────────────┘
                          │
         ┌────────────────┴────────────────┐
         │                                  │
┌────────▼────────┐              ┌─────────▼──────────┐
│  CrossRef Local │              │  Citation Graph    │
│  Port 3333      │              │  Port 3334         │
│  (FastAPI)      │              │  (FastAPI)         │
└────────┬────────┘              └─────────┬──────────┘
         │                                  │
         └──────────────┬───────────────────┘
                        │
              ┌─────────▼─────────┐
              │  CrossRef SQLite   │
              │  1.2TB Database    │
              │  ~/crossref_local  │
              └────────────────────┘
```

---

## Services

### 1. CrossRef Local API (Port 3333)

**Purpose**: Paper metadata search and lookup

**Location**: `deployment/docker/crossref_local/`

**Endpoints**:
- `GET /api/search/` - Search by DOI, title, year, authors
- `GET /api/citations/` - Get citation graph (basic)
- `GET /api/batch/` - Batch DOI lookup
- `GET /health` - Service health

**Database Schema**:
```sql
CREATE TABLE works (
    id INTEGER PRIMARY KEY,
    doi VARCHAR(255),
    metadata BLOB  -- JSON: title, authors, year, abstract, etc.
);

CREATE TABLE citations (
    citing_doi VARCHAR(255),
    cited_doi VARCHAR(255),
    citing_year INTEGER
);
```

**Recent Fix** (2025-12-06):
- Fixed title/author/year search using SQLite JSON functions
- Previously only DOI lookup worked
- Now uses `json_extract(metadata, '$.title[0]')` for queries
- See: `/home/ywatanabe/proj/crossref_local/docs/FASTAPI_DATABASE_FIX.md`

**Status**: ✅ Fully functional (all search types working)

---

### 2. Citation Graph API (Port 3334)

**Purpose**: Citation network analysis with similarity scoring

**Location**: `deployment/docker/citation_graph/`

**Endpoints**:
- `GET /api/network/` - Build citation network (full graph)
- `GET /api/related/` - Get related papers (lightweight)
- `GET /api/paper/` - Paper summary with citation counts
- `GET /health` - Service health
- `GET /api/cache/stats/` - Cache statistics

**Algorithm**: Combines three similarity metrics:
1. **Bibliographic coupling** - Papers citing same references (weight: 2.0)
2. **Co-citation** - Papers cited together (weight: 2.0)
3. **Direct citations** - Papers directly connected (weight: 1.0)

**Performance**:
| Endpoint | Uncached | Cached |
|----------|----------|--------|
| `/api/network/` (20 papers) | ~30s | <50ms |
| `/api/related/` (10 papers) | ~15s | <50ms |
| `/api/paper/` | <5s | <50ms |

**Features**:
- In-memory LRU cache (1000 items, 1-hour TTL)
- Configurable similarity weights
- Swagger + ReDoc documentation
- CORS enabled for frontend

**Status**: ✅ Code complete (needs FastAPI dependencies installed)

**Documentation**:
- Full API docs: `deployment/docker/citation_graph/README.md`
- Setup guide: `deployment/docker/citation_graph/SETUP.md`

---

### 3. Django Integration (scitex.ai)

**Purpose**: Citation graph integrated into Django scholar app

**Location**: `apps/scholar_app/`

**Endpoints** (via https://scitex.ai):
- `/api/scholar/citation-graph/network/`
- `/api/scholar/citation-graph/related/`
- `/api/scholar/citation-graph/paper/`
- `/api/scholar/citation-graph/health/`

**Files**:
- `services/citation_graph/service.py` - Business logic
- `api/citation_graph.py` - Django REST endpoints
- `urls.py` - Route configuration

**Features**:
- Django cache backend (Redis on NAS)
- DRF throttling (50 requests/hour)
- Integrated authentication
- HTTPS via Cloudflare

**Status**: ✅ Implemented and integrated

**Documentation**: `apps/scholar_app/services/citation_graph/IMPLEMENTATION.md`

---

## Port Allocation

| Service           | Port  | Protocol | Purpose                      |
|-------------------|-------|----------|------------------------------|
| Django (dev)      | 8000  | HTTP     | Full scholar app             |
| Django (NAS)      | 80    | HTTPS    | Production (scitex.ai)       |
| CrossRef Local    | 3333  | HTTP     | Paper metadata & search      |
| **Citation Graph** | **3334** | **HTTP** | **Citation network analysis** |
| (future services) | 3335+ | HTTP     | Reserved                     |

---

## Database

**Location**: `/home/ywatanabe/proj/crossref_local/data/crossref.db`

**Size**: ~1.2TB

**Contents**:
- 167M+ works (papers)
- 47M+ citations
- Indexed by DOI, year, citations

**Schema**:
- `works` - Paper metadata (JSON in `metadata` column)
- `citations` - Citation relationships (citing_doi, cited_doi, citing_year)

**Indexes**:
```sql
CREATE INDEX idx_citations_cited ON citations(cited_doi, citing_year);
CREATE INDEX idx_citations_citing ON citations(citing_doi);
CREATE INDEX idx_doi_lookup ON works(doi);
```

---

## Core Library (scitex-code)

**Location**: `~/proj/scitex-code/src/scitex/scholar/citation_graph/`

**Module**: `scitex.scholar.citation_graph`

**Components**:
- `CitationGraphBuilder` - Main API
- `PaperNode`, `CitationEdge`, `CitationGraph` - Data models
- `DatabaseAccess` - Optimized SQL queries
- Similarity scoring algorithms

**Usage**:
```python
from scitex.scholar.citation_graph import CitationGraphBuilder

builder = CitationGraphBuilder(db_path="/path/to/crossref.db")
graph = builder.build(seed_doi="10.1038/s41586-020-2008-3", top_n=20)

print(f"Network: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
```

**Installation**:
```bash
cd ~/proj/scitex-code
pip install -e .
```

---

## Deployment Options

### Option 1: Django Integration (Recommended for Production)

**Use for**: Public API, frontend integration

**Endpoints**: https://scitex.ai/api/scholar/citation-graph/

**Advantages**:
- ✅ Already integrated into scholar app
- ✅ HTTPS via Cloudflare
- ✅ Django authentication/authorization
- ✅ Redis caching (NAS)
- ✅ Part of deployed application

**Deploy**: Included in standard scitex-cloud deployment

---

### Option 2: FastAPI Microservice (Port 3334)

**Use for**: Standalone service, development, internal tools

**Endpoints**: http://localhost:3334/api/

**Advantages**:
- ✅ Lightweight, fast startup
- ✅ Independent scaling
- ✅ Swagger + ReDoc docs
- ✅ No Django overhead

**Deploy**:
```bash
# Local
cd ~/proj/scitex-cloud/deployment/docker/citation_graph
python3 server.py

# Docker
docker run -d -p 3334:3334 \
  -v /path/to/crossref.db:/data/crossref.db \
  citation-graph:latest
```

**Docker Compose**:
```yaml
services:
  citation_graph:
    build:
      context: .
      dockerfile: deployment/docker/citation_graph/Dockerfile
    ports:
      - "3334:3334"
    environment:
      - CROSSREF_DB_PATH=/data/crossref.db
      - CACHE_ENABLED=true
    volumes:
      - /volume1/docker/scitex-data/crossref:/data:ro
    restart: unless-stopped
```

---

## Configuration

### Environment Variables

**CrossRef Local (Port 3333)**:
```bash
CROSSREF_DB_PATH=/home/ywatanabe/proj/crossref_local/data/crossref.db
HOST=0.0.0.0
PORT=3333
LOG_LEVEL=INFO
```

**Citation Graph (Port 3334)**:
```bash
CROSSREF_DB_PATH=/home/ywatanabe/proj/crossref_local/data/crossref.db
HOST=0.0.0.0
PORT=3334
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600
CACHE_MAX_SIZE=1000
CORS_ENABLED=true
LOG_LEVEL=INFO
```

**Django (scitex.ai)**:
```python
# settings.py
CROSSREF_DB_PATH = os.getenv('CROSSREF_DB_PATH', '/home/ywatanabe/proj/crossref_local/data/crossref.db')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

---

## Dev vs NAS Configuration

### Development Environment

| Setting | Value |
|---------|-------|
| Django Port | 8000 |
| CrossRef Local | 169.254.11.50:3333 (NAS via LAN) |
| Citation Graph | localhost:3334 (if running) |
| Database | /home/ywatanabe/proj/crossref_local/data/crossref.db |

**Scholar Config** (`apps/scholar_app/default.yaml`):
```yaml
engines:
  - name: CrossRefLocal
    priority: 5
    url: http://169.254.11.50:8000  # NAS CrossRef (port 8000 for full search)
```

### NAS Production Environment

| Setting | Value |
|---------|-------|
| Django Port | 80 (nginx + Cloudflare) |
| CrossRef Local | crossref:3333 (Docker internal) |
| Citation Graph | citation_graph:3334 (Docker internal) |
| Database | /volume1/docker/scitex-data/crossref/crossref.db |

**Scholar Config**:
```yaml
engines:
  - name: CrossRefLocal
    priority: 5
    url: http://crossref:3333  # Docker service
```

See: `docs/DEV_VS_NAS.md` for complete comparison

---

## API Examples

### CrossRef Local API (Port 3333)

**Basic Search Operations**:

```bash
# DOI lookup (fastest, indexed)
curl "http://localhost:3333/api/search/?doi=10.1038/s41586-020-2008-3"

# Title search (case-insensitive, partial match)
curl "http://localhost:3333/api/search/?title=coronavirus&limit=10"

# Year search
curl "http://localhost:3333/api/search/?year=2020&limit=10"

# Author search (searches in author list)
curl "http://localhost:3333/api/search/?authors=Zhang&limit=10"

# Combined search (title + year)
curl "http://localhost:3333/api/search/?title=machine%20learning&year=2023&limit=5"
```

**Batch Operations**:

```bash
# Batch DOI lookup (JSON POST)
curl -X POST "http://localhost:3333/api/batch/" \
  -H "Content-Type: application/json" \
  -d '{"dois": ["10.1038/s41586-020-2008-3", "10.1126/science.abc1234"]}'

# Pretty-print JSON output
curl "http://localhost:3333/api/search/?doi=10.1038/s41586-020-2008-3" | jq .
```

**Health & Status**:

```bash
# Service health check
curl "http://localhost:3333/health"

# Expected response:
# {"status": "healthy", "database": "connected"}
```

---

### Citation Graph API (Port 3334)

**Network Building**:

```bash
# Build 20-paper citation network (FastAPI)
curl "http://localhost:3334/api/network/?doi=10.1038/s41586-020-2008-3&top_n=20"

# Build network with custom similarity weights
curl "http://localhost:3334/api/network/?doi=10.1038/s41586-020-2008-3&top_n=15&weight_coupling=2.5&weight_cocitation=1.5&weight_direct=1.0"

# Small network for quick preview
curl "http://localhost:3334/api/network/?doi=10.1038/s41586-020-2008-3&top_n=5"
```

**Related Papers**:

```bash
# Get 10 most related papers (lightweight, no full graph)
curl "http://localhost:3334/api/related/?doi=10.1038/s41586-020-2008-3&limit=10"

# Get top 20 related papers
curl "http://localhost:3334/api/related/?doi=10.1038/s41586-020-2008-3&limit=20"

# Pretty-print with similarity scores
curl "http://localhost:3334/api/related/?doi=10.1038/s41586-020-2008-3&limit=5" | jq '.papers[] | {title: .title, score: .similarity_score}'
```

**Paper Summary**:

```bash
# Get citation counts and metadata
curl "http://localhost:3334/api/paper/?doi=10.1038/s41586-020-2008-3"

# Pretty-print paper info
curl "http://localhost:3334/api/paper/?doi=10.1038/s41586-020-2008-3" | jq '{title: .title, year: .year, citations: .cited_by_count, references: .references_count}'
```

**Cache Management**:

```bash
# View cache statistics
curl "http://localhost:3334/api/cache/stats/"

# Expected response:
# {"cache_enabled": true, "cache_size": 42, "cache_max_size": 1000, "cache_ttl_seconds": 3600}
```

**Health Check**:

```bash
# Service and database health
curl "http://localhost:3334/health"
```

---

### Django API (Production - scitex.ai)

**Network Building** (HTTPS, requires authentication):

```bash
# Build network via Django (production)
curl "https://scitex.ai/api/scholar/citation-graph/network/?doi=10.1038/s41586-020-2008-3&top_n=20"

# With authentication token
curl -H "Authorization: Token YOUR_API_TOKEN" \
  "https://scitex.ai/api/scholar/citation-graph/network/?doi=10.1038/s41586-020-2008-3&top_n=20"

# Dev environment (local)
curl "http://localhost:8000/api/scholar/citation-graph/network/?doi=10.1038/s41586-020-2008-3&top_n=15"
```

**Related Papers**:

```bash
# Production
curl "https://scitex.ai/api/scholar/citation-graph/related/?doi=10.1038/s41586-020-2008-3&limit=10"

# Development
curl "http://localhost:8000/api/scholar/citation-graph/related/?doi=10.1038/s41586-020-2008-3&limit=10"
```

**Paper Summary**:

```bash
# Production
curl "https://scitex.ai/api/scholar/citation-graph/paper/?doi=10.1038/s41586-020-2008-3"

# Development
curl "http://localhost:8000/api/scholar/citation-graph/paper/?doi=10.1038/s41586-020-2008-3"
```

**Health Check**:

```bash
# Production health
curl "https://scitex.ai/api/scholar/citation-graph/health/"

# Development health
curl "http://localhost:8000/api/scholar/citation-graph/health/"
```

---

### Advanced Usage

**Pipeline: DOI → Network → Visualization**:

```bash
# 1. Find paper by title
PAPER=$(curl -s "http://localhost:3333/api/search/?title=BERT&limit=1" | jq -r '.results[0].doi')

# 2. Build citation network
curl "http://localhost:3334/api/network/?doi=${PAPER}&top_n=10" > network.json

# 3. Extract node count
jq '.total_nodes' network.json

# 4. List top papers by similarity
jq -r '.nodes[] | "\(.similarity_score | tonumber | . * 100 | floor)% - \(.title)"' network.json | sort -rn | head -5
```

**Monitoring Cache Performance**:

```bash
# Check cache stats before
curl "http://localhost:3334/api/cache/stats/"

# Make request (will be slow first time)
time curl "http://localhost:3334/api/network/?doi=10.1038/s41586-020-2008-3&top_n=20" > /dev/null

# Make same request again (should be fast - cached)
time curl "http://localhost:3334/api/network/?doi=10.1038/s41586-020-2008-3&top_n=20" > /dev/null

# Check cache stats after
curl "http://localhost:3334/api/cache/stats/"
```

**Testing Different Similarity Weights**:

```bash
# High weight on bibliographic coupling (papers citing same sources)
curl "http://localhost:3334/api/network/?doi=10.1038/s41586-020-2008-3&top_n=10&weight_coupling=3.0&weight_cocitation=1.0&weight_direct=1.0" > coupling_heavy.json

# High weight on co-citation (papers cited together)
curl "http://localhost:3334/api/network/?doi=10.1038/s41586-020-2008-3&top_n=10&weight_coupling=1.0&weight_cocitation=3.0&weight_direct=1.0" > cocitation_heavy.json

# Compare results
diff <(jq '.nodes[].doi' coupling_heavy.json) <(jq '.nodes[].doi' cocitation_heavy.json)
```

---

## Frontend Integration

### Fetch Citation Network

```javascript
// Using FastAPI microservice
const network = await fetch(
  'http://localhost:3334/api/network/?doi=10.1038/s41586-020-2008-3&top_n=20'
).then(r => r.json());

// Or using Django API (production)
const network = await fetch(
  'https://scitex.ai/api/scholar/citation-graph/network/?doi=10.1038/s41586-020-2008-3&top_n=20'
).then(r => r.json());

console.log(`Network: ${network.total_nodes} nodes, ${network.total_edges} edges`);
```

### Render with D3.js

```javascript
const graph = {
  nodes: network.nodes.map(n => ({
    id: n.doi,
    label: n.title,
    size: n.similarity_score,
    color: n.year > 2020 ? 'blue' : 'gray'
  })),
  links: network.edges.map(e => ({
    source: e.source,
    target: e.target,
    type: e.edge_type
  }))
};

// D3 force-directed layout
const simulation = d3.forceSimulation(graph.nodes)
  .force("link", d3.forceLink(graph.links).id(d => d.id))
  .force("charge", d3.forceManyBody().strength(-100))
  .force("center", d3.forceCenter(width / 2, height / 2));
```

---

## Troubleshooting

### CrossRef Local Issues

**Port 3333 title search broken**:
- ✅ **FIXED** (2025-12-06): Updated to use SQLite JSON functions
- See: `/home/ywatanabe/proj/crossref_local/docs/FASTAPI_DATABASE_FIX.md`

**Service unavailable**:
```bash
# Check database exists
ls -lh ~/proj/crossref_local/data/crossref.db

# Check service running
curl http://localhost:3333/health
```

### Citation Graph Issues

**Import error: scitex.scholar.citation_graph**:
```bash
cd ~/proj/scitex-code
pip install -e .
```

**Import error: fastapi**:
```bash
pip install fastapi uvicorn[standard] python-multipart
```

**Slow performance**:
- Enable caching (default: on)
- Reduce `top_n` parameter
- Check database on SSD/NVMe
- Consider adding composite indexes

---

## Performance Optimization

### Database Indexes

```sql
-- Composite index for citation queries
CREATE INDEX idx_citations_composite
ON citations(citing_doi, cited_doi, citing_year);

-- JSON extraction indexes (SQLite 3.38+)
CREATE INDEX idx_title
ON works(json_extract(metadata, '$.title[0]'));

CREATE INDEX idx_year
ON works(json_extract(metadata, '$.published.date-parts[0][0]'));
```

### Caching Strategy

**Django (scitex.ai)**:
- Backend: Redis
- TTL: 1 hour
- Keys: `citation_graph:{hash(doi:top_n:weights)}`

**FastAPI (port 3334)**:
- Backend: In-memory LRU
- Size: 1000 items
- TTL: 1 hour (configurable)

---

## Files and Locations

### Core Implementation

```
~/proj/scitex-code/src/scitex/scholar/citation_graph/
├── __init__.py
├── builder.py          # CitationGraphBuilder
├── database.py         # SQL query optimization
├── models.py           # Data models
├── example.py          # Usage examples
└── README.md

~/proj/crossref_local/
├── data/
│   └── crossref.db     # 1.2TB database
├── docs/
│   ├── FASTAPI_DATABASE_FIX.md
│   └── ...
└── .dev/
    ├── experiment_01_citation_extraction.py
    ├── experiment_02_cocitation_similarity.py
    ├── experiment_03_bibliographic_coupling.py
    ├── experiment_04_graph_network.py
    ├── EXPERIMENT_SUMMARY.md
    └── IMPLEMENTATION_SUMMARY.md
```

### Services

```
~/proj/scitex-cloud/

# CrossRef Local (Port 3333)
deployment/docker/crossref_local/
├── server.py           # FastAPI app
├── database.py         # Database access (FIXED)
├── models.py
├── config.py
└── README.md

# Citation Graph FastAPI (Port 3334)
deployment/docker/citation_graph/
├── server.py           # FastAPI app
├── service.py          # Business logic + cache
├── models.py
├── config.py
├── README.md
└── SETUP.md

# Citation Graph Django Integration
apps/scholar_app/
├── services/citation_graph/
│   ├── service.py
│   ├── README.md
│   ├── CONFIG.md
│   └── IMPLEMENTATION.md
├── api/
│   └── citation_graph.py
└── urls.py
```

---

## Dependencies

### Project Requirements

Added to `~/proj/scitex-cloud/requirements.txt`:
```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6
```

### scitex-code Installation

```bash
cd ~/proj/scitex-code
pip install -e .
```

---

## Testing & Validation

### Experiments Validated (All Passed ✅)

1. **Citation Extraction** - 0.1ms forward, 3.3s reverse
2. **Co-citation Similarity** - 3.2s per query
3. **Bibliographic Coupling** - 25s (needs optimization)
4. **Full Network Building** - ~30s for 20 papers

See: `/home/ywatanabe/proj/crossref_local/.dev/EXPERIMENT_SUMMARY.md`

### Test Commands

```bash
# Test CrossRef Local
curl "http://localhost:3333/api/search/?doi=10.1038/s41586-020-2008-3"

# Test Citation Graph (FastAPI)
curl "http://localhost:3334/api/network/?doi=10.1038/s41586-020-2008-3&top_n=20"

# Test Citation Graph (Django)
curl "http://localhost:8000/api/scholar/citation-graph/health/"
```

---

## Next Steps

### Phase 1: Core Implementation ✅
- ✅ Validate citation data extraction
- ✅ Implement similarity algorithms
- ✅ Create citation graph module (scitex-code)
- ✅ Build FastAPI microservice
- ✅ Integrate with Django

### Phase 2: Production Deployment ⏳
- [ ] Install FastAPI dependencies in Docker
- [ ] Add citation_graph service to docker-compose
- [ ] Deploy to NAS
- [ ] Performance testing
- [ ] Monitoring setup

### Phase 3: Frontend Visualization ⏳
- [ ] D3.js graph viewer
- [ ] Interactive controls (zoom, pan, filter)
- [ ] Paper detail popup
- [ ] Integration in scholar UI

### Phase 4: Optimization 🔮
- [ ] Database composite indexes
- [ ] Redis caching for Django
- [ ] Async/background processing (Celery)
- [ ] Pre-compute popular papers

---

## Summary

**Status**: Citation graph implementation complete (backend)

**Available via**:
- ✅ Django REST API: https://scitex.ai/api/scholar/citation-graph/
- ✅ FastAPI microservice: http://localhost:3334/api/ (code ready)
- ✅ Python library: `scitex.scholar.citation_graph`

**Database**:
- ✅ 1.2TB SQLite with 167M+ works, 47M+ citations
- ✅ All search types working (DOI, title, year, authors)

**Performance**:
- ~30s uncached, <50ms cached (20-paper network)

**Documentation**: Complete for all components

**Next**: Install dependencies, deploy, build frontend visualization

<!-- EOF -->
