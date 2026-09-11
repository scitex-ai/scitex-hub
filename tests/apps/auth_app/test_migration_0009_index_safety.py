"""Migration 0009 must not trust an index merely because the NAME matches.

``CREATE UNIQUE INDEX IF NOT EXISTS`` checks the name only. A preexisting index
under one of these names with a DIFFERENT definition would therefore make the
migration report success while the case-insensitive policy it exists to enforce
was never created — silently unguarded, which is the worst of the outcomes. The
same care applies in reverse: dropping by name alone could remove an index that
belongs to something else.

These tests drive the migration's OWN statements against the real database, so
they measure the behaviour rather than the shape of the script. Statements run one
at a time, exactly as the migration does.

NOTE ON THE ASSERTIONS. They use the migration's own ``looks_like_ours`` rather
than searching for the written form ``lower(username)``: PostgreSQL renders the
index as ``lower((username)::text)``, so the written form appears in NEITHER a
correct nor an incorrect index.
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
    """The index's real definition, straight from PostgreSQL — or None if absent."""
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


@pytest.fixture(autouse=True)
def _restore_our_indexes():
    """Leave the database holding the REAL indexes, whatever a test did to it."""
    yield
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _exec(f"DROP INDEX IF EXISTS {EMAIL_INDEX}")
    _run(mod.CREATE_STATEMENTS)


@pytest.mark.django_db(transaction=True)
def test_the_migration_can_recognise_its_own_index():
    """Precondition for every guard below: our index IS recognisable as ours.

    Without this, a guard that answered "not ours" for everything would make the
    reversal a silent no-op — which is exactly the bug this pair of guards is
    meant to prevent, and it is invisible unless asserted directly.
    """
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _run(mod.CREATE_STATEMENTS)

    definition = _index_definition(USERNAME_INDEX)
    assert definition is not None
    assert mod.looks_like_ours(definition, mod.USERNAME_COLUMN), (
        "the migration cannot recognise the index it just created, so every "
        f"guard built on this predicate is wrong: {definition}"
    )


@pytest.mark.django_db(transaction=True)
def test_a_preexisting_same_named_wrong_index_is_replaced_not_trusted():
    """A name matching must not be mistaken for a definition matching."""
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    # A same-named index with the WRONG definition: case-SENSITIVE, not unique.
    _exec(f"CREATE INDEX {USERNAME_INDEX} ON auth_user (username)")

    before = _index_definition(USERNAME_INDEX)
    assert before is not None and not mod.looks_like_ours(
        before, mod.USERNAME_COLUMN
    ), f"precondition not established, got: {before}"

    _run(mod.CREATE_STATEMENTS)

    after = _index_definition(USERNAME_INDEX)
    assert after is not None, "the migration left no index at all"
    assert mod.looks_like_ours(after, mod.USERNAME_COLUMN), (
        "the preexisting same-named index was TRUSTED and the CREATE skipped, so "
        f"the case-insensitive policy is silently unenforced: {after}"
    )
    assert "UNIQUE" in after.upper(), f"the replacement is not UNIQUE: {after}"


@pytest.mark.django_db(transaction=True)
def test_the_email_index_is_also_replaced_when_the_name_is_taken():
    """Same guarantee for the second index — the fix must be a class, not one site."""
    _exec(f"DROP INDEX IF EXISTS {EMAIL_INDEX}")
    _exec(f"CREATE INDEX {EMAIL_INDEX} ON auth_user (email)")

    _run(mod.CREATE_STATEMENTS)

    after = _index_definition(EMAIL_INDEX)
    assert after is not None and mod.looks_like_ours(after, mod.EMAIL_COLUMN), (
        f"the email index was skipped because its name was taken: {after}"
    )


@pytest.mark.django_db(transaction=True)
def test_our_own_index_survives_a_rerun():
    """Re-running must not drop and rebuild ours: it is recognised and kept."""
    _run(mod.CREATE_STATEMENTS)
    first = _index_definition(USERNAME_INDEX)
    assert first is not None

    _run(mod.CREATE_STATEMENTS)

    assert _index_definition(USERNAME_INDEX) == first, (
        "a second run did not recognise our own index — the guard is wrong and "
        "the reverse would be a no-op too"
    )


@pytest.mark.django_db(transaction=True)
def test_reverse_removes_the_index_this_migration_created():
    """The reversal must actually undo the migration."""
    _run(mod.CREATE_STATEMENTS)
    assert _index_definition(USERNAME_INDEX) is not None

    _run(mod.DROP_STATEMENTS)

    assert _index_definition(USERNAME_INDEX) is None, (
        "the reverse migration left our index behind — the 'is it ours' predicate "
        "does not match the definition PostgreSQL actually renders"
    )
    assert _index_definition(EMAIL_INDEX) is None


@pytest.mark.django_db(transaction=True)
def test_reverse_does_not_drop_a_same_named_index_that_is_not_ours():
    """CONTROL — reversing must not remove a stranger's index.

    Without this direction, a reverse that unconditionally ran ``DROP INDEX
    IF EXISTS`` would pass the test above while quietly deleting an unrelated
    index that happened to share the name.
    """
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _exec(f"CREATE INDEX {USERNAME_INDEX} ON auth_user (username)")
    assert _index_definition(USERNAME_INDEX) is not None

    _run(mod.DROP_STATEMENTS)

    survivor = _index_definition(USERNAME_INDEX)
    assert survivor is not None, (
        "the reverse migration dropped an index that was NOT created by this "
        "migration — a name is not ownership"
    )
    assert not mod.looks_like_ours(survivor, mod.USERNAME_COLUMN)
