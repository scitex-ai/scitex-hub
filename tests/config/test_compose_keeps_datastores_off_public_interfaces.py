#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A database or cache may only publish on loopback.

WHY THIS TEST EXISTS. Measured 2026-08-16 on ``origin/develop``,
``deployment/docker/docker-compose.staging.yml``::

    postgres:
      ports:
        - "5434:5432"   # Staging postgres port
    redis:
      ports:
        - "6380:6379"   # Staging redis port

Neither entry carries an interface, so Docker publishes both on ``0.0.0.0`` --
every interface the host has. Staging postgres holds real user rows, and redis
holds Django's sessions: a session key lifted from redis is an authenticated
account, with no password involved. Nothing in front of either port asks who is
calling, because neither service has its own authentication worth the name at
this exposure -- postgres trusts a password that lives in an env file, redis is
configured with none at all.

THE FIX HAD ALREADY BEEN WRITTEN AND THAT IS THE POINT. The one-line postgres
repair sat UNCOMMITTED in the shared checkout for four days -- no branch, no
commit, no remote -- while ``origin/develop`` stayed exposed. A fix that exists
only as a working-tree edit is one ``git checkout`` from never having happened,
and the redis line beside it shows the other half of the failure: a fix applied
by hand to the service someone was looking at, while the identical defect two
stanzas below went untouched. Both halves are memory failures, and memory is
what this file replaces.

WHY IT IS A GUARD AND NOT A NOTE. The regression is a single missing prefix,
added months from now by someone opening a port who has no reason to know the
rule. That is precisely the class of rule that is forgotten at the moment it
matters, so it belongs in a gate rather than in a comment.

HOW THIS DIFFERS FROM ITS SIBLING, which is not a duplicate of it.
``test_compose_keeps_debug_stacks_off_public_interfaces.py`` gates a DIFFERENT
population -- services whose Django ``DEBUG`` defaults to True -- and says so
explicitly: "It is not 'never bind 0.0.0.0'." Under that rule staging's postgres
is legal, because postgres runs no Django settings module at all and therefore
never enters its sweep. Two rules, two populations, one shared parser in
``_compose_helpers.py`` so they can never disagree about what "loopback" means.

WHY THE RULE IS ABSOLUTE FOR THIS POPULATION. The sibling deliberately pairs two
facts, because a public web port is legitimate. There is no matching legitimate
case here: a datastore reached from another host goes through an application, or
over the fleet overlay via an explicit address -- never by publishing on every
interface. Offering an exemption knob would be offering a choice we do not intend
to support, so this gate has none. If off-host access is ever genuinely required,
that is an edit to this file with a written reason, reviewed like any other.

THE LIMIT OF THIS GUARD, stated because a partial gate presented as a total one
is worse than none. It reads the compose files in THIS repository. It cannot see
a compose file kept on a host outside the repo, and it does not inspect a running
container -- so a green result here means "the repo asks for loopback", not "the
live host binds loopback". Confirming the second is a separate job, done against
``docker ps --format`` on the host.
"""

import pytest

from ._compose_helpers import (
    MIN_EXPECTED_COMPOSE_FILES,
    REPO_ROOT,
    UNPARSEABLE_SERVICE,
    compose_files,
    published_on_public_interface,
    services,
)

# Substrings that identify a datastore, matched against the service's image and,
# when the service is an override layer with no image of its own, its name.
#
# Every entry except the last three is an image ACTUALLY present in this repo's
# compose files, measured 2026-08-16 -- postgres:15-alpine, redis:7-alpine, and
# edoburu/pgbouncer. The remaining three are the stores this stack would plausibly
# grow into; they are cheap to carry and each would otherwise arrive unguarded.
#
# pgbouncer is here because it speaks the postgres wire protocol and accepts the
# same credentials. A pooler published to the world is a database published to the
# world with an extra hop.
_DATASTORE_TOKENS = (
    "postgres",
    "pgbouncer",
    "redis",
    "valkey",
    "mysql",
    "mariadb",
    "mongo",
    "elasticsearch",
    "opensearch",
    "memcached",
    "rabbitmq",
    "clickhouse",
)

# Images that CONTAIN a datastore token but are not datastores themselves. Umami
# ships as `umami:postgresql-latest` -- an analytics web UI whose tag names the
# database it talks to. Without this, the gate would fail a correct public bind,
# which is how a gate gets deleted instead of obeyed.
_NOT_DATASTORE_IMAGES = ("umami",)


def _is_datastore(name, service):
    """True when this compose service IS a database, cache or queue.

    Keyed on the image where there is one. Compose override layers -- staging's
    ``postgres:`` stanza carries only ``ports:`` and ``command:`` -- have no
    image, and those are exactly the stanzas this gate was written for, so the
    service NAME is the fallback rather than a reason to skip.
    """
    if name == UNPARSEABLE_SERVICE:
        return True
    image = str(service.get("image") or "").lower()
    if any(token in image for token in _NOT_DATASTORE_IMAGES):
        return False
    subject = image if image else str(name).lower()
    return any(token in subject for token in _DATASTORE_TOKENS)


def _cases():
    """``(path, service, ports)`` for every datastore service that publishes ports."""
    out = []
    for path in compose_files():
        for name, svc in services(path):
            if not _is_datastore(name, svc):
                continue
            ports = svc.get("ports") or []
            if ports:
                out.append((path, name, list(ports)))
    return out


_ALL = _cases()


def test_compose_discovery_found_the_expected_files():
    # Arrange -- THE DISCOVERY CONTROL. Without it a directory rename turns the
    # glob into zero files and every assertion below passes by finding nothing,
    # which is indistinguishable from finding nothing wrong.
    files = compose_files()
    # Act
    count = len(files)
    # Assert
    assert count >= MIN_EXPECTED_COMPOSE_FILES, (
        f"compose discovery found only {count} file(s) (expected at least "
        f"{MIN_EXPECTED_COMPOSE_FILES}). The sweep below is vacuous until this is "
        f"fixed -- do not lower the floor to go green."
    )


def test_sweep_actually_found_datastore_services():
    # Arrange -- THE POPULATION CONTROL. Files can be discovered while every
    # service is skipped: an image bump to a name the token list does not carry,
    # or a service rename, produces an empty sweep that reports clean.
    cases = _ALL
    # Act
    count = len(cases)
    # Assert
    assert count > 0, (
        "no datastore service with published ports was found in any compose file. "
        "Either the images changed to names _DATASTORE_TOKENS does not recognise, "
        "or the ports were removed entirely. Until this finds something, the rule "
        "below is enforced against nothing."
    )


@pytest.mark.parametrize(
    "name,service",
    [
        ("postgres", {"image": "postgres:15-alpine"}),
        ("redis", {"image": "redis:7-alpine"}),
        ("pgbouncer", {"image": "edoburu/pgbouncer:v1.25.1-p0"}),
        # The override-layer shape this gate exists for: no image, name only.
        ("postgres", {"ports": ["5434:5432"]}),
        ("redis", {"ports": ["6380:6379"]}),
    ],
)
def test_classifier_recognises_the_datastores_this_repo_runs(name, service):
    # Arrange -- POSITIVE CONTROL for the crux function. Every real assertion in
    # this file is negative ("nothing is exposed"), and a negative assertion
    # passes for free when the classifier silently answers False for everything.
    # Act
    detected = _is_datastore(name, service)
    # Assert
    assert detected, (
        f"the classifier failed to recognise {name} / {service.get('image')} as a "
        f"datastore, so every 'clean' verdict in this file is meaningless"
    )


@pytest.mark.parametrize(
    "name,service",
    [
        ("nginx", {"image": "nginx:alpine"}),
        ("django", {"image": "scitex-hub-prod-django:latest"}),
        ("gitea", {"image": "gitea/gitea:latest"}),
        ("cloudflared", {"image": "cloudflare/cloudflared:latest"}),
        # Its TAG names postgresql; the service is an analytics web UI.
        ("umami", {"image": "ghcr.io/umami-software/umami:postgresql-latest"}),
    ],
)
def test_classifier_clears_the_services_that_are_not_datastores(name, service):
    # Arrange -- NEGATIVE CONTROL. A classifier that answered True for everything
    # would fail nginx's deliberate 80/443, and that gate would be deleted rather
    # than obeyed. It must be shown not to over-trigger, not merely to trigger.
    # Act
    detected = _is_datastore(name, service)
    # Assert
    assert not detected, (
        f"{name} ({service.get('image')}) is not a datastore but the classifier "
        f"flagged it. This guard would fail a correct public bind, which is how a "
        f"gate gets removed instead of followed."
    )


def test_port_parser_flags_a_bind_on_all_interfaces():
    # Arrange -- POSITIVE CONTROL for the shared parser, asserted here as well as
    # in the sibling: this gate must be able to fail on its own, without depending
    # on another file's suite having run.  This is the exact string from
    # docker-compose.staging.yml:109 that this change fixes.
    entry = "5434:5432"
    # Act
    public = published_on_public_interface(entry)
    # Assert
    assert public, (
        "the parser failed to flag a ports entry with no interface prefix, which "
        "binds 0.0.0.0 -- so the sweep cannot see the very bug it exists for"
    )


@pytest.mark.parametrize(
    "entry",
    [
        "127.0.0.1:5434:5432",
        "127.0.0.1:${SCITEX_HUB_DB_PORT:-5434}:5432",
        {"target": 5432, "published": 5434, "host_ip": "127.0.0.1"},
    ],
)
def test_port_parser_accepts_loopback_forms(entry):
    # Arrange -- NEGATIVE CONTROL, including compose's long form. The middle case
    # matters most: "${VAR:-5434}" contains a colon inside the default-value
    # syntax, so a naive colon-count would misread it as an interface.
    # Act
    public = published_on_public_interface(entry)
    # Assert
    assert not public


@pytest.mark.parametrize(
    "path,service,ports",
    _ALL,
    ids=[f"{p.name}::{s}" for p, s, _ in _ALL],
)
def test_datastore_is_not_published_beyond_loopback(path, service, ports):
    # Arrange
    rel = path.relative_to(REPO_ROOT)
    # Act
    exposed = [p for p in ports if published_on_public_interface(p)]
    # Assert
    assert exposed == [], (
        f"{rel} service '{service}' publishes {exposed} on every interface. A "
        f"database or cache reachable off-host is reachable by anything that "
        f"reaches the host: postgres defends itself with a password from an env "
        f"file, and redis with nothing at all -- a session key read out of redis "
        f"is an authenticated account without a login.\n\n"
        f"FIX: give the entry an explicit loopback interface, and reach it through "
        f"an SSH tunnel rather than over the network:\n"
        f'    - "127.0.0.1:{str(exposed[0]).strip(chr(34))}"\n\n'
        f"There is no exemption knob by design. If off-host access is genuinely "
        f"required, it goes through an application, or over the fleet overlay at "
        f"an explicit address -- and that is an edit to this test with a written "
        f"reason, not a silenced check."
    )
