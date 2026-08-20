#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""No public route may be classified as a user profile.

WHAT WENT WRONG. `_is_user_profile_path` is a DENYLIST: any first path segment
that is not in `_NON_USER_PREFIXES` is treated as a username. So every public
route is a username *by default*, and stays one until somebody remembers to add
it to the list. Nothing errors when that is forgotten.

Measured on production 2026-08-15, signed in:

    GET /tokushoho/  ->  body class="workspace-page home-page no-transition"

/tokushoho/ is the 特定商取引法 disclosure. Classified as a workspace page it
lost its footer (hidden by `body.workspace-page`) AND could not scroll
(`height:100vh; overflow:hidden`), so any content below the fold was unreachable
on a statutory page. It only misbehaved when SIGNED IN — anonymous visitors take
a different branch — which is why every casual look at it seemed fine.

WHY THIS TEST IS DERIVED, NOT LISTED. Writing "assert tokushoho is in the set"
would guard the one route we already know about and rot exactly like the denylist
it is guarding. Instead it ENUMERATES the public URL conf, so a route added
tomorrow is covered without anyone editing this file. That is the only version
that survives the failure mode.

It also runs with no DB and no HTTP: it calls the classifier directly, so it
cannot pass for an unrelated reason such as a redirect or an auth branch.
"""

import pytest

from apps.infra.workspace_app.context_processors import _is_user_profile_path


def _public_first_segments():
    """First path segment of every STATIC route in public_app's page URLs.

    Dynamic routes (``<slug:...>``) are skipped: their first segment is a
    placeholder, not a literal path, so they are genuinely ambiguous with a
    username and are not what this guard is about.
    """
    from apps.infra.public_app.urls import pages

    segments = set()
    for entry in pages.urlpatterns:
        route = str(getattr(entry.pattern, "_route", ""))
        first = route.strip("/").split("/")[0]
        if not first or "<" in first:
            continue
        segments.add(first)
    return sorted(segments)


class TestPublicRoutesAreNotUserProfiles:
    """A public page must never be served as somebody's profile."""

    def test_public_url_conf_yields_routes_to_check(self):
        # Without this the two tests below pass vacuously on an empty list —
        # which is the same "gate that cannot fail" this file exists to prevent.
        # Arrange
        segments = _public_first_segments()
        # Act
        count = len(segments)
        # Assert
        assert count > 0

    def test_no_public_route_is_classified_as_a_username(self):
        # Arrange
        segments = _public_first_segments()
        # Act
        misrouted = [s for s in segments if _is_user_profile_path(f"/{s}/")]
        # Assert
        assert misrouted == []

    def test_the_tokushoho_disclosure_is_not_a_username(self):
        # Named explicitly as well as covered by the sweep above: this is the
        # statutory page, the reason the defect mattered, and the one whose
        # regression must be unmissable in a failure report.
        # Arrange
        path = "/tokushoho/"
        # Act
        is_profile = _is_user_profile_path(path)
        # Assert
        assert is_profile is False


class TestTheClassifierStillClassifies:
    """Positive control.

    Every assertion above is of the form "this is NOT a profile", and they would
    all pass on a classifier that returned False for everything — a change that
    would break real user profiles while turning this file green. So prove it
    still says yes to something.
    """

    def test_an_ordinary_username_is_still_a_profile(self):
        # Arrange
        path = "/some-person/"
        # Act
        is_profile = _is_user_profile_path(path)
        # Assert
        assert is_profile is True


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
