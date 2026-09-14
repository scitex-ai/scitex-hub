"""Shared scope-meta injection for hub leaf-app bridges.

The scitex-app manifest is the single source of truth for a leaf app's
release scope (``user`` vs ``project``, d8528de / #185). scitex-app's host
view layer (``scitex_editor_page`` -> ``_inject_scope_meta``) stamps
``<meta name="stx-app-scope" content="project">`` into the served HTML ONLY
for leaves embedded through that factory (e.g. Scholar's /apps/scholar/v2/).

The Hub's Writer + FigRecipe bridges do NOT go through that factory — they
call the raw leaf ``editor_page`` via WorkingDirScopedView (a pure
pass-through), so their pages carry no scope marker, and the leaf's
``mountProjectSelectorByScope`` (which reads the marker) has nothing to mount
against. This helper applies the SAME injection contract to a hub-served leaf
response, reusing scitex-app's own emitter (never re-implementing it) and the
registry's manifest scope (never duplicating leaf logic).

Scope semantics (from scitex-app ``_app_scope``): project-scoped -> emit the
marker; user-scoped / absent -> emit NOTHING (page byte-identical). This keeps
the "global header never forces a selector" ruling intact — the marker only
tells the per-app surface it MAY offer selection.
"""

from __future__ import annotations

from django.http import HttpResponse

# scitex-app is an editable source mount; the contract module may be absent if
# the mount predates d8528de. Guard the import so a stale mount degrades to
# "no marker" (the safe direction) rather than 500'ing every leaf page.
try:
    from scitex_app._app_scope import _inject_scope_meta
except Exception:  # noqa: BLE001 - scitex-app not advanced to the contract yet
    _inject_scope_meta = None


#: registry module name -> the importable scitex leaf package whose
#: ``_django/manifest.json`` declares the SDK ``scope`` (the SSoT). The hub's
#: OWN wrapper manifests (apps/workspace/<app>/manifest.json, what the registry
#: reads) do NOT carry ``scope`` — it lives in the leaf package. The package
#: name follows the scitex_app manifest ``pip_package`` convention
#: (hyphenated -> underscored).
_LEAF_MANIFEST_PKG = {
    "figrecipe": "figrecipe._django",
    "writer": "scitex_writer._django",
    "scholar": "scitex_scholar._django",
}


def _scope_for(app_name: str) -> str | None:
    """Read ``scope`` from the leaf package's ``_django/manifest.json``.

    The scitex-app manifest is the SSoT for a leaf's release scope (d8528de).
    Resolved via importlib on the leaf's ``_django`` package so it works for
    both editable source mounts and installed wheels. Returns None for an
    unknown app or a manifest without the key (-> no marker).
    """
    import importlib.util
    from pathlib import Path

    pkg = _LEAF_MANIFEST_PKG.get(app_name)
    if pkg is None:
        return None
    try:
        spec = importlib.util.find_spec(pkg)
    except Exception:  # noqa: BLE001 - leaf not importable -> no marker
        return None
    if spec is None or not spec.submodule_search_locations:
        return None
    manifest = Path(spec.submodule_search_locations[0]) / "manifest.json"
    try:
        import json

        data = json.loads(manifest.read_text())
    except Exception:  # noqa: BLE001 - missing/unreadable manifest -> no marker
        return None
    return data.get("scope")


def inject_scope_meta(response: HttpResponse, app_name: str) -> HttpResponse:
    """Return ``response`` with the scope marker injected for HTML pages.

    Non-HTML responses and the user-scoped/absent case are returned unchanged
    (byte-identical) — only a project-scoped leaf page gains the marker.
    """
    if not isinstance(response, HttpResponse):
        return response
    content_type = response.get("Content-Type", "") or ""
    if "html" not in content_type.lower():
        return response
    if _inject_scope_meta is None:
        return response  # scitex-app mount predates the contract -> no marker
    scope = _scope_for(app_name)
    if scope is None:
        return response
    html = response.content.decode("utf-8", "replace")
    new_html = _inject_scope_meta(html, scope)
    if new_html == html:
        return response
    response.content = new_html.encode("utf-8")
    return response
