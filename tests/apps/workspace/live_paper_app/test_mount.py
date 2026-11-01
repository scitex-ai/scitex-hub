"""Resolve actual leaf bundle directories through the actual user jail."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.test import RequestFactory, override_settings
from scitex_live_paper import BundleAccessDenied, BundleNotFound
from scitex_sdk.ui.project_scope import LocalProjectProvider

from apps.workspace.live_paper_app.mount import hub_resolver


class FixtureProjectProvider(LocalProjectProvider):
    """Real file-backed provider through the host's public dotted-path SPI."""

    def __init__(self):
        super().__init__(
            Path(settings.BASE_DIR) / "data/users/bundle-reader/proj",
            state_file=Path(settings.BASE_DIR) / "project-preference.json",
        )


def _request(path):
    request = RequestFactory().get("/apps/live-paper/", {"working_dir": str(path)})
    request.user = SimpleNamespace(username="bundle-reader", is_authenticated=False)
    return request


def _bundle(root):
    root.mkdir(parents=True)
    (root / "manuscript.tex").write_text(
        r"\documentclass{article}\begin{document}Example\end{document}"
    )
    (root / "claims.json").write_text("[]")
    return root


def test_directory_bundle_loads_through_real_leaf_parser(tmp_path):
    bundle = _bundle(tmp_path / "data/users/bundle-reader/proj/demo/paper")
    with override_settings(BASE_DIR=tmp_path):
        context = hub_resolver(_request(bundle))
        loaded = context.source.load()
    assert (
        loaded.root,
        loaded.manuscript_path.name,
        loaded.claims,
        context.api_base,
    ) == (
        bundle,
        "manuscript.tex",
        [],
        "/apps/live-paper/api/",
    )


def test_file_is_not_a_bundle_directory(tmp_path):
    bundle = _bundle(tmp_path / "data/users/bundle-reader/proj/demo/paper")
    with override_settings(BASE_DIR=tmp_path), pytest.raises(BundleNotFound):
        hub_resolver(_request(bundle / "claims.json"))


def test_another_users_directory_remains_forbidden(tmp_path):
    bundle = _bundle(tmp_path / "data/users/somebody-else/proj/demo/paper")
    with override_settings(BASE_DIR=tmp_path), pytest.raises(BundleAccessDenied):
        hub_resolver(_request(bundle))


def test_nested_bundle_symlink_cannot_read_another_users_claims(tmp_path):
    bundle = _bundle(tmp_path / "data/users/bundle-reader/proj/demo/paper")
    foreign = _bundle(tmp_path / "data/users/somebody-else/proj/demo/paper")
    (bundle / "claims.json").unlink()
    (bundle / "claims.json").symlink_to(foreign / "claims.json")
    with override_settings(BASE_DIR=tmp_path), pytest.raises(BundleAccessDenied):
        hub_resolver(_request(bundle)).source.load()


@pytest.mark.parametrize("embedded", [False, True])
def test_full_app_keeps_header_and_explicit_iframe_can_hide_it(tmp_path, embedded):
    from scitex_live_paper._django.views import viewer_page

    bundle = _bundle(tmp_path / "data/users/bundle-reader/proj/demo/paper")
    request = _request(bundle)
    if embedded:
        request.GET = request.GET.copy()
        request.GET["embed"] = "1"
    with override_settings(BASE_DIR=tmp_path, DEBUG=True, VITE_USE_BUILD=False):
        request.live_paper_context = hub_resolver(request)
        response = viewer_page(request)
    assert (b'data-embed-mode="1"' in response.content) == embedded


def test_unrelated_project_link_does_not_prevent_reading_actual_bundle(tmp_path):
    # Arrange
    bundle = _bundle(tmp_path / "data/users/bundle-reader/proj/demo/paper")
    outside = tmp_path / "unrelated-environment"
    outside.mkdir()
    (bundle / ".venv").symlink_to(outside, target_is_directory=True)
    # Act
    with override_settings(BASE_DIR=tmp_path):
        loaded = hub_resolver(_request(bundle)).source.load()
    # Assert
    assert loaded.root == bundle


@pytest.mark.parametrize("missing", ["manuscript.tex", "claims.json"])
@pytest.mark.parametrize("surface", ["viewer_page", "api_dispatch"])
def test_missing_leaf_members_become_empty_state_or_not_found(
    tmp_path, missing, surface
):
    from scitex_live_paper import mount

    bundle = _bundle(tmp_path / "data/users/bundle-reader/proj/demo/paper")
    (bundle / missing).unlink()
    patterns, _ = mount(resolver=hub_resolver)
    callback = next(pattern.callback for pattern in patterns if pattern.name == surface)
    request = _request(bundle)
    kwargs = {"endpoint": "api/dashboard"} if surface == "api_dispatch" else {}
    with override_settings(BASE_DIR=tmp_path, DEBUG=True, VITE_USE_BUILD=False):
        response = callback(request, **kwargs)
    if surface == "viewer_page":
        assert (
            response.status_code == 200
            and b'data-empty-reason="No LivePaper bundle' in response.content
        )
    else:
        assert response.status_code == 404


@pytest.mark.parametrize("surface", ["viewer_page", "api_dispatch"])
def test_malformed_leaf_content_remains_a_real_server_error(tmp_path, surface):
    from scitex_live_paper import mount

    bundle = _bundle(tmp_path / "data/users/bundle-reader/proj/demo/paper")
    (bundle / "claims.json").write_text("not-json")
    patterns, _ = mount(resolver=hub_resolver)
    callback = next(pattern.callback for pattern in patterns if pattern.name == surface)
    kwargs = {"endpoint": "api/dashboard"} if surface == "api_dispatch" else {}
    with override_settings(BASE_DIR=tmp_path):
        response = callback(_request(bundle), **kwargs)
    assert (
        response.status_code == 500 and b"Invalid LivePaper bundle" in response.content
    )


def test_explicit_project_resource_read_preserves_committed_selection(tmp_path):
    import json

    projects = tmp_path / "data/users/bundle-reader/proj"
    selected = _bundle(projects / "selected")
    _bundle(projects / "remembered")
    preference = tmp_path / "project-preference.json"
    preference.write_text(json.dumps({"project": "remembered"}))
    before = preference.read_bytes()

    class FilesystemStorage:
        def project_path(self, project_id, request):
            root = (projects / project_id).resolve()
            return str(root) if root.parent == projects and root.is_dir() else None

        def can_write(self, project_id, request):
            return False

    request = RequestFactory().get(
        "/apps/live-paper/api/dashboard", {"project": "selected"}
    )
    request.user = SimpleNamespace(username="bundle-reader", is_authenticated=True)
    with override_settings(
        BASE_DIR=tmp_path,
        SCITEX_APP_MODE="hub",
        SCITEX_PROJECT_PROVIDER=f"{__name__}.FixtureProjectProvider",
        SCITEX_PROJECT_STORAGE=FilesystemStorage(),
    ):
        context = hub_resolver(request)
    assert (context.source.load().root, preference.read_bytes()) == (selected, before)
