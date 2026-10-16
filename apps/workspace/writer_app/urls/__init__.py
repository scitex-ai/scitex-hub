#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Writer app URLs: the LEAF is the whole user path.

CUTOVER + OPERATOR ROUTE RULE (CCT 2763/2764) + RED START (CCT 2806,
binding): /apps/writer/ serves the Writer LEAF plugin (SITE-3 wrapper in
writer_django.py — see that module for why the working_dir injection stays
on the default path and which leaf routes the leaf authorizes itself).
RED START: the plain hub-side routes went dark first (404) and the plain
route is relit ONLY by the working leaf plugin — no app earns its route back
without one. The pre-cutover hub-native routes are NOT mounted here anymore;
they live in legacy.py and are served ONLY at /apps/writer/old-direct/ in
dev (mount + gate in config/urls.py), never in production, and old-direct
is deleted outright once v1 parity closes. CCT 2795: NO /v2/ alias remains
(the v2 paths live on ONLY as the old-direct reference, not as an alias).
"""

from __future__ import annotations

from .writer_django import urlpatterns as writer_leaf_patterns

# No app_name here ON PURPOSE. The leaf is mounted under its own namespace
# (writer-leaf — CCT 2795: no alias mount, so there is exactly one), and
# Django only propagates nested namespaces to reverse() when the outer
# include sets no app_name of its own (resolvers.py _populate: an app_name'd
# resolver registers only itself). An outer app_name would make
# writer-leaf:editor unresolvable by reverse() — the skill check
# (llm_app.E001) caught exactly this on scholar. The hub-side "writer_app"
# app_name lives on in legacy.py for the old-direct mount.
urlpatterns = writer_leaf_patterns


# EOF
