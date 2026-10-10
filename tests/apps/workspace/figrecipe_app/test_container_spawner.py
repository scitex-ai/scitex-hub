#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-user-UID spawner: mapping, ports, binds, argv (no spawn performed).

Card hub-figrecipe-leaf-move-20261009 (Apptainer pilot, HPC model). None
of these tests spawn anything, touch the DB, or need credentials: they
pin the pilot's least-privilege construction — login→uid allowlist (fail
closed), per-uid loopback ports, single-project binds, secret-free argv.
"""

from __future__ import annotations

import pytest

from apps.workspace.figrecipe_app.services import container_spawner as spawner


def test_empty_map_resolves_nothing(monkeypatch):
    # Arrange
    monkeypatch.delenv(spawner.UID_MAP_ENV, raising=False)
    # Act
    mapping = spawner.uid_map()
    # Assert
    assert mapping == {}


def test_map_parses_allowlist(monkeypatch):
    # Arrange
    monkeypatch.setenv(spawner.UID_MAP_ENV, "alice:10001,bob:10002")
    # Act
    mapping = spawner.uid_map()
    # Assert
    assert mapping == {"alice": 10001, "bob": 10002}


def test_bad_map_entry_fails_closed(monkeypatch):
    # Arrange
    monkeypatch.setenv(spawner.UID_MAP_ENV, "alice:not-a-uid")
    # Act / Assert
    with pytest.raises(spawner.SpawnerUnavailable):
        spawner.uid_map()


def test_unmapped_login_fails_closed(monkeypatch):
    # Arrange
    monkeypatch.setenv(spawner.UID_MAP_ENV, "alice:10001")
    # Act / Assert — mallory must never inherit another user's uid
    with pytest.raises(spawner.SpawnerUnavailable):
        spawner.resolve_uid("mallory")


def test_anonymous_has_no_uid(monkeypatch):
    # Arrange
    monkeypatch.setenv(spawner.UID_MAP_ENV, "alice:10001")
    # Act / Assert
    with pytest.raises(spawner.SpawnerUnavailable):
        spawner.resolve_uid("")


def test_sub_floor_uid_refused(monkeypatch):
    # Arrange — uid 1000 collides with the host service/human range
    monkeypatch.setenv(spawner.UID_MAP_ENV, "alice:1000")
    # Act / Assert
    with pytest.raises(spawner.SpawnerUnavailable):
        spawner.resolve_uid("alice")


def test_user_ports_are_deterministic_and_loopback_range(monkeypatch):
    # Arrange
    monkeypatch.delenv(spawner.PORT_BASE_ENV, raising=False)
    # Act
    port_a1 = spawner.user_port(10001)
    port_a2 = spawner.user_port(10001)
    port_b = spawner.user_port(10002)
    # Assert — stable per uid, distinct per user, inside the pilot range
    assert port_a1 == port_a2
    assert port_a1 != port_b
    assert 18100 <= port_a1 < 19100
    assert 18100 <= port_b < 19100


def test_binds_carry_only_the_own_project_jail():
    # Arrange
    project = "/opt/scitex/data/users/alice/paper"
    # Act
    binds = spawner.binds_for(project, "alice")
    joined = " ".join(binds)
    # Assert — own project RW + own tmp RW, nothing else
    assert f"{project}:/work:rw" in binds
    assert "/tmp/figrecipe-alice:/tmp/figrecipe:rw" in binds
    assert "/app" not in joined
    assert "data/users/bob" not in joined
    assert "docker.sock" not in joined
    assert "postgres" not in joined and "redis" not in joined


def test_binds_refuse_relative_paths():
    # Arrange / Act / Assert
    with pytest.raises(spawner.SpawnerUnavailable):
        spawner.binds_for("../../etc", "alice")


def test_spawn_argv_carries_no_secret(monkeypatch):
    # Arrange
    monkeypatch.setenv(spawner.SPAWNER_ENV, "direct")
    # Act
    argv = spawner.spawn_argv(
        10001, "/images/figrecipe-pilot.sif",
        "/opt/scitex/data/users/alice/paper", "alice", 18101,
        auth_key_present=True,
    )
    joined = " ".join(argv)
    # Assert — structure + containment flags, zero credentials
    assert argv[0] == "apptainer" and "figrecipe-pilot.sif" in joined
    assert "--contain" in argv and "--cleanenv" in argv and "--no-home" in argv
    assert "secret" not in joined.lower() and "key=" not in joined.lower()


def test_spawn_refuses_without_auth_key(monkeypatch):
    # Arrange
    monkeypatch.setenv(spawner.SPAWNER_ENV, "direct")
    # Act / Assert
    with pytest.raises(spawner.SpawnerUnavailable):
        spawner.spawn_argv(
            10001, "/images/figrecipe-pilot.sif",
            "/opt/scitex/data/users/alice/paper", "alice", 18101,
            auth_key_present=False,
        )


def test_helper_argv_names_uid_image_root_user_port(monkeypatch):
    # Arrange — privileged path builds the audited helper's exact argv
    monkeypatch.setenv(spawner.SPAWNER_ENV, "helper")
    monkeypatch.setenv(spawner.HELPER_ENV, "/usr/local/sbin/scitex-figrecipe-spawn")
    # Act
    argv = spawner.spawn_argv(
        10001, "/images/figrecipe-pilot.sif",
        "/opt/scitex/data/users/alice/paper", "alice", 18101,
        auth_key_present=True,
    )
    # Assert
    assert argv == [
        "/usr/local/sbin/scitex-figrecipe-spawn", "10001",
        "/images/figrecipe-pilot.sif",
        "/opt/scitex/data/users/alice/paper", "alice", "18101",
    ]
