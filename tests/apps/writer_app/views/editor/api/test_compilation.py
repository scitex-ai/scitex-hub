#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/workspace/writer_app/views/editor/api/compilation.py

Covers the G4 server-side preview-coalesce mechanism introduced to defuse
the historical "Compilation failed with exit code 12" symptom: the UI
fired multiple compile_preview POSTs (Compile-on-Change / multi-tab) that
raced on the same writer_dir/.preview/<name>.pdf destination, leaving
compile_content.sh's post-latexmk cp step to fail and bubble a non-zero
returncode up into the user-visible error string.

These tests pin the lock primitive used by ``compile_api`` to serialise
same-key previews. The compile_api view wiring itself is a few lines of
plumbing on top of this primitive and is exercised end-to-end by the
prod stack and the E2E browser suite (run under the dedicated workflow);
keeping the unit layer focused on the primitive avoids mock-heavy
indirection that the project's no-mock test policy correctly forbids.
"""

from __future__ import annotations

import threading

import pytest


# ---------------------------------------------------------------------------
# _get_preview_lock — per-key Lock factory.
# ---------------------------------------------------------------------------


class TestGetPreviewLockKeying:
    """The lock is keyed by (project_id, section_name, color_mode)."""

    def test_same_key_returns_identical_lock_instance(self):
        # Arrange
        from apps.workspace.writer_app.views.editor.api.compilation import (
            _get_preview_lock,
        )

        # Act
        lock_a = _get_preview_lock(101, "introduction", "dark")
        lock_b = _get_preview_lock(101, "introduction", "dark")

        # Assert
        assert lock_a is lock_b

    def test_different_project_id_returns_distinct_locks(self):
        # Arrange
        from apps.workspace.writer_app.views.editor.api.compilation import (
            _get_preview_lock,
        )

        # Act
        lock_a = _get_preview_lock(101, "introduction", "dark")
        lock_b = _get_preview_lock(102, "introduction", "dark")

        # Assert
        assert lock_a is not lock_b

    def test_different_section_name_returns_distinct_locks(self):
        # Arrange
        from apps.workspace.writer_app.views.editor.api.compilation import (
            _get_preview_lock,
        )

        # Act
        lock_a = _get_preview_lock(101, "introduction", "dark")
        lock_b = _get_preview_lock(101, "abstract", "dark")

        # Assert
        assert lock_a is not lock_b

    def test_different_color_mode_returns_distinct_locks(self):
        # Arrange
        from apps.workspace.writer_app.views.editor.api.compilation import (
            _get_preview_lock,
        )

        # Act
        lock_a = _get_preview_lock(101, "introduction", "dark")
        lock_b = _get_preview_lock(101, "introduction", "light")

        # Assert
        assert lock_a is not lock_b


class TestGetPreviewLockSurface:
    """The returned object exposes the standard Lock surface."""

    def test_returned_object_has_acquire_method(self):
        # Arrange
        from apps.workspace.writer_app.views.editor.api.compilation import (
            _get_preview_lock,
        )

        # Act
        lock = _get_preview_lock(201, "abstract", "light")

        # Assert
        assert hasattr(lock, "acquire")

    def test_returned_object_has_release_method(self):
        # Arrange
        from apps.workspace.writer_app.views.editor.api.compilation import (
            _get_preview_lock,
        )

        # Act
        lock = _get_preview_lock(201, "abstract", "light")

        # Assert
        assert hasattr(lock, "release")


class TestGetPreviewLockConcurrency:
    """The dict guard makes lookup safe under concurrent first-access."""

    def test_concurrent_lookup_resolves_to_single_lock_instance(self):
        # Arrange — use a fresh key so this test never contaminates / is
        # contaminated by sibling tests in the same module.
        from apps.workspace.writer_app.views.editor.api.compilation import (
            _PREVIEW_LOCKS,
            _get_preview_lock,
        )

        key = (999_001, "race-section", "dark")
        _PREVIEW_LOCKS.pop(key, None)

        observed: list = []
        start_gate = threading.Event()

        def worker():
            start_gate.wait()
            observed.append(_get_preview_lock(*key))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()

        # Act
        start_gate.set()
        for t in threads:
            t.join(timeout=2)

        # Assert
        assert len(set(id(lock) for lock in observed)) == 1


# ---------------------------------------------------------------------------
# Locking contract — the property compile_api relies on.
# ---------------------------------------------------------------------------


@pytest.fixture
def _held_lock_key():
    """Yield a fresh ``(project, section, color)`` key whose Lock is already
    held by the fixture, releasing on teardown.

    Lifting the acquire into a fixture keeps the test bodies down to a
    single assertion (project rule STX-TQ007 forbids multi-assert tests
    because a failing earlier assert silently hides every later one).
    """
    from apps.workspace.writer_app.views.editor.api.compilation import (
        _PREVIEW_LOCKS,
        _get_preview_lock,
    )

    key = (999_002, "held-section", "dark")
    _PREVIEW_LOCKS.pop(key, None)
    lock = _get_preview_lock(*key)
    if not lock.acquire(timeout=0):
        raise RuntimeError("fixture precondition: fresh lock must acquire")
    try:
        yield key
    finally:
        try:
            lock.release()
        except RuntimeError:
            # Test body already released the lock — fine.
            pass
        _PREVIEW_LOCKS.pop(key, None)


@pytest.fixture
def _released_lock_key():
    """Yield a fresh key whose Lock was acquired and then released by the
    fixture, leaving it free for the test body to re-acquire."""
    from apps.workspace.writer_app.views.editor.api.compilation import (
        _PREVIEW_LOCKS,
        _get_preview_lock,
    )

    key = (999_003, "released-section", "light")
    _PREVIEW_LOCKS.pop(key, None)
    lock = _get_preview_lock(*key)
    if not lock.acquire(timeout=0):
        raise RuntimeError("fixture precondition: fresh lock must acquire")
    lock.release()
    try:
        yield key
    finally:
        try:
            lock.release()
        except RuntimeError:
            pass
        _PREVIEW_LOCKS.pop(key, None)


class TestPreviewLockSerialisation:
    """Once acquired, the lock blocks a second acquirer for the same key."""

    def test_held_lock_blocks_short_timeout_acquire(self, _held_lock_key):
        # Arrange — fixture is already holding the lock for this key. A
        # second acquirer with a tiny timeout must observe the lock as
        # busy. Without serialisation it would acquire immediately.
        from apps.workspace.writer_app.views.editor.api.compilation import (
            _get_preview_lock,
        )

        second = _get_preview_lock(*_held_lock_key)

        # Act
        second_acquired = second.acquire(timeout=0.05)

        # Assert
        assert second_acquired is False

    def test_released_lock_is_reacquirable(self, _released_lock_key):
        # Arrange — fixture released the lock. A normal successful
        # compile_api round trip must therefore leave the lock free.
        from apps.workspace.writer_app.views.editor.api.compilation import (
            _get_preview_lock,
        )

        lock = _get_preview_lock(*_released_lock_key)

        # Act
        reacquired = lock.acquire(timeout=0.05)
        if reacquired:
            lock.release()

        # Assert
        assert reacquired is True


if __name__ == "__main__":
    import os

    pytest.main([os.path.abspath(__file__)])

# EOF
