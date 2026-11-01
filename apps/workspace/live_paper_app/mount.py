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

    Explicit deep links carry a bundle directory in ``working_dir``.
    Otherwise use the current authorized project, consistently for the
    viewer and its API calls. Both paths remain inside the caller's jail.
    """
    from scitex_live_paper import BundleAccessDenied

    raw = (request.GET.get("working_dir") or "").strip()
    if not raw:
        from apps.infra.project_app.services.filesystem.paths import (
            get_project_root_path,
        )
        from apps.infra.project_app.services.project_scope import resolve_scoped_project

        project = resolve_scoped_project(request)
        root = get_project_root_path(project.owner, project) if project else None
        if root is None:
            raise BundleNotFound("no paper bundle selected in your projects")
        raw = str(root)
    candidate = Path(raw)
    if not candidate.is_absolute():
        raise BundleNotFound(f"paper path is not absolute: {raw!r}")
    try:
        resolved = candidate.resolve()
    except OSError as exc:
        raise BundleNotFound(f"paper path does not resolve: {raw!r}") from exc
    if not resolved.is_dir():
        raise BundleNotFound(f"paper bundle directory not found: {raw!r}")
    if not _inside_user_jail(request, resolved):
        raise BundleAccessDenied("paper is outside your workspace")

    def _load():
        from scitex_live_paper.bundle import load

        # Bundle members are opened by the leaf after resolution. Refuse
        # symlink-bearing bundles so a nested manuscript/claims/figz link
        # cannot cross the user's jail through an otherwise safe directory.
        if not _inside_user_jail(request, resolved):
            raise BundleAccessDenied("paper is outside your workspace")
        if any(member.is_symlink() for member in resolved.rglob("*")):
            raise BundleAccessDenied("paper bundle must not contain symbolic links")
        return load(resolved)

    from django.urls import reverse

    api_ping = reverse("live_paper:api_dispatch", kwargs={"endpoint": "api/ping"})
    return BundleContext(
        source=BundleSource.from_resolver(_load),
        paper_state=PaperState(),
        api_base=api_ping.removesuffix("ping"),
        options=RendererOptions(embed_mode=False),
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
