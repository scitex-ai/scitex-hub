"""Installed-file and provider provenance for explicitly mounted view ownership."""

import sys
from functools import partial, wraps
from importlib import metadata, util
from types import SimpleNamespace

import pytest
import scitex_dev

from apps.infra.workspace_app._resolved_view_owner import resolved_view_owner


@pytest.fixture
def mounted_view(tmp_path, monkeypatch):
    package = tmp_path / "owned_mount"
    package.mkdir()
    source = package / "views.py"
    source.write_text(
        "def index(request):\n    raise AssertionError('must never execute')\n"
    )
    spec = util.spec_from_file_location("owned_mount.views", source)
    module = util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    dist = tmp_path / "owned_leaf-1.0.dist-info"
    dist.mkdir()
    (dist / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: owned-leaf\nVersion: 1.0\n"
    )
    (dist / "entry_points.txt").write_text(
        "[scitex_dev.docs]\nowned-leaf = owned_mount\n"
    )
    (dist / "RECORD").write_text("owned_mount/views.py,,\n")
    discover = metadata.distributions
    monkeypatch.setattr(
        metadata, "distributions", lambda **kw: discover(**({"path": [tmp_path]} | kw))
    )
    monkeypatch.setattr(
        scitex_dev,
        "list_doc_providers",
        partial(scitex_dev.list_doc_providers, path=[tmp_path]),
    )
    request = SimpleNamespace(resolver_match=SimpleNamespace(func=module.index))
    return request, dist, module


def test_real_metadata_and_recorded_callable_establish_owner(mounted_view):
    request, _, _ = mounted_view
    assert resolved_view_owner(request) == "owned-leaf"


def test_auth_decorator_retains_leaf_identity_without_execution(mounted_view):
    request, _, module = mounted_view

    @wraps(module.index)
    def guarded(request):
        raise AssertionError("view must never execute")

    request.resolver_match.func = guarded
    assert resolved_view_owner(request) == "owned-leaf"


@pytest.mark.parametrize(
    "change",
    ["unrecorded", "wrong-target", "duplicate", "missing-origin", "forged-module"],
)
def test_unproven_or_ambiguous_ownership_refused(mounted_view, change):
    request, dist, module = mounted_view
    if change == "unrecorded":
        (dist / "RECORD").write_text("unrelated.py,,\n")
    elif change == "wrong-target":
        (dist / "entry_points.txt").write_text(
            "[scitex_dev.docs]\nowned-leaf = owned_mount_other\n"
        )
    elif change == "duplicate":
        other = dist.parent / "other_leaf-1.0.dist-info"
        other.mkdir()
        (other / "METADATA").write_text(
            "Metadata-Version: 2.1\nName: other-leaf\nVersion: 1.0\n"
        )
        (other / "entry_points.txt").write_text(
            "[scitex_dev.docs]\nowned-leaf = other_mount\n"
        )
    elif change == "missing-origin":
        module.__spec__.origin = None
    else:
        module.index.__module__ = "unloaded_package.views"
    assert resolved_view_owner(request) is None


def test_callback_cycle_and_unresolved_request_refused(mounted_view):
    request, _, module = mounted_view
    module.index.__wrapped__ = module.index
    assert (resolved_view_owner(request), resolved_view_owner(SimpleNamespace())) == (
        None,
        None,
    )


def test_forged_real_module_does_not_claim_its_owner(mounted_view):
    request, _, module = mounted_view
    module.index.__module__ = "scitex_dev"
    assert resolved_view_owner(request) is None


def test_two_distinct_recorded_owners_refused(mounted_view):
    request, dist, _ = mounted_view
    other = dist.parent / "other_leaf-1.0.dist-info"
    other.mkdir()
    (other / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: other-leaf\nVersion: 1.0\n"
    )
    (other / "entry_points.txt").write_text(
        "[scitex_dev.docs]\nother-leaf = owned_mount\n"
    )
    (other / "RECORD").write_text("owned_mount/views.py,,\n")
    assert resolved_view_owner(request) is None


def test_wrapper_depth_is_bounded(mounted_view):
    request, _, module = mounted_view
    callback = module.index
    for _ in range(17):

        @wraps(callback)
        def outer(request):
            raise AssertionError("must not call")

        callback = outer
    request.resolver_match.func = callback
    assert resolved_view_owner(request) is None


def test_real_installed_sdk_creator_callback_is_owned():
    from django.contrib.auth.decorators import login_required
    from django.urls import resolve
    from scitex_sdk.creator import urls

    match = resolve("/", urlconf=tuple(urls.urlpatterns))
    request = SimpleNamespace(
        resolver_match=SimpleNamespace(func=login_required(match.func))
    )
    assert resolved_view_owner(request) == "scitex-sdk"
