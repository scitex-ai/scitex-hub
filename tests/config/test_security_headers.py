"""Origin-side browser security (config/security_headers.py).

- a visitor who reached the edge over plain HTTP is redirected to https, an
  internal caller with no edge header is not (no loop, no broken webhooks);
- every response carries a CSP (report-only by default) and a
  Permissions-Policy, without overwriting a CSP a view set itself;
- the Django admin answers 404 to anyone but active staff, including its
  login form, and honours the optional network allowlist.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.http import Http404, HttpResponse
from django.test import RequestFactory, override_settings

from config.security_headers import (
    AdminAccessMiddleware,
    EdgeHttpsRedirectMiddleware,
    SecurityHeadersMiddleware,
    build_csp,
    edge_scheme,
    with_analytics_origin,
)

rf = RequestFactory()


def _raised_type(call):
    """The exception type ``call()`` raises, or None."""
    try:
        call()
    except Exception as exc:  # noqa: BLE001 - the type is the result
        return type(exc)
    return None


def _ok(_request):
    return HttpResponse("ok")


# ── edge scheme / redirect ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "meta, expected",
    [
        ({"HTTP_CF_VISITOR": '{"scheme":"http"}'}, "http"),
        ({"HTTP_CF_VISITOR": '{"scheme":"https"}'}, "https"),
        # prod nginx forces X-Forwarded-Proto=https; CF-Visitor still wins
        (
            {"HTTP_CF_VISITOR": '{"scheme":"http"}', "HTTP_X_FORWARDED_PROTO": "https"},
            "http",
        ),
        ({"HTTP_X_FORWARDED_PROTO": "http"}, "http"),
        ({"HTTP_X_FORWARDED_PROTO": "https"}, "https"),
        ({}, None),
        ({"HTTP_CF_VISITOR": "not json"}, None),
    ],
)
def test_edge_scheme_reads_cf_visitor_then_forwarded_proto(meta, expected):
    # Arrange
    request = rf.get("/", **meta)
    # Act
    scheme = edge_scheme(request)
    # Assert
    assert scheme == expected


@override_settings(EDGE_HTTPS_REDIRECT=True, ALLOWED_HOSTS=["scitex.ai"])
def test_plain_http_visitor_is_redirected_to_https_with_path_and_query():
    # Arrange
    request = rf.get(
        "/auth/signin/?next=/x",
        HTTP_HOST="scitex.ai",
        HTTP_CF_VISITOR='{"scheme":"http"}',
    )
    # Act
    response = EdgeHttpsRedirectMiddleware(_ok)(request)
    # Assert
    assert (response.status_code, response["Location"]) == (
        301,
        "https://scitex.ai/auth/signin/?next=/x",
    )


@override_settings(EDGE_HTTPS_REDIRECT=True, ALLOWED_HOSTS=["scitex.ai"])
def test_plain_http_post_keeps_its_method_with_308():
    # Arrange
    request = rf.post("/api/x/", HTTP_HOST="scitex.ai", HTTP_X_FORWARDED_PROTO="http")
    # Act
    response = EdgeHttpsRedirectMiddleware(_ok)(request)
    # Assert
    assert response.status_code == 308


@override_settings(EDGE_HTTPS_REDIRECT=True, ALLOWED_HOSTS=["*"])
@pytest.mark.parametrize(
    "meta",
    [
        {},  # internal caller: http://django:8000, no edge header
        {"HTTP_CF_VISITOR": '{"scheme":"https"}'},
        {"HTTP_X_FORWARDED_PROTO": "https"},
    ],
)
def test_https_and_internal_requests_pass_through(meta):
    # Arrange
    request = rf.get("/healthz/", HTTP_HOST="django:8000", **meta)
    # Act
    response = EdgeHttpsRedirectMiddleware(_ok)(request)
    # Assert
    assert response.status_code == 200


@override_settings(EDGE_HTTPS_REDIRECT=False, ALLOWED_HOSTS=["scitex.ai"])
def test_redirect_can_be_switched_off():
    # Arrange
    request = rf.get("/", HTTP_HOST="scitex.ai", HTTP_X_FORWARDED_PROTO="http")
    # Act
    response = EdgeHttpsRedirectMiddleware(_ok)(request)
    # Assert
    assert response.status_code == 200


@override_settings(EDGE_HTTPS_REDIRECT=True, ALLOWED_HOSTS=["scitex.ai"])
def test_redirect_never_targets_a_foreign_host():
    # Arrange: get_host() refuses a Host outside ALLOWED_HOSTS
    from django.core.exceptions import DisallowedHost

    request = rf.get("/", HTTP_HOST="evil.example", HTTP_X_FORWARDED_PROTO="http")
    # Act
    raised = _raised_type(lambda: EdgeHttpsRedirectMiddleware(_ok)(request))
    # Assert
    assert raised is DisallowedHost


# ── CSP / Permissions-Policy ────────────────────────────────────────────


def test_csp_is_report_only_by_default_and_names_the_report_endpoint():
    # Arrange
    middleware = SecurityHeadersMiddleware(_ok)
    # Act
    response = middleware(rf.get("/"))
    # Assert
    assert (
        "Content-Security-Policy" not in response,
        "report-uri /api/csp-report/"
        in response["Content-Security-Policy-Report-Only"],
        # no report-to: with it, Chrome ignores report-uri (see build_csp)
        "report-to" in response["Content-Security-Policy-Report-Only"],
    ) == (True, True, False)


def test_csp_restricts_framing_objects_and_base():
    # Arrange
    response = SecurityHeadersMiddleware(_ok)(rf.get("/"))
    # Act
    policy = response["Content-Security-Policy-Report-Only"]
    # Assert
    assert all(
        d in policy
        for d in (
            "frame-ancestors 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "default-src 'self'",
        )
    )


@override_settings(CSP_MODE="enforce")
def test_enforce_mode_sends_the_enforcing_header():
    # Arrange
    middleware = SecurityHeadersMiddleware(_ok)
    # Act
    response = middleware(rf.get("/"))
    # Assert
    assert ("Content-Security-Policy" in response) and (
        "Content-Security-Policy-Report-Only" not in response
    )


@override_settings(CSP_MODE="off")
def test_off_mode_sends_no_csp_but_keeps_permissions_policy():
    # Arrange
    middleware = SecurityHeadersMiddleware(_ok)
    # Act
    response = middleware(rf.get("/"))
    # Assert
    assert (
        "Content-Security-Policy-Report-Only" not in response,
        "Permissions-Policy" in response,
    ) == (True, True)


@override_settings(CSP_MODE="block-everything")
def test_unknown_csp_mode_fails_loud_at_startup():
    # Arrange: nothing beyond the fixtures/settings
    # Act
    raised = _raised_type(lambda: SecurityHeadersMiddleware(_ok))
    # Assert
    assert raised is ValueError


def test_a_view_that_sets_its_own_csp_keeps_it():
    # Arrange: e.g. files_app serves user files with "sandbox; default-src 'none'"
    def sandboxed(_request):
        response = HttpResponse("file")
        response["Content-Security-Policy"] = "sandbox; default-src 'none'"
        return response

    # Act
    response = SecurityHeadersMiddleware(sandboxed)(rf.get("/files/x"))
    # Assert
    assert (
        response["Content-Security-Policy"],
        "Content-Security-Policy-Report-Only" in response,
    ) == ("sandbox; default-src 'none'", False)


def test_permissions_policy_allows_only_what_the_site_uses():
    # Arrange
    response = SecurityHeadersMiddleware(_ok)(rf.get("/"))
    # Act
    policy = response["Permissions-Policy"]
    # Assert
    assert all(
        p in policy
        for p in (
            "camera=(self)",
            "microphone=(self)",
            "fullscreen=(self)",
            "geolocation=()",
            "payment=()",
            "usb=()",
        )
    )


def test_analytics_origin_is_added_to_script_and_connect_only():
    # Arrange
    directives = {"script-src": ["'self'"], "connect-src": ["'self'"], "img-src": []}
    # Act
    out = with_analytics_origin(directives, "https://analytics.example/script.js")
    # Assert
    assert (out["script-src"][-1], out["connect-src"][-1], out["img-src"]) == (
        "https://analytics.example",
        "https://analytics.example",
        [],
    )


def test_build_csp_joins_directives():
    # Arrange: nothing beyond the fixtures/settings
    # Act
    value = build_csp({"default-src": ["'self'"]}, "/r/")
    # Assert
    assert value == "default-src 'self'; report-uri /r/"


# ── admin access ────────────────────────────────────────────────────────


def _user(**flags):
    user = get_user_model()(username="u", is_active=True, **flags)
    return user


def _admin_request(user, **meta):
    from django.conf import settings

    request = rf.get("/" + settings.ADMIN_URL_PATH + "login/", **meta)
    request.user = user
    return request


def test_anonymous_visitor_gets_404_not_the_admin_login_form():
    # Arrange
    from django.contrib.auth.models import AnonymousUser

    request = _admin_request(AnonymousUser())
    # Act
    raised = _raised_type(lambda: AdminAccessMiddleware(_ok)(request))
    # Assert
    assert raised is Http404


def test_signed_in_non_staff_user_gets_404():
    # Arrange
    request = _admin_request(_user(is_staff=False))
    # Act
    raised = _raised_type(lambda: AdminAccessMiddleware(_ok)(request))
    # Assert
    assert raised is Http404


def test_active_staff_reaches_the_admin():
    # Arrange
    request = _admin_request(_user(is_staff=True))
    # Act
    response = AdminAccessMiddleware(_ok)(request)
    # Assert
    assert response.status_code == 200


@override_settings(ADMIN_ALLOWED_NETWORKS=["192.0.2.0/24"])
def test_staff_outside_the_allowed_networks_gets_404():
    # Arrange
    request = _admin_request(_user(is_staff=True), HTTP_CF_CONNECTING_IP="198.51.100.7")
    # Act
    raised = _raised_type(lambda: AdminAccessMiddleware(_ok)(request))
    # Assert
    assert raised is Http404


@override_settings(ADMIN_ALLOWED_NETWORKS=["192.0.2.0/24"])
def test_staff_inside_the_allowed_networks_reaches_the_admin():
    # Arrange
    request = _admin_request(_user(is_staff=True), HTTP_CF_CONNECTING_IP="192.0.2.10")
    # Act
    response = AdminAccessMiddleware(_ok)(request)
    # Assert
    assert response.status_code == 200


@override_settings(ADMIN_ALLOWED_NETWORKS=["192.0.2.0/24"])
def test_a_forwarded_ip_from_an_untrusted_peer_is_not_honoured():
    # Arrange: the peer is not a trusted proxy, so its CF-Connecting-IP is
    # ignored and the gate keys on the peer address itself (apps.client_ip).
    request = _admin_request(
        _user(is_staff=True),
        REMOTE_ADDR="198.51.100.7",
        HTTP_CF_CONNECTING_IP="192.0.2.10",
    )
    # Act
    raised = _raised_type(lambda: AdminAccessMiddleware(_ok)(request))
    # Assert
    assert raised is Http404


@override_settings(ADMIN_ALLOWED_NETWORKS=["not-a-network"])
def test_a_malformed_network_fails_loud_at_startup():
    # Arrange: nothing beyond the fixtures/settings
    # Act
    raised = _raised_type(lambda: AdminAccessMiddleware(_ok))
    # Assert
    assert raised is ValueError


def test_non_admin_paths_are_untouched():
    # Arrange
    from django.contrib.auth.models import AnonymousUser

    request = rf.get("/about/")
    request.user = AnonymousUser()
    # Act
    response = AdminAccessMiddleware(_ok)(request)
    # Assert
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_login_url_is_a_404_end_to_end(client):
    # Arrange
    from django.conf import settings

    # Act
    response = client.get("/" + settings.ADMIN_URL_PATH + "login/")
    # Assert
    assert (response.status_code, response.has_header("Location")) == (404, False)
