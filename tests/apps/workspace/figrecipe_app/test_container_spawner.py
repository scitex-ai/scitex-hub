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
    monkeypatch.setenv(spawner.ALLOW_DIRECT_ENV, "1")
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
    monkeypatch.setenv(spawner.ALLOW_DIRECT_ENV, "1")
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


def test_traversal_username_rejected(monkeypatch):
    # Arrange — blocker 1 (Python layer): logins interpolated into the
    # setuid tmp-bind path must be allowlisted hub-side too
    monkeypatch.setenv(spawner.UID_MAP_ENV, "alice:10001")
    # Act / Assert — traversal, slash, and empty logins all fail closed
    for bad in ("../../etc/x", "a/b", "..", "", "a b", "a;b", "../alice"):
        with pytest.raises(spawner.SpawnerUnavailable):
            spawner.check_username(bad)
        with pytest.raises(spawner.SpawnerUnavailable):
            spawner.binds_for("/opt/scitex/data/users/alice/paper", bad)
    # Sanity — ordinary logins still pass
    assert spawner.check_username("alice") == "alice"
    assert spawner.check_username("bob.smith-2_x") == "bob.smith-2_x"


def test_users_evil_bind_rejected():
    # Arrange — blocker 2 (Python layer): bare prefix match would accept
    # /opt/scitex/data/users-evil/x as "under" the users tree
    # Act / Assert
    with pytest.raises(spawner.SpawnerUnavailable):
        spawner.binds_for("/opt/scitex/data/users-evil/x", "alice")
    with pytest.raises(spawner.SpawnerUnavailable):
        spawner.binds_for("/opt/scitex/data/usersX", "alice")
    with pytest.raises(spawner.SpawnerUnavailable):
        spawner.binds_for("/opt/scitex/data/users/../evil", "alice")
    # Sanity — the tree itself and real children still pass
    binds = spawner.binds_for("/opt/scitex/data/users/alice/paper", "alice")
    assert "/opt/scitex/data/users/alice/paper:/work:rw" in binds


def test_over_ceiling_uid_refused(monkeypatch):
    # Arrange — m5: the hub ceiling must mirror the helper's MAX_UID (60000)
    monkeypatch.setenv(spawner.UID_MAP_ENV, "alice:60001")
    # Act / Assert
    with pytest.raises(spawner.SpawnerUnavailable):
        spawner.resolve_uid("alice")


def test_ceiling_uid_accepted(monkeypatch):
    # Arrange — boundary: exactly 60000 is still a legal pilot uid
    monkeypatch.setenv(spawner.UID_MAP_ENV, "alice:60000")
    # Act / Assert
    assert spawner.resolve_uid("alice") == 60000


def test_direct_spawner_gated_to_dev(monkeypatch):
    # Arrange — m4: direct mode performs no uid switch and must never run
    # in production; without the explicit allow flag it refuses
    monkeypatch.setenv(spawner.SPAWNER_ENV, "direct")
    monkeypatch.delenv(spawner.ALLOW_DIRECT_ENV, raising=False)
    kwargs = dict(
        uid=10001, image="/images/figrecipe-pilot.sif",
        project_root="/opt/scitex/data/users/alice/paper",
        username="alice", port=18101, auth_key_present=True,
    )
    # Act / Assert — refused by default, even with valid everything-else
    with pytest.raises(spawner.SpawnerUnavailable):
        spawner.spawn_argv(**kwargs)
    # ... and the default mode is the helper, never direct
    monkeypatch.delenv(spawner.SPAWNER_ENV, raising=False)
    argv = spawner.spawn_argv(**kwargs)
    assert argv[0] == spawner.DEFAULT_HELPER
    # ... while the explicit dev opt-in still runs direct
    monkeypatch.setenv(spawner.SPAWNER_ENV, "direct")
    monkeypatch.setenv(spawner.ALLOW_DIRECT_ENV, "1")
    assert spawner.spawn_argv(**kwargs)[0] == "apptainer"


def test_port_override_registry_breaks_collision(monkeypatch):
    # Arrange — m3: uid % 1000 provably collides (10001 vs 11001); explicit
    # overrides are the pilot registry until a real allocator lands
    monkeypatch.delenv(spawner.PORT_BASE_ENV, raising=False)
    monkeypatch.delenv(spawner.PORT_MAP_ENV, raising=False)
    assert spawner.user_port(10001) == spawner.user_port(11001)
    # Act
    monkeypatch.setenv(spawner.PORT_MAP_ENV, "10001:18101,11001:18102")
    # Assert — registry wins over the colliding fallback
    assert spawner.user_port(10001) == 18101
    assert spawner.user_port(11001) == 18102


def test_bad_port_base_fails_closed(monkeypatch):
    # Arrange — garbage port config must fail closed, never 500
    monkeypatch.setenv(spawner.PORT_BASE_ENV, "not-a-port")
    # Act / Assert
    with pytest.raises(spawner.SpawnerUnavailable):
        spawner.user_port(10001)
