"""SciTeX Live Paper — cloud-side thin wrapper.

This Django sub-app is a **thin shim** over the standalone
``scitex-live-paper`` package. The standalone owns:

- The viewer + handlers + services (``_django/``).
- The plugin-mount contract (``mount(resolver=...)``) — its multi-
  tenant entry point. The hub wrapper currently uses the single-
  tenant env-pinned path (``SCITEX_LIVE_PAPER_BUNDLE``) and will
  flip to ``mount(resolver=...)`` in a follow-up once live-paper's
  ``BundleContext`` dataclass lands publicly.

The wrapper owns nothing except the registration into the
``apps/workspace`` discovery list and the URL include. If the
wrapper grows beyond ``apps.py`` + ``urls.py`` + ``manifest.json``,
that's a smell — push the logic back upstream.
"""

default_app_config = "apps.workspace.live_paper_app.apps.LivePaperAppConfig"
