#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FigRecipe app URLs: the LEAF is the whole user path.

CUTOVER (CCT-2784) + OPERATOR ROUTE RULE (CCT 2763/2764): /apps/figrecipe/
serves the FigRecipe LEAF plugin (login-gated wrapper in figrecipe_django.py
— see that module for why the gate is not optional and why the jail guard
itself stays hub-side for old-direct). The pre-cutover hub-native routes are
NOT mounted here anymore; they live in legacy.py and are served ONLY at
/apps/figrecipe/old-direct/ in dev (mount + gate in config/urls.py, listed
BEFORE the default because the leaf's <path:endpoint> catch-all would
otherwise swallow old-direct URLs), never in production, with no tiles or
links.
"""

from __future__ import annotations

from .figrecipe_django import urlpatterns as figrecipe_django_patterns

# No app_name here ON PURPOSE. The leaf is mounted under its own namespace
# (figrecipe-leaf), and Django only propagates nested namespaces to reverse()
# when the outer include sets no app_name of its own (resolvers.py _populate:
# an app_name'd resolver registers only itself). An outer app_name would make
# figrecipe-leaf:figure_editor unresolvable by reverse() — the skill check
# (llm_app.E001) caught exactly this on scholar. The hub-side
# "figrecipe_app" app_name lives on in legacy.py for the old-direct mount.
urlpatterns = figrecipe_django_patterns


# EOF
