# Citation Graph Service - API Documentation

REST API for building and analyzing citation networks using CrossRef data.

## Base URL

```
https://scitex.ai/api/scholar/citation-graph/
```

## Endpoints

### 1. Build Citation Network

Build a complete citation network graph for a paper.

**Endpoint:** `GET /network/`

**Parameters:**
- `doi` (required): DOI of the seed paper
- `top_n` (optional): Number of similar papers (default: 20, max: 50)
- `weight_coupling` (optional): Bibliographic coupling weight (default: 2.0)
- `weight_cocitation` (optional): Co-citation weight (default: 2.0)
- `weight_direct` (optional): Direct citation weight (default: 1.0)
- `no_cache` (optional): Skip cache (default: false)

**Rate Limit:** 50 requests/hour

**Example Request:**
```bash
curl "https://scitex.ai/api/scholar/citation-graph/network/?doi=10.1038/s41586-020-2008-3&top_n=20"
```

**Example Response:**
```json
{
  "seed": "10.1038/s41586-020-2008-3",
  "nodes": [
    {
      "id": "10.1038/s41586-020-2008-3",
      "title": "A Randomized Controlled Trial...",
      "year": 2020,
      "authors": ["Smith J", "Jones A"],
      "journal": "Nature",
      "similarity_score": 100.0
    },
    ...
  ],
  "edges": [
    {
      "source": "10.1038/...",
      "target": "10.1016/...",
      "type": "cites",
      "weight": 1.0
    },
    ...
  ],
  "metadata": {
    "top_n": 20,
    "weights": {
      "coupling": 2.0,
      "cocitation": 2.0,
      "direct": 1.0
    },
    "cached": false
  }
}
```

---

### 2. Get Related Papers

Get a simple list of papers related to a given paper (lightweight).

**Endpoint:** `GET /related/`

**Parameters:**
- `doi` (required): DOI of the paper
- `limit` (optional): Number of papers (default: 10, max: 30)
- `no_cache` (optional): Skip cache (default: false)

**Rate Limit:** 50 requests/hour

**Example Request:**
```bash
curl "https://scitex.ai/api/scholar/citation-graph/related/?doi=10.1038/s41586-020-2008-3&limit=10"
```

**Example Response:**
```json
{
  "doi": "10.1038/s41586-020-2008-3",
  "count": 10,
  "related": [
    {
      "id": "10.1016/j.cell.2019.11.025",
      "title": "Understanding Cellular Mechanisms...",
      "year": 2019,
      "authors": ["Johnson M", "Williams K"],
      "journal": "Cell",
      "similarity_score": 42.5
    },
    ...
  ]
}
```

---

### 3. Get Paper Summary

Get summary information for a single paper (no rate limiting).

**Endpoint:** `GET /paper/`

**Parameters:**
- `doi` (required): DOI of the paper

**Rate Limit:** None

**Example Request:**
```bash
curl "https://scitex.ai/api/scholar/citation-graph/paper/?doi=10.1038/s41586-020-2008-3"
```

**Example Response:**
```json
{
  "doi": "10.1038/s41586-020-2008-3",
  "title": "A Randomized Controlled Trial...",
  "year": 2020,
  "authors": ["Smith J", "Jones A", "Brown R"],
  "journal": "Nature",
  "reference_count": 45,
  "citation_count": 123,
  "cached": false
}
```

---

### 4. Health Check

Check service health status.

**Endpoint:** `GET /health/`

**Parameters:** None

**Rate Limit:** None

**Example Request:**
```bash
curl "https://scitex.ai/api/scholar/citation-graph/health/"
```

**Example Response:**
```json
{
  "status": "healthy",
  "database": "/path/to/crossref.db",
  "database_accessible": true
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "DOI parameter required"
}
```

### 404 Not Found
```json
{
  "error": "Paper not found in database"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Request was throttled. Expected available in 3600 seconds."
}
```

### 500 Internal Server Error
```json
{
  "error": "Failed to build citation network: ..."
}
```

### 503 Service Unavailable
```json
{
  "error": "Citation graph service unavailable - database not configured"
}
```

---

## Similarity Metrics

The citation graph uses three metrics to calculate paper similarity:

### 1. **Bibliographic Coupling** (weight: 2.0)
Papers are related if they cite similar references.
- Algorithm: Count shared references between papers
- Use case: Find papers addressing similar problems/methods

### 2. **Co-citation** (weight: 2.0)
Papers are related if they are frequently cited together.
- Algorithm: Find papers that appear together in reference lists
- Use case: Find foundational/seminal works in the same field

### 3. **Direct Citations** (weight: 1.0)
Papers directly citing or cited by the seed paper.
- Use case: Find immediately related work

**Combined Score:** `similarity_score = (coupling * 2.0) + (cocitation * 2.0) + (direct * 1.0)`

---

## Caching

- Network graphs are cached for 1 hour
- Paper summaries are cached for 1 hour
- Use `no_cache=true` to force rebuild
- Cache key includes all parameters

---

## Performance

Typical response times (with 47M+ citations):

| Endpoint | Cached | Uncached | Status |
|----------|--------|----------|--------|
| `/network/` (20 papers) | <50ms | ~30s | ⚡ Cached recommended |
| `/related/` (10 papers) | <50ms | ~15s | ✓ Good |
| `/paper/` | <50ms | <5s | ✓ Fast |
| `/health/` | <100ms | <5s | ✓ Fast |

---

## Configuration

### Django Settings

Add to your `settings.py`:

```python
# CrossRef Database Path
CROSSREF_DB_PATH = '/home/ywatanabe/proj/crossref_local/data/crossref.db'

# Or use environment variable
import os
CROSSREF_DB_PATH = os.getenv(
    'CROSSREF_DB_PATH',
    '/home/ywatanabe/proj/crossref_local/data/crossref.db'
)
```

### Environment Variables

```bash
export CROSSREF_DB_PATH=/path/to/crossref.db
```

---

## Frontend Integration

### D3.js Force-Directed Graph

```javascript
// Fetch network
fetch(`/api/scholar/citation-graph/network/?doi=${doi}&top_n=20`)
  .then(res => res.json())
  .then(data => {
    // data.nodes and data.edges ready for D3.js
    const simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(data.edges).id(d => d.id))
      .force("charge", d3.forceManyBody())
      .force("center", d3.forceCenter(width / 2, height / 2));
  });
```

### Vis.js Network

```javascript
fetch(`/api/scholar/citation-graph/network/?doi=${doi}`)
  .then(res => res.json())
  .then(data => {
    const network = new vis.Network(container, {
      nodes: data.nodes,
      edges: data.edges
    }, options);
  });
```

---

## Testing

```bash
# Health check
curl http://localhost:8000/api/scholar/citation-graph/health/

# Get paper summary
curl "http://localhost:8000/api/scholar/citation-graph/paper/?doi=10.1038/s41586-020-2008-3"

# Get related papers
curl "http://localhost:8000/api/scholar/citation-graph/related/?doi=10.1038/s41586-020-2008-3&limit=5"

# Build network
curl "http://localhost:8000/api/scholar/citation-graph/network/?doi=10.1038/s41586-020-2008-3&top_n=10"
```

---

## References

- Connected Papers (inspiration): https://www.connectedpapers.com/
- Co-citation: Small, H. (1973). Co-citation in the scientific literature
- Bibliographic coupling: Kessler, M. M. (1963). Bibliographic coupling
