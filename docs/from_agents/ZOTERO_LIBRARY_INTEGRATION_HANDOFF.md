# Handoff: Zotero Integration + Project-Specific Library for Scholar Library Page

**Date:** 2026-02-18
**Scope:** `http://127.0.0.1:8000/scholar/#library`
**Prepared by:** Claude (scitex-python develop branch)

---

## Background

Two capabilities were just added to `scitex.scholar` that should be exposed in the cloud library UI:

### 1. `ZoteroLocalReader` (NEW — commit `21a7907d` on scitex-python `develop`)

Reads directly from a local Zotero SQLite database — **no API key required**.

```python
from scitex.scholar.integration.zotero import ZoteroLocalReader, export_for_zotero

reader = ZoteroLocalReader()                          # auto-detects ~/Zotero/
papers = reader.read_all()                            # all items
papers = reader.read_by_tags(["EEG", "Epilepsy"])    # filter by Zotero tags
papers = reader.read_by_collection("My Collection")  # filter by collection name
export_for_zotero(papers, "enriched.bib")            # export BibTeX for re-import
```

Auto-detects:
- Linux: `~/Zotero/zotero.sqlite`
- Windows WSL: `/mnt/c/Users/*/Zotero/zotero.sqlite`

### 2. Project-Specific Library (`ensure_workspace` + symlinks)

The project-local library pattern (already in scitex-cloud via `ProjectLibraryLinker`) mirrors
papers from the user's central library into `{project_dir}/scitex/scholar/library/`.
`ensure_workspace()` sets up this structure on demand.

---

## What to Build in scitex-cloud

### Feature A: Zotero Import on Library Page

**UI Location:** Library page → new "Import from Zotero" button/panel

**Flow:**
1. User clicks "Import from Zotero" on the library page
2. Modal: user selects source (local DB / tags / collection name)
3. Backend calls `ZoteroLocalReader` → returns `Papers`
4. Papers are added to `UserLibrary` (same as `add_paper()` in `UserLibraryService`)
5. Confirmation shown: "N papers imported from Zotero"

#### Django View to Add

**File:** `apps/scholar_app/views/library/zotero_import.py` (NEW)

```python
"""Zotero import endpoints for the library page."""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.scholar_app.services.user_library_service import UserLibraryService


@login_required
@require_http_methods(["GET"])
def zotero_status(request):
    """Check if local Zotero database is accessible."""
    try:
        from scitex.scholar.integration.zotero import ZoteroLocalReader
        reader = ZoteroLocalReader()
        return JsonResponse({
            "available": True,
            "db_path": str(reader.db_path),
        })
    except FileNotFoundError:
        return JsonResponse({"available": False, "db_path": None})


@login_required
@require_http_methods(["POST"])
def zotero_import(request):
    """Import papers from local Zotero database into user library.

    POST body (JSON):
        mode: "all" | "tags" | "collection"
        tags: list[str]        (for mode="tags")
        collection: str        (for mode="collection")
        match_all: bool        (for mode="tags", default False)
        db_path: str | null    (optional override; null = auto-detect)
    """
    import json
    from scitex.scholar.integration.zotero import ZoteroLocalReader

    data = json.loads(request.body)
    mode = data.get("mode", "all")
    db_path = data.get("db_path") or None

    try:
        reader = ZoteroLocalReader(db_path=db_path)

        if mode == "tags":
            tags = data.get("tags", [])
            papers = reader.read_by_tags(tags, match_all=data.get("match_all", False))
        elif mode == "collection":
            papers = reader.read_by_collection(data.get("collection", ""))
        else:
            papers = reader.read_all()

        # Save each paper to the user's library
        service = UserLibraryService(user=request.user)
        imported, skipped = 0, 0
        for paper in papers:
            try:
                service.add_paper_from_scholar(paper)
                imported += 1
            except Exception:
                skipped += 1

        return JsonResponse({
            "imported": imported,
            "skipped": skipped,
            "total": len(papers),
        })

    except FileNotFoundError as e:
        return JsonResponse({"error": str(e)}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def zotero_collections(request):
    """List available Zotero collections from local database."""
    import sqlite3
    try:
        from scitex.scholar.integration.zotero import ZoteroLocalReader
        reader = ZoteroLocalReader()
        with sqlite3.connect(f"file:{reader.db_path}?mode=ro", uri=True) as conn:
            rows = conn.execute("SELECT collectionName FROM collections ORDER BY collectionName").fetchall()
        return JsonResponse({"collections": [r[0] for r in rows]})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def zotero_tags(request):
    """List available Zotero tags from local database."""
    import sqlite3
    try:
        from scitex.scholar.integration.zotero import ZoteroLocalReader
        reader = ZoteroLocalReader()
        with sqlite3.connect(f"file:{reader.db_path}?mode=ro", uri=True) as conn:
            rows = conn.execute("SELECT name, COUNT(*) as cnt FROM tags GROUP BY name ORDER BY cnt DESC").fetchall()
        return JsonResponse({"tags": [{"name": r[0], "count": r[1]} for r in rows]})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
```

#### URL Registration

**File:** `apps/scholar_app/urls/library.py` — add to existing patterns:

```python
from apps.scholar_app.views.library.zotero_import import (
    zotero_status,
    zotero_import,
    zotero_collections,
    zotero_tags,
)

urlpatterns += [
    path("api/library/zotero/status/",      zotero_status,      name="zotero_status"),
    path("api/library/zotero/import/",      zotero_import,      name="zotero_import"),
    path("api/library/zotero/collections/", zotero_collections, name="zotero_collections"),
    path("api/library/zotero/tags/",        zotero_tags,        name="zotero_tags"),
]
```

#### Template / JS (Library Page)

Add to `apps/scholar_app/templates/scholar_app/personal_library.html` (or its JS):

```javascript
// Check if Zotero is available (on page load)
fetch('/api/library/zotero/status/')
  .then(r => r.json())
  .then(data => {
    if (data.available) {
      document.getElementById('zotero-import-btn').classList.remove('hidden');
      document.getElementById('zotero-db-path').textContent = data.db_path;
    }
  });

// Import button handler
function importFromZotero(mode, options = {}) {
  fetch('/api/library/zotero/import/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()},
    body: JSON.stringify({ mode, ...options })
  })
  .then(r => r.json())
  .then(data => {
    showNotification(`Imported ${data.imported} papers from Zotero (${data.skipped} skipped)`);
    refreshLibraryList();  // reload the papers list
  });
}
```

---

### Feature B: Project-Specific Library on Library Page

**UI Location:** Library page → "My Projects" panel / paper detail view

**Current State:** `ProjectLibraryLinker` already creates symlinks between user library and project dirs.
What's missing: surfacing the per-project BibTeX aggregation and `ensure_workspace()` setup in the UI.

**Flow:**
1. User selects papers in library + picks a project → "Link to Project" (already exists)
2. **NEW:** Show per-project BibTeX file path (`{project_dir}/scitex/scholar/project.bib`)
3. **NEW:** "Setup workspace" button → calls `ensure_workspace(project_dir)` to create the directory structure

#### Django Service Addition

**File:** `apps/scholar_app/services/project_library_linker.py` — add method:

```python
def setup_project_workspace(self, project) -> dict:
    """Ensure scholar workspace exists for a project.

    Delegates to scitex.scholar.ensure_workspace().
    Returns the workspace paths for display in UI.
    """
    from scitex.scholar import ensure_workspace

    project_dir = Path(project.get_local_path())
    workspace = ensure_workspace(project_dir)

    return {
        "workspace_dir": str(workspace),
        "bib_dir": str(workspace / "bib_files"),
        "library_dir": str(workspace / "library"),
        "project_bib": str(project_dir / "scitex" / "scholar" / "project.bib"),
    }
```

#### URL to Add

```python
path("api/library/projects/<int:project_id>/setup-workspace/",
     setup_project_workspace_view, name="setup_project_workspace"),
```

---

## Key Files Reference

### scitex-python (already implemented)

| File | Purpose |
|------|---------|
| `src/scitex/scholar/integration/zotero/local_reader.py` | `ZoteroLocalReader`, `export_for_zotero` |
| `src/scitex/scholar/integration/zotero/__init__.py` | Exports both above |
| `src/scitex/scholar/ensure_workspace.py` | `ensure_workspace(project_dir)` |
| `src/scitex/scholar/storage/ScholarLibrary.py` | `ScholarLibrary` class |

### scitex-cloud (existing, to hook into)

| File | Purpose |
|------|---------|
| `apps/scholar_app/views/library/views.py` | `personal_library()` — main library page |
| `apps/scholar_app/views/library/project_linking.py` | `link_paper_to_project()` |
| `apps/scholar_app/services/user_library_service.py` | `add_paper()`, `link_to_project()` |
| `apps/scholar_app/services/project_library_linker.py` | `sync_project_bibtex()` |
| `apps/scholar_app/models/library/models.py` | `UserLibrary`, `Collection` |
| `apps/scholar_app/urls/library.py` | Library URL patterns |
| `apps/scholar_app/integrations/scitex_scholar.py` | Existing scitex.scholar bridge |

---

## Implementation Priority

1. **`zotero_status` + `zotero_import` endpoints** — minimum viable Zotero import (30 min)
2. **Library page UI: "Import from Zotero" button** — show only when Zotero detected (1 hr)
3. **`zotero_collections` + `zotero_tags`** — richer import filtering (30 min)
4. **`setup_project_workspace` endpoint** — expose ensure_workspace in project UI (30 min)

---

## Notes

- `ZoteroLocalReader` uses **read-only** SQLite connection — safe to call while Zotero is open
- The Windows WSL path auto-detection works: `/mnt/c/Users/wyusu/Zotero/` has 1,384 items
- `UserLibraryService.add_paper()` signature should be checked — it may need a thin adapter
  to accept scitex `Paper` objects (which have `paper.metadata.basic.title` etc.) instead of
  the plain dict format
- All 16 `ZoteroLocalReader` tests pass on the actual `~/Zotero/zotero.sqlite`
