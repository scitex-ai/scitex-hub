#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/infra/llm_app/skills/registry.py URL derivation.

Every app's URL is aggregated verbatim into the in-product assistant's system
prompt. Before this, each app DECLARED its prefix as a literal in skill.py, and
eight of eleven had gone stale after the move to /apps/<name>/: the assistant
handed users paths that only 301-redirect, and one (notebook) with no mount
behind it at all.

Retyping the literals would re-arm the same trap, so the literal is gone: the
mount is derived via reverse(). These tests are the barrier that keeps it gone.

EXPECTATIONS ARE DERIVED, NEVER HAND-TYPED. A hand-typed expectation drifts
exactly like the code it checks — while writing the bug report for this, a
hand-typed "real mount" table got two of eleven entries wrong. So the assertions
ask the resolver and LEGACY_APP_NAMES what is true, and never restate it.

Assertions collect an offender list and assert it is empty, so one failure names
every drifted app rather than stopping at the first.
"""

import pytest
from django.urls import NoReverseMatch, reverse

from apps.infra.llm_app.skills import (
    build_aggregated_context,
    get_all_skills,
    get_skill_for_page,
)
from apps.infra.llm_app.skills.registry import DuplicateSkillError, Skill, register
from config.urls_legacy_redirects import LEGACY_APP_NAMES


def _mounted_skills():
    """Skills that declare a route, i.e. claim to be reachable."""
    return {n: s for n, s in get_all_skills().items() if s.url_route}


def _unmounted_skills():
    """Skills that deliberately declare no route."""
    return {n: s for n, s in get_all_skills().items() if not s.url_route}


def test_skill_registry_is_not_empty():
    """Guard the guard: an empty registry makes every test below vacuous."""
    # Arrange
    # Act
    skills = get_all_skills()
    # Assert
    assert skills, "no skills registered — skill discovery did not run"


def test_at_least_one_skill_declares_a_route():
    """A registry where nothing is mounted would also pass vacuously."""
    # Arrange
    # Act
    mounted = _mounted_skills()
    # Assert
    assert mounted, "no skill declares a url_route"


def test_every_declared_route_resolves():
    """A declared route that does not resolve means a dead URL in the prompt."""
    # Arrange
    mounted = _mounted_skills()
    # Act
    unresolvable = []
    for name, skill in sorted(mounted.items()):
        try:
            reverse(skill.url_route)
        except NoReverseMatch as exc:
            unresolvable.append(f"{name}: url_route={skill.url_route!r} ({exc})")
    # Assert
    assert not unresolvable, f"skills with unresolvable url_route: {unresolvable}"


def test_resolve_url_agrees_with_reverse():
    """resolve_url() must be reverse(), not a reimplementation that can drift."""
    # Arrange
    mounted = _mounted_skills()
    # Act
    mismatched = [
        f"{name}: resolve_url={skill.resolve_url()!r} reverse={reverse(skill.url_route)!r}"
        for name, skill in sorted(mounted.items())
        if skill.resolve_url() != reverse(skill.url_route)
    ]
    # Assert
    assert not mismatched, f"resolve_url() disagrees with reverse(): {mismatched}"


def test_page_patterns_derive_from_the_resolved_url():
    """page_patterns held a second copy of the same stale string; now derived."""
    # Arrange
    mounted = _mounted_skills()
    # Act
    drifted = [
        f"{name}: page_patterns={skill.page_patterns!r} url={skill.resolve_url()!r}"
        for name, skill in sorted(mounted.items())
        if skill.page_patterns != [skill.resolve_url()]
    ]
    # Assert
    assert not drifted, f"page_patterns not derived from the mount: {drifted}"


def test_no_advertised_url_is_a_legacy_redirect():
    """The advertised URL must be the real mount, not a 301 shim.

    This is the regression that shipped: /scholar/, /writer/, /console/ and five
    more are RedirectView-only paths listed in LEGACY_APP_NAMES. The forbidden
    set is read from that list rather than restated, so adding a legacy name
    automatically widens the check.
    """
    # Arrange
    forbidden = {f"/{legacy}/" for legacy in LEGACY_APP_NAMES}
    mounted = _mounted_skills()
    # Act
    stale = [
        f"{name} -> {skill.resolve_url()}"
        for name, skill in sorted(mounted.items())
        if skill.resolve_url() in forbidden
    ]
    # Assert
    assert not stale, f"skills advertising a legacy 301 redirect: {stale}"


def test_unmounted_skill_resolves_to_none():
    """An app with no mount gets no URL — never a guessed root."""
    # Arrange
    unmounted = _unmounted_skills()
    # Act
    guessed = [
        f"{name} -> {skill.resolve_url()!r}"
        for name, skill in sorted(unmounted.items())
        if skill.resolve_url() is not None
    ]
    # Assert
    assert not guessed, f"unmounted skills produced a URL: {guessed}"


def test_unmounted_skill_has_no_page_patterns():
    """A skill with no mount must not claim pages either."""
    # Arrange
    unmounted = _unmounted_skills()
    # Act
    claiming = [
        f"{name} -> {skill.page_patterns!r}"
        for name, skill in sorted(unmounted.items())
        if skill.page_patterns
    ]
    # Assert
    assert not claiming, f"unmounted skills claiming pages: {claiming}"


def test_unmounted_skill_is_absent_from_the_assistant_context():
    """notebook_app advertised '/notebook/', which redirects to a 404."""
    # Arrange
    unmounted = _unmounted_skills()
    # Act
    context = build_aggregated_context()
    advertised = [
        name
        for name, skill in sorted(unmounted.items())
        if f"**{skill.display_name}** (" in context
    ]
    # Assert
    assert not advertised, f"unmounted skills advertised to the LLM: {advertised}"


def test_every_resolvable_url_appears_in_the_assistant_context():
    """The context must carry the derived URL, not some other string."""
    # Arrange
    mounted = {
        n: s for n, s in _mounted_skills().items() if s.module_description
    }
    # Act
    context = build_aggregated_context()
    missing = [
        f"{name} ({skill.resolve_url()})"
        for name, skill in sorted(mounted.items())
        if f"(`{skill.resolve_url()}`)" not in context
    ]
    # Assert
    assert not missing, f"mounted skills missing from the context: {missing}"


def test_page_match_prefers_the_most_specific_app():
    """Longest prefix wins, so a shallow mount cannot claim every page.

    repo_app previously declared page_patterns=['/'] and get_skill_for_page
    returned the FIRST substring match over dict order, so which app's
    capabilities the assistant loaded depended on registration order.
    """
    # Arrange
    resolved = {n: s.resolve_url() for n, s in _mounted_skills().items()}
    deepest = max(resolved, key=lambda n: len(resolved[n].rstrip("/")))
    # Act
    selected = get_skill_for_page(f"{resolved[deepest]}some/inner/page")
    # Assert
    assert selected is not None and selected.app_name == deepest, (
        f"page under {resolved[deepest]!r} selected "
        f"{selected and selected.app_name!r} instead of {deepest!r}"
    )


def test_no_landing_page_is_claimed_by_a_shallower_app():
    """Each app's own landing page must not resolve to a shallower mount."""
    # Arrange
    mounted = _mounted_skills()
    # Act
    hijacked = []
    for name, skill in sorted(mounted.items()):
        url = skill.resolve_url()
        selected = get_skill_for_page(url)
        if selected is None:
            hijacked.append(f"{name}: no skill matched its own page {url}")
        elif len(selected.resolve_url().rstrip("/")) < len(url.rstrip("/")):
            hijacked.append(
                f"{name} ({url}) claimed by shallower "
                f"{selected.app_name} ({selected.resolve_url()})"
            )
    # Assert
    assert not hijacked, f"landing pages claimed by a shallower app: {hijacked}"


def test_duplicate_app_name_from_another_module_is_rejected():
    """Two apps claiming one app_name silently dropped one from the map.

    public_app/skill.py and tools_app/skill.py shipped byte-identical, both
    registering app_name='tools'; the second overwrote the first with no signal.
    """
    # Arrange
    existing = next(iter(get_all_skills()))
    duplicate = Skill(
        app_name=existing,
        display_name="Collision Probe",
        description="registered from a different module than the original",
    )
    # Act
    # Assert
    with pytest.raises(DuplicateSkillError):
        register(duplicate)
