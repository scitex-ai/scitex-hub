"""SciTeX Agentic Journal — cloud-side thin wrapper.

This Django sub-app is a **thin shim** over the standalone
``scitex-agentic-journal`` package. The standalone owns:

- The reviewer-dashboard logic + templates (`_django/`).
- The journal manifest + permissions (`_django/manifest.json`).
- The ARA rubric + reviewer-agent runner (`_review/`).
- The MCP tool surface (`_mcp/`).

The wrapper owns nothing except the registration into the
``apps/workspace`` discovery list. If the wrapper grows beyond
``apps.py`` + ``urls.py`` + ``manifest.json``, that's a smell — push
the logic back to ``scitex-agentic-journal`` upstream.
"""

default_app_config = "apps.workspace.agentic_journal_app.apps.AgenticJournalAppConfig"
