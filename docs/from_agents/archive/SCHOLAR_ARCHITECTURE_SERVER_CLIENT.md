# Scholar Architecture: Server vs Client Division

**Date:** 2025-10-20
**Status:** Design Document
**Priority:** P1 - Architecture

---

## Principle: Smart Division of Responsibilities

**Server-Side:**
- 🧠 Smart operations (search, metadata, organization)
- 📊 Scalable operations (batch processing, caching)
- 🔒 Legal operations (only open-access downloads)

**Client-Side:**
- 🌐 Browser automation (institutional access)
- 💾 Heavy downloads (PDFs to user's machine)
- 🔑 User credentials (OpenAthens, Shibboleth)

---

## Detailed Breakdown

### ✅ Server-Side Operations (Django API)

#### 1. **Search Engines** 🔍
**Why Server:**
- API keys managed centrally
- Rate limiting handled properly
- Caching results for all users
- Aggregation across multiple sources

```python
# Django API
POST /api/scholar/search/
{
  "query": "neural networks spike sorting",
  "sources": ["pubmed", "arxiv", "semantic_scholar"],
  "limit": 50
}

# Response (fast, cached)
{
  "results": [
    {"doi": "10.1038/...", "title": "...", "open_access": true},
    {"doi": "10.1016/...", "title": "...", "open_access": false},
    ...
  ],
  "open_access_count": 23,
  "paywalled_count": 27
}
```

**CLI Wrapper:**
```bash
# Calls Django API
scitex scholar search "neural networks" --source pubmed --limit 50
```

#### 2. **BibTeX Processing** 📚
**Why Server:**
- Complex parsing logic centralized
- DOI resolution (Crossref API calls)
- Metadata enrichment from multiple sources
- Deduplication across users
- Format validation

```python
# Django API
POST /api/scholar/bibtex/parse/
{
  "bibtex_content": "@article{...}",
  "enrich": true
}

# Server:
# 1. Parses BibTeX entries
# 2. Resolves missing DOIs (title→DOI via Crossref)
# 3. Enriches metadata (abstract, keywords, citations)
# 4. Checks open-access status
# 5. Returns enriched entries + download strategy

# Response
{
  "entries": [
    {
      "id": "entry1",
      "doi": "10.1038/nature12373",
      "title": "...",
      "open_access": false,
      "enriched": true,
      "download_strategy": "client"  // needs institutional access
    },
    {
      "id": "entry2",
      "doi": "10.1371/journal.pone.0123456",
      "title": "...",
      "open_access": true,
      "enriched": true,
      "download_strategy": "server"  // can download server-side
    }
  ],
  "open_access_dois": ["10.1371/..."],
  "paywalled_dois": ["10.1038/..."]
}
```

**CLI Wrapper:**
```bash
# Uploads BibTeX to server for processing
scitex scholar bibtex analyze refs.bib

# Output:
# Analyzed: 50 papers
# Open access: 23 papers (server can download)
# Paywalled: 27 papers (requires local browser)
#
# Download open-access papers? [y/N]: y
# → Server downloading 23 papers...
# → Downloaded to cloud library
#
# Download paywalled papers locally? [y/N]: y
# → scitex scholar parallel --dois 10.1038/... --num-workers 8
```

#### 3. **Metadata Enrichment** 📝
**Why Server:**
- API access to Crossref, PubMed, Semantic Scholar
- Caching (same paper, multiple users)
- Background jobs (don't block CLI)
- Impact factor database updates

```python
POST /api/scholar/metadata/enrich/
{
  "doi": "10.1038/nature12373"
}

# Server fetches from:
# - Crossref (citation data)
# - PubMed (MeSH terms, abstracts)
# - Semantic Scholar (influential citations)
# - Local impact factor database

# Response
{
  "doi": "10.1038/nature12373",
  "title": "...",
  "abstract": "...",
  "citations": 1234,
  "influential_citations": 89,
  "impact_factor": 42.778,
  "mesh_terms": ["Neural Networks", "Computer Simulation"],
  "enriched_at": "2025-10-20T..."
}
```

#### 4. **Library Management** 📖
**Why Server:**
- Sync across devices
- Collaborative libraries (teams)
- Search within library
- Statistics and analytics

```python
# Store metadata in Django (not PDFs!)
POST /api/scholar/library/add/
{
  "doi": "10.1038/nature12373",
  "project": "neuroscience",
  "tags": ["spike-sorting", "review"],
  "local_pdf_path": "~/.scitex/scholar/library/MASTER/12345678/paper.pdf"
}

# Django stores:
# - Metadata
# - User's tags/notes
# - Project association
# - Reference to local file (path only, not content)
```

**CLI Integration:**
```bash
# Add to library (uploads metadata, not PDF)
scitex scholar library add --doi "10.1038/..." --project neuroscience

# Sync library metadata from server
scitex scholar library sync

# Search in library (queries Django API)
scitex scholar library search "spike sorting"
```

#### 5. **Recommendations** 💡
**Why Server:**
- Machine learning models
- Collaborative filtering
- Citation network analysis
- Trending papers tracking

```python
GET /api/scholar/recommendations/
{
  "user_id": 123,
  "project": "neuroscience",
  "limit": 20
}

# Server analyzes:
# - User's library
# - Reading history
# - Citation network
# - Similar users
# - Trending papers

# Returns recommended papers
```

---

### ✅ Client-Side Operations (CLI)

#### 1. **PDF Downloads (Paywalled)** 📄
**Why Client:**
- Uses institutional credentials (OpenAthens, Shibboleth)
- Browser automation (cookie management)
- User's network (IP-based access)
- Legal liability on user

```bash
# Runs on user's machine
scitex scholar single --doi "10.1038/nature12373" \
  --browser-mode stealth \
  --chrome-profile university

# Browser:
# 1. Opens publisher page
# 2. Detects paywall
# 3. Uses OpenAthens/Shibboleth from cookies
# 4. Downloads PDF
# 5. Stores locally: ~/.scitex/scholar/library/MASTER/12345678/paper.pdf
# 6. Optionally uploads metadata to Django (not PDF)
```

#### 2. **Parallel Processing** ⚡
**Why Client:**
- Utilizes user's machine resources
- Multiple browser instances
- Dedicated Chrome profiles per worker
- Doesn't overload server

```bash
scitex scholar parallel \
  --dois doi1 doi2 doi3 ... doi50 \
  --num-workers 8 \
  --project neuroscience

# CLI:
# 1. Spawns 8 browser workers
# 2. Each worker has dedicated Chrome profile
# 3. Processes DOIs in parallel
# 4. Downloads PDFs locally
# 5. Batch uploads metadata to Django
```

#### 3. **Local Library Operations** 💾
**Why Client:**
- Fast (no network latency)
- Works offline
- User controls their files
- Privacy (PDFs stay local)

```bash
# List local library (no API call)
scitex scholar library list --local

# Extract text from local PDF
scitex scholar extract text ~/.scitex/scholar/library/MASTER/12345678/paper.pdf

# Search local PDFs (full-text)
scitex scholar search-local "spike sorting algorithms"
```

---

## Hybrid Workflows

### Workflow 1: BibTeX Smart Processing

```bash
# Step 1: Upload BibTeX to server for analysis
scitex scholar bibtex analyze papers.bib

# Server:
# - Parses BibTeX
# - Enriches metadata
# - Determines open-access status
# - Returns download strategy

# Output:
# ✓ Analyzed 50 papers
# ✓ Open access: 23 papers
# ✓ Paywalled: 27 papers
#
# Download strategy:
# → Server will download 23 open-access papers
# → You can download 27 paywalled papers locally

# Step 2: Server downloads open-access
scitex scholar bibtex download-open-access papers.bib

# Server downloads to cloud library
# User can access from any device

# Step 3: Client downloads paywalled
scitex scholar bibtex download-paywalled papers.bib \
  --num-workers 8 \
  --chrome-profile university

# CLI downloads to local machine
# Optionally syncs metadata to server
```

### Workflow 2: Search + Smart Download

```bash
# Step 1: Search via server (fast, cached)
scitex scholar search "neural networks" --source all --save results.json

# Server:
# - Queries APIs (pubmed, arxiv, semantic scholar)
# - Caches results
# - Returns with open-access flags

# Step 2: Review results
cat results.json | jq '.[] | select(.open_access == true)'

# Step 3: Download open-access from server
scitex scholar download-from-server results.json --open-access-only

# Step 4: Download paywalled locally
scitex scholar download-local results.json --paywalled-only --num-workers 4
```

### Workflow 3: Library Sync

```bash
# User A (at university)
scitex scholar parallel --dois ... --project shared-project
# Downloads 50 papers locally
# Uploads metadata to Django

# User B (at home)
scitex scholar library sync --project shared-project
# Downloads metadata from Django
# Sees what papers are available
# Can download PDFs if they have access
```

---

## API Endpoints Design

### Search API

```python
# /apps/scholar_app/api/views.py

@api_view(['POST'])
def search_papers(request):
    """
    Smart search across multiple sources.
    Handles API keys, rate limiting, caching.
    """
    query = request.data.get('query')
    sources = request.data.get('sources', ['all'])
    limit = request.data.get('limit', 50)

    # Check cache first
    cache_key = f"scholar_search:{query}:{sources}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    # Search across sources
    results = []

    if 'pubmed' in sources or 'all' in sources:
        results.extend(search_pubmed(query, limit))

    if 'arxiv' in sources or 'all' in sources:
        results.extend(search_arxiv(query, limit))

    if 'semantic' in sources or 'all' in sources:
        results.extend(search_semantic_scholar(query, limit))

    # Enrich with open-access status
    for result in results:
        result['open_access'] = check_open_access(result['doi'])

    # Cache for 1 hour
    cache.set(cache_key, results, 3600)

    return Response({
        'results': results[:limit],
        'total': len(results),
        'open_access_count': sum(1 for r in results if r['open_access']),
    })
```

### BibTeX Processing API

```python
@api_view(['POST'])
def process_bibtex(request):
    """
    Parse and enrich BibTeX file.
    Returns enriched entries + download strategy.
    """
    bibtex_content = request.data.get('bibtex_content')
    enrich = request.data.get('enrich', True)

    # Parse BibTeX
    entries = parse_bibtex(bibtex_content)

    # Enrich each entry
    for entry in entries:
        if 'doi' not in entry and 'title' in entry:
            # Resolve DOI from title (Crossref API)
            entry['doi'] = resolve_doi_from_title(entry['title'])

        if enrich and entry.get('doi'):
            # Enrich metadata
            metadata = enrich_metadata(entry['doi'])
            entry.update(metadata)

            # Check open-access
            entry['open_access'] = check_open_access(entry['doi'])
            entry['download_strategy'] = 'server' if entry['open_access'] else 'client'

    return Response({
        'entries': entries,
        'total': len(entries),
        'open_access_dois': [e['doi'] for e in entries if e.get('open_access')],
        'paywalled_dois': [e['doi'] for e in entries if not e.get('open_access')],
    })
```

### Library Sync API

```python
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
def sync_library(request):
    """
    Sync library metadata (not PDFs).
    Upload/download library state.
    """
    action = request.data.get('action')  # 'upload' or 'download'

    if action == 'upload':
        # User uploads local library metadata
        papers = request.data.get('papers')

        for paper in papers:
            LibraryPaper.objects.update_or_create(
                user=request.user,
                doi=paper['doi'],
                defaults={
                    'title': paper['title'],
                    'metadata': paper['metadata'],
                    'local_path': paper['local_path'],  # Just path reference
                    'project': paper.get('project'),
                    'tags': paper.get('tags', []),
                }
            )

        return Response({'uploaded': len(papers)})

    elif action == 'download':
        # User downloads library metadata
        papers = LibraryPaper.objects.filter(user=request.user)

        return Response({
            'papers': [
                {
                    'doi': p.doi,
                    'title': p.title,
                    'metadata': p.metadata,
                    'project': p.project,
                    'tags': p.tags,
                    'has_local_pdf': bool(p.local_path),
                }
                for p in papers
            ]
        })
```

---

## CLI Implementation Updates

```python
# /home/ywatanabe/proj/scitex-code/src/scitex/cli/scholar.py

@scholar.command()
@click.argument('query')
@click.option('--source', type=click.Choice(['pubmed', 'arxiv', 'semantic', 'all']), default='all')
@click.option('--limit', type=int, default=50)
@click.option('--save', help='Save results to file')
def search(query, source, limit, save):
    """
    Search for papers via Django API

    Examples:
        scitex scholar search "neural networks"
        scitex scholar search "spike sorting" --source pubmed --limit 100
        scitex scholar search "deep learning" --save results.json
    """
    import requests

    # Call Django API
    response = requests.post(
        'http://localhost:8000/api/scholar/search/',
        json={
            'query': query,
            'sources': [source],
            'limit': limit
        }
    )

    data = response.json()

    # Display results
    click.echo(f"\nFound {data['total']} papers")
    click.echo(f"Open access: {data['open_access_count']}")
    click.echo(f"Paywalled: {data['total'] - data['open_access_count']}\n")

    for result in data['results']:
        access = "🟢 Open" if result['open_access'] else "🔒 Paywalled"
        click.echo(f"{access} - {result['title']}")
        click.echo(f"       DOI: {result['doi']}\n")

    if save:
        import json
        with open(save, 'w') as f:
            json.dump(data['results'], f, indent=2)
        click.echo(f"Saved to {save}")
```

---

## Summary

### Server Handles (Smart/Scalable/Legal):
✅ Search engines (API keys, caching, rate limiting)
✅ BibTeX parsing (complex logic, DOI resolution)
✅ Metadata enrichment (Crossref, PubMed, Semantic Scholar)
✅ Library management (sync, search, analytics)
✅ Open-access downloads (PMC, arXiv, bioRxiv)
✅ Recommendations (ML models, collaborative filtering)

### Client Handles (Heavy/Credentials/Browser):
✅ Paywalled PDF downloads (institutional access)
✅ Browser automation (OpenAthens, Shibboleth)
✅ Parallel processing (multiple workers)
✅ Local file operations (fast, offline)
✅ User's credentials management

### Best of Both:
🎯 Fast search (server)
🎯 Smart downloads (server for open-access, client for paywalled)
🎯 Cross-device sync (metadata only)
🎯 Legal compliance (server doesn't touch paywalled content)
🎯 Full automation (client uses legitimate access)

---

**Status:** ✅ Architecture Defined
**Next:** Implement Django search/bibtex APIs
**Impact:** Optimal division of responsibilities!

<!-- EOF -->
