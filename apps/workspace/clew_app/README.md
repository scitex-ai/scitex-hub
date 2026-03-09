# clew_app

Hash-based verification and Clew Registry for reproducible science.

Clew ("clue" in archaic English, from Ariadne's thread) traces research artifacts back to their source data through hash verification chains. This Django app is a **thin wrapper** around the `scitex.clew` Python package — all core logic lives there.

## What This App Does

1. **Webapp** (`/clew/`) — DAG visualization for verification chains
2. **Local Verification API** (`/clew/api/...`) — wraps `scitex.clew` for the frontend
3. **Clew Registry** (`/clew/api/register/`, `/clew/api/verify/`) — remote hash timestamping
4. **Badge** (`/clew/badge/<hash>/`) — embeddable SVG verification badges

## Architecture

```
User / CLI / MCP
       │
       ▼
  scitex.clew          ← Core logic: hashing, tracking, verification, SQLite DB
       │
       ▼
  clew_app (Django)    ← Thin wrapper: 2 view files + 1 model + templates
       │
       ▼
  HashRegistration     ← Server-side timestamps ("this data existed at this time")
```

**Design principle**: Django never implements verification logic. It delegates to `scitex.clew` and only adds server-side timestamps via `HashRegistration`.

## Verification Levels

| Level | Name | Where | What |
|-------|------|-------|------|
| L1 | Cache | Local | Compare stored hashes vs current files |
| L2 | Rerun | Local | Re-execute pipeline and compare outputs |
| L3 | Registered | Server | L2 + register hashes with Clew Registry (timestamped) |

## URL Structure

### Pages (no prefix)

| URL | View | Auth | Purpose |
|-----|------|------|---------|
| `/clew/` | `clew_index` | Optional | Webapp — DAG visualization |
| `/clew/badge/<hash>/` | `badge` | Public | SVG badge for embedding |

### API (`/clew/api/`)

| URL | Method | Auth | View | Purpose |
|-----|--------|------|------|---------|
| `/clew/api/status/` | GET | None | `verification_status` | Status summary (like `git status`) |
| `/clew/api/stats/` | GET | None | `database_stats` | DB statistics |
| `/clew/api/runs/` | GET | None | `list_runs` | List tracked runs |
| `/clew/api/verify-run/` | GET | None | `verify_run` | Verify specific run |
| `/clew/api/verify-chain/` | GET | None | `verify_chain` | Verify dependency chain |
| `/clew/api/dag/json/` | GET | None | `get_dag_data` | DAG data for visualization |
| `/clew/api/dag/mermaid/` | GET | None | `get_mermaid_dag` | Mermaid diagram code |
| `/clew/api/add-examples/` | POST | Login | `add_examples` | Copy example scripts |
| `/clew/api/register/` | POST | API key or session | `register_hash` | Register hash (L3) |
| `/clew/api/verify/<hash>/` | GET | Public | `verify_hash` | Check if hash registered |

## Model

### `HashRegistration`

Stores hashes with **server-side timestamps** (trusted, not client-provided).

| Field | Type | Description |
|-------|------|-------------|
| `hash` | CharField(64) | SHA256 hex string, indexed |
| `registered_at` | DateTimeField | Server timestamp (auto_now_add) |
| `user` | ForeignKey(User) | Who registered |
| `source_type` | CharField(20) | `session`, `file`, `stamp`, or `manual` |
| `session_id` | CharField(100) | Optional session reference |
| `metadata` | JSONField | Arbitrary extra data |

**Constraints**: `unique_together = (hash, user)` — same user can't register same hash twice.

## Authentication

The `/clew/api/register/` endpoint accepts two auth methods:

1. **Session cookie** — browser users already logged in
2. **API key** — `Authorization: Bearer scitex_xxxxx...` (for CLI/programmatic use)

The `/clew/api/verify/<hash>/` endpoint is **public** — anyone (reviewers, journals) can verify without an account. Response is **anonymized** (no usernames, only `registration_count` and `first_registered_at`).

## File Structure

```
clew_app/
├── README.md                  ← You are here
├── __init__.py
├── apps.py                    ← AppConfig
├── models.py                  ← HashRegistration model
├── migrations/
│   └── 0001_initial.py
├── urls/
│   ├── __init__.py            ← Combines index + api/ prefix
│   ├── index.py               ← Page routes + badge
│   └── api.py                 ← API routes (csrf_exempt on register)
├── views/
│   ├── __init__.py            ← clew_index page view
│   ├── api.py                 ← Local verification API (wraps scitex.clew)
│   └── registry.py            ← Clew Registry API (register, verify, badge)
├── templates/clew_app/
│   ├── index.html             ← Main page
│   └── index_partial.html     ← HTMX partial
└── static/clew_app/
    ├── clew-icon.svg
    ├── css/clew.css
    └── ts/
        ├── api-client.ts      ← Frontend API client
        └── clew-init.ts       ← Frontend initialization
```

## Quick Reference

### Register a hash (Python)

```python
from scitex.clew import get_registry
registry = get_registry()  # reads SCITEX_REGISTRY_URL, SCITEX_API_KEY from env
registry.register("deadbeef1234...", source_type="session")
```

### Register a hash (curl)

```bash
curl -X POST https://scitex.ai/clew/api/register/ \
  -H "Authorization: Bearer scitex_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"hash": "abc123example456hash789", "source_type": "session"}'
```

### Verify a hash (curl, public)

```bash
curl https://scitex.ai/clew/api/verify/abc123example456hash789/
```

### Embed badge in README

```markdown
![Clew](https://scitex.ai/clew/badge/YOUR_HASH/?level=L3)
```

### CLI

```bash
scitex clew run ./script.py --register    # L3: verify + register
scitex clew list                          # List tracked runs
scitex clew chain ./results/figure3.png   # Trace back to source
scitex clew status                        # Show changes
```

## Related

- **Core logic**: `~/proj/scitex-code/src/scitex/clew/` (Python package)
- **CLI**: `~/proj/scitex-code/src/scitex/cli/clew.py`
- **MCP tools**: `~/proj/scitex-code/src/scitex/_mcp_tools/clew.py`
- **Registry client**: `~/proj/scitex-code/src/scitex/clew/_registry.py`
