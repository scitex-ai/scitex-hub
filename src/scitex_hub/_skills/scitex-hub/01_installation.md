---
description: |
  [TOPIC] scitex-hub Installation
  [DETAILS] pip install scitex-hub with optional [django] (server stack), [gui], [mcp] extras; smoke verify.
tags: [scitex-hub-installation]
---

# Installation

## Standard

```bash
pip install scitex-hub
```

## Optional extras

| Extra     | Adds                                                          |
|-----------|---------------------------------------------------------------|
| `django`  | full Django server stack — DRF, channels, celery, weasyprint, … |
| `gui`     | dearpygui + cairosvg + Pillow (desktop GUI)                   |
| `mcp`     | fastmcp (expose tools to AI agents)                           |

```bash
pip install 'scitex-hub[django]'   # for self-hosting the platform
pip install 'scitex-hub[mcp]'      # for AI-agent integration
```

The pure CLI surface (project / repo / sync / sdk subcommands) works
without any extras.

## Verify

```bash
python -c "import scitex_hub; print(scitex_hub.__version__)"
scitex-hub --help
scitex-hub status
```
