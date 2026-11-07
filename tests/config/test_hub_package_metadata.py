"""The header must identify the installed distribution, never a checkout guess."""

from html.parser import HTMLParser
from importlib.metadata import PackageNotFoundError

import pytest
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, override_settings

from config.context_processors import get_scitex_hub_version, scitex_version
from config.package_metadata import get_hub_package_metadata


@pytest.fixture
def installed_hub(tmp_path, monkeypatch):
    """Exercise the real metadata reader with an owned distribution directory."""
    dist = tmp_path / "scitex_hub-0.22.0a0.dist-info"
    dist.mkdir()
    (dist / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: scitex-hub\nVersion: 0.22.0a0\n"
        'Summary: A browser workspace with <projects> & "apps"\n\n'
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    return get_hub_package_metadata()


def test_context_uses_installed_identity_even_when_settings_are_stale(installed_hub):
    from apps.infra.project_app.context_processors import version_context

    with override_settings(SCITEX_HUB_VERSION="stale-source-version"):
        assert get_scitex_hub_version() == "0.22.0a0"
        for adapter in (scitex_version, version_context):
            assert adapter(None) == {
                "SCITEX_HUB_VERSION": installed_hub["version"],
                "SCITEX_HUB_DESCRIPTION": installed_hub["description"],
            }


class HeaderIdentity(HTMLParser):
    def __init__(self):
        super().__init__()
        self.identities = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "header-hub-version" in attrs.get("class", "").split():
            self.identities.append(attrs)


@pytest.mark.parametrize("environment", ["dev", "prod"])
def test_real_header_fragment_reads_metadata_and_escapes_attributes(
    installed_hub, environment
):
    request = RequestFactory().get("/landing/")
    request.user = AnonymousUser()
    request.session = {}
    with override_settings(SCITEX_ENV=environment, SCITEX_HUB_VERSION="stale-setting"):
        html = render_to_string(
            "global_base_partials/global_header.html",
            {
                "request": request,
                "user": request.user,
                "SCITEX_HUB_VERSION": "stale-context",
                "SCITEX_FAVICON": "favicon.svg",
                "SCITEX_FAVICON_DARK": "favicon.svg",
            },
        )
    parser = HeaderIdentity()
    parser.feed(html)
    assert len(parser.identities) == 1
    attrs = parser.identities[0]
    assert attrs["data-package"] == "scitex-hub"
    assert attrs["data-package-version"] == "0.22.0a0"
    assert attrs["data-package-description"] == installed_hub["description"]
    assert attrs["title"] == f'scitex-hub v0.22.0a0: {installed_hub["description"]}'
    assert "&lt;projects&gt; &amp; &quot;apps&quot;" in html
    assert "stale-setting" not in html and "stale-context" not in html


def test_missing_distribution_never_claims_a_checkout_release(monkeypatch):
    def missing(name):
        raise PackageNotFoundError(name)

    monkeypatch.setattr("config.package_metadata.metadata", missing)
    assert get_hub_package_metadata() == {
        "name": "scitex-hub",
        "version": "unknown",
        "description": "",
    }
