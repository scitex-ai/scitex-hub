# SciTeX Scholar Search Integration Guide

## Overview

The SciTeX Scholar search functionality has been integrated into the Django web application, providing powerful multi-source academic paper search capabilities through both sequential and parallel search pipelines.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                Django Web Application                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  scholar_app/scholar/scitex_search.py                  │  │
│  │  - Django view wrappers                                │  │
│  │  - Request/Response conversion                         │  │
│  │  - Database integration                                │  │
│  └────────────────┬───────────────────────────────────────┘  │
└───────────────────┼──────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────┐
│         SciTeX Search Pipelines (scitex-code)                 │
│  ┌──────────────────────┐  ┌──────────────────────────┐     │
│  │ Single Pipeline      │  │ Parallel Pipeline        │     │
│  │ (Sequential)         │  │ (Concurrent, Faster)     │     │
│  └──────────────────────┘  └──────────────────────────┘     │
│                    │                    │                     │
│                    └──────────┬─────────┘                     │
│                               ▼                               │
│  ┌────────────────────────────────────────────────────┐     │
│  │        ScholarEngine (Base Engine)                 │     │
│  └────────────────┬───────────────────────────────────┘     │
└───────────────────┼──────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────┐
│              Individual Search Engines                        │
│  ┌──────────┬──────────┬──────────┬───────────┬──────────┐  │
│  │ PubMed   │CrossRef  │  arXiv   │ Semantic  │ OpenAlex │  │
│  │ Engine   │ Engine   │ Engine   │ Scholar   │ Engine   │  │
│  └──────────┴──────────┴──────────┴───────────┴──────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Installation & Setup

### 1. Prerequisites

Ensure `scitex-code` package is installed and accessible:

```bash
# Check if scitex is importable
python -c "from scitex.scholar.metadata_engines import ScholarPipelineSearchParallel; print('✓ SciTeX available')"
```

If not available, add the path to your Python environment or install the package.

### 2. Django Settings

Settings are configured in `/home/ywatanabe/proj/scitex-cloud/config/settings/settings_shared.py`:

```python
# SciTeX Scholar Search Settings
SCITEX_SCHOLAR_USE_CACHE = True  # Enable result caching
SCITEX_SCHOLAR_MAX_WORKERS = 5  # Parallel workers
SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE = 30  # Seconds
SCITEX_SCHOLAR_ENGINES = ["CrossRef", "PubMed", "Semantic_Scholar", "arXiv", "OpenAlex"]
SCITEX_SCHOLAR_DEFAULT_MODE = "parallel"  # or "single"
```

### 3. Environment Variables (Optional)

Override settings via environment variables:

```bash
export SCITEX_SCHOLAR_USE_CACHE=True
export SCITEX_SCHOLAR_MAX_WORKERS=5
export SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE=30
export SCITEX_SCHOLAR_ENGINES="CrossRef,PubMed,arXiv"
export SCITEX_SCHOLAR_DEFAULT_MODE=parallel
```

## API Endpoints

### 1. Main Search Endpoint (Parallel)

**Endpoint**: `GET /scholar/api/search/scitex/`

**Query Parameters**:
- `q` (required): Search query string
- `search_fields`: Comma-separated fields (title,abstract,keywords)
- `year_start`: Start year filter (e.g., 2020)
- `year_end`: End year filter (e.g., 2024)
- `open_access`: Filter for OA papers (true/false)
- `author`: Author name filter
- `journal`: Journal name filter
- `max_results`: Maximum results (default: 100, max: 1000)

**Example Request**:
```bash
curl "http://127.0.0.1:8000/scholar/api/search/scitex/?q=machine+learning&search_fields=title,abstract&year_start=2020&open_access=true&max_results=50"
```

**Example Response**:
```json
{
  "query": "machine learning",
  "search_fields": ["title", "abstract"],
  "filters": {
    "year_start": 2020,
    "open_access": true
  },
  "results": [
    {
      "id": "uuid-here",
      "title": "Deep Learning for Natural Language Processing",
      "authors": ["Author One", "Author Two"],
      "year": 2023,
      "abstract": "Abstract text...",
      "doi": "10.1234/example",
      "pmid": "12345678",
      "citation_count": 150,
      "is_open_access": true,
      "pdf_url": "https://...",
      "source_engines": ["CrossRef", "PubMed"]
    }
  ],
  "metadata": {
    "engines_used": ["CrossRef", "PubMed", "arXiv"],
    "total_engines": 5,
    "successful_engines": 3,
    "total_results": 1,
    "search_time": 2.5,
    "timestamp": "2025-10-22T12:00:00"
  },
  "stats": {
    "total_searches": 10,
    "successful_searches": 8,
    "success_rate": 80.0,
    "average_time": 2.1
  }
}
```

### 2. Sequential Search Endpoint

**Endpoint**: `GET /scholar/api/search/scitex/single/`

Same parameters as parallel endpoint, but uses sequential engine querying (better for rate limits).

**Use When**:
- Rate limiting is a concern
- Testing/debugging
- Predictable, ordered results needed

### 3. Engine Capabilities Endpoint

**Endpoint**: `GET /scholar/api/search/scitex/capabilities/`

**Example Response**:
```json
{
  "available": true,
  "engines": {
    "PubMed": {
      "fields": ["title", "author", "abstract", "journal", "pmid", "doi"],
      "max_results": 1000,
      "supports_filters": ["year", "journal", "author"]
    },
    "CrossRef": {
      "fields": ["title", "author", "doi", "journal"],
      "max_results": 1000,
      "supports_filters": ["year", "type", "publisher"]
    }
  },
  "statistics": {
    "total_searches": 100,
    "success_rate": 85.0
  }
}
```

## Frontend Integration

### JavaScript Example

```javascript
// Search function using the SciTeX API
async function searchWithSciTeX(query, filters = {}) {
    // Build query string
    const params = new URLSearchParams({
        q: query,
        search_fields: 'title,abstract',
        ...filters
    });

    try {
        const response = await fetch(`/scholar/api/search/scitex/?${params}`);
        const data = await response.json();

        if (data.error) {
            console.error('Search error:', data.error);
            return [];
        }

        // Display results
        displayResults(data.results);

        // Show metadata
        console.log(`Found ${data.results.length} results in ${data.metadata.search_time}s`);
        console.log(`Engines used: ${data.metadata.engines_used.join(', ')}`);

        return data.results;

    } catch (error) {
        console.error('Search failed:', error);
        return [];
    }
}

// Example usage
searchWithSciTeX('attention is all you need', {
    year_start: 2017,
    open_access: true,
    max_results: 20
});
```

### Progressive Search UI

```javascript
// Show search progress with engine status
async function progressiveSearch(query) {
    const resultsDiv = document.getElementById('search-results');
    const statusDiv = document.getElementById('search-status');

    // Clear previous results
    resultsDiv.innerHTML = '';
    statusDiv.innerHTML = '<div class="alert alert-info">Searching...</div>';

    try {
        const response = await fetch(`/scholar/api/search/scitex/?q=${encodeURIComponent(query)}&search_fields=title,abstract`);
        const data = await response.json();

        // Update status with engines used
        const engines = data.metadata.engines_used || [];
        statusDiv.innerHTML = `
            <div class="alert alert-success">
                Search completed in ${data.metadata.search_time.toFixed(2)}s
                <br>Engines: ${engines.join(', ')}
            </div>
        `;

        // Display results
        data.results.forEach(paper => {
            const paperCard = createPaperCard(paper);
            resultsDiv.appendChild(paperCard);
        });

    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger">Search failed: ${error.message}</div>`;
    }
}

function createPaperCard(paper) {
    const card = document.createElement('div');
    card.className = 'card mb-3';
    card.innerHTML = `
        <div class="card-body">
            <h5 class="card-title">${paper.title}</h5>
            <p class="card-text"><strong>Authors:</strong> ${paper.authors.join(', ')}</p>
            <p class="card-text"><strong>Year:</strong> ${paper.year}</p>
            <p class="card-text">${paper.abstract.substring(0, 200)}...</p>
            <div class="mt-2">
                ${paper.is_open_access ? '<span class="badge badge-success">Open Access</span>' : ''}
                <span class="badge badge-info">${paper.citation_count} citations</span>
                ${paper.source_engines.map(e => `<span class="badge badge-secondary">${e}</span>`).join(' ')}
            </div>
            ${paper.pdf_url ? `<a href="${paper.pdf_url}" class="btn btn-sm btn-primary mt-2">View PDF</a>` : ''}
        </div>
    `;
    return card;
}
```

## Testing

### 1. Basic Test

```bash
# Test if SciTeX is available
curl "http://127.0.0.1:8000/scholar/api/search/scitex/capabilities/"
```

Expected: `{"available": true, "engines": {...}}`

### 2. Simple Search Test

```bash
# Search for a famous paper
curl "http://127.0.0.1:8000/scholar/api/search/scitex/?q=Attention+is+All+You+Need"
```

Expected: JSON response with results

### 3. Advanced Search Test

```bash
# Search with filters
curl "http://127.0.0.1:8000/scholar/api/search/scitex/?q=neural+networks&search_fields=title,abstract&year_start=2020&year_end=2024&open_access=true&max_results=10"
```

### 4. Python Test Script

```python
import requests

BASE_URL = "http://127.0.0.1:8000"

def test_scitex_search():
    # Test 1: Check availability
    response = requests.get(f"{BASE_URL}/scholar/api/search/scitex/capabilities/")
    assert response.status_code == 200
    data = response.json()
    assert data['available'] == True
    print("✓ SciTeX is available")

    # Test 2: Simple search
    response = requests.get(
        f"{BASE_URL}/scholar/api/search/scitex/",
        params={'q': 'machine learning'}
    )
    assert response.status_code == 200
    data = response.json()
    print(f"✓ Found {len(data['results'])} results")
    print(f"✓ Search time: {data['metadata']['search_time']:.2f}s")

    # Test 3: Filtered search
    response = requests.get(
        f"{BASE_URL}/scholar/api/search/scitex/",
        params={
            'q': 'deep learning',
            'search_fields': 'title,abstract',
            'year_start': 2020,
            'open_access': 'true',
            'max_results': 5
        }
    )
    assert response.status_code == 200
    data = response.json()
    print(f"✓ Filtered search returned {len(data['results'])} results")

    print("\n All tests passed!")

if __name__ == "__main__":
    test_scitex_search()
```

## Troubleshooting

### Issue: "SciTeX search engine not available"

**Solution**:
1. Check if scitex package is installed:
   ```bash
   python -c "import scitex; print(scitex.__file__)"
   ```

2. Add scitex-code to Python path if needed:
   ```python
   import sys
   sys.path.insert(0, '/home/ywatanabe/proj/scitex-code/src')
   ```

3. Restart Django server

### Issue: "Failed to initialize search pipeline"

**Solution**:
- Check logs: `tail -f /path/to/logs/django.log`
- Verify settings in `settings_shared.py`
- Test manually:
  ```python
  from scitex.scholar.metadata_engines import ScholarPipelineSearchParallel
  pipeline = ScholarPipelineSearchParallel()
  ```

### Issue: Slow searches

**Solutions**:
- Use `search_fields=title` instead of `title,abstract` (fewer engines support abstract)
- Reduce `SCITEX_SCHOLAR_MAX_WORKERS` to avoid rate limiting
- Use single pipeline: `/api/search/scitex/single/`
- Enable caching: `SCITEX_SCHOLAR_USE_CACHE=True`

### Issue: Rate limiting errors

**Solutions**:
- Switch to single pipeline
- Reduce `SCITEX_SCHOLAR_MAX_WORKERS`
- Increase `SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE`
- Add delays between requests in frontend

## Performance Optimization

### Caching

Results are automatically cached based on query+filters hash:
- **Cache location**: `~/.scitex/cache/engines/`
- **Cache duration**: Persistent until manually cleared
- **Clear cache**: Set `SCITEX_SCHOLAR_USE_CACHE=False` or delete cache files

### Database Storage

Search results are automatically stored in Django's `SearchIndex` model:
- Deduplication by DOI/PMID/arXiv ID
- Searchable for future queries
- Reduces external API calls

### Rate Limit Management

```python
# Conservative settings (good for production)
SCITEX_SCHOLAR_MAX_WORKERS = 3
SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE = 45

# Aggressive settings (good for local development)
SCITEX_SCHOLAR_MAX_WORKERS = 8
SCITEX_SCHOLAR_TIMEOUT_PER_ENGINE = 20
```

## Monitoring & Analytics

### Search Statistics

Access via capabilities endpoint:
```javascript
const stats = await fetch('/scholar/api/search/scitex/capabilities/');
const data = await stats.json();

console.log('Total searches:', data.statistics.total_searches);
console.log('Success rate:', data.statistics.success_rate);
```

### User Search Tracking

All searches are tracked in `SearchQuery` model:
```python
from apps.scholar_app.models import SearchQuery

# Get recent searches
recent_searches = SearchQuery.objects.filter(
    user=request.user
).order_by('-created_at')[:10]

# Analytics
from django.db.models import Avg, Count
stats = SearchQuery.objects.aggregate(
    avg_results=Avg('result_count'),
    total=Count('id')
)
```

## Next Steps

1. **Add to Frontend**:
   - Update `apps/scholar_app/templates/scholar_app/index.html`
   - Replace existing search with SciTeX integration
   - Add engine status indicators

2. **Advanced Features**:
   - Implement saved searches with SciTeX
   - Add export functionality for SciTeX results
   - Create search analytics dashboard

3. **Optimization**:
   - Implement Redis caching for production
   - Add rate limiting middleware
   - Set up monitoring/alerting

## Support

For issues or questions:
- Check logs: `apps/scholar_app/scholar/scitex_search.py`
- Review SciTeX docs: `/home/ywatanabe/proj/scitex-code/src/scitex/scholar/metadata_engines/SEARCH_PIPELINES.md`
- Test pipelines directly: See scitex-code examples

---

**Last Updated**: 2025-10-22
**Version**: 1.0.0
