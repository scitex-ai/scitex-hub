# scitex-python v2.18.0 Handoff

**Date**: 2026-02-18
**PyPI**: `pip install scitex==2.18.0`
**PR**: https://github.com/ywatanabe1989/scitex-python/pull/164

## Changes Summary

### 1. Citation Graph Visualization (v2.17.x)
- `scitex.scholar.citation_graph.visualization` — new module
- `plot_citation_graph()` with pluggable backends: figrecipe, scitex.plt, pyvis
- `CitationGraph.to_networkx()` method added to models
- **Impact on scitex-cloud**: None. `CitationGraphBuilder` API unchanged. Cloud's `services/citation_graph/service.py` continues to work as-is.

### 2. API Minimization (v2.17.x)
- `scitex.scholar` public API reduced from 59 to 14 names
- Hidden names still importable via `__getattr__` backward compatibility
- **Impact on scitex-cloud**: None. All deep imports (`from scitex.scholar.formatting import ...`, `from scitex.scholar.pipelines.ScholarPipelineSearchParallel import ...`) are unchanged. Top-level imports like `from scitex.scholar import ScholarConfig` still work via `__getattr__`.

### 3. Standalone Flask GUI (v2.17.x)
- `scitex scholar gui` CLI command launches standalone Citation Graph viewer
- Located at `scitex.scholar.gui` — Flask app with force-directed SVG graph
- **Impact on scitex-cloud**: None. This is a standalone alternative, not a replacement for the Django scholar_app. Shares the same `CitationGraphBuilder` backend.

### 4. ZoteroLocalReader Additions (v2.17.x)
- New methods: `list_collections()`, `list_tags()`
- **Impact on scitex-cloud**: New capabilities available. `apps/scholar_app/views/library/zotero_import.py` can now list Zotero collections and tags.

### 5. Docker Support for Scholar GUI (v2.18.0)
- `Dockerfile.scholar-gui` + `docker-compose.scholar-gui.yml`
- New `[scholar-gui]` optional dependency (Flask, click, crossref-local, openalex-local)
- `_app.py` now checks `CROSSREF_DB_PATH` environment variable for DB path injection
- **Impact on scitex-cloud**: None. Separate deployment path.

## Compatibility Check

All scitex-cloud imports verified compatible:

| Import Pattern | Status |
|---|---|
| `from scitex.scholar import ScholarConfig` | OK (via `__getattr__`) |
| `from scitex.scholar import ensure_workspace` | OK (via `__getattr__`) |
| `from scitex.scholar.citation_graph import CitationGraphBuilder` | OK (unchanged) |
| `from scitex.scholar.integration.zotero import ZoteroLocalReader` | OK (new methods added) |
| `from scitex.scholar.formatting import ...` | OK (unchanged) |
| `from scitex.scholar.local_dbs import crossref_scitex` | OK (unchanged) |
| `from scitex.scholar.pipelines.* import ...` | OK (unchanged) |
| `from scitex.scholar.storage import BibTeXHandler` | OK (unchanged) |

## Action Items for scitex-cloud

- **Required**: None. All changes are backward-compatible.
- **Optional**: Update Docker images to pull `scitex>=2.18.0` for new features.
- **Optional**: Use `ZoteroLocalReader.list_collections()` / `.list_tags()` in library views.

## New `scitex.scholar` Public API (14 names)

```
CitationGraphBuilder, Scholar, ScholarConfig, ScholarLibrary,
ZoteroLocalReader, build_citation_graph, ensure_workspace,
formatting, local_dbs, pipelines, plot_citation_graph,
search_engines, storage, version_info
```
