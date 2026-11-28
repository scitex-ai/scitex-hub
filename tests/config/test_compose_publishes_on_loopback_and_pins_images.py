#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compose files publish on loopback and run pinned images.

Two rules, checked over every compose file under ``deployment/`` by parsing
the real YAML:

1. PORTS. Every published port binds 127.0.0.1 (or a variable whose default is
   127.0.0.1). nginx and the Cloudflare tunnel reach services over the compose
   network, so a host publish is only ever for someone on the host itself.
   The exceptions are listed in ``_PUBLIC_ON_PURPOSE`` with the reason, and
   must spell their interface out as ``0.0.0.0:``.

2. IMAGES. Every image pulled from a registry names an exact version: a
   digest, or a tag that is not ``latest`` / ``*-latest``. Images this repo
   builds itself (``scitex-*``, or a service with ``build:``) are exempt; their
   deploy tag is set by the release tooling.

Plus the live files' Redis password, Umami secret and munge mount contracts.

Siblings: ``test_compose_keeps_datastores_off_public_interfaces.py`` and
``test_compose_keeps_debug_stacks_off_public_interfaces.py`` gate narrower
populations with the same parser (``_compose_helpers.py``).

The gate reads the repository. A green result means "the repo asks for
loopback", not "the running host binds loopback"; containers created from an
older checkout keep their old bindings until they are recreated.
"""

import re

import pytest
import yaml

from ._compose_helpers import (
    MIN_EXPECTED_COMPOSE_FILES,
    REPO_ROOT,
    compose_files,
    published_on_public_interface,
    services,
)

# (compose file relative to repo root, service, container port) -> reason.
_PUBLIC_ON_PURPOSE = {
    (
        "deployment/docker/docker_prod/docker-compose.yml",
        "gitea",
        "22",
    ): "git over SSH for users; Gitea authenticates by key",
    (
        "deployment/docker/docker_dev/docker-compose.yml",
        "gitea",
        "22",
    ): "git over SSH on the dev hub; Gitea authenticates by key",
    (
        "deployment/docker/docker-compose.prod.yml",
        "gitea",
        "22",
    ): "dormant copy of the prod file; kept identical to it",
    (
        "deployment/docker/docker_prod/docker-compose.yml",
        "django",
        "2200",
    ): "workspace SSH for users (HPC-style access); gateway accepts keys only",
    (
        "deployment/docker/docker-compose.prod.yml",
        "django",
        "2200",
    ): "dormant copy of the prod file; kept identical to it",
}

_FLOATING_TAGS = re.compile(r"(^|-)latest$")


def _rel(path):
    return path.relative_to(REPO_ROOT).as_posix()


def _container_port(entry):
    if isinstance(entry, dict):
        return str(entry.get("target"))
    text = str(entry).strip().strip('"').strip("'")
    return text.rsplit(":", 1)[-1].split("/")[0]


def _resolve_default(image):
    """``${VAR:-default}`` -> ``default``; anything else unchanged."""
    match = re.fullmatch(r"\$\{[A-Z0-9_]+:-([^}]*)\}", image)
    return match.group(1) if match else image


def _is_built_here(service, image):
    name = image.split("@", 1)[0].rsplit(":", 1)[0] if image else ""
    return "build" in service or name.startswith("scitex-")


def image_is_pinned(image):
    """True when ``image`` names an exact version (digest, or a fixed tag)."""
    if "@sha256:" in image:
        return True
    last = image.rsplit("/", 1)[-1]
    if ":" not in last:
        return False  # no tag means :latest
    tag = last.rsplit(":", 1)[1]
    return not _FLOATING_TAGS.search(tag)


def _port_cases():
    out = []
    for path in compose_files():
        for name, svc in services(path):
            for entry in svc.get("ports") or []:
                out.append((_rel(path), name, entry))
    return out


def _image_cases():
    out = []
    for path in compose_files():
        for name, svc in services(path):
            image = svc.get("image")
            if not image:
                continue
            image = _resolve_default(str(image))
            if _is_built_here(svc, image):
                continue
            out.append((_rel(path), name, image))
    return out


_PORTS = _port_cases()
_IMAGES = _image_cases()
_EXCEPTED = [
    (r, s, e) for r, s, e in _PORTS if (r, s, _container_port(e)) in _PUBLIC_ON_PURPOSE
]
_ORDINARY = [
    (r, s, e)
    for r, s, e in _PORTS
    if (r, s, _container_port(e)) not in _PUBLIC_ON_PURPOSE
]


def _port_id(case):
    rel, service, entry = case
    return f"{'/'.join(rel.split('/')[-2:])}::{service}::{entry}"


def test_discovery_found_the_compose_files():
    # Arrange
    files = compose_files()
    # Act
    count = len(files)
    # Assert
    assert count >= MIN_EXPECTED_COMPOSE_FILES, (
        f"only {count} compose files found; the sweeps below would be vacuous"
    )


def test_port_sweep_found_published_ports():
    # Arrange -- population control: an empty sweep passes every rule.
    cases = _PORTS
    # Act
    count = len(cases)
    # Assert
    assert count >= 10, f"only {count} published ports found"


def test_image_sweep_found_registry_images():
    # Arrange -- population control, as above.
    cases = _IMAGES
    # Act
    count = len(cases)
    # Assert
    assert count >= 10, f"only {count} registry images found"


@pytest.mark.parametrize(
    "entry,public",
    [
        ("3300:3000", True),
        ("0.0.0.0:2222:22", True),
        ("${SCITEX_HUB_UMAMI_PORT:-3300}:3000", True),
        ("127.0.0.1:3300:3000", False),
        ("${SCITEX_HUB_OPENALEX_BIND_PROD:-127.0.0.1}:31292:31292", False),
        ("${SCITEX_HUB_OPENALEX_BIND_PROD:-0.0.0.0}:31292:31292", True),
        ({"target": 3000, "published": 3300, "host_ip": "127.0.0.1"}, False),
        ({"target": 3000, "published": 3300}, True),
    ],
)
def test_port_parser_classifies_known_forms(entry, public):
    # Arrange
    expected = public
    # Act
    result = published_on_public_interface(entry)
    # Assert
    assert result is expected


@pytest.mark.parametrize(
    "image,pinned",
    [
        ("gitea/gitea:latest", False),
        ("gitea/gitea", False),
        ("ghcr.io/umami-software/umami:postgresql-latest", False),
        ("localhost:5000/thing", False),
        ("gitea/gitea:1.25.2", True),
        ("willfarrell/autoheal@sha256:" + "a" * 64, True),
        ("localhost:5000/thing:1.2", True),
    ],
)
def test_image_pin_check_classifies_known_forms(image, pinned):
    # Arrange
    expected = pinned
    # Act
    result = image_is_pinned(image)
    # Assert
    assert result is expected


def test_every_listed_exception_still_exists():
    # Arrange -- an exception whose port is gone must be removed, or the list
    # becomes a silent allowance for whatever lands there next.
    present = {(f, s, _container_port(e)) for f, s, e in _PORTS}
    # Act
    stale = [key for key in _PUBLIC_ON_PURPOSE if key not in present]
    # Assert
    assert stale == [], f"remove stale exceptions: {stale}"


@pytest.mark.parametrize("case", _EXCEPTED, ids=[_port_id(c) for c in _EXCEPTED])
def test_public_on_purpose_port_names_its_interface(case):
    # Arrange
    rel, service, entry = case
    # Act
    explicit = str(entry).strip('"').startswith("0.0.0.0:")
    # Assert
    assert explicit, (
        f"{rel} {service}: a port that is public on purpose must say so with "
        f"an explicit 0.0.0.0: prefix, got {entry!r}"
    )


@pytest.mark.parametrize("case", _ORDINARY, ids=[_port_id(c) for c in _ORDINARY])
def test_port_is_published_on_loopback_only(case):
    # Arrange
    rel, service, entry = case
    # Act
    public = published_on_public_interface(entry)
    # Assert
    assert not public, (
        f"{rel} service '{service}' publishes {entry!r} on every interface. "
        f'Bind it to loopback ("127.0.0.1:{str(entry).strip(chr(34))}"); '
        f"nginx and the tunnel use the compose network. If it really must be "
        f"reachable from other hosts, add it to _PUBLIC_ON_PURPOSE with the reason."
    )


@pytest.mark.parametrize(
    "rel,service,image",
    _IMAGES,
    ids=[f"{'/'.join(r.split('/')[-2:])}::{s}" for r, s, _ in _IMAGES],
)
def test_registry_image_is_pinned(rel, service, image):
    # Arrange
    ref = image
    # Act
    pinned = image_is_pinned(ref)
    # Assert
    assert pinned, (
        f"{rel} service '{service}' uses {ref!r}, which moves whenever the "
        f"publisher pushes. Pin the version that runs now: read "
        f"`docker image inspect --format '{{{{json .RepoDigests}}}}' {ref}` on "
        f"the host, then write name:version@sha256:..."
    )


# ---------------------------------------------------------------------------
# Live deployment files: secrets and mounts.
# ---------------------------------------------------------------------------
_PROD = REPO_ROOT / "deployment/docker/docker_prod/docker-compose.yml"
_STAGING = REPO_ROOT / "deployment/docker/docker-compose.staging.yml"
_BASE = REPO_ROOT / "deployment/docker/docker-compose.yml"
_DEV = REPO_ROOT / "deployment/docker/docker_dev/docker-compose.yml"
_REDIS_FILES = pytest.mark.parametrize(
    "path", [_PROD, _STAGING], ids=["prod", "staging"]
)


def _service(path, name):
    return yaml.safe_load(path.read_text(encoding="utf-8"))["services"][name]


def _redis_script(path):
    command = _service(path, "redis")["command"]
    return command[-1] if isinstance(command, list) else str(command)


@_REDIS_FILES
def test_redis_refuses_to_start_without_a_password(path):
    # Arrange
    env = _service(path, "redis").get("environment") or {}
    # Act
    value = str(env.get("SCITEX_HUB_REDIS_PASSWORD", ""))
    # Assert
    assert value.startswith("${SCITEX_HUB_REDIS_PASSWORD:?")


@_REDIS_FILES
def test_redis_reads_requirepass_from_stdin(path):
    # Arrange
    script = _redis_script(path)
    # Act
    from_stdin = (
        "redis-server -" in script
        and "requirepass $$SCITEX_HUB_REDIS_PASSWORD" in script
    )
    # Assert
    assert from_stdin, "requirepass must be given as config on stdin"


@_REDIS_FILES
def test_redis_password_is_not_in_argv(path):
    # Arrange -- argv is readable by every user on the host through ps.
    script = _redis_script(path)
    # Act
    in_argv = "--requirepass" in script
    # Assert
    assert not in_argv


@_REDIS_FILES
def test_redis_healthcheck_authenticates(path):
    # Arrange
    test = _service(path, "redis")["healthcheck"]["test"]
    # Act
    authenticated = "REDISCLI_AUTH" in " ".join(test)
    # Assert
    assert authenticated


@_REDIS_FILES
def test_celery_reads_the_broker_from_settings(path):
    # Arrange -- the settings add the password; a --broker flag would bypass it.
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))["services"]
    commands = {
        name: " ".join(svc["command"])
        if isinstance(svc["command"], list)
        else svc["command"]
        for name, svc in doc.items()
        if isinstance(svc, dict) and str(svc.get("command", "")).startswith("celery")
    }
    # Act
    flagged = {n: c for n, c in commands.items() if "--broker" in c}
    # Assert
    assert len(commands) >= 2 and flagged == {}, (commands, flagged)


@pytest.mark.parametrize("path", [_PROD, _BASE, _DEV], ids=["prod", "base", "dev"])
def test_umami_secret_has_no_fallback(path):
    # Arrange
    env = _service(path, "umami")["environment"]
    if isinstance(env, list):
        env = dict(item.split("=", 1) for item in env)
    # Act
    value = str(env["APP_SECRET"])
    # Assert
    assert value.startswith("${SCITEX_HUB_UMAMI_APP_SECRET:?"), (
        "APP_SECRET must come from the env file; a fallback literal in a "
        "public repository is not a secret"
    )


def test_munge_is_mounted_read_only_everywhere():
    # Arrange -- clients only connect to the munge socket, which works on a
    # read-only bind mount; nothing in a hub container writes there.
    found = []
    for path in compose_files():
        for name, svc in services(path):
            for vol in svc.get("volumes") or []:
                text = str(vol)
                if text.split(":", 1)[0] == "/run/munge":
                    found.append((_rel(path), name, text))
    # Act
    writable = [f for f in found if not f[2].endswith(":ro")]
    # Assert
    assert found and writable == [], (found, writable)
