# CrossRef Local Database Integration Plan

**Author**: Claude Code
**Date**: 2025-12-03
**Status**: Design Phase

## Executive Summary

Integrate the local CrossRef SQLite database (on NAS) with the Scholar module to enable:
1. **Fast local searches** - No API rate limits, instant responses
2. **Impact factor calculation** - Computed from citation data (avoiding Clarivate licensing)
3. **Citation graphs** - Build and visualize paper relationships
4. **Connected Papers** - Discover related research through citation networks
5. **Metadata enrichment** - High-quality paper metadata from CrossRef

## Current Architecture

### Existing Components

#### 1. **scitex-code** (Python Package)
- `CrossRefLocalEngine` - Queries local API at `http://127.0.0.1:3333`
- `CrossRefEngine` - Public CrossRef API client
- `ScholarEngine` - Aggregates metadata from multiple sources
- `ImpactFactorEngine` - Currently uses JCR database (licensing issue)
- Impact Factor Estimation - Calculates from OpenAlex/Crossref/Semantic Scholar APIs

#### 2. **Django Scholar App** (`apps/scholar_app/`)
- **Models**:
  - `SearchIndex` - Main paper model (DOI, citations, metadata)
  - `Citation` - Citation relationships (citing_paper → cited_paper)
  - `Journal` - Journal metadata with `impact_factor` field
  - `Author` - Author information with h-index, citations
- **Services**: search, bibtex, repository
- **Integrations**: scitex package integration layer

#### 3. **Local CrossRef Database** (NAS)
- Location: `/home/ywatanabe/crossref_local/` or `/mnt/nas_ug/crossref_local/`
- Components:
  - `dois2sqlite/` - DOI to SQLite converter
  - `impact_factor/` - Impact factor calculations
  - `labs-data-file-api/` - CrossRef Labs API
  - `data/` - The actual SQLite database(s)

### Data Flow (Current)

```
User Query
    ↓
Django Scholar App
    ↓
scitex.scholar.ScholarEngine
    ↓
┌─────────────────┬──────────────────┬──────────────┐
│ CrossRefEngine  │ SemanticScholar  │ PubMed       │
│ (Public API)    │ (Public API)     │ (Public API) │
└─────────────────┴──────────────────┴──────────────┘
    ↓
Aggregate & Store in Django Models
```

## Proposed Architecture

### New Data Flow (Local-First)

```
User Query
    ↓
Django Scholar App
    ↓
scitex.scholar.ScholarEngine
    ↓
┌────────────────────┐
│ CrossRefLocalEngine│ ← Primary (Fast, Unlimited)
│ (Local SQLite)     │
└────────┬───────────┘
         │ (if not found or enrichment needed)
         ↓
┌─────────────────┬──────────────────┬──────────────┐
│ CrossRefEngine  │ SemanticScholar  │ PubMed       │
│ (Public API)    │ (Public API)     │ (Public API) │
└─────────────────┴──────────────────┴──────────────┘
    ↓
Aggregate & Store in Django Models
    ↓
┌──────────────────────────────────┐
│ Citation Graph & Impact Factors  │
└──────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Local CrossRef API Server (CRITICAL)

**Goal**: Make the local CrossRef SQLite database accessible via HTTP API

#### 1.1 Understand Current Database Schema

```bash
# Check what's in the crossref_local directory
ls -la /mnt/nas_ug/crossref_local/
cd /mnt/nas_ug/crossref_local/data/

# Inspect SQLite database schema
sqlite3 crossref.db ".schema"
sqlite3 crossref.db ".tables"
```

**Key Questions**:
- What tables exist?
- How are DOIs indexed?
- Is citation data available?
- How are journals identified (ISSN)?

#### 1.2 Build Local API Server

**Location**: `apps/scholar_app/services/crossref_local/`

**Components**:

```python
# apps/scholar_app/services/crossref_local/server.py
"""
FastAPI or Django view serving local CrossRef data
Port: 3333 (matches CrossRefLocalEngine.api_url)
"""

class CrossRefLocalAPI:
    def __init__(self, db_path="/mnt/nas_ug/crossref_local/data/crossref.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)

    # Endpoints:
    # GET /api/search/?doi=10.1038/nature12345
    # GET /api/search/?title=deep+learning&year=2015
    # GET /api/citations/?doi=10.1038/nature12345
    # GET /api/journal/?issn=0028-0836
```

**Endpoints to Implement**:

| Endpoint | Method | Parameters | Returns |
|----------|--------|------------|---------|
| `/api/search/` | GET | `doi`, `title`, `year`, `authors` | Paper metadata (CrossRef format) |
| `/api/citations/` | GET | `doi` | List of citing/cited papers |
| `/api/journal/` | GET | `issn`, `name` | Journal metadata |
| `/api/batch/` | POST | List of DOIs | Batch metadata |
| `/api/stats/` | GET | - | Database statistics |

**Startup**:
```bash
# Add to docker-compose or systemd
# Run on NAS or accessible server
python apps/scholar_app/services/crossref_local/server.py
# Or: uvicorn apps.scholar_app.services.crossref_local.server:app --port 3333
```

### Phase 2: Impact Factor Calculation from Local Data

**Goal**: Calculate journal impact factors from citation data (no Clarivate license needed)

#### 2.1 Citation Data Extraction

```python
# apps/scholar_app/services/crossref_local/impact_factor_calculator.py

class LocalImpactFactorCalculator:
    """
    Calculate impact factors from local CrossRef citation data.

    Classical 2-Year IF Formula:
    IF(year) = Citations in year to papers from (year-1, year-2)
               / Papers published in (year-1, year-2)
    """

    def calculate_journal_if(self, issn: str, year: int) -> float:
        # Query local database for:
        # 1. Papers published in (year-1, year-2) with this ISSN
        # 2. Citations to those papers made in year
        # 3. Calculate ratio
        pass

    def batch_calculate_all_journals(self, year: int):
        # One-time calculation for all journals
        # Store in Django Journal.impact_factor
        pass
```

#### 2.2 Django Management Command

```python
# apps/scholar_app/management/commands/calculate_impact_factors.py

class Command(BaseCommand):
    """
    python manage.py calculate_impact_factors --year 2023
    """
    def handle(self, *args, **options):
        year = options['year']
        calculator = LocalImpactFactorCalculator()
        calculator.batch_calculate_all_journals(year)
```

#### 2.3 Caching Strategy

```python
# Store in Django Journal model
class Journal(models.Model):
    impact_factor = models.DecimalField(max_digits=6, decimal_places=3)
    impact_factor_year = models.IntegerField()  # Add this field
    impact_factor_calculated_at = models.DateTimeField()  # Add this
    impact_factor_source = models.CharField()  # "local_crossref" or "jcr"
```

**Update Schedule**:
- Calculate once per year (when new year's data available)
- Store in database for fast lookups
- Optionally recalculate quarterly for recent papers

### Phase 3: Citation Graph Infrastructure

**Goal**: Build and query citation relationships for Connected Papers functionality

#### 3.1 Populate Citation Model from Local Data

```python
# apps/scholar_app/services/crossref_local/citation_importer.py

class CitationImporter:
    def import_citations_for_paper(self, doi: str):
        """
        Get citing/cited papers from local CrossRef DB
        Create Citation entries in Django
        """
        # Get references (papers this one cites)
        references = self.api.get_references(doi)

        # Get citations (papers citing this one)
        citations = self.api.get_citations(doi)

        # Store in Citation model
        for ref_doi in references:
            Citation.objects.get_or_create(
                citing_paper=paper,
                cited_paper=get_or_create_paper(ref_doi)
            )
```

#### 3.2 Citation Graph Query API

```python
# apps/scholar_app/api/citations.py

@api_view(['GET'])
def get_citation_graph(request, doi):
    """
    GET /api/scholar/citations/graph/?doi=10.1038/xxx&depth=2

    Returns:
    {
        "nodes": [
            {"id": "doi:10.1038/xxx", "title": "...", "year": 2020, ...},
            {"id": "doi:10.1016/yyy", "title": "...", "year": 2019, ...}
        ],
        "edges": [
            {"source": "doi:10.1038/xxx", "target": "doi:10.1016/yyy", "type": "cites"}
        ]
    }
    """
    depth = request.GET.get('depth', 2)
    graph = build_citation_graph(doi, depth)
    return Response(graph)
```

#### 3.3 Graph Algorithms

```python
# apps/scholar_app/services/graph/algorithms.py

class CitationGraphAlgorithms:
    def find_related_papers(self, doi: str, limit=10):
        """
        Connected Papers algorithm:
        1. Get papers citing this one
        2. Get papers this one cites
        3. Get co-citations (papers cited by same papers)
        4. Rank by relevance (shared citations, dates, topics)
        """
        pass

    def calculate_paper_influence(self, doi: str):
        """PageRank-style influence score"""
        pass

    def find_research_lineage(self, doi: str):
        """Trace citation chain backwards"""
        pass
```

### Phase 4: Connected Papers Visualization

**Goal**: Interactive citation graph visualization like ConnectedPapers.com

#### 4.1 Frontend Components

**Location**: `apps/scholar_app/static/scholar_app/ts/citation-graph/`

```typescript
// CitationGraphVisualization.tsx
interface Node {
    id: string;
    doi: string;
    title: string;
    year: number;
    citationCount: number;
    authors: string[];
}

interface Edge {
    source: string;
    target: string;
    type: 'cites' | 'cited_by';
}

class CitationGraphVisualization {
    // Use D3.js force-directed graph
    // Or: Cytoscape.js
    // Or: vis.js

    renderGraph(nodes: Node[], edges: Edge[]) {
        // Interactive visualization
        // - Node size = citation count
        // - Color = publication year
        // - Click = show paper details
        // - Hover = show connections
    }
}
```

#### 4.2 UI Components

```html
<!-- templates/scholar_app/paper_detail.html -->
<div id="citation-graph-container">
    <div class="controls">
        <button id="expand-graph">Expand</button>
        <button id="contract-graph">Contract</button>
        <select id="layout-selector">
            <option value="force">Force-Directed</option>
            <option value="hierarchical">Hierarchical</option>
            <option value="radial">Radial</option>
        </select>
    </div>
    <svg id="citation-graph"></svg>
    <div id="graph-info">
        <h3>Selected Paper</h3>
        <div id="paper-details"></div>
    </div>
</div>
```

#### 4.3 API Integration

```typescript
// services/CitationGraphAPI.ts
class CitationGraphAPI {
    async getGraph(doi: string, depth: number = 2): Promise<Graph> {
        const response = await fetch(
            `/api/scholar/citations/graph/?doi=${doi}&depth=${depth}`
        );
        return response.json();
    }

    async getRelatedPapers(doi: string, limit: number = 10): Promise<Paper[]> {
        const response = await fetch(
            `/api/scholar/citations/related/?doi=${doi}&limit=${limit}`
        );
        return response.json();
    }
}
```

### Phase 5: Fast Search Integration

**Goal**: Use local database for primary searches, fall back to APIs

#### 5.1 Search Priority Configuration

```python
# config/settings/settings_shared.py

SCHOLAR_SEARCH_ENGINES = [
    'CrossRefLocal',     # Primary - fast, unlimited
    'SemanticScholar',   # Fallback - good citation data
    'CrossRef',          # Fallback - official but rate-limited
    'PubMed',           # Fallback - biomedical papers
]
```

#### 5.2 Search Service Update

```python
# apps/scholar_app/services/search/unified_search.py

class UnifiedSearchService:
    def search(self, query: str, filters: dict):
        results = []

        # Try local first (fast)
        local_results = self.crossref_local.search(query, filters)
        results.extend(local_results)

        # If insufficient results, try APIs
        if len(results) < filters.get('min_results', 10):
            api_results = self.api_search(query, filters)
            results.extend(api_results)

        # Deduplicate by DOI
        results = self.deduplicate_by_doi(results)

        # Store new papers in database
        for result in results:
            self.store_paper(result)

        return results
```

## Database Schema Updates

### New Fields for Journal Model

```python
# Migration: apps/scholar_app/migrations/00XX_add_impact_factor_fields.py

class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='journal',
            name='impact_factor_year',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='journal',
            name='impact_factor_calculated_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='journal',
            name='impact_factor_source',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('local_crossref', 'Local CrossRef Calculation'),
                    ('jcr', 'Journal Citation Reports'),
                    ('estimated', 'API Estimation'),
                ],
                default='local_crossref',
            ),
        ),
    ]
```

### Indexes for Citation Queries

```python
# Migration: apps/scholar_app/migrations/00XX_add_citation_indexes.py

class Migration(migrations.Migration):
    operations = [
        migrations.AddIndex(
            model_name='citation',
            index=models.Index(
                fields=['citing_paper', 'cited_paper'],
                name='citation_bidirectional_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='citation',
            index=models.Index(
                fields=['cited_paper'],  # For reverse lookup
                name='citation_cited_idx',
            ),
        ),
    ]
```

## Testing Strategy

### Unit Tests

```python
# tests/unit/scholar/test_crossref_local.py

class TestCrossRefLocalAPI:
    def test_search_by_doi(self):
        result = api.search(doi="10.1038/nature12345")
        assert result['DOI'] == "10.1038/nature12345"
        assert 'title' in result

    def test_citation_retrieval(self):
        citations = api.get_citations(doi="10.1038/nature12345")
        assert isinstance(citations, list)
        assert all('DOI' in c for c in citations)

class TestImpactFactorCalculation:
    def test_calculate_journal_if(self):
        # Mock database with known papers and citations
        if_value = calculator.calculate_journal_if("0028-0836", 2023)
        assert 40.0 < if_value < 50.0  # Nature's typical range
```

### Integration Tests

```python
# tests/integration/scholar/test_search_flow.py

class TestSearchWithLocalDB:
    def test_local_first_search(self):
        # Search should hit local DB first
        results = search_service.search("deep learning")

        # Verify local DB was queried
        assert mock_local_api.search.called

        # Verify results stored in Django
        assert SearchIndex.objects.filter(title__icontains="deep learning").exists()
```

### E2E Tests

```python
# tests/e2e/scholar/test_citation_graph.py

class TestCitationGraphVisualization:
    @pytest.mark.playwright
    def test_graph_renders(self, page):
        page.goto("/scholar/paper/10.1038/nature12345/")
        page.click("#citation-graph-tab")

        # Wait for graph to render
        graph = page.wait_for_selector("#citation-graph svg")
        assert graph.is_visible()

        # Verify nodes rendered
        nodes = page.query_selector_all(".citation-node")
        assert len(nodes) > 5
```

## Deployment Considerations

### NAS Configuration

```yaml
# docker-compose.nas.yml addition

services:
  crossref-local-api:
    build: ./apps/scholar_app/services/crossref_local/
    ports:
      - "3333:3333"
    volumes:
      - /mnt/nas_ug/crossref_local/data:/data:ro
    environment:
      - DATABASE_PATH=/data/crossref.db
    restart: unless-stopped
```

### Systemd Service (Alternative)

```ini
# /etc/systemd/system/crossref-local-api.service

[Unit]
Description=CrossRef Local API Server
After=network.target

[Service]
Type=simple
User=ywatanabe
WorkingDirectory=/home/ywatanabe/proj/scitex-cloud
ExecStart=/home/ywatanabe/proj/scitex-cloud/.venv/bin/python \
    -m apps.scholar_app.services.crossref_local.server
Restart=always

[Install]
WantedBy=multi-user.target
```

### Environment Variables

```bash
# .env.nas additions

# CrossRef Local Database
CROSSREF_LOCAL_API_URL=http://localhost:3333
CROSSREF_LOCAL_DB_PATH=/mnt/nas_ug/crossref_local/data/crossref.db

# Impact Factor Calculation
CALCULATE_IMPACT_FACTORS=true
IMPACT_FACTOR_YEAR=2023
```

## Performance Considerations

### Database Query Optimization

```sql
-- Add indexes to CrossRef SQLite database
CREATE INDEX IF NOT EXISTS idx_doi ON works(doi);
CREATE INDEX IF NOT EXISTS idx_title ON works(title);
CREATE INDEX IF NOT EXISTS idx_issn ON works(issn);
CREATE INDEX IF NOT EXISTS idx_publication_date ON works(publication_date);
CREATE INDEX IF NOT EXISTS idx_citations ON citations(citing_doi, cited_doi);
```

### Caching Strategy

```python
# Redis caching for frequently accessed papers
CACHES = {
    'crossref_local': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/2',
        'OPTIONS': {
            'db': 2,
            'parser_class': 'redis.connection.PythonParser',
            'pool_class': 'redis.BlockingConnectionPool',
        },
        'TIMEOUT': 3600 * 24,  # 1 day
    }
}
```

### Batch Processing

```python
# For initial database population
class BulkImporter:
    def import_all_papers(self, batch_size=1000):
        """Import all papers from local CrossRef DB to Django"""
        offset = 0
        while True:
            papers = self.get_papers_batch(offset, batch_size)
            if not papers:
                break

            SearchIndex.objects.bulk_create(
                [self.convert_to_django_model(p) for p in papers],
                ignore_conflicts=True,
            )
            offset += batch_size
```

## Monitoring & Maintenance

### Logging

```python
# Add structured logging
import logging
logger = logging.getLogger('scholar.crossref_local')

logger.info("CrossRef local search", extra={
    'query': query,
    'results_count': len(results),
    'response_time_ms': response_time,
    'source': 'local_database',
})
```

### Health Checks

```python
# apps/scholar_app/api/health.py

@api_view(['GET'])
def crossref_local_health(request):
    """GET /api/scholar/health/crossref-local/"""
    try:
        response = requests.get(
            f"{settings.CROSSREF_LOCAL_API_URL}/api/stats/",
            timeout=5
        )
        return Response({
            'status': 'healthy',
            'database_size': response.json()['database_size'],
            'total_papers': response.json()['total_papers'],
        })
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'error': str(e),
        }, status=503)
```

### Metrics to Track

- Search response time (local vs API)
- Cache hit rate
- Papers in local DB vs total searches
- Citation graph query performance
- Impact factor calculation time

## Timeline Estimate

| Phase | Component | Estimated Effort |
|-------|-----------|-----------------|
| 1 | Local API Server | 2-3 days |
| 2 | Impact Factor Calculation | 3-4 days |
| 3 | Citation Graph Infrastructure | 3-4 days |
| 4 | Connected Papers Visualization | 4-5 days |
| 5 | Fast Search Integration | 2-3 days |
| - | Testing & Debugging | 3-4 days |
| - | Documentation | 1-2 days |
| **Total** | | **18-25 days** |

## Success Criteria

✅ **Performance**
- Local searches < 100ms response time
- API searches fallback functional
- Citation graph queries < 500ms

✅ **Functionality**
- Impact factors calculated for major journals (>1000)
- Citation graphs render for papers with citation data
- Connected Papers algorithm finds relevant papers
- Search uses local DB as primary source

✅ **Data Quality**
- Impact factors within ±20% of official JCR values
- Citation data matches CrossRef API
- No duplicate papers in database

✅ **User Experience**
- Seamless fallback between local and API sources
- Visual citation graphs load smoothly
- Clear indication of data sources and confidence

## Next Steps

1. **Immediate**: Inspect local CrossRef SQLite database schema
2. **Priority**: Build and test local API server
3. **Parallel**: Design citation graph API while server is built
4. **Incremental**: Implement phases 1-5 sequentially
5. **Continuous**: Test each component before moving to next phase

## Questions to Resolve

1. What is the exact schema of the CrossRef SQLite database?
2. Does it contain reference data (citations)?
3. How is it updated (frequency, process)?
4. What indices are already present?
5. Is the NAS accessible from dev environment?
6. Should we mount via NFS, SMB, or access via API?
7. What's the database size (for performance planning)?

## Resources

- CrossRef API Documentation: https://www.crossref.org/documentation/
- CrossRef Labs: https://www.crossref.org/labs/
- Connected Papers Algorithm: https://www.connectedpapers.com/about
- Impact Factor Calculation: https://en.wikipedia.org/wiki/Impact_factor
- Citation Graph Visualization Libraries:
  - D3.js: https://d3js.org/
  - Cytoscape.js: https://js.cytoscape.org/
  - vis.js: https://visjs.org/

---

**Status**: Awaiting user feedback and database schema inspection
