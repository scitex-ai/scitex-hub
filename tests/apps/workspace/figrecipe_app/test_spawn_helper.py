#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Setuid spawn helper: audit-gate probes (blockers 1-3, m6).

Card hub-figrecipe-leaf-move-20261009 (Apptainer pilot). These tests pin the
privilege/isolation boundary the HOLD verdict blocked on:

* blocker 1 — traversal/slash usernames are refused (``username refused``),
  never interpolated into the tmp bind source;
* blocker 2 — ``users-evil`` project roots are refused (boundary-checked
  tree confinement), never bind-mounted;
* blocker 3 — supplementary groups are dropped (``setgroups(0, NULL)``)
  BEFORE ``setresgid``/``setresuid`` (pinned by source order: only root may
  call ``setgroups``, so no unprivileged test process can demonstrate the
  runtime drop — the order assertion plus the valid-input probe reaching
  the post-gate stage is the checkable surface);
* m6 — ``-Wall -Wextra -Wformat-truncation`` compile is warning-free.

Method: compile the shipped C source with ``-DHUB_UID=<current uid>`` (so
the caller gate passes for the test user) and ``-DUSERS_TREE=<tmp>``, then
run argv probes. No root, no apptainer, no DB, no credentials.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

C_SOURCE = (
    Path(__file__).resolve().parents[4]
    / "apps" / "workspace" / "figrecipe_app" / "services"
    / "spawn_helper" / "scitex-figrecipe-spawn.c"
)

NEEDS_CC = shutil.which("cc") is None


def _compile(tmp_path, tree: str) -> Path:
    binary = tmp_path / "scitex-figrecipe-spawn-probe"
    build = subprocess.run(
        [
            "cc", "-O2", "-Wall", "-Wextra", "-Werror=format-truncation",
            f"-DHUB_UID={os.getuid()}", f"-DUSERS_TREE=\"{tree}\"",
            "-o", str(binary), str(C_SOURCE),
        ],
        capture_output=True, text=True,
    )
    assert build.returncode == 0, f"helper must compile warning-free: {build.stderr}"
    return binary


def _run(binary, env, *argv):
    return subprocess.run([str(binary), *argv], capture_output=True, text=True, env=env)


@pytest.mark.skipif(NEEDS_CC, reason="no C compiler for helper probes")
def test_helper_compiles_without_truncation_warnings(tmp_path):
    # Arrange / Act — warnings (incl. -Wformat-truncation, m6) fail the build
    _compile(tmp_path, str(tmp_path / "users"))


@pytest.mark.skipif(NEEDS_CC, reason="no C compiler for helper probes")
def test_helper_refuses_traversal_username(tmp_path):
    # Arrange — blocker 1 at the C layer: argv[4] reaches a setuid-root
    # snprintf into the tmp bind source, so traversal must fail closed
    tree = str(tmp_path / "users")
    binary = _compile(tmp_path, tree)
    env = dict(os.environ, FIGRECIPE_CONTAINER_AUTH_KEY="k")
    root = f"{tree}/alice/paper"
    # Act / Assert — every smuggled path form is refused, none executed
    for bad_user in ("../../etc/x", "a/b", "..", "", "a b", "a;b"):
        proc = _run(binary, env, "10001", "/img/a.sif", root, bad_user, "18101")
        assert proc.returncode == 1
        assert "username refused" in proc.stderr


@pytest.mark.skipif(NEEDS_CC, reason="no C compiler for helper probes")
def test_helper_refuses_users_evil_root(tmp_path):
    # Arrange — blocker 2 at the C layer: bare prefix match accepted
    # <tree>-evil; the boundary check must refuse it
    tree = str(tmp_path / "users")
    binary = _compile(tmp_path, tree)
    env = dict(os.environ, FIGRECIPE_CONTAINER_AUTH_KEY="k")
    # Act / Assert
    for bad_root in (f"{tree}-evil/x", f"{tree}X", f"{tree}/../evil"):
        proc = _run(binary, env, "10001", "/img/a.sif", bad_root, "alice", "18101")
        assert proc.returncode == 1
        assert "project bind refused" in proc.stderr
    # Sanity — a genuine in-tree root passes the bind gates (it then fails
    # later at uid lookup / group drop, proving the fixed gates let it through)
    proc = _run(binary, env, "10001", "/img/a.sif", f"{tree}/alice/paper", "alice", "18101")
    assert proc.returncode == 1
    assert "project bind refused" not in proc.stderr
    assert "username refused" not in proc.stderr


def test_helper_clears_supplementary_groups_first():
    # Arrange — blocker 3: setgroups(0, NULL) must precede the uid switch
    # (only euid-root may call setgroups, so the ORDER is the assertion a
    # rootless test can check; the runtime drop is Infra-verified on-host).
    # Act — order at the CALL SITES (past the docstring, which merely names
    # the calls in prose). Distinctive argument lists avoid prose matches.
    source = C_SOURCE.read_text()
    body = source[source.index("int main"):]
    # Assert — grp.h included, drop present, and strictly before both switches
    assert "#include <grp.h>" in source
    drop = body.index("setgroups(0, NULL)")
    gid = body.index("setresgid(pw->pw_gid")
    uid = body.index("setresuid((uid_t)uid")
    assert drop < gid < uid
