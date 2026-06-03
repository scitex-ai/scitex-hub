<!-- ---
!-- Timestamp: 2026-02-01 04:32:52
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-hub/docs/ISSUES_PAGE.md
!-- --- -->

# SciTeX Hub - GitHub for Researchers

SciTeX Hub aims to be a complete GitHub-like platform for researchers, with all
issue tracking, discussions, and collaboration hosted internally (not on GitHub).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  scitex.ai (Django)                                             │
│  ├── User/Org profile pages: /<username>/, /orgs/<name>/        │
│  ├── Repository pages: /<username>/<repo>/                      │
│  ├── Issues: /<username>/<repo>/issues/                         │
│  ├── Discussions: /<username>/<repo>/discussions/               │
│  └── Pull Requests: /<username>/<repo>/pulls/                   │
├─────────────────────────────────────────────────────────────────┤
│  git.scitex.ai (Gitea)                                          │
│  └── Git hosting backend (clone, push, pull)                    │
├─────────────────────────────────────────────────────────────────┤
│  scitex cloud CLI                                               │
│  └── Thin wrapper calling scitex-hub Django APIs              │
└─────────────────────────────────────────────────────────────────┘
```

## URL Structure (GitHub-style)

| Feature | URL Pattern | Status |
|---------|-------------|--------|
| User profile | `/<username>/` | ✅ Implemented |
| User repos | `/<username>/?tab=repositories` | ✅ Implemented |
| Organization | `/orgs/<name>/` | ❌ Not implemented |
| Repository | `/<username>/<repo>/` | ✅ Implemented |
| Issues list | `/<username>/<repo>/issues/` | ⚠️ Views exist, URLs not wired |
| Create issue | `/<username>/<repo>/issues/new` | ⚠️ Views exist, URLs not wired |
| Discussions | `/<username>/<repo>/discussions/` | ❌ Not implemented |
| Pull requests | `/<username>/<repo>/pulls/` | ⚠️ Partial |

## Implementation Status

### Completed
- [x] Footer links updated to internal URLs
- [x] Landing page community section with internal links
- [x] User profile pages (/<username>/)
- [x] Repository browsing and file editing
- [x] Gitea API client (apps/gitea_app/)

### TODO - Phase 1: Wire up existing Issue views
- [ ] Add issue URLs to project_app/urls.py
- [ ] Test issue creation flow
- [ ] Add issue labels (bug, enhancement, etc.)

### TODO - Phase 2: Organization support
- [ ] Implement organization profile views
- [ ] Organization member listing
- [ ] Pinned repositories feature

### TODO - Phase 3: Discussions
- [ ] Discussion model and views
- [ ] Discussion categories (General, Q&A, Ideas, etc.)

### TODO - Phase 4: CLI Migration
- [ ] Move `scitex cloud` logic from scitex-code to scitex-hub
- [ ] Create Django management commands for CLI operations
- [ ] Keep scitex CLI as thin wrapper calling Django APIs

## Internal Links

These are the target URLs for community feedback:
- Bug Reports: `/scitex-ai/scitex-hub/issues/new?labels=bug`
- Feature Requests: `/scitex-ai/scitex-hub/issues/new?labels=enhancement`
- Discussions: `/scitex-ai/scitex-hub/discussions`
- Organization Page: `/scitex-ai/`

## Setup Required

1. **Create `scitex-ai` organization** in Django admin or via CLI
2. **Create `scitex-hub` repository** under the organization
3. **Wire up issue URLs** in project_app

<!-- EOF -->
