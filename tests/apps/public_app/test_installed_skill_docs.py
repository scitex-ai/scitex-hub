"""Real installed resources, exact owner admission, containment and HTML safety."""

from importlib import metadata
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import hashlib
import json

import pytest
from packaging.utils import canonicalize_name

from apps.infra.public_app.services.installed_skill_docs import (
    installed_skill_guides,
    read_installed_skill,
)


@pytest.fixture
def guide_provider(tmp_path, monkeypatch):
    info = tmp_path / "demo_guide-1.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: demo-guide\nVersion: 1.0\n"
    )
    (info / "entry_points.txt").write_text(
        "[scitex_dev.skills]\ndemo-guide=demo_guide\n"
    )
    module = tmp_path / "demo_guide"
    module.mkdir()
    marker = tmp_path / "IMPORTED"
    (module / "__init__.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\nraise RuntimeError('resource reader must not import provider')\n"
    )
    skills = module / "_skills/demo-guide"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text(
        "---\nname: demo-guide\ndescription: Owned package guidance\n---\n# Guide\n"
    )
    content = "# API guide\n\nExisting leaf URL: GET /owned/legacy\n<script>untrusted()</script>\n"
    (skills / "api.md").write_text(content)
    monkeypatch.syspath_prepend(str(tmp_path))
    dist = metadata.Distribution.at(info)
    original = metadata.distribution
    monkeypatch.setattr(
        metadata,
        "distribution",
        lambda name: (
            dist if canonicalize_name(name) == "demo-guide" else original(name)
        ),
    )
    return skills, marker, content


def test_resource_inventory_preserves_owner_without_imports_or_host_paths(
    guide_provider,
):
    # Arrange
    skills, marker, _ = guide_provider
    # Act
    result = installed_skill_guides("Demo_Guide")
    # Assert
    assert (
        result["state"],
        len(result["entries"]),
        {r["owner"] for r in result["entries"]},
        str(skills) in json.dumps(result),
        marker.exists(),
    ) == ("available", 2, {"demo-guide"}, False, False)


def test_exact_listed_resource_is_read_through_public_dev_reader(guide_provider):
    # Arrange
    _, marker, content = guide_provider
    listing = installed_skill_guides("demo-guide")
    link = next(r["url"] for r in listing["entries"] if r["name"] == "api")
    query = parse_qs(urlsplit(link).query)
    # Act
    result = read_installed_skill(
        query["package"][0], query["namespace"][0], query["name"][0]
    )
    # Assert
    assert (
        result["content"],
        result["version"],
        result["sha256"],
        marker.exists(),
    ) == (content, "1.0", hashlib.sha256(content.encode()).hexdigest(), False)


@pytest.mark.parametrize("name", ["../outside", "/etc/passwd", "*", "ap"])
def test_unlisted_or_fuzzy_resource_names_are_not_admitted(guide_provider, name):
    # Arrange
    # The Dev reader's legacy fuzzy lookup is not exposed by the browser route.
    # Act / Assert
    with pytest.raises(LookupError):
        read_installed_skill("demo-guide", "demo-guide", name)


def test_another_namespace_cannot_be_read_through_an_owned_package(guide_provider):
    # Arrange
    # A registered owner is required for the exact namespace/name pair.
    # Act / Assert
    with pytest.raises(LookupError):
        read_installed_skill("demo-guide", "scitex-scholar", "06_api-overview")


def test_escaping_skill_symlink_is_an_explicit_invalid_inventory(
    guide_provider, tmp_path
):
    # Arrange
    skills, marker, _ = guide_provider
    outside = tmp_path / "outside.md"
    outside.write_text("outside-private-fixture")
    (skills / "escape.md").symlink_to(outside)
    # Act
    result = installed_skill_guides("demo-guide")
    # Assert
    assert (result, marker.exists()) == ({"state": "invalid", "entries": []}, False)


def test_leaf_guidance_is_escaped_as_documentation_not_executable_html(guide_provider):
    # Arrange
    from django.template import Context, Engine

    root = Path(__file__).resolve().parents[3]
    template = Engine(
        loaders=[
            (
                "django.template.loaders.locmem.Loader",
                {"global_base.html": "{% block content %}{% endblock %}"},
            ),
            (
                "django.template.loaders.filesystem.Loader",
                [root / "apps/infra/public_app/templates"],
            ),
        ],
        libraries={
            "static": "django.templatetags.static",
            "i18n": "django.templatetags.i18n",
        },
    ).get_template("public_app/pages/api_docs_skill.html")
    skill = read_installed_skill("demo-guide", "demo-guide", "api")
    # Act
    html = template.render(Context({"skill": skill}))
    # Assert
    assert (
        "&lt;script&gt;untrusted()&lt;/script&gt;" in html,
        "<script>untrusted()" in html,
        "Existing leaf URL: GET /owned/legacy" in html,
        "not proof of an enabled or responding API" in html,
    ) == (True, False, True, True)


@pytest.mark.django_db
def test_http_selected_package_lists_real_installed_leaf_guidance(client):
    # Arrange
    from urllib.parse import unquote
    from scitex_dev.ecosystem import list_skills

    owned = list_skills(package="scitex-scholar")
    namespace, entries = next(iter(owned.items()))
    name = next(row["name"] for row in entries if row["name"] != "SKILL")
    # Act
    response = client.get("/docs/web-api/", {"package": "SciTex_Scholar"})
    html = unquote(response.content.decode())
    # Assert
    assert (
        response.status_code,
        "Installed leaf guidance" in html,
        f"namespace={namespace}&amp;name={name}" in html,
        "No canonical Web API provider registered" in html,
    ) == (200, True, True, True)


@pytest.mark.django_db
def test_http_leaf_resource_is_actual_installed_documentation(client):
    # Arrange
    from scitex_dev.ecosystem import get_skill, list_skills

    namespace, entries = next(iter(list_skills(package="scitex-scholar").items()))
    name = next(row["name"] for row in entries if row["name"] != "SKILL")
    content = get_skill(namespace, name)
    # Act
    response = client.get(
        "/docs/web-api/skill/",
        {"package": "scitex-scholar", "namespace": namespace, "name": name},
    )
    # Assert
    assert (
        response.status_code,
        hashlib.sha256(content.encode()).hexdigest().encode() in response.content,
        b"not proof of an enabled or responding API" in response.content,
    ) == (200, True, True)


@pytest.mark.django_db
@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_http_skill_reader_refuses_writes(client, method):
    # Arrange
    # Discovery is not called for a write method.
    # Act
    response = getattr(client, method)("/docs/web-api/skill/")
    # Assert
    assert (response.status_code, response.get("Allow")) == (405, "GET")


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["../outside", "/etc/passwd", "*"])
def test_http_skill_reader_refuses_unlisted_paths(client, name):
    # Arrange
    # Request parameters are exact resource identities, never filesystem paths.
    # Act
    response = client.get(
        "/docs/web-api/skill/",
        {"package": "scitex-scholar", "namespace": "scitex-scholar", "name": name},
    )
    # Assert
    assert response.status_code == 404


@pytest.mark.django_db
def test_http_legacy_docs_alias_uses_the_same_provider_projection(client):
    # Arrange
    # The former page had unsupported universal API examples.
    # Act
    response = client.get("/apps/docs/api/", {"package": "scitex-scholar"})
    # Assert
    assert (
        response.status_code,
        b"Installed leaf guidance" in response.content,
        b"No canonical Web API provider registered" in response.content,
    ) == (200, True, True)
