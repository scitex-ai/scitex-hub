"""An INVALID index is not ours, even when its name and shape match exactly.

THE CASE. ``CREATE UNIQUE INDEX CONCURRENTLY`` can FAIL and leave the index behind,
marked ``indisvalid = false``. Its name, table, uniqueness flag, expression and
predicate are all exactly what this migration builds — the only thing wrong with it
is that it enforces NOTHING. Every ownership field checked so far accepted it:

  * FORWARD — ``CREATE UNIQUE INDEX IF NOT EXISTS`` skips, so the migration reports
    success while case-insensitive uniqueness is not enforced at all; and
  * REVERSE — the wreckage is treated as ours and DELETED.

``indisvalid`` is what separates a working index from a residue, so it is part of
ownership. These tests build an exact index and then invalidate it, driving the
migration's own statements in both directions.
"""

from __future__ import annotations

import importlib

import pytest
from django.db import connection, utils

MODULE = "apps.infra.auth_app.migrations.0009_identity_case_insensitive_uniqueness"
mod = importlib.import_module(MODULE)

USERNAME_INDEX = "auth_user_username_lower_uniq"
EMAIL_INDEX = "auth_user_email_lower_uniq"


def _exec(sql: str, params=None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)


def _run(statements) -> None:
    for statement in statements:
        _exec(statement)


def _invalidate(name: str) -> bool:
    """Flag an index invalid the way a failed CONCURRENTLY build would.

    Returns False where the role cannot write the catalog (CI may not be
    superuser); the caller skips rather than asserting something it could not set
    up, because a test that silently did nothing would be worse than a skip.
    """
    try:
        _exec(
            "UPDATE pg_index SET indisvalid = false WHERE indexrelid = %s::regclass",
            [name],
        )
    except utils.ProgrammingError:
        connection.rollback() if hasattr(connection, "rollback") else None
        return False
    return True


def _structure(name: str) -> dict | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT i.indisvalid, i.indisunique, i.indnkeyatts, i.indnatts,
                   i.indkey::text, pg_get_indexdef(c.oid)
              FROM pg_index i
              JOIN pg_class c ON c.oid = i.indexrelid
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE c.relname = %s
               AND n.nspname = current_schema()
            """,
            [name],
        )
        row = cursor.fetchone()
    if row is None:
        return None
    return {
        "valid": row[0],
        "unique": row[1],
        "nkeyatts": row[2],
        "natts": row[3],
        "indkey": row[4],
        "definition": row[5],
    }


@pytest.fixture(autouse=True)
def _restore_our_indexes():
    yield
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _exec(f"DROP INDEX IF EXISTS {EMAIL_INDEX}")
    _run(mod.CREATE_STATEMENTS)


@pytest.mark.django_db(transaction=True)
def test_our_own_indexes_are_valid():
    """PRECONDITION: what the migration builds really is valid and unique."""
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _run(mod.CREATE_STATEMENTS)

    structure = _structure(USERNAME_INDEX)
    assert structure is not None
    assert structure["valid"], "our own index is not marked valid"
    assert structure["unique"]


@pytest.mark.django_db(transaction=True)
def test_an_invalid_exact_index_is_replaced_not_accepted():
    """FORWARD — an exact-but-invalid index must be rebuilt, not skipped."""
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _run(mod.CREATE_STATEMENTS)

    if not _invalidate(USERNAME_INDEX):
        pytest.skip("cannot write pg_index with this role; needs superuser")

    wrecked = _structure(USERNAME_INDEX)
    assert wrecked is not None and not wrecked["valid"], "precondition not set"

    _run(mod.CREATE_STATEMENTS)

    after = _structure(USERNAME_INDEX)
    assert after is not None, "the migration left no index at all"
    assert after["valid"], (
        "an INVALID index with our exact name and shape was accepted as ours, so "
        "CREATE ... IF NOT EXISTS skipped and case-insensitive uniqueness is "
        f"enforced by nothing: {after['definition']}"
    )


@pytest.mark.django_db(transaction=True)
def test_reverse_does_not_delete_an_invalid_exact_index():
    """REVERSE — the destructive direction must not remove invalid wreckage.

    It is invalid, so this migration did not successfully create it. Deleting it
    would destroy a residue that someone may still need to diagnose, and would
    report a clean reversal over an object this migration never owned.
    """
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _run(mod.CREATE_STATEMENTS)

    if not _invalidate(USERNAME_INDEX):
        pytest.skip("cannot write pg_index with this role; needs superuser")

    _run(mod.DROP_STATEMENTS)

    survivor = _structure(USERNAME_INDEX)
    assert survivor is not None, (
        "the reverse DELETED an index it did not successfully create — an invalid "
        "index is not owned by this migration"
    )
    assert not survivor["valid"], "the decoy was altered, not merely kept"


@pytest.mark.django_db(transaction=True)
def test_the_valid_index_is_still_recognised_after_the_indisvalid_check():
    """CONTROL — adding indisvalid must not make ownership unsatisfiable.

    If the check were wrong, the forward path above could pass by dropping and
    rebuilding on every run, and the reverse would never remove anything. This
    pins that a VALID index is still recognised as ours.
    """
    _run(mod.CREATE_STATEMENTS)
    first = _structure(USERNAME_INDEX)
    assert first is not None and first["valid"]

    _run(mod.CREATE_STATEMENTS)
    assert _structure(USERNAME_INDEX)["definition"] == first["definition"], (
        "our own valid index was not recognised — it was dropped and rebuilt"
    )

    _run(mod.DROP_STATEMENTS)
    assert _structure(USERNAME_INDEX) is None, (
        "the reverse no longer removes our own valid index"
    )
