---
description: |
  [TOPIC] Python API
  [DETAILS] Python API for scitex-hub — CloudClient class, project functions, and health_check. For programmatic access from Python scripts..
tags: [scitex-hub-python-api]
---

# Python API

## CloudClient

```python
import scitex_hub

client = scitex_hub.CloudClient(
    api_key=None,    # or set SCITEX_HUB_API_KEY env var
    base_url=None,   # or set SCITEX_HUB_URL env var (default: https://scitex.ai)
)
```

### Methods

```python
# Scholar / literature
result = client.scholar_search(query: str, limit: int = 10) -> dict
# Returns: {"papers": [...]}  (public, no auth required)

result = client.crossref_search(query: str, rows: int = 10, offset: int = 0) -> dict
result = client.crossref_by_doi(doi: str) -> dict

enriched_bib = client.enrich_bibtex(
    bibtex_content: str,
    use_cache: bool = True,
    timeout: int = 120,
) -> str
# Uploads bib, polls for job completion, returns enriched BibTeX string

# Writer / LaTeX
result = client.writer_compile(
    project_id: str,
    document_type: str = "manuscript",  # or "supplementary", "revision"
) -> dict
# Returns: {"pdf_url": ..., ...}

# Project files
result = client.project_list_files(project_id: str, path: str = "") -> dict

# Browser / AI agent tools (onsite)
result = client.get_context(page: str = "") -> dict
# Returns: username, active_skill, all_skills, available_actions, context

result = client.eval_js(code: str, timeout: int = 10) -> dict

result = client.ui_action(
    steps: list,    # each: {"action": "click"|"fill"|"navigate"|..., ...}
    delay_ms: int = 900,
) -> dict

result = client.status() -> dict
# Returns: {"base_url": ..., "api_key_configured": bool, "cloud_status": "online"|"error"|"unreachable"}
```

## Project Functions

```python
from scitex_hub.project import project_list, project_create, project_delete, project_rename

projects: list[dict] = project_list()
# Each dict: id, name, description, created_at, updated_at

new_project: dict = project_create(
    name: str,
    description: str = "",
    template: str = "scitex_minimal",
)
# Returns: {"project_id": ..., "name": ..., "success": True}

deleted: bool = project_delete(slug: str)

updated: dict = project_rename(slug: str, new_name: str)
```

## Package-Level

```python
import scitex_hub

version: str = scitex_hub.get_version()

status: dict = scitex_hub.health_check(endpoint: str | None = None)
# endpoint=None -> local package info only
# endpoint="https://scitex.ai/api/health/" -> HTTP probe

env = scitex_hub.get_environment()          # current Environment object
docker = scitex_hub.DockerManager(env)      # container management
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `SCITEX_HUB_API_KEY` | API key for authenticated endpoints |
| `SCITEX_HUB_URL` | Cloud server base URL (default: https://scitex.ai) |

## Examples

```python
# Search and enrich
client = scitex_hub.CloudClient()
papers = client.scholar_search("spiking neural networks", limit=5)

with open("refs.bib") as f:
    bib = f.read()
enriched = client.enrich_bibtex(bib)
with open("refs_enriched.bib", "w") as f:
    f.write(enriched)

# List projects
from scitex_hub.project import project_list
for p in project_list():
    print(p["name"], p["id"])
```

# EOF
