# Scholar Module Integration Strategy for Django Web App

## Current State Analysis

### Scholar Module (`~/proj/scitex_repo/src/scitex/scholar/`)
**Capabilities:**
- Multi-source search (CrossRef, PubMed, OpenAlex, Semantic Scholar, arXiv)
- PDF downloading with institutional authentication
- Metadata enrichment
- Browser automation (Selenium, ZenRows)
- OpenAthens SSO integration
- Local library management
- Export formats (BibTeX, RIS, JSON, Markdown)

**Challenges:**
- ❌ **Browser automation** - Selenium/headless Chrome for authenticated downloads
- ❌ **Authentication complexity** - OpenAthens, institutional SSO
- ❌ **Heavy dependencies** - Browser drivers, authentication systems
- ❌ **Session management** - Cookies, persistent sessions

### Django Scholar App (`apps/scholar_app/`)
**Current Implementation:**
- ✅ Database models (SearchIndex, Author, Journal, Citation)
- ✅ Search interface with PostgreSQL full-text search
- ✅ Paper recommendations and similarity
- ✅ Export functionality (CSV, BibTeX, RIS, JSON)
- ✅ Caching and optimization
- ❌ **NOT connected to actual scitex.scholar module!**

## Integration Challenges

### 1. Browser Automation (Biggest Challenge)
```python
# scitex.scholar uses browser for:
- PDF downloads from paywalled sites
- Institutional authentication
- JavaScript-rendered content
- Cookie/session management
```

**Problem:** Running headless Chrome in Django web app:
- Heavy resource usage (each user needs browser instance)
- Security risks (browser sessions)
- Scalability issues

### 2. Authentication Complexity
```python
# scitex.scholar supports:
- OpenAthens SSO
- University login portals
- Captcha solving
- Session persistence
```

**Problem:** User-specific auth credentials:
- Each user has different institutional access
- Can't share browser sessions
- Need secure credential storage

## Recommended Integration Approach

### Architecture: Hybrid Model

```
┌─────────────────────────────────────────────────────────────┐
│                    Django Web App                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────┐      ┌──────────────────────┐    │
│  │   scholar_app/       │      │   Task Queue         │    │
│  │   (Web Interface)    │─────>│   (Celery/Redis)    │    │
│  │                      │      │                      │    │
│  │  - Search UI         │      │  - PDF downloads     │    │
│  │  - Results display   │      │  - Heavy tasks       │    │
│  │  - User management   │      │                      │    │
│  └──────────────────────┘      └──────────────────────┘    │
│           │                              │                  │
│           │                              │                  │
│           v                              v                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           scitex.scholar Service Layer               │  │
│  │  (Thin wrapper around scitex_repo/src/scitex/scholar)│  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           v
         ┌────────────────────────────────────────┐
         │  scitex_repo/src/scitex/scholar/      │
         │  (Core Python package - no changes)   │
         │                                        │
         │  - Multi-source search                 │
         │  - Browser automation                  │
         │  - PDF processing                      │
         │  - Authentication                      │
         └────────────────────────────────────────┘
```

### Phase 1: Lightweight Integration (Immediate)

**Use scitex.scholar WITHOUT browser automation:**

```python
# apps/scholar_app/services/scholar_service.py

import sys
sys.path.insert(0, '/home/ywatanabe/proj/scitex_repo/src')
from scitex.scholar import Scholar

class ScholarService:
    """Service layer wrapping scitex.scholar module."""

    @staticmethod
    def search_papers(query, sources=['crossref', 'pubmed', 'openalex']):
        """
        Search papers using scitex.scholar (API-only, no browser).

        Advantages:
        - Fast, lightweight
        - No browser overhead
        - Works for most queries
        - Scalable

        Limitations:
        - No PDF downloads (yet)
        - No institutional auth (yet)
        """
        scholar = Scholar(
            use_browser=False,  # API-only mode
            verbose=False
        )

        results = scholar.search(
            query=query,
            sources=sources,
            max_results=20
        )

        return results

    @staticmethod
    def get_paper_metadata(doi):
        """Get detailed metadata for a paper."""
        scholar = Scholar(use_browser=False)
        return scholar.get_metadata(doi)

    @staticmethod
    def export_to_bibtex(papers):
        """Export papers to BibTeX using scitex.scholar."""
        scholar = Scholar()
        return scholar.export(papers, format='bibtex')
```

**Benefits:**
- ✅ Use proven scitex.scholar search logic
- ✅ No browser overhead (API-only)
- ✅ Fast and scalable
- ✅ Easy to implement

**Limitations:**
- ❌ No PDF downloads (requires browser)
- ❌ No institutional authentication

### Phase 2: Background PDF Downloads (Later)

**Use Celery for heavy browser tasks:**

```python
# apps/scholar_app/tasks.py (Celery tasks)

from celery import shared_task
from scitex.scholar import Scholar

@shared_task
def download_pdf_background(paper_id, user_id):
    """
    Download PDF in background using scitex.scholar browser.

    User flow:
    1. User requests PDF download
    2. Task queued in Celery
    3. Worker process runs browser automation
    4. User gets notification when ready
    """
    user = User.objects.get(id=user_id)
    paper = SearchIndex.objects.get(id=paper_id)

    # Initialize Scholar with user's credentials
    scholar = Scholar(
        use_browser=True,
        auth_credentials={
            'openathens_email': user.profile.institutional_email,
            'openathens_password': decrypt(user.profile.encrypted_password)
        }
    )

    try:
        pdf_path = scholar.download_pdf(paper.doi)

        # Save to user's library
        paper.pdf_file = pdf_path
        paper.save()

        # Notify user
        send_notification(user, f"PDF ready: {paper.title}")

    except Exception as e:
        send_notification(user, f"PDF download failed: {str(e)}")
```

**Benefits:**
- ✅ Non-blocking (user doesn't wait)
- ✅ Isolated browser sessions
- ✅ Retry on failure
- ✅ User-specific authentication

**Requirements:**
- Need Celery + Redis
- Need worker processes
- Credential encryption

### Phase 3: Local Client (Advanced Users)

**For power users who want full features:**

```bash
# Desktop client using scitex.scholar directly
$ pip install scitex

$ scitex scholar search "machine learning"
# Uses local browser, full authentication
# Syncs to cloud via API
```

**Benefits:**
- ✅ Full scitex.scholar capabilities
- ✅ Local browser (no server resources)
- ✅ User manages own auth
- ✅ Sync results to cloud

## Recommended Implementation Plan

### Week 1: API-Only Integration

```python
# 1. Create ScholarService
apps/scholar_app/services/scholar_service.py

# 2. Update views to use service
def search_dashboard(request):
    query = request.GET.get('q')

    # Use scitex.scholar instead of Django search
    results = ScholarService.search_papers(query)

    # Convert to Django models for display
    papers = _convert_to_models(results)

    return render(request, 'scholar_app/search_dashboard.html', {
        'papers': papers
    })

# 3. Helper to convert scitex results to Django models
def _convert_to_models(results):
    papers = []
    for r in results:
        paper, created = SearchIndex.objects.get_or_create(
            doi=r['doi'],
            defaults={
                'title': r['title'],
                'abstract': r['abstract'],
                # ... map all fields
            }
        )
        papers.append(paper)
    return papers
```

### Week 2-3: Background Tasks (Optional)

**Only if PDF downloads are essential:**

```bash
# Install Celery
pip install celery redis

# Add to settings.py
CELERY_BROKER_URL = 'redis://localhost:6379/0'

# Create tasks
apps/scholar_app/tasks.py

# Add worker
celery -A config worker --loglevel=info
```

### Week 4: Polish & Testing

- Handle errors gracefully
- Add progress indicators
- Test with real queries
- Optimize performance

## Code Integration Pattern

### Service Layer (Recommended)

```python
# apps/scholar_app/services/scholar_service.py

import sys
from pathlib import Path

# Add scitex to path
SCITEX_PATH = Path.home() / 'proj/scitex_repo/src'
if str(SCITEX_PATH) not in sys.path:
    sys.path.insert(0, str(SCITEX_PATH))

from scitex.scholar import Scholar

class ScholarService:
    """
    Service layer wrapping scitex.scholar module.
    Provides Django-friendly interface to Scholar functionality.
    """

    def __init__(self, use_browser=False, user=None):
        self.scholar = Scholar(
            use_browser=use_browser,
            verbose=False
        )
        self.user = user

    def search(self, query, **kwargs):
        """Search papers using scitex.scholar API search."""
        return self.scholar.search(query, **kwargs)

    def get_metadata(self, identifier):
        """Get paper metadata by DOI/PMID/arXiv ID."""
        return self.scholar.get_metadata(identifier)

    def import_from_file(self, file_path):
        """Import papers from file (PDF, BibTeX, etc.)."""
        return self.scholar.import_papers(file_path)

    def export(self, papers, format='bibtex'):
        """Export papers in specified format."""
        return self.scholar.export(papers, format=format)
```

### View Integration

```python
# apps/scholar_app/views.py

from .services.scholar_service import ScholarService

def search_dashboard(request):
    query = request.GET.get('q', '').strip()

    if not query:
        return render(request, 'scholar_app/search_dashboard.html')

    # Use ScholarService (wraps scitex.scholar)
    service = ScholarService(user=request.user)

    try:
        # Get results from multiple sources
        results = service.search(
            query=query,
            sources=['crossref', 'pubmed', 'openalex'],
            max_results=20
        )

        # Convert to Django models and save to database
        papers = []
        for result in results:
            paper = _upsert_paper(result)
            papers.append(paper)

        # Cache results
        cache.set(f'search:{query}', papers, 3600)

    except Exception as e:
        messages.error(request, f"Search error: {str(e)}")
        papers = []

    return render(request, 'scholar_app/search_dashboard.html', {
        'query': query,
        'papers': papers
    })
```

## Decision Matrix

| Feature | Web-Only | + Celery | + Local Client |
|---------|----------|----------|----------------|
| **API Search** | ✅ Fast | ✅ Fast | ✅ Fast |
| **PDF Downloads** | ❌ No | ✅ Background | ✅ Instant |
| **Institutional Auth** | ❌ No | ⚠️ Complex | ✅ User-managed |
| **Resource Usage** | ✅ Light | ⚠️ Medium | ✅ Light (client) |
| **User Experience** | ⚠️ Limited | ✅ Good | ✅ Excellent |
| **Implementation** | ✅ Easy | ⚠️ Medium | ✅ Easy |
| **Scalability** | ✅ High | ⚠️ Medium | ✅ High |

## Recommendation

**Start with Phase 1 (API-Only):**

1. **Week 1:** Integrate scitex.scholar for search (no browser)
   - Fast to implement
   - Proves the integration pattern
   - Provides immediate value

2. **Week 2-3:** Add background PDF downloads (if needed)
   - Only implement if users really need it
   - Use Celery for async tasks
   - Allow user-provided credentials

3. **Later:** Offer desktop client for power users
   - Full scitex.scholar features
   - Local browser automation
   - Sync to cloud

## Implementation Checklist

### Immediate (Week 1)
- [ ] Create `apps/scholar_app/services/scholar_service.py`
- [ ] Add scitex_repo to Python path in service
- [ ] Update search views to use ScholarService
- [ ] Test API-based search
- [ ] Handle errors gracefully

### Optional (Week 2-3)
- [ ] Set up Celery + Redis
- [ ] Create background PDF download task
- [ ] Add user credential management
- [ ] Implement notification system
- [ ] Test async downloads

### Future
- [ ] Desktop client with sync API
- [ ] Full browser automation for power users
- [ ] Chrome extension for browser integration

## Key Principle

**Don't fight the architecture:**
- scitex.scholar is designed for LOCAL command-line use
- Django web app is designed for SHARED server use
- Use scitex.scholar for what it does best (API search, parsing)
- Skip browser features for web app (or background them)

## Next Steps

1. Review this strategy
2. Decide: API-only or + Background tasks?
3. Implement ScholarService wrapper
4. Test with real Scholar module
5. Iterate based on user feedback

---

Generated: 2025-10-15
Author: Claude Code
Related: REFACTORING_PLAN.md, TODO.md
