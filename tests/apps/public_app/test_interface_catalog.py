"""Owned distribution metadata, never imported leaf handlers or network calls."""

from importlib import metadata
from types import SimpleNamespace

import pytest
from packaging.utils import canonicalize_name

from apps.infra.public_app.services.interface_catalog import (
    api_docs_url,
    build_interface_catalog,
    documentation_providers,
)
from scitex_sdk.app.api_mount import dump_inert_descriptor
from scitex_sdk.app.api_plugin import (
    ApiPlugin,
    ApiRoute,
    AuthScope,
    RateLimit,
    discover_api_plugins,
)


@pytest.fixture
def installed_provider(tmp_path, monkeypatch):
    info = tmp_path / "demo_leaf-1.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: Demo_Leaf\nVersion: 1.0\nSummary: <script>unsafe</script>\n"
    )
    (info / "entry_points.txt").write_text(
        "[scitex_dev.docs]\ndemo-leaf=untrusted_demo\n[scitex.apis]\ndemo=untrusted_demo:plugin\n"
    )
    marker = tmp_path / "EXECUTED"
    (tmp_path / "untrusted_demo.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\nraise RuntimeError('must not import')\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    distribution = metadata.Distribution.at(info)
    original = metadata.distribution
    monkeypatch.setattr(
        metadata,
        "distribution",
        lambda name: (
            distribution if canonicalize_name(name) == "demo-leaf" else original(name)
        ),
    )
    docs = tuple(
        SimpleNamespace(
            name=e.name,
            target=e.value,
            distribution=distribution.metadata["Name"],
            version=distribution.version,
            summary=distribution.metadata["Summary"],
        )
        for e in distribution.entry_points
        if e.group == "scitex_dev.docs"
    )
    apis = discover_api_plugins(
        entry_points=[e for e in distribution.entry_points if e.group == "scitex.apis"]
    )
    return info, marker, docs, apis


def test_real_inert_descriptor_projects_operations_without_import(installed_provider):
    # Arrange
    info, marker, docs, apis = installed_provider
    descriptor = ApiPlugin(
        id="demo",
        title="Demo",
        api_version="1",
        routes=(
            ApiRoute(
                path="items",
                methods=("GET",),
                handler="untrusted_demo:items",
                auth=AuthScope(public=True, project_scope="none"),
                rate=RateLimit(rate_class="free", compute_cost="low"),
            ),
        ),
    )
    (info / "scitex_api.json").write_text(dump_inert_descriptor(descriptor))
    # Act
    catalog = build_interface_catalog("DEMO_Leaf", docs=docs, apis=apis)
    row = catalog["packages"][0]
    # Assert
    assert (
        row["distribution"],
        row["web_apis"][0]["state"],
        row["web_apis"][0]["operations"][0]["path"],
        marker.exists(),
        catalog["host_admission"],
        catalog["live_availability"],
    ) == (
        "demo-leaf",
        "inert_descriptor",
        "/items",
        False,
        "not_observed",
        "not_probed",
    )


def test_absent_inert_data_does_not_import_or_claim_routes(installed_provider):
    # Arrange
    info, marker, docs, apis = installed_provider
    # Act
    catalog = build_interface_catalog(docs=docs, apis=apis)
    state = catalog["packages"][0]["web_apis"][0]
    # Assert
    assert (state["state"], state["operations"], marker.exists()) == (
        "declaration_only",
        [],
        False,
    )


def test_bad_inert_data_does_not_import_or_claim_routes(installed_provider):
    # Arrange
    info, marker, docs, apis = installed_provider
    (info / "scitex_api.json").write_text("not JSON")
    # Act
    state = build_interface_catalog(docs=docs, apis=apis)["packages"][0]["web_apis"][0]
    # Assert
    assert (state["state"], state["operations"], marker.exists()) == (
        "invalid_descriptor",
        [],
        False,
    )


def test_duplicate_documentation_names_preserve_both_owners(installed_provider):
    # Arrange
    _, marker, docs, _ = installed_provider
    second = SimpleNamespace(**{**vars(docs[0]), "distribution": "another-owner"})
    # Act
    rows = build_interface_catalog(docs=(*docs, second), apis=())["packages"]
    # Assert
    assert (
        len(rows),
        [r["docs"][0]["state"] for r in rows],
        [r["docs"][0]["url"] for r in rows],
        marker.exists(),
    ) == (2, ["ambiguous", "ambiguous"], ["", ""], False)


@pytest.mark.parametrize(
    "value",
    [
        "../private",
        "/etc/passwd",
        "scitex/../secret",
        "%2e%2e",
        "bad name",
        "demo\x00name",
    ],
)
def test_package_selector_refuses_path_like_inputs(value):
    # Arrange
    # The parameter is an untrusted query value, not a filesystem input.
    # Act
    # Assert
    with pytest.raises(ValueError):
        build_interface_catalog(value, docs=(), apis=())


def test_missing_registration_is_explicit_and_does_not_fall_back(installed_provider):
    # Arrange
    _, _, docs, apis = installed_provider
    # Act
    catalog = build_interface_catalog("other-package", docs=docs, apis=apis)
    # Assert
    assert (
        catalog["packages"],
        catalog["selected_not_registered"],
        api_docs_url("Demo_Leaf"),
    ) == ([], True, "/docs/web-api/?package=demo-leaf")


def test_missing_dev_capability_is_unknown_not_ecosystem_fallback(monkeypatch):
    # Arrange
    import scitex_dev

    monkeypatch.setattr(scitex_dev, "list_doc_providers", None, raising=False)
    # Act
    result = documentation_providers()
    # Assert
    assert result == ((), "unavailable")


def test_browser_projection_escapes_metadata_and_explains_absent_web_contract(
    installed_provider,
):
    # Arrange
    from pathlib import Path
    from django.template import Context, Engine

    _, marker, docs, _ = installed_provider
    root = Path(__file__).resolve().parents[3]
    engine = Engine(
        dirs=[root / "apps/workspace/docs_app/templates"],
        libraries={"i18n": "django.templatetags.i18n"},
    )
    template = engine.get_template("docs_app/partials/interface_architecture.html")
    catalog = build_interface_catalog(docs=docs, apis=())
    # Act
    html = template.render(Context({"interface_catalog": catalog}))
    # Assert
    assert (
        'data-provider-package="demo-leaf"' in html,
        "&lt;script&gt;unsafe&lt;/script&gt;" in html,
        "<script>unsafe</script>" in html,
        "scitex-dev dev skills list --package demo-leaf --json" in html,
        marker.exists(),
    ) == (True, True, False, True, False)


def test_public_catalog_get_returns_only_metadata_without_authentication():
    # Arrange
    import json
    from django.test import RequestFactory
    from apps.infra.public_app.views.api import api_docs_catalog

    request = RequestFactory().get(
        "/docs/web-api/catalog.json", {"package": "scitex-sdk"}
    )
    # Act
    response = api_docs_catalog(request)
    body = json.loads(response.content)
    # Assert
    assert (
        response.status_code,
        body["selected_package"],
        body["host_admission"],
        body["live_availability"],
    ) == (200, "scitex-sdk", "not_observed", "not_probed")


@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_public_catalog_refuses_mutating_methods_before_discovery(method):
    # Arrange
    import json
    from django.test import RequestFactory
    from apps.infra.public_app.views.api import api_docs_catalog

    request = getattr(RequestFactory(), method)("/docs/web-api/catalog.json")
    # Act
    response = api_docs_catalog(request)
    # Assert
    assert (
        response.status_code,
        response["Allow"],
        json.loads(response.content)["error"]["code"],
    ) == (405, "GET", "method_not_allowed")


def test_public_catalog_bad_package_is_typed_client_error():
    # Arrange
    import json
    from django.test import RequestFactory
    from apps.infra.public_app.views.api import api_docs_catalog

    request = RequestFactory().get(
        "/docs/web-api/catalog.json", {"package": "../private"}
    )
    # Act
    response = api_docs_catalog(request)
    # Assert
    assert (response.status_code, json.loads(response.content)["error"]["code"]) == (
        400,
        "invalid_package",
    )


def test_direct_docs_url_refuses_unregistered_names_before_artifact_lookup(monkeypatch):
    # Arrange
    import scitex_dev
    from apps.workspace.docs_app._sphinx import resolve_sphinx_path

    calls = []
    monkeypatch.setattr(scitex_dev, "get_docs", lambda **kwargs: calls.append(kwargs))
    # Act
    result = resolve_sphinx_path("unregistered-private-module")
    # Assert
    assert (result, calls) == (None, [])


def test_direct_docs_url_refuses_duplicate_owned_metadata(
    installed_provider, tmp_path, monkeypatch
):
    # Arrange
    import scitex_dev
    from apps.workspace.docs_app._sphinx import resolve_sphinx_path

    second = tmp_path / "another_owner-1.0.dist-info"
    second.mkdir()
    (second / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: another-owner\nVersion: 1.0\n"
    )
    (second / "entry_points.txt").write_text(
        "[scitex_dev.docs]\ndemo-leaf=another_untrusted\n"
    )
    calls = []
    monkeypatch.setattr(scitex_dev, "get_docs", lambda **kwargs: calls.append(kwargs))
    # Act
    result = resolve_sphinx_path("demo-leaf")
    # Assert
    assert (result, calls, installed_provider[1].exists()) == (None, [], False)


def test_unique_registered_docs_name_reaches_only_its_artifact_lookup(
    installed_provider, tmp_path, monkeypatch
):
    # Arrange
    import scitex_dev
    from apps.workspace.docs_app._sphinx import resolve_sphinx_path

    html = tmp_path / "owned-html"
    html.mkdir()
    (html / "index.html").write_text("<!doctype html><title>Owned fixture docs</title>")
    calls = []

    def artifact(**kwargs):
        calls.append(kwargs)
        return html

    monkeypatch.setattr(scitex_dev, "get_docs", artifact)
    # Act
    result = resolve_sphinx_path("demo-leaf")
    # Assert
    assert (result, calls, installed_provider[1].exists()) == (
        html,
        [{"package": "demo-leaf", "format": "html"}],
        False,
    )


@pytest.mark.django_db
def test_installed_sdk_provider_is_available_as_inert_metadata_over_http(client):
    # Arrange
    import sys

    before = set(sys.modules)
    # Act
    response = client.get("/docs/web-api/catalog.json", {"package": "SciTex_SDK"})
    catalog = response.json()
    provider = catalog["packages"][0]["web_apis"][0]
    # Assert
    assert (
        response.status_code,
        provider["state"],
        [(row["method"], row["path"]) for row in provider["operations"]],
        catalog["host_admission"],
        catalog["live_availability"],
        sorted(
            name
            for name in set(sys.modules) - before
            if name.startswith("scitex_sdk._web")
        ),
    ) == (
        200,
        "inert_descriptor",
        [("GET", "/skills")],
        "not_observed",
        "not_probed",
        [],
    )
