# CrossRef Local Docker Architecture

**Author**: Claude Code
**Date**: 2025-12-03
**Status**: Design Phase

## Docker Service Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Docker Compose                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────┐    ┌────────────────────┐  │
│  │  Django/Daphne   │◄──►│ CrossRef Local API │  │
│  │  (Port 8000)     │    │  (Port 3333)       │  │
│  └────────┬─────────┘    └─────────┬──────────┘  │
│           │                         │              │
│           │                         │              │
│  ┌────────▼─────────┐    ┌─────────▼──────────┐  │
│  │   PostgreSQL     │    │  CrossRef SQLite   │  │
│  │   (Port 5432)    │    │  (NAS Volume)      │  │
│  └──────────────────┘    └────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Directory Structure

```
scitex-cloud/
├── deployment/
│   ├── docker/
│   │   ├── docker_dev/
│   │   │   └── docker-compose.yml          # Development config
│   │   ├── docker_nas/
│   │   │   └── docker-compose.yml          # NAS/Production config
│   │   └── crossref_local/                 # NEW: CrossRef service
│   │       ├── Dockerfile
│   │       ├── requirements.txt
│   │       ├── server.py                   # FastAPI server
│   │       ├── database.py                 # SQLite queries
│   │       ├── models.py                   # Response models
│   │       └── config.py                   # Configuration
│   └── ...
├── apps/
│   └── scholar_app/
│       └── integrations/
│           └── crossref_local_client.py    # Django client
└── ...
```

## Implementation

### 1. CrossRef Local API Service

#### Dockerfile

```dockerfile
# deployment/docker/crossref_local/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3333/health || exit 1

# Expose port
EXPOSE 3333

# Run server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3333", "--workers", "4"]
```

#### requirements.txt

```txt
# deployment/docker/crossref_local/requirements.txt

fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
aiofiles==23.2.1
cachetools==5.3.2
redis==5.0.1
```

#### FastAPI Server

```python
# deployment/docker/crossref_local/server.py

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
import logging

from database import CrossRefDatabase
from models import (
    PaperMetadata,
    CitationGraph,
    JournalMetrics,
    SearchResponse,
    HealthResponse,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize app
app = FastAPI(
    title="CrossRef Local API",
    description="Fast local CrossRef database API",
    version="1.0.0",
)

# Initialize database connection
db = CrossRefDatabase()


@app.get("/", response_model=dict)
async def root():
    """API root endpoint"""
    return {
        "name": "CrossRef Local API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "/api/search/",
            "/api/citations/",
            "/api/journal/",
            "/api/batch/",
            "/api/stats/",
            "/health",
        ],
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Docker/Kubernetes"""
    try:
        stats = db.get_database_stats()
        return HealthResponse(
            status="healthy",
            database_connected=True,
            total_papers=stats["total_papers"],
            database_size_mb=stats["size_mb"],
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.get("/api/search/", response_model=SearchResponse)
async def search_papers(
    doi: Optional[str] = None,
    title: Optional[str] = None,
    year: Optional[int] = None,
    authors: Optional[str] = None,
    limit: int = Query(default=10, le=100),
):
    """
    Search for papers in local CrossRef database

    Priority: DOI > (Title + Year + Authors)
    """
    try:
        if doi:
            # Direct DOI lookup (fastest)
            result = db.get_by_doi(doi)
            if result:
                return SearchResponse(results=[result], total=1, query_time_ms=0)
            return SearchResponse(results=[], total=0, query_time_ms=0)

        if title or authors or year:
            # Full-text search
            results = db.search_by_metadata(
                title=title,
                year=year,
                authors=authors,
                limit=limit
            )
            return SearchResponse(
                results=results,
                total=len(results),
                query_time_ms=0
            )

        raise HTTPException(
            status_code=400,
            detail="Must provide at least one search parameter"
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/citations/", response_model=CitationGraph)
async def get_citations(
    doi: str,
    depth: int = Query(default=1, ge=1, le=3),
    include_references: bool = True,
    include_citations: bool = True,
):
    """
    Get citation graph for a paper

    Args:
        doi: Paper DOI
        depth: Graph traversal depth (1-3)
        include_references: Include papers this one cites
        include_citations: Include papers citing this one
    """
    try:
        graph = db.get_citation_graph(
            doi=doi,
            depth=depth,
            include_references=include_references,
            include_citations=include_citations,
        )
        return graph
    except Exception as e:
        logger.error(f"Citation graph error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/journal/", response_model=JournalMetrics)
async def get_journal_info(
    issn: Optional[str] = None,
    name: Optional[str] = None,
):
    """Get journal information and metrics"""
    try:
        if issn:
            journal = db.get_journal_by_issn(issn)
        elif name:
            journal = db.get_journal_by_name(name)
        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide issn or name"
            )

        if not journal:
            raise HTTPException(status_code=404, detail="Journal not found")

        return journal
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Journal lookup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/batch/", response_model=List[PaperMetadata])
async def batch_lookup(dois: List[str]):
    """Batch DOI lookup (max 100 per request)"""
    if len(dois) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 DOIs per batch request"
        )

    try:
        results = db.batch_get_by_dois(dois)
        return results
    except Exception as e:
        logger.error(f"Batch lookup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/")
async def get_database_stats():
    """Get database statistics"""
    try:
        return db.get_database_stats()
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3333)
```

#### Database Module

```python
# deployment/docker/crossref_local/database.py

import sqlite3
import json
import os
from typing import Optional, List, Dict
from pathlib import Path
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class CrossRefDatabase:
    """SQLite database interface for local CrossRef data"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
                    Defaults to CROSSREF_DB_PATH environment variable
        """
        self.db_path = db_path or os.getenv(
            "CROSSREF_DB_PATH",
            "/data/crossref.db"
        )

        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        logger.info(f"Connected to CrossRef database: {self.db_path}")

        # Test connection
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM works")
            count = cursor.fetchone()[0]
            logger.info(f"Database contains {count:,} papers")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Access columns by name
        try:
            yield conn
        finally:
            conn.close()

    def get_by_doi(self, doi: str) -> Optional[Dict]:
        """Get paper metadata by DOI"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM works WHERE doi = ? LIMIT 1",
                (doi,)
            )
            row = cursor.fetchone()

            if row:
                return self._row_to_dict(row)
            return None

    def search_by_metadata(
        self,
        title: Optional[str] = None,
        year: Optional[int] = None,
        authors: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Search papers by metadata"""
        query = "SELECT * FROM works WHERE 1=1"
        params = []

        if title:
            query += " AND title LIKE ?"
            params.append(f"%{title}%")

        if year:
            query += " AND year = ?"
            params.append(year)

        if authors:
            query += " AND authors LIKE ?"
            params.append(f"%{authors}%")

        query += f" LIMIT {limit}"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_dict(row) for row in rows]

    def get_citation_graph(
        self,
        doi: str,
        depth: int = 1,
        include_references: bool = True,
        include_citations: bool = True,
    ) -> Dict:
        """Build citation graph for a paper"""
        nodes = {}
        edges = []

        # Get root paper
        root = self.get_by_doi(doi)
        if not root:
            return {"nodes": [], "edges": []}

        nodes[doi] = root

        # Get references (papers this one cites)
        if include_references:
            refs = self._get_references(doi, depth)
            nodes.update(refs["nodes"])
            edges.extend(refs["edges"])

        # Get citations (papers citing this one)
        if include_citations:
            cites = self._get_citations(doi, depth)
            nodes.update(cites["nodes"])
            edges.extend(cites["edges"])

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
        }

    def _get_references(self, doi: str, depth: int) -> Dict:
        """Get papers that this paper cites"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT cited_doi, w.*
                FROM references r
                LEFT JOIN works w ON r.cited_doi = w.doi
                WHERE r.citing_doi = ?
                LIMIT 100
                """,
                (doi,)
            )
            rows = cursor.fetchall()

            nodes = {}
            edges = []

            for row in rows:
                cited_doi = row["cited_doi"]
                if cited_doi:
                    edges.append({
                        "source": doi,
                        "target": cited_doi,
                        "type": "cites",
                    })

                    # Add node if we have metadata
                    if row["title"]:
                        nodes[cited_doi] = self._row_to_dict(row)

            return {"nodes": nodes, "edges": edges}

    def _get_citations(self, doi: str, depth: int) -> Dict:
        """Get papers that cite this paper"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT citing_doi, w.*
                FROM references r
                LEFT JOIN works w ON r.citing_doi = w.doi
                WHERE r.cited_doi = ?
                LIMIT 100
                """,
                (doi,)
            )
            rows = cursor.fetchall()

            nodes = {}
            edges = []

            for row in rows:
                citing_doi = row["citing_doi"]
                if citing_doi:
                    edges.append({
                        "source": citing_doi,
                        "target": doi,
                        "type": "cites",
                    })

                    # Add node if we have metadata
                    if row["title"]:
                        nodes[citing_doi] = self._row_to_dict(row)

            return {"nodes": nodes, "edges": edges}

    def get_journal_by_issn(self, issn: str) -> Optional[Dict]:
        """Get journal info by ISSN"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM journals WHERE issn = ? LIMIT 1",
                (issn,)
            )
            row = cursor.fetchone()

            if row:
                return self._row_to_dict(row)
            return None

    def get_journal_by_name(self, name: str) -> Optional[Dict]:
        """Get journal info by name"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM journals WHERE name LIKE ? LIMIT 1",
                (f"%{name}%",)
            )
            row = cursor.fetchone()

            if row:
                return self._row_to_dict(row)
            return None

    def batch_get_by_dois(self, dois: List[str]) -> List[Dict]:
        """Batch fetch papers by DOIs"""
        placeholders = ",".join("?" * len(dois))
        query = f"SELECT * FROM works WHERE doi IN ({placeholders})"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, dois)
            rows = cursor.fetchall()

            return [self._row_to_dict(row) for row in rows]

    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Total papers
            cursor.execute("SELECT COUNT(*) FROM works")
            total_papers = cursor.fetchone()[0]

            # Database size
            db_size = Path(self.db_path).stat().st_size / (1024 * 1024)  # MB

            # Year range
            cursor.execute("SELECT MIN(year), MAX(year) FROM works")
            min_year, max_year = cursor.fetchone()

            return {
                "total_papers": total_papers,
                "size_mb": round(db_size, 2),
                "year_range": [min_year, max_year],
                "database_path": self.db_path,
            }

    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """Convert SQLite row to dictionary"""
        return dict(row)
```

#### Pydantic Models

```python
# deployment/docker/crossref_local/models.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class PaperMetadata(BaseModel):
    """Paper metadata response"""
    doi: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    issn: Optional[str] = None
    abstract: Optional[str] = None
    citation_count: Optional[int] = 0
    references_count: Optional[int] = 0

    class Config:
        extra = "allow"  # Allow additional fields


class CitationEdge(BaseModel):
    """Citation graph edge"""
    source: str  # DOI
    target: str  # DOI
    type: str = "cites"  # or "cited_by"


class CitationGraph(BaseModel):
    """Citation graph response"""
    nodes: List[PaperMetadata]
    edges: List[CitationEdge]


class JournalMetrics(BaseModel):
    """Journal metrics response"""
    issn: str
    name: str
    publisher: Optional[str] = None
    impact_factor: Optional[float] = None
    total_papers: Optional[int] = None


class SearchResponse(BaseModel):
    """Search results response"""
    results: List[PaperMetadata]
    total: int
    query_time_ms: float


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    database_connected: bool
    total_papers: int
    database_size_mb: float
```

### 2. Docker Compose Integration

#### Development Environment

```yaml
# deployment/docker/docker_dev/docker-compose.yml

services:
  django:
    # ... existing Django config ...
    depends_on:
      - postgres
      - crossref-local  # Add dependency
    environment:
      - CROSSREF_LOCAL_API_URL=http://crossref-local:3333

  postgres:
    # ... existing PostgreSQL config ...

  # NEW: CrossRef Local API Service
  crossref-local:
    build: ../crossref_local/
    container_name: scitex-crossref-local-dev
    ports:
      - "3333:3333"
    volumes:
      # Mount local CrossRef database (read-only)
      - ${CROSSREF_DB_PATH:-./data/crossref.db}:/data/crossref.db:ro
    environment:
      - CROSSREF_DB_PATH=/data/crossref.db
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3333/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    networks:
      - scitex-network

networks:
  scitex-network:
    driver: bridge
```

#### NAS/Production Environment

```yaml
# deployment/docker/docker_nas/docker-compose.yml

services:
  django:
    # ... existing Django config ...
    depends_on:
      - postgres
      - crossref-local
    environment:
      - CROSSREF_LOCAL_API_URL=http://crossref-local:3333

  postgres:
    # ... existing PostgreSQL config ...

  # CrossRef Local API Service (Production)
  crossref-local:
    build: ../crossref_local/
    container_name: scitex-crossref-local-nas
    ports:
      - "3333:3333"
    volumes:
      # Mount NAS CrossRef database (read-only)
      - /mnt/nas_ug/crossref_local/data/crossref.db:/data/crossref.db:ro
    environment:
      - CROSSREF_DB_PATH=/data/crossref.db
      - LOG_LEVEL=INFO
      - WORKERS=8  # More workers for production
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3333/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    networks:
      - scitex-network

networks:
  scitex-network:
    driver: bridge
```

### 3. Django Client Integration

```python
# apps/scholar_app/integrations/crossref_local_client.py

import requests
from typing import Optional, List, Dict
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class CrossRefLocalClient:
    """
    Django client for CrossRef Local API

    Usage:
        client = CrossRefLocalClient()
        paper = client.search_by_doi("10.1038/nature12345")
    """

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or settings.CROSSREF_LOCAL_API_URL
        self.timeout = 10  # seconds
        self.cache_prefix = "crossref_local"

    def search_by_doi(self, doi: str) -> Optional[Dict]:
        """Search by DOI with caching"""
        cache_key = f"{self.cache_prefix}:doi:{doi}"

        # Check cache first
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            response = requests.get(
                f"{self.api_url}/api/search/",
                params={"doi": doi},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if data["results"]:
                result = data["results"][0]
                # Cache for 1 hour
                cache.set(cache_key, result, 3600)
                return result

            return None

        except Exception as e:
            logger.warning(f"CrossRef Local search failed: {e}")
            return None

    def get_citation_graph(
        self,
        doi: str,
        depth: int = 1,
        include_references: bool = True,
        include_citations: bool = True,
    ) -> Dict:
        """Get citation graph"""
        try:
            response = requests.get(
                f"{self.api_url}/api/citations/",
                params={
                    "doi": doi,
                    "depth": depth,
                    "include_references": include_references,
                    "include_citations": include_citations,
                },
                timeout=self.timeout * 2,  # Longer timeout for graphs
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Citation graph fetch failed: {e}")
            return {"nodes": [], "edges": []}

    def health_check(self) -> Dict:
        """Check if service is healthy"""
        try:
            response = requests.get(
                f"{self.api_url}/health",
                timeout=5,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
```

### 4. Settings Configuration

```python
# config/settings/settings_shared.py

# CrossRef Local API Configuration
CROSSREF_LOCAL_API_URL = os.getenv(
    "CROSSREF_LOCAL_API_URL",
    "http://localhost:3333"
)

# Cache configuration for CrossRef data
CACHES = {
    # ... existing cache configs ...

    'crossref_local': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://redis:6379/2',
        'OPTIONS': {
            'db': 2,
        },
        'TIMEOUT': 3600,  # 1 hour default
    }
}
```

## Makefile Commands

```makefile
# Makefile additions

.PHONY: crossref-build crossref-up crossref-down crossref-logs crossref-health

# Build CrossRef Local service
crossref-build:
	docker-compose -f deployment/docker/docker_$(ENV)/docker-compose.yml \
		build crossref-local

# Start CrossRef Local service
crossref-up:
	docker-compose -f deployment/docker/docker_$(ENV)/docker-compose.yml \
		up -d crossref-local

# Stop CrossRef Local service
crossref-down:
	docker-compose -f deployment/docker/docker_$(ENV)/docker-compose.yml \
		stop crossref-local

# View CrossRef Local logs
crossref-logs:
	docker-compose -f deployment/docker/docker_$(ENV)/docker-compose.yml \
		logs -f crossref-local

# Health check
crossref-health:
	curl http://localhost:3333/health | jq
```

## Development Workflow

```bash
# 1. Build the CrossRef service
make ENV=dev crossref-build

# 2. Start it
make ENV=dev crossref-up

# 3. Check health
make ENV=dev crossref-health

# 4. View logs
make ENV=dev crossref-logs

# 5. Test from Django
docker exec -it scitex-django-dev python manage.py shell
>>> from apps.scholar_app.integrations.crossref_local_client import CrossRefLocalClient
>>> client = CrossRefLocalClient()
>>> result = client.search_by_doi("10.1038/nature12345")
>>> print(result)
```

## Testing Strategy

```python
# tests/integration/scholar/test_crossref_local.py

import pytest
from apps.scholar_app.integrations.crossref_local_client import CrossRefLocalClient


@pytest.mark.integration
class TestCrossRefLocalDocker:
    """Test CrossRef Local API via Docker"""

    def test_service_is_running(self):
        """Verify service is accessible"""
        client = CrossRefLocalClient()
        health = client.health_check()
        assert health["status"] == "healthy"
        assert health["database_connected"] is True

    def test_search_by_doi(self):
        """Test DOI search"""
        client = CrossRefLocalClient()
        result = client.search_by_doi("10.1038/nature12345")
        assert result is not None
        assert "title" in result

    def test_citation_graph(self):
        """Test citation graph retrieval"""
        client = CrossRefLocalClient()
        graph = client.get_citation_graph("10.1038/nature12345", depth=1)
        assert "nodes" in graph
        assert "edges" in graph
```

## Monitoring

```yaml
# deployment/docker/docker_nas/docker-compose.yml additions

services:
  crossref-local:
    # ... existing config ...
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    labels:
      - "com.scitex.service=crossref-local"
      - "com.scitex.environment=${ENV}"
```

## Benefits of Docker Architecture

✅ **Isolation** - Separate process, resource limits, independent failures
✅ **Scalability** - Can run multiple instances, load balancing
✅ **Deployment** - Same setup dev/prod, easy rollback
✅ **Monitoring** - Docker logs, health checks, resource metrics
✅ **Security** - Read-only database mount, network isolation
✅ **Maintenance** - Update service without Django restart

## Next Steps

1. **Create the Docker service** - Implement FastAPI server
2. **Test locally** - Verify with sample database
3. **Deploy to NAS** - Add to production docker-compose
4. **Integrate with Django** - Update scholar_app to use it
5. **Monitor** - Set up logging and metrics

---

**Ready to implement?** We can start with Phase 1: Building the Docker service.
