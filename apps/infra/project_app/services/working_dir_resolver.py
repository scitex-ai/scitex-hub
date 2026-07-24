#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Server-side resolution of the authenticated user's working directory.

Single source of truth for the thin upstream-plugin wrappers (writer,
figrecipe, ...) that must feed a ``?working_dir=`` to a package view. The
sweep behind card ``sec-working-dir-passthrough-family`` found THREE
divergent hand-rolled implementations of this same idea, two of which
contained an ``if request.GET.get("working_dir"): return`` early-return —
a pass-through that let a caller-supplied absolute path reach the package
unvalidated (arbitrary cross-tenant host-directory read AND write). This
module exists so every wrapper shares ONE correct implementation.

Contract:
  * The working directory is derived EXCLUSIVELY from server-side data —
    the authenticated user's current project (``get_current_project``,
    which enforces ``can_view``) resolved to its on-disk path. A
    caller-supplied ``?working_dir=`` is NEVER honoured; it is an
    OVERRIDE, not a default (mirrors ``TodoBoardTenancyMiddleware`` which
    discards any client ``?store=``).
  * The resolver returns ``None`` when no project can be resolved. Callers
    that fail closed (``WorkingDirScopedView(fail_closed=True)``) turn that
    into an explicit error / redirect — never a silent fallback to a
    package that will happily accept an env-var or empty path.

``WorkingDirScopedView`` takes its collaborators (the project resolver and
the downstream package view) as constructor arguments so the security
behaviour is exercised with hand-rolled fakes in tests WITHOUT a database
— the same dependency-injection shape as
``OnSiteAuthMiddleware.user_lookup`` (see tests/security/).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def resolve_user_working_dir(request) -> Optional[Path]:
    """Return the requester's current-project directory, or ``None``.

    Purely server-side: the returned path comes from the DB project the
    authenticated user is authorised to view, resolved to an absolute
    filesystem path. Any ``?working_dir=`` on the request is ignored.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None

    # Imported lazily so this module stays import-safe in urlconf context
    # (avoids pulling the Django app registry at module import time).
    from apps.infra.project_app.services.project_utils import (
        get_current_project,
    )

    project = get_current_project(request, user=user)
    if project is None:
        return None

    try:
        working_dir = Path(project.get_local_path()).resolve()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "[working_dir_resolver] get_local_path() failed for user %s: %s",
            getattr(user, "username", "?"),
            exc,
        )
        return None
    return working_dir


class WorkingDirScopedView:
    """Wrap a package view, OVERRIDING ``?working_dir=`` from the project.

    Collaborators are injected (like ``OnSiteAuthMiddleware.user_lookup``)
    so the override / fail-closed behaviour is testable without a DB:

      ``downstream(request, *args) -> HttpResponse`` — the package view.
      ``resolver(request) -> Optional[Path]`` — server-side project dir;
          defaults to :func:`resolve_user_working_dir`.
      ``on_missing(request) -> HttpResponse`` — fail-closed response used
          when ``resolver`` returns ``None`` and ``fail_closed`` is set.
      ``guard(request, *args) -> Optional[HttpResponse]`` — optional extra
          per-site check run AFTER the override (e.g. reject an absolute
          ``?recipe=`` outside the jail); returning a response short-circuits.
          It receives the SAME positional args as ``downstream`` — notably
          the URL ``<path:endpoint>`` capture — so a guard can validate a
          path that rides the URL segment, not only the query/body.

    This object holds NO authentication logic — ``@login_required`` is
    applied to the URL view that calls it, so an anonymous request never
    reaches here.
    """

    def __init__(
        self,
        downstream: Callable,
        *,
        resolver: Optional[Callable] = None,
        on_missing: Optional[Callable] = None,
        guard: Optional[Callable] = None,
        fail_closed: bool = True,
    ):
        self.downstream = downstream
        self.resolver = resolver or resolve_user_working_dir
        self.on_missing = on_missing
        self.guard = guard
        self.fail_closed = fail_closed

    def __call__(self, request, *args):
        working_dir = self.resolver(request)
        if working_dir is not None:
            if request.GET.get("working_dir") and request.GET.get(
                "working_dir"
            ) != str(working_dir):
                logger.warning(
                    "[working_dir_resolver] discarding client-supplied "
                    "working_dir from user %s (server-side tenancy only)",
                    getattr(getattr(request, "user", None), "username", "?"),
                )
            params = request.GET.copy()
            params["working_dir"] = str(working_dir)  # OVERWRITE, never default
            request.GET = params
        elif self.fail_closed:
            if self.on_missing is None:  # pragma: no cover - misconfiguration
                raise RuntimeError(
                    "WorkingDirScopedView(fail_closed=True) needs on_missing"
                )
            return self.on_missing(request)

        if self.guard is not None:
            blocked = self.guard(request, *args)
            if blocked is not None:
                return blocked

        return self.downstream(request, *args)


# EOF
