---
description: |
  [TOPIC] Vite Frontend Build
  [DETAILS] Vite frontend build — HMR, entry points, template tags, troubleshooting..
tags: [scitex-hub-vite-frontend]
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

## Dynamic Hostname (LAN + localhost)

Never hardcode `VITE_HOST_IP` or any IP in templates. Use `window.location.hostname` so the same build works for localhost and LAN access:

```typescript
// Good
const host = window.location.hostname;
const wsUrl = `ws://${host}:${port}/ws/...`;

// Bad — breaks on LAN / remote access
const host = import.meta.env.VITE_HOST_IP || "localhost";
```

This applies to WebSocket URLs, API base URLs, and any URL constructed in TypeScript that needs to reach the backend.

## SDK UI integration

The required `scitex-sdk>=0.3.0` owns UI sources and assets. Vite discovers
`scitex_sdk.get_frontend_package_dir()` from the active Python environment,
then checks SDK source checkouts under `.apps/scitex-sdk/` or `../scitex-sdk/`.
Canonical imports use `@scitex/sdk/ui/...` and its package exports. The npm
`file:` dependency must name that environment's frontend package directory;
regenerate its lockfile after changing environments.

`SCITEX_UI_STATIC` remains a trusted build override, but must point to
`scitex_sdk/ui/static/scitex_sdk/ui` inside the SDK frontend package. Old
`scitex-ui` and deep `@scitex/ui/src/scitex_ui/static/scitex_ui` aliases are a
transitional bridge for uncutover leaf sources; both resolve only SDK files.
Those leaf imports remain a migration gate, rather than a second UI owner.

Shared Vite entry names start with `scitex_sdk/ui/`. Development uses Vite's
`/@fs/` route for installed package files; production uses the built manifest.
