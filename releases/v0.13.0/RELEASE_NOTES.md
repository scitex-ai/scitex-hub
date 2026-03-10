# v0.13.0 - 2026-03-10

## Store URL Fix & Hub/Org Unification

### Store API URLs
- Fixed all API URLs from `/apps/api/` to `/apps/store/api/` after module rename
- Module reorder, install, toggle, star, dev-install all work again

### Hub & Org Profile Consistency
- Extracted shared mode switcher partial (DRY: org vs personal tabs)
- Fixed org profile DOM: removed invalid nested `<main>`, eliminated `hub-workspace` flex wrapper
- Unified CSS classes: replaced `org-mode-*` with `hub-mode-*`
- Fixed context processor registry order override for modules without installations

### Terminal Broker Fix
- Fixed SLURM job lookup: was filtering by user `scitex`, but Docker submits as `root`
- Added automatic stale job cleanup on broker startup (self-healing)
- Added `make slurm-cleanup` command for manual admin use

### Refactors
- Clew: split monolithic CSS into modular directory structure
- Scholar: extracted paper-actions module, improved library init
