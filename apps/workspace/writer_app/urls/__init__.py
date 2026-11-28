#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub-native Writer route modules (dev-only old-direct reference).

/apps/writer/ is NOT mounted from here: the generic plugin mount
(``apps.workspace.apps_app.services.plugin_apps``) serves whatever routes the
scitex-writer leaf's own urlconf declares, through the ``scitex.apps``
contract. The hub names no writer route.

The submodules of this package are the pre-cutover hub-native routes,
assembled by legacy.py and served ONLY at /apps/writer/old-direct/ in dev
(mount + gate in config/urls.py), never in production, and deleted outright
once v1 parity closes.
"""

# EOF
