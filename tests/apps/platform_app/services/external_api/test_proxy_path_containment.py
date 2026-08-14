"""ExternalAPIProxy._build_url must not let `path` escape base_url.

CodeQL py/partial-ssrf #9386 (critical, open on develop since 2026-03-09) fires
on proxy.py:86. The card hub-codeql-13-critical-exec-and-ssrf-20260805 recorded
it as "FIXED" by an earlier PR; it was not — measured 2026-08-14, the alert is
open on refs/heads/develop and the code still concatenated.

WHY THIS IS REACHABLE, which is what makes it worth a test rather than a
dismissal: views/api/external_api.py::external_proxy is `@login_required`
`@require_POST` and reads `path` straight out of the JSON request body, so any
authenticated tenant chooses it. The proxy then attaches the API's configured
credentials via default_headers. An escaping path therefore spends OUR
credentials on an endpoint the caller picked — a confused deputy, not merely a
malformed URL.

The traversal cases below are the point. The old code rendered "../admin" as
the *string* ".../v1/../admin", which looks contained; `requests` resolves the
`..` at send time, so the URL inspected and the URL sent were different values.
"""

import pytest

from apps.infra.platform_app.services.external_api.proxy import (
    ExternalAPIProxy,
    PathEscapesBaseURLError,
)

BASE = "https://api.example.com/v1"


def _proxy(base_url=BASE):
    return ExternalAPIProxy(
        app_name="test-app",
        api_config={"base_url": base_url, "allowed_methods": ["GET"]},
    )


# --------------------------------------------------------------------------- #
# Contained paths must still work — a containment check that rejects
# everything would pass every escape test and break the feature.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "path,expected",
    [
        ("works", f"{BASE}/works"),
        ("/works", f"{BASE}/works"),
        ("works/123", f"{BASE}/works/123"),
        ("nested/a/b/c", f"{BASE}/nested/a/b/c"),
    ],
)
def test_contained_paths_are_joined_unchanged(path, expected):
    assert _proxy()._build_url(path) == expected


def test_base_url_without_path_prefix_allows_any_path_on_that_host():
    """No path prefix on base_url means the whole host is the intended scope."""
    proxy = _proxy("https://api.example.com")
    assert proxy._build_url("anything/at/all") == "https://api.example.com/anything/at/all"


# --------------------------------------------------------------------------- #
# Escapes must raise. Each of these reaches a DIFFERENT origin or a path
# outside base_url once the URL is normalised.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "path",
    [
        "../admin",  # one level up, out of /v1
        "../../etc/passwd",  # several levels up
        "works/../../admin",  # traversal after a legitimate-looking segment
        "/../admin",  # leading slash does not change the resolution
    ],
)
def test_traversal_out_of_base_path_is_refused(path):
    with pytest.raises(PathEscapesBaseURLError):
        _proxy()._build_url(path)


@pytest.mark.parametrize(
    "path",
    [
        "..%2Fadmin",  # encoded separator: one segment here, traversal upstream
        "%2E%2E/admin",  # encoded dots
        "%2e%2e%2fadmin",  # both, lowercase
    ],
)
def test_percent_encoded_traversal_is_refused(path):
    """urljoin treats an encoded separator as an opaque segment, so it does not
    traverse in OUR resolution — it traverses on any upstream that decodes
    before routing. We cannot know which upstreams do, so this is refused
    rather than assumed safe."""
    with pytest.raises(PathEscapesBaseURLError):
        _proxy()._build_url(path)


@pytest.mark.parametrize(
    "path",
    [
        "https://evil.example.net/steal",  # absolute URL swaps the host
        "http://evil.example.net/steal",  # ...including a scheme downgrade
        "//evil.example.net/steal",  # protocol-relative
    ],
)
def test_absolute_or_protocol_relative_path_cannot_change_origin(path):
    with pytest.raises(PathEscapesBaseURLError):
        _proxy()._build_url(path)


def test_sibling_prefix_is_not_treated_as_contained():
    """Component-wise, not string-prefix: /v1x must not pass as inside /v1."""
    with pytest.raises(PathEscapesBaseURLError):
        _proxy()._build_url("../v1x/secrets")


# --------------------------------------------------------------------------- #
# POSITIVE CONTROL. Asserts the OLD implementation fails these tests, so a
# future refactor that silently reintroduces concatenation cannot leave this
# file green. Without this, the suite proves only that today's code passes
# today's tests.
# --------------------------------------------------------------------------- #
def test_the_old_concatenation_would_fail_this_suite():
    def old_build_url(base_url, path):
        return base_url.rstrip("/") + "/" + path.lstrip("/")

    escaped = old_build_url(BASE, "../admin")

    # The old result LOOKS contained as a string...
    assert escaped.startswith(BASE)
    # ...but normalises to a URL outside base_url, which is the whole bug.
    from urllib.parse import urlsplit, urljoin

    normalised = urljoin(escaped, ".")
    assert not urlsplit(normalised).path.startswith("/v1/"), (
        "positive control is inert: '../admin' no longer escapes /v1, so these "
        "tests would pass against the vulnerable implementation too"
    )
