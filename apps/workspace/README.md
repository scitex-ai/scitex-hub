<!-- ---
!-- Timestamp: 2026-03-16 05:25:56
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/scitex-hub/apps/workspace/README.md
!-- --- -->

# Workspace Apps

## Architecture

All workspace apps consume shared packages following DRY and SOC principles:

| Package | Role | What it provides |
|---------|------|------------------|
| **scitex-ui** (`~/proj/scitex-ui`) | Frontend components | React + vanilla TS components, CSS tokens, Python registry |
| **scitex-app** (`~/proj/scitex-app`) | Backend SDK | File I/O, chat streaming, path resolution, CLI, MCP tools |
| **scitex-hub** | Orchestration | Django workspace shell, tab switching, App Store, auth |

## Component Flow

```
scitex-ui (canonical source)
    |
    v  (Vite alias: "scitex-ui" -> scitex_ui.get_static_dir())
scitex-hub/static/shared/ts/components/ (re-export stubs)
    |
    v  (Vite alias: "@" -> static/shared/ts/)
apps/workspace/*/static/*/ts/ (app code imports via @/components/*)
```

## Migrated Components (scitex-hub -> scitex-ui)

| Component | Lines | Used by | Status |
|-----------|-------|---------|--------|
| confirm-modal | ~100 | scholar_app | Re-exports from scitex-ui |
| data-table | ~3700 | public_app, console_app, figrecipe_app | Re-exports from scitex-ui |
| resizer | ~1500 | writer_app | Re-exports from scitex-ui |

## Cloud-Specific (stays here)

| Component | Reason |
|-----------|--------|
| inspiring-spinner | Django template integration |
| workspace-files-tree | Workspace shell auto-init |
| workspace-viewer | Workspace shell auto-init |
| _global-ai-chat | WebSocket + Django auth (candidate for extraction) |
| utils/csrf, api, storage | Django-specific helpers |

## Builtin Apps

| App | Shortcut | Description |
|-----|----------|-------------|
| hub_app | Alt+H | User dashboard, projects |
| writer_app | Alt+W | LaTeX manuscript editor |
| scholar_app | Alt+S | Literature management |
| figrecipe_app | Alt+F | Interactive figure editor |
| clew_app | Alt+R | Verification & reproducibility |
| discovery_app | Alt+X | Dataset discovery |
| docs_app | Alt+D | Documentation viewer |
| apps_app | Alt+M | App Store (browse, install, publish) |
| console_app | - | Terminal & job management |
| tools_app | Alt+T | Shared utilities |
| dev_app | - | Developer tools (internal) |

## Manifest Schema (v2.0.0)

Each app declares its configuration in `manifest.json`:

```json
{
  "$schema_version": "2.0.0",
  "name": "myapp",
  "label": "My App",
  "privileges": [
    {"type": "filesystem", "scope": "project", "reason": "Read/write project files"}
  ],
  "standalone": true,
  "standalone_command": "myapp gui",
  "frontend_type": "react"
}
```

## Creating New Apps

```bash
scitex-hub app init ./my_app --name my_app --frontend react
```

Generated apps automatically consume scitex-ui components and scitex-app SDK.
Apps work both standalone and as scitex-hub extensions (dual-mode).

## Future: AI Chat Extraction

The `_global-ai-chat` component is a candidate for extraction:
- **scitex-ui**: Chat UI component (message list, input, streaming display)
- **scitex-app**: Already has `_chat` module (Anthropic/LiteLLM backends, SSE streaming, Django views)
- **scitex-hub**: Thin wrapper connecting WebSocket auth + workspace context

This would let standalone apps have AI chat without depending on scitex-hub's Django WebSocket.

<!-- EOF -->
