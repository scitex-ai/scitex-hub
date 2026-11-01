"""Resolve actual leaf bundle directories through the actual user jail."""

from types import SimpleNamespace

import pytest
from django.test import RequestFactory, override_settings
from scitex_live_paper import BundleAccessDenied, BundleNotFound

from apps.workspace.live_paper_app.mount import hub_resolver


def _request(path):
    request = RequestFactory().get("/apps/live-paper/", {"working_dir": str(path)})
    request.user = SimpleNamespace(username="bundle-reader")
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
    assert (loaded.root, loaded.manuscript_path.name, loaded.claims) == (
        bundle,
        "manuscript.tex",
        [],
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
