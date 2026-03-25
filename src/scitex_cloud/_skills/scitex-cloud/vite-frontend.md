---
description: Vite frontend build — HMR, entry points, template tags, troubleshooting.
---

# Vite Frontend Build

## Overview
Vite handles all TypeScript/CSS compilation with Hot Module Replacement (HMR).
**DO NOT run `tsc` manually** — Vite handles everything.

## HMR Flow
Edit `.ts` -> Vite detects -> HMR to browser (~200ms)

## Template Tags
```html
{% load vite %}
{% vite_hmr_client %}
{% vite_script 'code_app/workspace' %}
```

## Entry Points
- Config: `vite.config.ts` + `vite.entries.ts`
- `getEntryPoints()` in `vite.entries.ts` supports glob-like auto-discovery
- Entry pattern: `{app}/name` -> `apps/{app}/static/{app}/ts/name.ts`
- Dev app config: `vite.config.devapp.ts` (for standalone app development)

## TypeScript Rules
- Always use `.ts` extension (never `.js`)
- Use `.ts` extension in imports
- External TypeScript files only (no inline `<script>` in templates)

## Troubleshooting
```bash
# Vite logs
tail -f ./logs/vite-dev.log

# Restart dev environment
make env=dev restart
```

## scitex-ui Integration
Vite auto-discovers scitex-ui static directory:
1. `.apps/scitex-ui/` (dev-installed, preferred)
2. `../scitex-ui/` (sibling checkout)
3. pip-installed location (fallback)
