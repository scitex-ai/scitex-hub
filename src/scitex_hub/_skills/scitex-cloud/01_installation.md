---
description: |
  [TOPIC] scitex-cloud Installation
  [DETAILS] pip install scitex-cloud with optional [django] (server stack), [gui], [mcp] extras; smoke verify.
tags: [scitex-cloud-installation]
---

# Installation

## Standard

```bash
pip install scitex-cloud
```

## Optional extras

| Extra     | Adds                                                          |
|-----------|---------------------------------------------------------------|
| `django`  | full Django server stack — DRF, channels, celery, weasyprint, … |
| `gui`     | dearpygui + cairosvg + Pillow (desktop GUI)                   |
| `mcp`     | fastmcp (expose tools to AI agents)                           |

```bash
pip install 'scitex-cloud[django]'   # for self-hosting the platform
pip install 'scitex-cloud[mcp]'      # for AI-agent integration
```

The pure CLI surface (project / repo / sync / sdk subcommands) works
without any extras.

## Verify

```bash
python -c "import scitex_hub; print(scitex_hub.__version__)"
scitex-cloud --help
scitex-cloud show-status
```
