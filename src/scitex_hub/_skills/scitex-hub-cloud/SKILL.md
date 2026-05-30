---
name: scitex-hub-cloud
description: SciTeX Hub web service integration — health monitoring, web app context, JavaScript evaluation, and browser UI control. Module-level helpers wrap CloudClient.
user-invocable: false
---

# scitex-hub: Cloud Web Service Integration

`scitex_hub` exposes module-level helpers that wrap
:class:`scitex_hub.CloudClient` for the most common web-app interactions:
reading context, evaluating JavaScript, and driving the browser UI.

These are re-exported by the umbrella as `stx.cloud.get_context`,
`stx.cloud.eval_js`, and `stx.cloud.ui_action`.

## Sub-skills

### Setup and Availability
- [01_availability.md](01_availability.md) — `AVAILABLE` flag, optional dependency pattern, installation

### Core API
- [02_health-and-version.md](02_health-and-version.md) — `health_check()`, `get_version()`
- [03_context.md](03_context.md) — `get_context(page, **kw)`: username, page state, available actions
- [04_browser-control.md](04_browser-control.md) — `eval_js(code, timeout, **kw)`, `ui_action(steps, delay_ms, **kw)`

### Integration
- [05_matplotlib-hook.md](05_matplotlib-hook.md) — inline figure display in headless cloud sessions

## Public API Summary

```python
import scitex_hub

scitex_hub.get_version()      # -> str
scitex_hub.health_check()     # -> dict

scitex_hub.get_context(page="", **kw)            # -> dict
scitex_hub.eval_js(code, timeout=10, **kw)       # -> dict
scitex_hub.ui_action(steps, delay_ms=900, **kw)  # -> dict
```

## Quick Start

```python
import scitex_hub

# Verify connection
status = scitex_hub.health_check()

# Get current page context
ctx = scitex_hub.get_context()
print(ctx["username"], ctx["actions"])

# Read from the browser
result = scitex_hub.eval_js("document.title")

# Drive UI
scitex_hub.ui_action([
    {"action": "click", "selector": "#submit-btn"},
])
```
