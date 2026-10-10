"""FigRecipe app views — thin hub adapter over the leaf-owned editor.

Leaf flip (card hub-figrecipe-leaf-move-20261009): the editor surface is
owned by ``figrecipe._django`` (leaf repo src-layout, >=0.36). This module
is a thin adapter, not an owner:

- page: :func:`figure_editor` keeps the hub auth gate (anonymous ->
  signup, pinned by test_signed_out_browser_is_sent_to_signup) and hub
  project scoping, and renders the leaf ``figrecipe/workspace.html``.
- context: :func:`build_figrecipe_context` calls the leaf
  ``figrecipe._django.workspace.build_workspace_context`` and stamps only
  what the host owns (``stx_mount`` + SDK shell mount marker + hub project
  object). The hub-local frontend keys (``app_mount_css``,
  ``bridge_entry_name``) and hub shell keys (``module_name``,
  ``module_icon``, ``is_workspace_page``, ``figrecipe_embedded``) are
  retired: the leaf bundle serves the frontend, and the leaf template
  extends the SDK shell, not ``shared/app_editor.html``.
- SECURITY: ``urls/figrecipe.py`` (SITE-2 jail guard) is untouched by this
  move — see that module's docstring. The SPA's API base (``stx_mount``)
  points at the guarded wrapper (``figrecipe_app:figrecipe_editor``), so
  every API call the leaf frontend makes passes the hub jail guard.
- MOUNTS (triple-serve dedupe): the bespoke ``apps/figrecipe/`` include
  (config/urls.py) stays the single serving mount — it carries the jail
  guard and the auth gate. The generic plugin mount
  (``plugin_urlpatterns``) skips the leaf's ``apps/figrecipe/`` route via
  ``_route_taken`` (pinned by test), so the leaf urlconf is never
  double-mounted raw. No route file changes at flip.
- FAIL LOUD: a missing leaf (below the ``figrecipe>=0.36`` floor) raises
  instead of rendering stale hub keys — a wrong-answer-that-looks-right
  page is worse than an error with the floor version in it. A leaf that is
  installed but cannot resolve SDK authority for the hub-scoped project
  with a 404 status (no on-disk workspace yet) is per-project absence,
  not skew: the page degrades to the hub-owned
  ``shared/app_editor.html`` presentation (``data-project-*`` + provider
  meta) instead of 500ing. Any other SDK failure (non-404
  ``AccessError`` — input validation, infra/provider outage — or
  ``CapabilityUnavailable``) raises loud like a missing leaf: masking
  those as a clean 200 hub shell hides real breakage.
"""

from __future__ import annotations

import logging

from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.module_loading import import_string

from apps.infra.project_app.services.project_scope import project_for_scope_app

try:
    from scitex_sdk.host import AccessError as _SDKAccessError
except ImportError:  # pragma: no cover — without the SDK the leaf cannot serve either
    _SDKAccessError = None

#: HTTP status marking per-project authority absence: the SDK raises
#: ``AccessError("Project workspace not found", 404)`` (scitex_sdk/host.py:
#: ``AccessError.__init__(self, message, status=400)`` stores ``.status``)
#: when the hub-scoped project has no on-disk root. ONLY this status
#: degrades to hub presentation — a non-404 ``AccessError`` (input
#: validation, infra/provider outage) and ``CapabilityUnavailable``
#: (unconfigured host capability, no ``.status`` at all) are NOT caught
#: and still propagate loud, exactly like a missing leaf's ImportError.
_LEAF_ABSENT_STATUS = 404


def _is_absent_workspace(exc: BaseException) -> bool:
    """Return True only for 404-status SDK authority absence."""
    if _SDKAccessError is None:
        return False
    return isinstance(exc, _SDKAccessError) and getattr(exc, "status", None) == _LEAF_ABSENT_STATUS

logger = logging.getLogger(__name__)

_LEAF_BUILDER_PATH = "figrecipe._django.workspace.build_workspace_context"

#: Leaf-owned templates served by the hub page and workspace content endpoint.
LEAF_PAGE_TEMPLATE = "figrecipe/workspace.html"
LEAF_PARTIAL_TEMPLATE = "figrecipe/workspace_partial.html"

#: Hub-owned fallback shell for the page when the leaf is installed but the
#: SDK reports 404-status authority absence for the hub-scoped project
#: (see ``_is_absent_workspace``). Extends ``global_base.html``, so it carries
#: the hub project presentation the page contracts pin: ``data-project-*``
#: on ``#app-mount`` and the ``stx-project-provider`` meta. No retired
#: frontend keys (``app_mount_css``/``bridge_entry_name``): the editor bundle
#: is leaf-served or absent, never hub-reconstructed.
HUB_FALLBACK_TEMPLATE = "shared/app_editor.html"


def _stx_mount() -> str:
    """Return the SPA's API base: the guarded figrecipe wrapper mount.

    Derived from the hub URLconf (``figrecipe_app:figrecipe_editor`` ->
    ``/apps/figrecipe/figrecipe/``), never from ``request.path``: the
    workspace content endpoint serves the same partial from
    ``/apps/workspace/content/figrecipe/``, where a path-derived prefix
    would point the SPA at unguarded 404s. This is the legacy mount the
    leaf's own frontend mount test pins (``/apps/figrecipe/figrecipe``).
    """
    return reverse("figrecipe_app:figrecipe_editor").rstrip("/")


def _mount_marker(request):
    """Return the SDK shell mount-marker context for the hub page view.

    The hub page lives at the app root within its include (``pages.py``:
    ``path("", views.figure_editor)``), so ``view_path=""`` — the prefix
    is the whole request path. Falls back to the same derivation when
    ``scitex_sdk`` is not importable ( дев / skew envs); the derivation is
    byte-identical to ``mount_prefix(request, view_path="")``.
    """
    try:
        from scitex_sdk.ui.mount import mount_context
    except ImportError:
        return {
            "stx_mount_prefix": request.path.rstrip("/"),
            "stx_mount_declared": True,
        }
    return mount_context(request, view_path="")


def figure_editor(request, figrecipe_embedded=False):
    """Main figure editor — mounts the leaf-owned React editor.

    Requires an authenticated account.
    """
    if not request.user.is_authenticated:
        return redirect("auth_app:signup")

    # Apptainer pilot: serve the page from the user's own container (their
    # uid, their project jail) when enabled; any container failure falls
    # back to the in-process leaf render below (pilot reversibility). The
    # auth gate above and the SITE-2 API guard stay authoritative either way.
    try:
        from apps.workspace.figrecipe_app.services.container_proxy import (
            ContainerUnavailable,
            enabled,
            proxy_page,
        )

        if enabled():
            try:
                return proxy_page(request)
            except ContainerUnavailable as exc:
                logger.warning("[figrecipe] container unavailable (%r); in-process", exc)
            except Exception as exc:
                # SDK authority errors during token mint (AccessError /
                # CapabilityUnavailable) fall through so the in-process path
                # below applies its own 404-degrade vs fail-loud policy to
                # the IDENTICAL condition — pilot changes transport, never
                # the authority verdict. Anything else re-raises loud.
                try:
                    from scitex_sdk.host import (
                        AccessError as _SDKAccessError2,
                    )
                    from scitex_sdk.host import (
                        CapabilityUnavailable as _SDKUnavailable2,
                    )
                except ImportError:
                    raise
                if isinstance(exc, (_SDKAccessError2, _SDKUnavailable2)):
                    logger.warning(
                        "[figrecipe] container authority (%r); in-process", exc
                    )
                else:
                    raise
    except ImportError:
        pass

    # Project-scope pilot: ?project=owner/slug wins, else the last visited project.
    current_project = project_for_scope_app(request)

    try:
        # Single builder for page and partial (page and partial previously built
        # two divergent context dicts; the flip serves one leaf surface).
        context = build_figrecipe_context(request, current_project)
    except Exception as exc:
        # 404-status authority absence ONLY, not leaf skew: the leaf is
        # installed but the SDK has no workspace for this hub-scoped
        # project, so the page keeps the hub project presentation instead
        # of 500ing. Anything else (non-404 AccessError, CapabilityUnavailable,
        # missing-leaf ImportError) re-raises loud — it must never render as
        # a clean 200 hub shell.
        if not _is_absent_workspace(exc):
            raise
        logger.warning(
            "[figrecipe] leaf authority unavailable (%r); hub presentation", exc
        )
        context = {
            "app_slug": "figrecipe",
            "app_label": "FigRecipe",
            "current_project": current_project,
        }
        if current_project:
            context["project"] = current_project
        else:
            context["needs_project_creation"] = True
        return render(request, HUB_FALLBACK_TEMPLATE, context)

    if current_project:
        context["project"] = current_project
    else:
        context["needs_project_creation"] = True

    return render(request, LEAF_PAGE_TEMPLATE, context)


def build_figrecipe_context(request, current_project=None):
    """Context builder for the hub page and workspace content endpoint.

    Leaf-owned: the leaf builder resolves SDK project authority and the
    working dir. The hub stamps only what the host owns — the guarded API
    mount (``stx_mount``), the SDK shell mount marker, and the hub project
    presentation object (the leaf resolves authority through the SDK, not
    through the hub object). Raises when the leaf cannot serve (fail loud,
    no silent hub parity — see module docstring).
    """
    builder = import_string(_LEAF_BUILDER_PATH)
    context = builder(request, current_project)
    context = dict(context)
    context.update(_mount_marker(request))
    context["stx_mount"] = _stx_mount()
    # Hub scoping wins for the hub shell: the leaf resolves authority
    # through the SDK, not through the hub presentation object.
    context["current_project"] = current_project
    if not current_project:
        context["needs_project_creation"] = True
    return context
