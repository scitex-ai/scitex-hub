#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which unauthenticated requests deserve a PROVISIONED visitor workspace.

Card hub-visitor-slots-burned-by-scraper-botnet-20260817.

``VisitorAutoLoginMiddleware`` allocates a REAL pool slot — a wiped-and-
verified workspace plus its Gitea repo — for any unauthenticated browser
request outside its skip-list. Measured on prod twice on 2026-08-17
(03:26Z and 18:34Z), a crawler walking GitHub-style repo URLs held the
whole 16-slot pool (``allocated=11 free=5 ready=0 ALLOCATABLE=0``), so
real humans fell through to the shared read-only account and lost write
access to the entire product.

The crawl is indistinguishable from a browser BY IDENTITY: the measured
User-Agents are spoofed Chrome strings from rotating residential IPs. So
this module does not ask *who* is asking. It asks **what the path is
for** — and a page that only READS a repository, or that enumerates the
hub launcher by id, does not need a workspace to render.

Nothing here is a bot heuristic and nothing here decides *when* a visitor
becomes a visitor. Lazy allocation on first genuine interaction, and
requiring a heartbeat before provisioning, remain the operator's open
decisions on the same card.
"""

from __future__ import annotations

import re

#: Third URL segment of every GitHub-style repo-BROWSE route mounted under
#: ``/<username>/<slug>/``. Read off the real URLconf, NOT off the access
#: log — see ``apps/infra/project_app/urls/__init__.py`` (``pulls/``,
#: ``pull/<int>/``, ``compare/<str>/``, ``issues/``) and
#: ``apps/infra/project_app/urls/repository.py`` (``blob/<path>``,
#: ``commits/<branch>/<path>``, ``commit/<hash>/``).
#:
#: ``raw`` has NO route of its own: raw file content is ``/blob/<path>``
#: with ``?mode=raw`` (see ``project_file_view``), which this list already
#: covers via ``blob`` — query strings never change the classification.
#: It is listed anyway because ``/<user>/<repo>/raw/...`` still resolves,
#: through the ``<path:directory_path>/`` catch-all, to a directory read.
REPO_BROWSE_SEGMENTS = (
    "blob",
    "raw",
    "commits",
    "commit",
    "issues",
    "pulls",
    "pull",
    "compare",
)

#: ``/<username>/<slug>/<browse-verb>`` and everything beneath it.
#:
#: The third segment MUST be one of the verbs above. The repository
#: URLconf also ends in a ``<path:directory_path>/`` catch-all, but
#: matching THAT shape here would exempt most of the site — ``/apps/
#: figrecipe/`` is itself a two-segment path — so plain directory
#: browsing is deliberately left allocating, exactly as today.
_REPO_BROWSE_RE = re.compile(
    r"^/[^/]+/[^/]+/(?:" + "|".join(REPO_BROWSE_SEGMENTS) + r")(?:/|$)"
)

#: Hub launcher mount (``config/urls.py``: ``path("apps/home/", ...)``).
HUB_INDEX_PATH = "/apps/home"

#: The query parameter the crawl enumerates sequentially
#: (``/apps/home/?project=NNNNN``). NOTHING in the hub reads it — the
#: launcher resolves the current project from the session and the user's
#: profile (``get_current_project``), never from ``request.GET``. So a
#: numeric ``?project=`` is a probe by construction, not a deep link any
#: page of ours emits.
ENUMERATED_QUERY_PARAM = "project"

#: Only reads are exempt. A POST to an issue or a PR is a genuine
#: interaction and still allocates.
SAFE_METHODS = frozenset({"GET", "HEAD"})


def is_repo_browse_path(path: str) -> bool:
    """True for a GitHub-style repo-BROWSE URL under ``/<user>/<repo>/``."""
    return bool(_REPO_BROWSE_RE.match(path or ""))


def is_hub_project_enumeration(path: str, query_params) -> bool:
    """True for ``/apps/home/?project=<numeric-id>`` — the enumeration probe.

    A bare ``/apps/home/`` is the hero CTA, the one deliberate "enter the
    workspace" click, and MUST keep allocating. Only the numeric
    ``?project=`` form is exempt.
    """
    if (path or "").rstrip("/") != HUB_INDEX_PATH:
        return False
    return query_params.get(ENUMERATED_QUERY_PARAM, "").isdigit()


def needs_no_visitor_workspace(request) -> bool:
    """True when this request can render without a provisioned workspace."""
    if request.method not in SAFE_METHODS:
        return False
    path = request.path
    return is_repo_browse_path(path) or is_hub_project_enumeration(path, request.GET)


# EOF
