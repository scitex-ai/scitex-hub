#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Old-direct reference: the pre-cutover hub-native Writer routes.

OPERATOR ROUTE RULE (CCT 2763/2764) + RED START (CCT 2806, binding): current
hub-side app routes move to ``apps/<app>/old-direct`` for ALL apps, and
old-direct NEVER ships in production — dev-gated (``settings.DEBUG`` or an
explicit dev flag), no launcher tiles/links, no user path, deleted outright
once parity closes. RED START sequencing per app, no gradual flip: FIRST the
plain hub-side routes go dark (404, including a currently-live v1), THEN the
plain route is relit ONLY when that app's leaf plugin-ification succeeds —
no app earns its route back without a working leaf plugin. This module is
Writer's instance of that convention (Scholar #1074 / FigRecipe #1075
template): the exact hub-native route set that used to be served at
/apps/writer/, now served ONLY at /apps/writer/old-direct/ as the
parity/fallback reference while v1 parity is open (/apps/writer/ itself is
relit by the working Writer leaf through the SITE-3 wrapper in
writer_django.py).

WHAT LIVES HERE (byte-identical to the pre-cutover user-path mount):

* feature pages — ``api/``, ``editor/``, ``compilation/``,
  ``version-control/``, ``arxiv/``, ``collaboration/`` + the ``""`` index
  adapter. KEPT: the hub adapter surface the leaf is measured against.
* ``writer_django.v2_urlpatterns`` — ``editor-v2/``, ``viewer-v2/``,
  ``v2/<path:endpoint>`` behind the SITE-3 jail guard. KEPT: these ARE the
  guard (WorkingDirScopedView server-side `working_dir` override + login +
  Origin check) applied to the leaf views — the parity reference for the
  default path, which rebinds the SAME function objects to the leaf paths.

The mount itself lives in config/urls.py (dev-gated there, and listed
BEFORE the default mount ON PURPOSE: the leaf urlconf carries a
``<path:endpoint>`` catch-all, so a default-first order would swallow every
old-direct URL into the leaf dispatcher); this module only assembles the
patterns and owns the gate predicate so both the mount and the tests read
one definition.

FAIL-CLOSED NOTE (writer-specific, differs from scholar/figrecipe): the v2
paths are leaf-BACKED (SITE-3 views over leaf views), not hub-native views.
When the leaf is unimportable, `v2_urlpatterns` is [] — the v2 reference
goes dark WITH the leaf (no silent fallback, CCT 2768) while the hub-native
feature surface below still serves. That is the honest shape: there is no
hub-native equivalent of v2 to fall back TO.

NOT MOVED (kept with reasons, same as the cutover leaves them):

* ``WriterAppConfig`` — DB continuity for the writer models/migrations.
* ``models/`` + ``migrations/`` — deletion/squash needs prod-applied
  evidence + lead sign-off (CCT 2790 pattern) — tracked, NOT executed.
* Hub manifest ``builtin: true`` — binding CCT 2770: built-in means a
  pre-installed PLUGIN (pip-installed leaf), not hub-native code. The tile
  keeps resolving to /apps/writer/, which the leaf now serves.
"""

from __future__ import annotations

from django.conf import settings
from django.urls import include, path

from .writer_django import v2_urlpatterns

app_name = "writer_app"

# The complete pre-cutover hub-native surface, byte-identical routes, order,
# and include shape (string includes, exactly as urls/__init__.py mounted
# them — the v2 insert sat at position 1, ahead of editor/). Nested tuple
# includes are NOT used here on purpose: they would nest a second
# "writer_app" namespace under the old-direct mount's own "writer_app" and
# break every reverse("writer_app:...") the parity reference exists to keep
# resolving (scholar's legacy concatenates flat lists for the same reason;
# writer's prefixed groups keep their string includes instead).
urlpatterns = [
    path("api/", include("apps.workspace.writer_app.urls.api")),
    path("", include(v2_urlpatterns)),
    path("editor/", include("apps.workspace.writer_app.urls.editor")),
    path("compilation/", include("apps.workspace.writer_app.urls.compilation")),
    path(
        "version-control/",
        include("apps.workspace.writer_app.urls.version_control"),
    ),
    path("arxiv/", include("apps.workspace.writer_app.urls.arxiv")),
    path(
        "collaboration/",
        include("apps.workspace.writer_app.urls.collaboration"),
    ),
    path("", include("apps.workspace.writer_app.urls.index")),
]


def old_direct_enabled() -> bool:
    """Whether the old-direct reference mount may exist in this process.

    Dev-only by rule: ``settings.DEBUG`` (dev/staging settings) or the
    explicit ``WRITER_OLD_DIRECT_ENABLED`` escape hatch for a
    production-like box where parity is being compared. Production has
    neither, so old-direct can never ship there.
    """
    return bool(settings.DEBUG or getattr(settings, "WRITER_OLD_DIRECT_ENABLED", False))


# EOF
