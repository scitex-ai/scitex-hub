#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: tests/security/test_comms_participant_tenant_scope.py
"""Exploit-regression: cross-tenant participant directory leak (comms_app).

CONFIRMED VULNERABILITY
-----------------------
``apps/workspace/comms_app/views/participants.py`` exposed::

    class ParticipantListCreateView(generics.ListCreateAPIView):
        permission_classes = [permissions.IsAuthenticated]
        queryset = Participant.objects.all()          # <-- no caller filter

routed at ``GET /apps/comms/api/participants/`` (comms_app/urls.py ->
config/urls.py ``path("apps/comms/", ...)``).

``ParticipantSerializer`` returns ``display_name`` — populated from
``User.get_full_name()`` in ``ChannelListCreateView.perform_create`` — plus
``agent_name``, ``avatar_url``, ``is_online`` and ``last_seen``. With no
queryset filter, ANY authenticated caller read EVERY tenant's real names,
agent fleet and presence data: a cross-tenant user+agent directory. The hub
auto-logs real browsers in as pooled anonymous visitors
(``apps/infra/project_app/middleware.py``, whose skip list covers ``/api/``
but NOT ``/apps/comms/api/...``), so the public reached it without
registering. Being a ListCREATEAPIView, POST also let any caller mint
arbitrary agent Participant rows (``agent_name`` has no unique constraint,
so a forged ``orochi-bridge`` row wedges the bridge daemon's
``Participant.objects.get(...)`` with ``MultipleObjectsReturned``).

THE FIX
-------
``ParticipantListView`` (ListAPIView — POST removed) scopes ``get_queryset``
to the caller's own Participant plus co-members of the non-archived channels
the caller belongs to. ``ChannelMembership`` is the authoritative access
relation everywhere else in this app.

WHY THESE TESTS LOOK LIKE THIS
------------------------------
These are BEHAVIOURAL, not source-text gates. The fixtures build TWO real
tenants with their own users, participants, channels and memberships, each
test dispatches the REAL view through DRF's ``APIRequestFactory``, and the
assertions read the RESPONSE BODY — tenant B's participant ids and display
names must be ABSENT from tenant A's payload. The anti-regression twins
assert a legitimate co-member and the caller's own row ARE returned, so
"deny everything" cannot pass. No mocks (project rule); the DB is real.
One assertion per test (STX-TQ007), shared setup lifted into fixtures.

DB NOTE: these need the Django test DB. The pytest-matrix workflow runs the
whole suite with ``SCITEX_HUB_USE_SQLITE_DEV=1``; the security-regression job
in tests.yml sets the same flag so this gate runs there too.
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.workspace.comms_app.models import Channel, ChannelMembership, Participant
from apps.workspace.comms_app.views import ParticipantListView

pytestmark = [pytest.mark.security, pytest.mark.django_db]

TENANT_B_SECRET_NAME = "Beatrice Cross-Tenant-Surname"
TENANT_B_AGENT_NAME = "tenant-b-private-agent"
URL = "/apps/comms/api/participants/"


# ---------------------------------------------------------------------------
# Builders (assert-free on purpose — the assertions live in the tests)
# ---------------------------------------------------------------------------


def _make_user(username, first, last):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="Password123!",  # pragma: allowlist secret
        first_name=first,
        last_name=last,
    )


def _make_participant(user):
    """Mint a participant exactly the way the app does (channels.py)."""
    return Participant.objects.create(
        user=user,
        participant_type="user",
        display_name=user.get_full_name() or user.username,
    )


def _make_channel(name, slug, owner_participant, is_archived=False):
    channel = Channel.objects.create(
        name=name,
        slug=slug,
        created_by=owner_participant,
        is_archived=is_archived,
    )
    ChannelMembership.objects.create(
        channel=channel, participant=owner_participant, role="owner"
    )
    return channel


def _get_as(user):
    """Dispatch the REAL view as ``user`` and return the rendered response."""
    request = APIRequestFactory().get(URL)
    force_authenticate(request, user=user)
    response = ParticipantListView.as_view()(request)
    response.render()
    return response


def _rows(response):
    """Unwrap the body's rows (DRF pagination is enabled globally)."""
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return list(data["results"])
    return list(data)


def _ids(response):
    return [row["id"] for row in _rows(response)]


def _post_as(user):
    """Attempt a client-side Participant creation (the spoofing surface)."""
    request = APIRequestFactory().post(
        URL,
        {
            "participant_type": "agent",
            "agent_name": "orochi-bridge",
            "display_name": "Impersonator",
        },
        format="json",
    )
    force_authenticate(request, user=user)
    return ParticipantListView.as_view()(request)


# ---------------------------------------------------------------------------
# Fixtures — two genuinely separate tenants sharing NO channel
# ---------------------------------------------------------------------------


@pytest.fixture
def tenants():
    # --- Tenant A -----------------------------------------------------
    user_a = _make_user("tenant-a-owner", "Alice", "Alpha")
    part_a = _make_participant(user_a)
    channel_a = _make_channel("Tenant A Room", "tenant-a-room", part_a)

    # A legitimate co-member of tenant A's channel (anti-regression twin).
    user_a_mate = _make_user("tenant-a-mate", "Aaron", "Ally")
    part_a_mate = _make_participant(user_a_mate)
    ChannelMembership.objects.create(
        channel=channel_a, participant=part_a_mate, role="member"
    )

    # --- Tenant B (must never be visible to tenant A) ------------------
    user_b = _make_user("tenant-b-owner", "Beatrice", "Cross-Tenant-Surname")
    part_b = _make_participant(user_b)
    channel_b = _make_channel("Tenant B Room", "tenant-b-room", part_b)

    # Tenant B's private agent fleet — tenant-owned property.
    part_b_agent = Participant.objects.create(
        participant_type="agent",
        agent_name=TENANT_B_AGENT_NAME,
        display_name="Tenant B Private Agent",
    )
    ChannelMembership.objects.create(
        channel=channel_b, participant=part_b_agent, role="member"
    )

    return {
        "user_a": user_a,
        "part_a": part_a,
        "part_a_mate": part_a_mate,
        "user_b": user_b,
        "part_b": part_b,
        "part_b_agent": part_b_agent,
    }


@pytest.fixture
def response_a(tenants):
    """Tenant A's live GET against the real view."""
    return _get_as(tenants["user_a"])


@pytest.fixture
def names_a(response_a):
    """Every human-readable identity string in tenant A's response body."""
    names = set()
    for row in _rows(response_a):
        names.add(row["display_name"])
        names.add(row["agent_name"])
    return names


# ---------------------------------------------------------------------------
# THE LEAK — another tenant must be ABSENT from the response BODY
# ---------------------------------------------------------------------------


def test_list_request_succeeds_for_a_participant_owning_caller(response_a):
    # Arrange
    expected = 200
    # Act
    observed = response_a.status_code
    # Assert
    assert observed == expected


def test_other_tenants_participant_ids_are_absent_from_the_body(tenants, response_a):
    # Arrange
    other_ids = {tenants["part_b"].id, tenants["part_b_agent"].id}
    # Act
    leaked = other_ids & set(_ids(response_a))
    # Assert
    assert not leaked, (
        f"Cross-tenant leak: GET {URL} returned participant ids "
        f"{sorted(leaked)} belonging to another tenant. "
        "ParticipantListView.get_queryset must scope to the caller's own row "
        "plus their channel co-members (ChannelMembership)."
    )


def test_other_tenants_real_name_is_absent_from_the_body(names_a):
    # Arrange
    secret = TENANT_B_SECRET_NAME
    # Act
    leaked = secret in names_a
    # Assert
    assert not leaked, (
        "Cross-tenant PII leak: another tenant's real name (from "
        f"User.get_full_name()) appeared in the {URL} response body."
    )


def test_other_tenants_private_agent_name_is_absent_from_the_body(names_a):
    # Arrange
    secret = TENANT_B_AGENT_NAME
    # Act
    leaked = secret in names_a
    # Assert
    assert not leaked, (
        "Cross-tenant leak: another tenant's private agent name appeared in "
        "the participant list body — an agent participant is tenant-owned "
        "property (its owner is reachable only through APIKey.user)."
    )


def test_scoping_is_symmetric_tenant_b_cannot_see_tenant_a(tenants):
    """Scoping must not be a one-way accident: B must not see A either."""
    # Arrange
    a_ids = {tenants["part_a"].id, tenants["part_a_mate"].id}
    # Act
    leaked = a_ids & set(_ids(_get_as(tenants["user_b"])))
    # Assert
    assert not leaked, (
        "Cross-tenant leak in the opposite direction: tenant B's response "
        f"contained tenant A participant ids {sorted(leaked)}."
    )


# ---------------------------------------------------------------------------
# ANTI-REGRESSION TWINS — "deny everything" must NOT pass
# ---------------------------------------------------------------------------


def test_caller_sees_their_own_participant_row(tenants, response_a):
    # Arrange
    my_id = tenants["part_a"].id
    # Act
    returned_ids = set(_ids(response_a))
    # Assert
    assert my_id in returned_ids, (
        "Over-restriction: the caller's OWN participant row is missing. "
        "Q(pk=me.pk) must be its own term in the scoping predicate — a caller "
        "with zero memberships would otherwise get an empty list."
    )


def test_a_legitimate_channel_co_member_is_still_returned(tenants, response_a):
    # Arrange
    mate_id = tenants["part_a_mate"].id
    # Act
    returned_ids = set(_ids(response_a))
    # Assert
    assert mate_id in returned_ids, (
        "Over-restriction: a participant who co-members the caller's channel "
        "must still be visible — otherwise the fix is 'deny everything', "
        "which is not a fix."
    )


def test_a_returned_co_member_keeps_its_display_name(tenants, response_a):
    # Arrange
    mate_id = tenants["part_a_mate"].id
    # Act
    by_id = {row["id"]: row for row in _rows(response_a)}
    # Assert
    assert by_id.get(mate_id, {}).get("display_name") == "Aaron Ally", (
        "A legitimately visible co-member's payload was altered or dropped."
    )


def test_a_co_member_sharing_two_channels_appears_exactly_once(tenants):
    """`.distinct()` is load-bearing: the reverse join duplicates per channel."""
    # Arrange — a SECOND shared channel between the same two participants
    second = _make_channel("Tenant A Room 2", "tenant-a-room-2", tenants["part_a"])
    ChannelMembership.objects.create(
        channel=second, participant=tenants["part_a_mate"], role="member"
    )
    # Act
    occurrences = _ids(_get_as(tenants["user_a"])).count(tenants["part_a_mate"].id)
    # Assert
    assert occurrences == 1, (
        f"Duplicate rows: a co-member sharing 2 channels was returned "
        f"{occurrences} times. ParticipantListView.get_queryset must call "
        ".distinct()."
    )


# ---------------------------------------------------------------------------
# FAIL CLOSED — no participant row, archived channels
# ---------------------------------------------------------------------------


@pytest.fixture
def response_for_user_without_participant(tenants):
    """A caller with NO Participant row — the common case.

    Rows are only minted on first channel creation
    (``ChannelListCreateView.perform_create``), so most accounts have none.
    ``tenants`` is requested so the table is NOT empty: a fail-open queryset
    would hand this caller other tenants' rows.
    """
    stranger = _make_user("no-participant-user", "Nora", "Nobody")
    return _get_as(stranger)


def test_user_without_a_participant_row_is_not_a_server_error(
    response_for_user_without_participant,
):
    # Arrange
    expected = 200
    # Act
    observed = response_for_user_without_participant.status_code
    # Assert
    assert observed == expected, (
        "A user with no Participant row must not 500 — resolve the caller's "
        "Participant with a try/except DoesNotExist, not a bare .get()."
    )


def test_user_without_a_participant_row_gets_an_empty_list(
    response_for_user_without_participant,
):
    # Arrange
    response = response_for_user_without_participant
    # Act
    rows = _rows(response)
    # Assert
    assert rows == [], (
        f"Fail-open: a caller with no Participant row received {len(rows)} "
        "row(s) from a populated table. Participant.DoesNotExist must return "
        ".none(), never .all() and never a silent fallback."
    )


def test_co_members_reachable_only_through_an_archived_channel_are_hidden(tenants):
    """Mirrors ChannelListCreateView / CommsConsumer: archived channels are out."""
    # Arrange
    archived = _make_channel(
        "Archived Room", "archived-room", tenants["part_a"], is_archived=True
    )
    outsider = _make_participant(_make_user("archived-mate", "Zed", "Zulu"))
    ChannelMembership.objects.create(
        channel=archived, participant=outsider, role="member"
    )
    # Act
    returned_ids = set(_ids(_get_as(tenants["user_a"])))
    # Assert
    assert outsider.id not in returned_ids, (
        "A co-member reachable only through an ARCHIVED channel was returned; "
        "the channel-id subquery must filter channel__is_archived=False."
    )


# ---------------------------------------------------------------------------
# POST — the identity-spoofing surface must be gone
# ---------------------------------------------------------------------------


@pytest.fixture
def post_attempt(tenants):
    """(response, participant-count-delta) for a client-side create attempt."""
    before = Participant.objects.count()
    response = _post_as(tenants["user_a"])
    return response, Participant.objects.count() - before


def test_post_to_the_participant_endpoint_is_method_not_allowed(post_attempt):
    # Arrange
    response, _delta = post_attempt
    # Act
    observed = response.status_code
    # Assert
    assert observed == 405, (
        f"POST {URL} must be Method Not Allowed (got {observed}). A "
        "client-minted Participant can never authenticate (the serializer "
        "cannot set user/api_key), so the verb is pure identity-spoofing "
        "surface: a forged agent_name='orochi-bridge' row wedges the bridge "
        "daemon's Participant.objects.get(...) with MultipleObjectsReturned."
    )


def test_post_to_the_participant_endpoint_creates_no_row(post_attempt):
    # Arrange
    _response, delta = post_attempt
    # Act
    created = delta
    # Assert
    assert created == 0, (
        f"{created} Participant row(s) were created over HTTP. Every row is "
        "minted server-side (channels.py perform_create, the orochi_bridge "
        "management command, or Django admin)."
    )
