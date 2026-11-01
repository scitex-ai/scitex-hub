"""Live Paper hub mount: per-request bundle resolution + leaf URL include.

Thin-hub wrapper (scholar pattern): the leaf owns views, the hub owns
auth gating (applied at the config/urls.py mount via the shared login
wrapper) and bundle resolution for the current request.
"""

from __future__ import annotations

from pathlib import Path

from scitex_live_paper import (
    BundleContext,
    BundleError,
    BundleMissingError,
    BundleNotFound,
    BundleResolverError,
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
        from scitex_sdk.host import AccessError, project_access

        try:
            # Resource GETs authorize through the host's actual providers without
            # changing the navigation preference shared with other app tabs.
            access = project_access(request, remember=False)
        except AccessError as exc:
            if exc.status == 404:
                raise BundleNotFound(
                    "no paper bundle selected in your projects"
                ) from exc
            if exc.status in {401, 403}:
                raise BundleAccessDenied("paper access is denied") from exc
            raise BundleResolverError(str(exc)) from exc
        raw = str(access.root)
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
        # A project may also contain unrelated source/runtime links. Check
        # only members the renderer reads, not the entire project tree.
        for name in (
            "manuscript.pdf",
            "manuscript.tex",
            "claims.json",
            "dag.mmd",
            "provenance.yaml",
            "state.yaml",
            "figz",
        ):
            member = resolved / name
            if (member.exists() or member.is_symlink()) and not _inside_user_jail(
                request, member
            ):
                raise BundleAccessDenied(
                    "paper bundle member is outside your workspace"
                )
        figures = resolved / "figz"
        if figures.is_dir() and any(
            member.is_symlink() for member in figures.rglob("*")
        ):
            raise BundleAccessDenied("paper figures must not contain symbolic links")
        return load(resolved)

    from django.urls import reverse

    api_ping = reverse("live_paper:api_dispatch", kwargs={"endpoint": "api/ping"})
    # A jailed project directory need not be a LivePaper bundle. Let the
    # leaf's parser decide once, before rendering a shell that would start
    # failing every lazy API request. Preserve malformed-content failures.
    try:
        bundle = _load()
    except BundleMissingError as exc:
        raise BundleNotFound(
            "No LivePaper bundle in the selected directory. Open a bundle "
            "containing manuscript.pdf or manuscript.tex and claims.json."
        ) from exc
    except BundleError as exc:
        raise BundleResolverError(f"Invalid LivePaper bundle: {exc}") from exc
    return BundleContext(
        source=BundleSource.from_bundle(bundle),
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
