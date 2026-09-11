"""Migration 0009 ownership is decided STRUCTURALLY, not by name or substring.

``CREATE UNIQUE INDEX IF NOT EXISTS`` checks the name only, so a preexisting index
under one of our names but NOT being our index would make the migration report
success while the policy was never created — and the reversal would then DELETE AN
INDEX THAT IS NOT OURS.

An earlier revision matched on a substring of ``pg_get_indexdef`` (``lower(`` plus
the column name). That accepted exactly the two shapes that matter, and both are
asserted here in BOTH directions:

  * a same-named NON-UNIQUE index on ``lower(username)`` — the CREATE is skipped
    and uniqueness stays UNENFORCED while the migration reports success;
  * the email index with the WRONG PREDICATE — e.g. one that does not exclude
    blanks, so it does not mean what the migration promises.

These tests drive the migration's OWN statements against the real database, so
they measure behaviour rather than the shape of the script.
"""

from __future__ import annotations

import importlib

import pytest
from django.db import connection

MODULE = "apps.infra.auth_app.migrations.0009_identity_case_insensitive_uniqueness"
mod = importlib.import_module(MODULE)

USERNAME_INDEX = "auth_user_username_lower_uniq"
EMAIL_INDEX = "auth_user_email_lower_uniq"


def _exec(sql: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(sql)


def _run(statements) -> None:
    """Run a migration statement list the way the migration does — one at a time."""
    for statement in statements:
        _exec(statement)


def _index_definition(name: str) -> str | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT pg_get_indexdef(c.oid)
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE c.relname = %s
               AND n.nspname = current_schema()
            """,
            [name],
        )
        row = cursor.fetchone()
        return row[0] if row else None


def _is_unique(name: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT i.indisunique
              FROM pg_index i
              JOIN pg_class c ON c.oid = i.indexrelid
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE c.relname = %s
               AND n.nspname = current_schema()
            """,
            [name],
        )
        row = cursor.fetchone()
        return bool(row and row[0])


@pytest.fixture(autouse=True)
def _restore_our_indexes():
    """Leave the database holding the REAL indexes, whatever a test did to it."""
    yield
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _exec(f"DROP INDEX IF EXISTS {EMAIL_INDEX}")
    _run(mod.CREATE_STATEMENTS)


# ---------------------------------------------------------------------------
# The ownership predicate itself.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_the_migration_recognises_its_own_index():
    """Precondition for every guard: our index IS identifiable as ours.

    A predicate that answered "not ours" for everything would make the reversal a
    silent no-op and the CREATE path drop an index it had just built — invisible
    unless asserted directly.
    """
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _run(mod.CREATE_STATEMENTS)

    definition = _index_definition(USERNAME_INDEX)
    assert definition is not None
    assert _is_unique(USERNAME_INDEX), f"our own index is not unique: {definition}"
    # The normalisation must agree with PostgreSQL's rendering.
    assert mod.normalise("lower((username)::text)") == mod.USERNAME_EXPRESSION


# ---------------------------------------------------------------------------
# Forward: a same-named foreign index must be REPLACED.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_a_non_unique_same_named_lower_index_is_replaced():
    """THE COUNTEREXAMPLE. Non-unique, same expression, same name.

    A substring check calls this "ours", skips the CREATE, and leaves uniqueness
    UNENFORCED while the migration reports success.
    """
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _exec(f"CREATE INDEX {USERNAME_INDEX} ON auth_user (lower(username))")
    assert not _is_unique(USERNAME_INDEX), "precondition: the decoy must be non-unique"

    _run(mod.CREATE_STATEMENTS)

    assert _is_unique(USERNAME_INDEX), (
        "a non-unique same-named index on lower(username) was ACCEPTED as ours, so "
        "CREATE ... IF NOT EXISTS skipped and the case-insensitive uniqueness "
        "policy is silently unenforced"
    )


@pytest.mark.django_db(transaction=True)
def test_a_wrong_predicate_email_index_is_replaced():
    """THE OTHER COUNTEREXAMPLE. Unique and on lower(email), but the wrong predicate.

    ``WHERE email IS NOT NULL`` only — it does not exclude blanks, so it does not
    mean what this migration promises.
    """
    _exec(f"DROP INDEX IF EXISTS {EMAIL_INDEX}")
    _exec(
        f"CREATE UNIQUE INDEX {EMAIL_INDEX} ON auth_user (lower(email)) "
        "WHERE email IS NOT NULL"
    )

    _run(mod.CREATE_STATEMENTS)

    definition = _index_definition(EMAIL_INDEX)
    assert definition is not None and "<>" in definition, (
        "a same-named email index with the WRONG PREDICATE was accepted as ours, "
        f"so the blank-excluding uniqueness policy was never created: {definition}"
    )


@pytest.mark.django_db(transaction=True)
def test_a_plain_case_sensitive_index_is_still_replaced():
    """The original decoy, kept: no lower() at all."""
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _exec(f"CREATE INDEX {USERNAME_INDEX} ON auth_user (username)")

    _run(mod.CREATE_STATEMENTS)

    assert _is_unique(USERNAME_INDEX)


@pytest.mark.django_db(transaction=True)
def test_our_own_index_survives_a_rerun():
    """Re-running must not drop and rebuild ours: it is recognised and kept."""
    _run(mod.CREATE_STATEMENTS)
    first = _index_definition(USERNAME_INDEX)
    assert first is not None

    _run(mod.CREATE_STATEMENTS)

    assert _index_definition(USERNAME_INDEX) == first, (
        "a second run did not recognise our own index — then the reverse would be "
        "a no-op too"
    )


# ---------------------------------------------------------------------------
# Reverse: a same-named foreign index must SURVIVE.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_reverse_removes_the_index_this_migration_created():
    """The reversal must actually undo the migration."""
    _run(mod.CREATE_STATEMENTS)
    assert _index_definition(USERNAME_INDEX) is not None

    _run(mod.DROP_STATEMENTS)

    assert _index_definition(USERNAME_INDEX) is None, (
        "the reverse left our index behind — the ownership predicate does not "
        "match the definition PostgreSQL actually renders"
    )
    assert _index_definition(EMAIL_INDEX) is None


@pytest.mark.django_db(transaction=True)
def test_reverse_does_not_drop_a_non_unique_same_named_lower_index():
    """CONTROL for the counterexample: a name is not ownership, even with lower().

    This is the direction that matters most, because the failure is destructive:
    reversing would DELETE an index the migration never created.
    """
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _exec(f"CREATE INDEX {USERNAME_INDEX} ON auth_user (lower(username))")

    _run(mod.DROP_STATEMENTS)

    assert _index_definition(USERNAME_INDEX) is not None, (
        "the reverse DELETED a same-named, non-unique index that this migration "
        "never created"
    )
    assert not _is_unique(USERNAME_INDEX), "the decoy was altered, not just kept"


@pytest.mark.django_db(transaction=True)
def test_reverse_does_not_drop_a_wrong_predicate_email_index():
    """CONTROL: the email guard must also reject a wrong-predicate index."""
    _exec(f"DROP INDEX IF EXISTS {EMAIL_INDEX}")
    _exec(
        f"CREATE UNIQUE INDEX {EMAIL_INDEX} ON auth_user (lower(email)) "
        "WHERE email IS NOT NULL"
    )

    _run(mod.DROP_STATEMENTS)

    assert _index_definition(EMAIL_INDEX) is not None, (
        "the reverse DELETED a same-named email index whose predicate is not the "
        "one this migration creates"
    )


@pytest.mark.django_db(transaction=True)
def test_reverse_does_not_drop_a_plain_same_named_index():
    """CONTROL: the original, simplest foreign index is left alone too."""
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _exec(f"CREATE INDEX {USERNAME_INDEX} ON auth_user (username)")

    _run(mod.DROP_STATEMENTS)

    assert _index_definition(USERNAME_INDEX) is not None
