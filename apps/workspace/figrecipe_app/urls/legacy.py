#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Old-direct reference: the pre-cutover hub-native FigRecipe routes.

OPERATOR ROUTE RULE (CCT 2763/2764) + RED START (CCT 2806, binding): current
hub-side app routes move to ``apps/<app>/old-direct`` for ALL apps, and
old-direct NEVER ships in production — dev-gated (``settings.DEBUG`` or an
explicit dev flag), no launcher tiles/links, no user path, deleted outright
once parity closes. RED START sequencing per app, no gradual flip: FIRST the
plain hub-side routes go dark (404, including a currently-live v1), THEN the
plain route is relit ONLY when that app's leaf plugin-ification succeeds —
no app earns its route back without a working leaf plugin. This module is
FigRecipe's instance of that convention (Scholar #1074 template): the exact
hub-native route set that used to be served at /apps/figrecipe/, now served
ONLY at /apps/figrecipe/old-direct/ as the parity/fallback reference while
v1 parity is open (/apps/figrecipe/ itself is relit by the working FigRecipe
leaf through the login-gated wrapper in figrecipe_django.py).

WHAT LIVES HERE (byte-identical to the pre-cutover user-path mount):

* ``pages.py`` — ``""`` -> the hub adapter page (auth gate to signup,
  per-UID container proxy pilot from #1068, project scoping, leaf template
  render). KEPT: the proxy pilot and the adapter's fail-loud policy are
  still the reference the leaf is measured against.
* ``figrecipe.py`` — ``figrecipe/`` + ``figrecipe/<path:endpoint>`` behind
  the SITE-2 jail guard. KEPT UNTIL SAC-MANAGER SIGN-OFF: the guard stays
  authoritative here while leaf-side tenant containment (leaf manifest
  ``mount_policy`` jail declaration, figrecipe#456) is proven. Thinning the
  guard is a SAC-manager call, not this move.

The mount itself lives in config/urls.py (dev-gated there, and listed
BEFORE the default mount ON PURPOSE: the leaf urlconf carries a
``<path:endpoint>`` catch-all, so a default-first order would swallow every
old-direct URL into the leaf dispatcher); this module only assembles the
patterns and owns the gate predicate so both the mount and the tests read
one definition.

NOT MOVED (kept with reasons, same as the cutover leaves them):

* ``FigrecipeAppConfig`` (label ``vis_app``) — DB continuity for
  migrations 0001-0005 + 0006_drop_all_orm_models.
* ``models/`` + ``migrations/0001-0005`` — deletion/squash is TRACKED on
  card hub-figrecipe-leaf-move-20261009 but NOT executed here: it needs
  prod-0006-applied evidence + lead sign-off (CCT 2790). Touching them in
  this handover would strand any database that has not applied 0006.
* Hub manifest ``builtin: true`` — binding CCT 2770: built-in means a
  pre-installed PLUGIN (pip-installed leaf), not hub-native code. The tile
  keeps resolving to /apps/figrecipe/, which the leaf now serves.
"""

from __future__ import annotations

from django.conf import settings

from .figrecipe import urlpatterns as figrecipe_patterns
from .pages import urlpatterns as page_patterns

app_name = "figrecipe_app"

# The complete pre-cutover hub-native surface, byte-identical routes.
urlpatterns = page_patterns + figrecipe_patterns


def old_direct_enabled() -> bool:
    """Whether the old-direct reference mount may exist in this process.

    Dev-only by rule: ``settings.DEBUG`` (dev/staging settings) or the
    explicit ``FIGRECIPE_OLD_DIRECT_ENABLED`` escape hatch for a
    production-like box where parity is being compared. Production has
    neither, so old-direct can never ship there.
    """
    return bool(settings.DEBUG or getattr(settings, "FIGRECIPE_OLD_DIRECT_ENABLED", False))


# EOF
