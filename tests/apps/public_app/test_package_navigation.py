"""Native SDK hierarchy projection and host template rendering, no leaf loads."""

import json
import sys
from importlib import invalidate_caches

import pytest
from django.template import Context, Engine

from apps.infra.public_app.services.package_navigation import build_package_navigation
from apps.infra.public_app.services.interface_catalog import build_interface_catalog


@pytest.fixture
def hierarchy(tmp_path):
    package = tmp_path / "hub_owned_hierarchy_fixture"
    package.mkdir()
    (package / "__init__.py").write_text("raise RuntimeError('provider must not import')\n")
    resource = package / "_package_hierarchy.json"
    resource.write_text(json.dumps({"schema_version": 1, "root": "owned-hub", "nodes": [
        {"id": "owned-hub", "index": "0", "label": "SciTeX", "parent_id": None, "kind": "root"},
        {"id": "hub-apps", "index": "2", "label": "Apps", "parent_id": "owned-hub", "kind": "group"},
        {"id": "hub-leaf", "index": "2.4", "label": "Owned leaf", "parent_id": "hub-apps", "kind": "package", "distribution": "owned-hub-leaf"},
    ]}))
    info = tmp_path / "owned_hub_hierarchy-1.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: owned-hub-hierarchy\nVersion: 1.0\n")
    (info / "entry_points.txt").write_text("[scitex_dev.hierarchy]\nowned-hub = hub_owned_hierarchy_fixture\n")
    sys.path.insert(0, str(tmp_path))
    invalidate_caches()
    yield resource
    sys.path.remove(str(tmp_path))
    invalidate_caches()


def test_host_uses_real_sdk_breadcrumbs_and_never_imports_provider(hierarchy):
    # Arrange
    selected = ["owned-hub-leaf"]
    # Act
    result = build_package_navigation(selected)
    row = result["packages"][0]
    # Assert
    assert (result["discovery"], row["index"], [a["id"] for a in row["breadcrumbs"]], "hub_owned_hierarchy_fixture" in sys.modules) == ("available", "2.4", ["owned-hub", "hub-apps", "hub-leaf"], False)


def test_invalid_hierarchy_does_not_claim_packages_are_unindexed(hierarchy):
    # Arrange
    hierarchy.write_text("{bad json")
    # Act
    result = build_package_navigation(["owned-hub-leaf"])
    # Assert
    assert (result["discovery"], result["packages"], result["unindexed"]) == ("invalid", [], None)


def test_interface_catalog_projects_navigation_for_selected_registered_owner(hierarchy):
    # Arrange
    from scitex_dev.doc_providers import DocProvider
    provider = DocProvider(name="owned-hub-leaf", target="unimported_leaf", distribution="owned-hub-leaf", version="1.0", summary="Owned")
    # Act
    result = build_interface_catalog(docs=(provider,), apis=())
    # Assert
    assert (result["package_navigation"]["discovery"], result["packages"][0]["navigation"]["index"], result["host_admission"], result["live_availability"]) == ("available", "2.4", "not_observed", "not_probed")


def test_rendered_breadcrumbs_use_shared_identity_and_escape_provider_label(hierarchy):
    # Arrange
    from pathlib import Path
    root = Path(__file__).resolve().parents[3]
    data = json.loads(hierarchy.read_text())
    data["nodes"][2]["label"] = "<script>unsafe</script>"
    hierarchy.write_text(json.dumps(data))
    from scitex_dev.doc_providers import DocProvider
    provider = DocProvider(name="owned-hub-leaf", target="unimported_leaf", distribution="owned-hub-leaf", version="1.0", summary="Owned")
    catalog = build_interface_catalog(docs=(provider,), apis=())
    engine = Engine(dirs=[str(root/'apps/workspace/docs_app/templates')], libraries={"i18n": "django.templatetags.i18n"})
    # Act
    html = engine.get_template('docs_app/partials/interface_provider_catalog.html').render(Context({"interface_catalog":catalog}))
    # Assert
    assert ('data-package-hierarchy="hub-leaf"' in html, '&lt;script&gt;unsafe&lt;/script&gt;' in html, '<script>unsafe</script>' in html) == (True, True, False)
