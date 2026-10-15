#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Old-direct reference: the pre-cutover hub-native Scholar routes.

OPERATOR ROUTE RULE (CCT 2763/2764) + RED START (CCT 2806, binding): current
hub-side app routes move to ``apps/<app>/old-direct`` for ALL apps, and
old-direct NEVER ships in production — dev-gated (``settings.DEBUG`` or an
explicit dev flag), no launcher tiles/links, no user path, deleted outright
once parity closes. RED START sequencing per app, no gradual flip: FIRST the
plain hub-side routes go dark (404, including a currently-live v1), THEN the
plain route is relit ONLY when that app's leaf plugin-ification succeeds —
no app earns its route back without a working leaf plugin. This module is
Scholar's instance of that convention: the exact hub-native route set that
used to be served at /apps/scholar/ alongside the leaf, now served ONLY at
/apps/scholar/old-direct/ as the parity/fallback reference while v1 parity
is open (/apps/scholar/ itself is relit by the working Scholar leaf through
the gated wrapper). FigRecipe / Writer / Console / every other hub-side leaf
route follows the identical pattern as it migrates — same mount shape, same
gate, same no-tiles rule, and per CCT 2795 no /v2/ alias remains anywhere.

The mount itself lives in config/urls.py (dev-gated there); this module
only assembles the patterns and owns the gate predicate so both the mount
and the tests read one definition.
"""

from __future__ import annotations

from django.conf import settings

from .api import urlpatterns as api_patterns
from .bibtex import urlpatterns as bibtex_patterns
from .library import urlpatterns as library_patterns
from .repository import urlpatterns as repository_patterns
from .search import urlpatterns as search_patterns
from .workspace import urlpatterns as workspace_patterns

app_name = "scholar_app"

# The complete pre-cutover hub-native surface, byte-identical routes.
urlpatterns = (
    workspace_patterns
    + search_patterns
    + library_patterns
    + bibtex_patterns
    + repository_patterns
    + api_patterns
)


def old_direct_enabled() -> bool:
    """Whether the old-direct reference mount may exist in this process.

    Dev-only by rule: ``settings.DEBUG`` (dev/staging settings) or the
    explicit ``SCHOLAR_OLD_DIRECT_ENABLED`` escape hatch for a
    production-like box where parity is being compared. Production has
    neither, so old-direct can never ship there.
    """
    return bool(settings.DEBUG or getattr(settings, "SCHOLAR_OLD_DIRECT_ENABLED", False))


# EOF
