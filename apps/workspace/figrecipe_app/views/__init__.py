"""FigRecipe app views — thin hub adapter over the leaf-owned editor.

Leaf move (pilot, card hub-figrecipe-leaf-move-20261009): the editor surface
is owned by ``figrecipe._django`` (leaf repo src-layout, >=0.36 — workspace.py,
workspace.html/workspace_partial.html). This module is a thin adapter, not an
owner:

- context: :func:`build_figrecipe_context` prefers the leaf
  ``figrecipe._django.workspace.build_workspace_context`` and falls back to
  the hub-local keys when the installed leaf predates the workspace surface
  (<0.36 has no ``figrecipe._django.workspace`` module at all) or the SDK
  project authority is unavailable. It never raises for a missing/failing
  leaf — the page and the workspace content endpoint must keep rendering on
  a stale install.
- page: :func:`figure_editor` keeps the hub auth gate (anonymous -> signup,
  pinned by test_signed_out_browser_is_sent_to_signup) and hub project
  scoping, and shares the single context builder with the partial (page and
  partial previously built two divergent context dicts).
- SECURITY: ``urls/figrecipe.py`` (SITE-2 jail guard) is untouched by this
  move — see that module's docstring.

Retire mapping for the follow-up flip (NOT done here — the leaf page render
needs an authed verification with figrecipe>=0.36 installed, and no dev DB
is reachable from the pilot env to prove it):

- templates/figrecipe_app/editor.html          -> figrecipe/workspace.html
- templates/figrecipe_app/figrecipe_partial.html -> figrecipe/workspace_partial.html
- hub-local fallback keys below               -> leaf build_workspace_context
"""

import logging

from django.shortcuts import redirect, render
from django.utils.module_loading import import_string

from apps.infra.project_app.services.project_scope import project_for_scope_app

logger = logging.getLogger(__name__)

_LEAF_BUILDER_PATH = "figrecipe._django.workspace.build_workspace_context"


def _leaf_build_context(request, current_project=None):
    """Return the leaf context dict, or ``None`` when the leaf can't serve.

    ``None`` covers both "leaf too old to have the surface" (ImportError /
    AttributeError on ``figrecipe._django.workspace`` — e.g. installed 0.35.0)
    and "leaf present but SDK project authority unavailable" (AccessError /
    CapabilityUnavailable from ``prepare_request``). Either way the caller
    falls back to hub-local keys, so a stale install or an unconfigured
    provider degrades to hub parity instead of 500ing the page.
    """
    try:
        builder = import_string(_LEAF_BUILDER_PATH)
    except Exception as exc:  # noqa: BLE001 — any import failure means "leaf can't serve"
        logger.debug("[figrecipe] leaf context builder unavailable (%r); hub fallback", exc)
        return None
    try:
        return builder(request, current_project)
    except Exception as exc:  # noqa: BLE001 — fallback must hold for any leaf failure
        logger.warning("[figrecipe] leaf context builder failed (%r); hub fallback", exc)
        return None


def figure_editor(request, figrecipe_embedded=False):
    """Main figure editor — mounts figrecipe React editor.

    Requires an authenticated account.
    """
    if not request.user.is_authenticated:
        return redirect("auth_app:signup")

    # Project-scope pilot: ?project=owner/slug wins, else the last visited project.
    current_project = project_for_scope_app(request)

    # Single builder for page and partial (dedupe: the page previously built
    # its own inline dict diverging from the partial's builder).
    context = build_figrecipe_context(request, current_project)
    context.update(
        {
            "module_name": "FigRecipe",
            "module_icon": "fa-chart-line",
            "is_workspace_page": True,
            "figrecipe_embedded": figrecipe_embedded,
            # Generic app editor context (used by shared/app_editor.html)
            # (app_* keys already set by the builder; repeated here so the
            # page contract reads in one place.)
            "app_slug": "figrecipe",
            "app_label": "FigRecipe",
        }
    )
    if current_project:
        context["project"] = current_project
    else:
        context["needs_project_creation"] = True

    return render(request, "figrecipe_app/editor.html", context)


def build_figrecipe_context(request, current_project=None):
    """Context builder for workspace content endpoint (partial rendering).

    Leaf-first: the leaf-owned builder wins when the installed figrecipe
    provides it (>=0.36); hub-local keys fill the gaps the hub shell still
    needs (mount CSS, bridge entry, hub project object) and are the whole
    context when the leaf can't serve.
    """
    context = {
        "app_slug": "figrecipe",
        "app_label": "FigRecipe",
        "app_mount_css": "figrecipe_app/css/figrecipe-mount.css",
        "bridge_entry_name": "figrecipe_app/figrecipe-bridge-init",
        "current_project": current_project,
    }
    leaf = _leaf_build_context(request, current_project)
    if leaf:
        context.update(leaf)
        # Hub scoping wins for the hub shell: the leaf resolves authority
        # through the SDK, not through the hub presentation object.
        context["current_project"] = current_project
    if not current_project:
        context["needs_project_creation"] = True
    return context
