#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar app URLs: the LEAF is the whole user path.

CUTOVER (CCT 2760) + OPERATOR ROUTE RULE (CCT 2763/2764): /apps/scholar/
serves the Scholar LEAF plugin (login-gated wrapper in scholar_django.py —
see that module for why the gate is not optional). The pre-cutover
hub-native routes are NOT mounted here anymore; they live in legacy.py and
are served ONLY at /apps/scholar/old-direct/ in dev (mount + gate in
config/urls.py), never in production, with no tiles or links.
"""

from __future__ import annotations

from .scholar_django import urlpatterns as scholar_django_patterns

# No app_name here ON PURPOSE. The leaf is mounted under its own namespaces
# (scholar-leaf / scholar-leaf-v2), and Django only propagates nested
# namespaces to reverse() when the outer include sets no app_name of its own
# (resolvers.py _populate: an app_name'd resolver registers only itself).
# An outer app_name would make scholar-leaf:index unresolvable by reverse()
# — the skill check (llm_app.E001) caught exactly this. The hub-side
# "scholar_app" app_name lives on in legacy.py for the old-direct mount.
urlpatterns = scholar_django_patterns


# EOF
