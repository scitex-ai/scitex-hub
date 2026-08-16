#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The visitor entry CTA must land on the LAUNCHER, not the repository browser.

A visitor clicking "Enter as visitor" used to be sent to /apps/home/, which
allocates a slot correctly but renders the Gitea-style repository browser — so
the first thing a prospective customer saw was dotfiles and "No commit message"
repeated six times.

The fix is a dedicated /enter/ route. Its correctness rests on ONE non-obvious
property: /enter/ must stay ABSENT from VisitorAutoLoginMiddleware's skip lists,
because that absence is what causes a slot to be allocated. Adding it to those
lists would break the funnel SILENTLY — the page would still load, just without
a workspace. That is the regression these tests exist to catch.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse

MIDDLEWARE_REL = "apps/infra/project_app/middleware.py"
HERO_REL = (
    "apps/infra/public_app/templates/public_app/landing_partials/landing_hero.html"
)

# The tuple names inside VisitorAutoLoginMiddleware._sync_body that cause a
# request to be skipped (i.e. NOT given a visitor slot).
SKIP_TUPLE_NAMES = ("skip_paths", "exact_public_paths")

# Below this, the AST parse is certainly matching the wrong nodes and every
# containment check built on it would pass vacuously.
MIN_CREDIBLE_SKIP_ENTRIES = 10


def _parse_skip_tuples():
    """Collect the string entries of the middleware's skip tuples via AST.

    Read from SOURCE rather than imported, because both tuples are locals inside
    a method and cannot be reached any other way.
    """
    src = (Path(settings.BASE_DIR) / MIDDLEWARE_REL).read_text(encoding="utf-8")
    tree = ast.parse(src)
    found = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name) or target.id not in SKIP_TUPLE_NAMES:
                continue
            if not isinstance(node.value, (ast.Tuple, ast.List)):
                continue
            found[target.id] = [
                el.value
                for el in node.value.elts
                if isinstance(el, ast.Constant) and isinstance(el.value, str)
            ]
    return found


@pytest.fixture
def skip_entries_by_name():
    """The middleware's skip tuples, keyed by variable name."""
    return _parse_skip_tuples()


@pytest.fixture
def enter_path():
    """Derived via reverse() so a route rename cannot silently pass these tests."""
    return reverse("public_app:visitor_enter")


@pytest.fixture
def hero_source():
    """Raw landing-hero template text."""
    return (Path(settings.BASE_DIR) / HERO_REL).read_text(encoding="utf-8")


@pytest.fixture
def provisioned_entry_response(client, django_user_model):
    """Response to GET /enter/ for a session that already has a user."""
    user = django_user_model.objects.create_user(
        username="visitor-test-entry", password="Password123!"
    )
    client.force_login(user)
    return client.get(reverse("public_app:visitor_enter"))


@pytest.fixture
def unprovisioned_entry_response():
    """Response from calling the view directly with no visitor session.

    Uses RequestFactory so VisitorAutoLoginMiddleware never runs — that is the
    only way to exercise the view's own no-slot branch.
    """
    from apps.infra.public_app.views import visitor_enter

    request = RequestFactory().get("/enter/")
    request.user = AnonymousUser()
    return visitor_enter(request)


def test_middleware_skip_tuples_are_both_found(skip_entries_by_name):
    """Anti-vacuity: the containment checks below mean nothing without a parse."""
    # Arrange
    expected = set(SKIP_TUPLE_NAMES)

    # Act
    actual = set(skip_entries_by_name)

    # Assert
    assert actual == expected, (
        f"AST parse did not find both skip tuples in {MIDDLEWARE_REL}; found "
        f"{sorted(actual)}. If the middleware was refactored, update "
        "SKIP_TUPLE_NAMES — do not delete this check."
    )


def test_middleware_skip_entries_are_plentiful(skip_entries_by_name):
    """Anti-vacuity: too few entries means the parse matched the wrong nodes."""
    # Arrange
    minimum = MIN_CREDIBLE_SKIP_ENTRIES

    # Act
    total = sum(len(v) for v in skip_entries_by_name.values())

    # Assert
    assert total > minimum, (
        f"only {total} skip entries parsed from {MIDDLEWARE_REL}, expected more "
        f"than {minimum}; the parse is unreliable so the containment checks "
        "would pass vacuously"
    )


def test_enter_path_is_not_prefix_skipped(skip_entries_by_name, enter_path):
    """skip_paths is startswith-matched, so a prefix entry would disable it.

    Checks ONLY skip_paths. The two tuples are matched by DIFFERENT operators in
    the middleware and must not be pooled: skip_paths via
    `any(path.startswith(p) ...)`, exact_public_paths via `path in (...)`.
    Pooling them makes this assertion fail on the "/" entry of
    exact_public_paths, which is harmless there precisely BECAUSE it is compared
    by equality — middleware.py:78-80 spells out that "/" must never be
    prefix-matched, since it prefixes every URL.
    """
    # Arrange
    prefix_matched_entries = skip_entries_by_name["skip_paths"]

    # Act
    prefix_hits = [e for e in prefix_matched_entries if enter_path.startswith(e)]

    # Assert
    assert prefix_hits == [], (
        f"{enter_path} is prefix-matched by skip_paths entries "
        f"{prefix_hits}, so VisitorAutoLoginMiddleware will NOT allocate a "
        "visitor slot and the entry CTA silently yields no workspace"
    )


def test_enter_path_is_not_exact_skipped(skip_entries_by_name, enter_path):
    """exact_public_paths is equality-matched and would also disable it."""
    # Arrange
    exact_matched_entries = skip_entries_by_name["exact_public_paths"]

    # Act
    exact_hits = [e for e in exact_matched_entries if e == enter_path]

    # Assert
    assert exact_hits == [], (
        f"{enter_path} is exact-matched by exact_public_paths {exact_hits}, so "
        "no visitor slot is allocated for the entry CTA"
    )


def test_hero_cta_links_the_enter_route(hero_source, enter_path):
    """The positive half of the CTA contract."""
    # Arrange
    cta_marker = f'href="{enter_path}" class="hero-cta-button"'

    # Act
    has_enter_cta = cta_marker in hero_source

    # Assert
    assert has_enter_cta, (
        f"expected the hero CTA to link {enter_path}; marker {cta_marker!r} is "
        f"absent from {HERO_REL}"
    )


def test_hero_cta_no_longer_links_repo_browser(hero_source):
    """The negative half, paired with the positive one on the same marker.

    Asserted separately because a negative assertion alone can pass for the
    wrong reason — if the CTA class were ever renamed, this would go quiet while
    the sibling positive test above would fail loudly.
    """
    # Arrange
    repo_browser_marker = 'href="/apps/home/" class="hero-cta-button"'

    # Act
    has_repo_browser_cta = repo_browser_marker in hero_source

    # Assert
    assert not has_repo_browser_cta, (
        "the hero CTA still links /apps/home/, which renders the Gitea-style "
        "repository browser — that first impression is the defect being removed"
    )


def test_enter_route_reverses_to_stable_path(enter_path):
    """The hero CTA and the middleware guard both depend on this exact path."""
    # Arrange
    expected = "/enter/"

    # Act
    resolved = enter_path

    # Assert
    assert resolved == expected, (
        f"public_app:visitor_enter resolves to {resolved!r}, not {expected!r}"
    )


@pytest.mark.django_db
def test_enter_redirects_a_provisioned_visitor(provisioned_entry_response):
    """An entry request with a session must redirect, not render."""
    # Arrange
    expected_status = 302

    # Act
    status = provisioned_entry_response.status_code

    # Assert
    assert status == expected_status, (
        f"expected {expected_status} toward the launcher, got {status}"
    )


@pytest.mark.django_db
def test_enter_location_is_the_launcher_root(provisioned_entry_response):
    """The launcher is served at "/" by root_dispatch, not at its own URL."""
    # Arrange
    expected_location = "/"

    # Act
    location = provisioned_entry_response["Location"]

    # Assert
    assert location == expected_location, (
        f"expected Location {expected_location!r}, got {location!r} — the "
        "launcher has no dedicated route and is only reachable via root_dispatch"
    )


@pytest.mark.django_db
def test_enter_without_a_session_still_redirects(unprovisioned_entry_response):
    """The no-slot branch must respond, not raise."""
    # Arrange
    expected_status = 302

    # Act
    status = unprovisioned_entry_response.status_code

    # Assert
    assert status == expected_status, (
        f"expected {expected_status} when unprovisioned, got {status}"
    )


@pytest.mark.django_db
def test_enter_without_a_session_fails_loudly(unprovisioned_entry_response):
    """No slot must not degrade quietly to the marketing page."""
    # Arrange
    expected_location = reverse("public_app:visitor_pool_full")

    # Act
    location = unprovisioned_entry_response["Location"]

    # Assert
    assert location == expected_location, (
        "an unprovisioned entry must go to the pool-full page, which TELLS the "
        f"user no workspace was available; got {location!r}. Redirecting to the "
        "landing page instead would be indistinguishable from the visitor "
        "never having clicked."
    )


# EOF
