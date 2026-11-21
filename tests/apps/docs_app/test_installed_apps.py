"""Installed-app documentation projection consumes inert SDK/Dev metadata."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from apps.workspace.docs_app._app_docs import register_installed_app_docs


def installed_distribution(root, name):
    directory = root / (name.replace("-", "_") + "-1.0.dist-info")
    directory.mkdir()
    (directory / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n"
    )
    return directory


def module(name, owner, *, docs_slug=""):
    return SimpleNamespace(
        name=name, label=name.title(), pip_package=owner, docs_slug=docs_slug
    )


def test_sdk_plugin_is_discovered_without_importing_its_entry_point(
    tmp_path, monkeypatch
):
    # Arrange
    dist = installed_distribution(tmp_path, "owned-plugin")
    (dist / "entry_points.txt").write_text(
        "[scitex.apps]\nowned = must_never_import._django.apps:Config\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    pages, lookup = [], {}
    # Act
    register_installed_app_docs(pages, lookup, modules=[])
    # Assert
    assert lookup["app-owned"]["distribution"] == "owned-plugin"
    assert lookup["app-owned"]["section"] == "apps"
    assert lookup["app-owned"]["template"] == "docs_app/docs_installed_app.html"


def test_host_owned_leaf_does_not_need_a_legacy_docs_slug(tmp_path, monkeypatch):
    # Arrange
    installed_distribution(tmp_path, "owned-leaf")
    monkeypatch.syspath_prepend(str(tmp_path))
    pages, lookup = [], {}
    # Act
    register_installed_app_docs(
        pages, lookup, modules=[module("research", "owned-leaf")], plugins=[]
    )
    # Assert
    assert lookup["app-research"]["distribution"] == "owned-leaf"
    assert lookup["app-research"]["label"] == "Research"


def test_missing_docs_registration_does_not_hide_an_installed_application(
    tmp_path, monkeypatch
):
    # Arrange
    installed_distribution(tmp_path, "app-without-docs")
    monkeypatch.syspath_prepend(str(tmp_path))
    pages, lookup = [], {}
    # Act
    register_installed_app_docs(
        pages,
        lookup,
        modules=[],
        plugins=[SimpleNamespace(name="undocumented", distribution="app-without-docs")],
    )
    # Assert
    assert lookup["app-undocumented"]["distribution"] == "app-without-docs"


def test_host_alias_and_sdk_declaration_share_one_owner_page(tmp_path, monkeypatch):
    # Arrange
    installed_distribution(tmp_path, "owned-leaf")
    monkeypatch.syspath_prepend(str(tmp_path))
    pages, lookup = [], {}
    mounted = [module("mounted-name", "owned-leaf")]
    plugins = [SimpleNamespace(name="entry-name", distribution="owned-leaf")]
    # Act
    register_installed_app_docs(pages, lookup, modules=mounted, plugins=plugins)
    # Assert
    assert [page["slug"] for page in pages] == ["app-mounted-name"]


def test_existing_authored_guide_is_preserved(tmp_path, monkeypatch):
    # Arrange
    installed_distribution(tmp_path, "owned-leaf")
    monkeypatch.syspath_prepend(str(tmp_path))
    original = {"slug": "authored", "template": "leaf/docs.html"}
    pages, lookup = [original], {"authored": original}
    # Act
    register_installed_app_docs(
        pages,
        lookup,
        modules=[module("owned", "owned-leaf", docs_slug="authored")],
        plugins=[],
    )
    # Assert
    assert pages == [original]
    assert lookup == {"authored": original}


def test_repeat_and_concurrent_projection_adds_each_app_once(tmp_path, monkeypatch):
    # Arrange
    installed_distribution(tmp_path, "owned-leaf")
    monkeypatch.syspath_prepend(str(tmp_path))
    pages, lookup = [], {}

    def project(_):
        register_installed_app_docs(
            pages, lookup, modules=[module("owned", "owned-leaf")], plugins=[]
        )

    # Act
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(project, range(12)))
    # Assert
    assert len(pages) == len(lookup) == 1
    assert pages[0]["distribution"] == "owned-leaf"


@pytest.mark.parametrize(
    "name,owner",
    [("missing", "not-installed-owned-fixture"), ("../escape", "owned-leaf")],
)
def test_stale_and_unroutable_app_metadata_creates_no_doc_link(
    tmp_path, monkeypatch, name, owner
):
    # Arrange
    installed_distribution(tmp_path, "owned-leaf")
    monkeypatch.syspath_prepend(str(tmp_path))
    pages, lookup = [], {}
    # Act
    register_installed_app_docs(
        pages, lookup, modules=[module(name, owner)], plugins=[]
    )
    # Assert
    assert pages == []
    assert lookup == {}


def test_plugin_uses_the_registered_display_label_with_a_host_guide(tmp_path, monkeypatch):
    # Arrange
    installed_distribution(tmp_path, "owned-leaf")
    monkeypatch.syspath_prepend(str(tmp_path))
    guide = {"slug": "authored", "section": "howto"}
    pages, lookup = [guide], {"authored": guide}
    mounted = [module("owned", "scitex-hub", docs_slug="authored")]
    plugins = [SimpleNamespace(name="owned", distribution="owned-leaf")]
    # Act
    register_installed_app_docs(pages, lookup, modules=mounted, plugins=plugins)
    # Assert
    assert lookup["app-owned"]["label"] == "Owned"
    assert lookup["authored"] is guide
