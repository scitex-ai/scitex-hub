"""Live Paper hub mount: per-request bundle resolution + leaf URL include.

Thin-hub wrapper (scholar pattern): the leaf owns views, the hub owns
auth gating (applied at the config/urls.py mount via the shared login
wrapper) and bundle resolution for the current request.
"""

from __future__ import annotations

from pathlib import Path

from scitex_live_paper import (
    BundleContext,
    BundleNotFound,
    BundleSource,
    PaperState,
    RendererOptions,
    mount,
)


def hub_resolver(request, **url_kwargs) -> BundleContext:
    """Resolve the paper bundle for this request from ``?working_dir=``.

    The manifest declares ``working_dir_param: working_dir``: the deep
    link carries the bundle file path, resolved server-side against the
    caller's data jail. Missing/unreadable/out-of-jail paths map to the
    leaf's documented HTTP statuses (404/403), never a 500.
    """
    from scitex_live_paper import BundleAccessDenied

    raw = (request.GET.get("working_dir") or "").strip()
    if not raw:
        raise BundleNotFound("no paper selected (missing ?working_dir=)")
    candidate = Path(raw)
    if not candidate.is_absolute():
        raise BundleNotFound(f"paper path is not absolute: {raw!r}")
    try:
        resolved = candidate.resolve()
    except OSError as exc:
        raise BundleNotFound(f"paper path does not resolve: {raw!r}") from exc
    if not resolved.is_file():
        raise BundleNotFound(f"paper not found: {raw!r}")
    if not _inside_user_jail(request, resolved):
        raise BundleAccessDenied("paper is outside your workspace")

    def _load():
        from scitex_live_paper.bundle import load

        return load(resolved)

    return BundleContext(
        source=BundleSource.from_resolver(_load),
        paper_state=PaperState(),
        api_base=request.path.rsplit("/", 1)[0] + "/",
        options=RendererOptions(embed_mode=True),
    )


def _inside_user_jail(request, path: Path) -> bool:
    """Containment in the caller's data jail (component-wise)."""
    try:
        from apps.infra.project_app.services.filesystem.permissions import (
            validate_path_in_user_jail,
        )

        return bool(validate_path_in_user_jail(request.user, path))
    except Exception:
        return False


urlpatterns, app_namespace = mount(resolver=hub_resolver)

# EOF
