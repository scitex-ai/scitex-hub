"""Adversarial COMPOSITE and INCLUDE indexes under our index names.

THE GAP THESE CLOSE. The ownership predicate matched on
``pg_get_expr(indexprs, indrelid)``, which renders ONLY the expression columns. So
a same-named UNIQUE COMPOSITE index

    CREATE UNIQUE INDEX auth_user_username_lower_uniq
        ON auth_user (lower(username), email);

renders exactly ``lower((username)::text)`` — indistinguishable from ours by
expression text. It was therefore accepted as ours, which is wrong in both
directions:

  * FORWARD — ``CREATE UNIQUE INDEX IF NOT EXISTS`` skips, so the migration reports
    success while the enforced constraint is the WEAKER COMPOSITE one. Duplicate
    ``lower(username)`` values are still allowed whenever the emails differ, so the
    case-insensitive uniqueness policy this migration exists to create is simply
    not there.
  * REVERSE — the index is treated as ours and DELETED, destroying a foreign
    constraint.

``INCLUDE`` columns are invisible to ``indexprs`` for the same reason:
``(lower(username)) INCLUDE (email)`` matched too.

Ownership therefore also requires the structure: ``indnkeyatts = 1``,
``indnatts = 1``, and ``indkey::text = '0'`` (a single key that is an expression).
These tests drive the migration's own statements against the real database, in
BOTH directions, for both index names.
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
    for statement in statements:
        _exec(statement)


def _structure(name: str) -> dict | None:
    """The index's real catalogue structure, or None when it does not exist."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT i.indisunique, i.indnkeyatts, i.indnatts, i.indkey::text,
                   pg_get_indexdef(c.oid)
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
        "unique": row[0],
        "nkeyatts": row[1],
        "natts": row[2],
        "indkey": row[3],
        "definition": row[4],
    }


@pytest.fixture(autouse=True)
def _restore_our_indexes():
    """Leave the database holding the REAL indexes, whatever a test did to it."""
    yield
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _exec(f"DROP INDEX IF EXISTS {EMAIL_INDEX}")
    _run(mod.CREATE_STATEMENTS)


@pytest.mark.django_db(transaction=True)
def test_our_own_indexes_are_single_key_without_include_columns():
    """PRECONDITION: ours really is one expression key and nothing else.

    Every structural assertion below is relative to this, so it is pinned rather
    than assumed.
    """
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _exec(f"DROP INDEX IF EXISTS {EMAIL_INDEX}")
    _run(mod.CREATE_STATEMENTS)

    for name in (USERNAME_INDEX, EMAIL_INDEX):
        structure = _structure(name)
        assert structure is not None, f"{name} was not created"
        assert structure["unique"], f"{name} is not unique"
        assert structure["nkeyatts"] == 1, (
            f"{name} has {structure['nkeyatts']} key columns"
        )
        assert structure["natts"] == 1, f"{name} carries INCLUDE columns"
        assert structure["indkey"] == "0", (
            f"{name} key is not a single expression (indkey={structure['indkey']})"
        )


# ---------------------------------------------------------------------------
# COMPOSITE decoys — the exact shape the expression check could not see.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_a_unique_composite_username_index_is_replaced_not_accepted():
    """`(lower(username), email)` renders ONLY lower(username) — must not pass."""
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _exec(f"CREATE UNIQUE INDEX {USERNAME_INDEX} ON auth_user (lower(username), email)")

    before = _structure(USERNAME_INDEX)
    assert before is not None and before["nkeyatts"] == 2, (
        f"precondition: the decoy should be a 2-key composite, got {before}"
    )

    _run(mod.CREATE_STATEMENTS)

    after = _structure(USERNAME_INDEX)
    assert after is not None
    assert after["nkeyatts"] == 1 and after["natts"] == 1, (
        "a UNIQUE COMPOSITE same-named index was accepted as ours, so the CREATE "
        "was skipped and the enforced constraint is the WEAKER composite one — "
        f"duplicate lower(username) values are still allowed: {after['definition']}"
    )
    assert after["unique"]


@pytest.mark.django_db(transaction=True)
def test_reverse_does_not_drop_a_unique_composite_username_index():
    """CONTROL, destructive direction: a composite is not ours, so it must SURVIVE."""
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _exec(f"CREATE UNIQUE INDEX {USERNAME_INDEX} ON auth_user (lower(username), email)")
    assert _structure(USERNAME_INDEX) is not None

    _run(mod.DROP_STATEMENTS)

    survivor = _structure(USERNAME_INDEX)
    assert survivor is not None, (
        "the reverse DELETED a same-named UNIQUE COMPOSITE index that this "
        "migration never created — a foreign constraint was destroyed"
    )
    assert survivor["nkeyatts"] == 2, "the decoy was altered, not merely kept"


@pytest.mark.django_db(transaction=True)
def test_a_unique_composite_email_index_with_the_right_predicate_is_replaced():
    """`(lower(email), username)` WITH the expected predicate — must not pass."""
    _exec(f"DROP INDEX IF EXISTS {EMAIL_INDEX}")
    _exec(
        f"CREATE UNIQUE INDEX {EMAIL_INDEX} ON auth_user (lower(email), username) "
        "WHERE email IS NOT NULL AND email <> ''"
    )

    before = _structure(EMAIL_INDEX)
    assert before is not None and before["nkeyatts"] == 2

    _run(mod.CREATE_STATEMENTS)

    after = _structure(EMAIL_INDEX)
    assert after is not None
    assert after["nkeyatts"] == 1 and after["natts"] == 1, (
        "a UNIQUE COMPOSITE email index carrying the RIGHT predicate was accepted "
        f"as ours, leaving the weaker composite constraint in place: {after['definition']}"
    )


@pytest.mark.django_db(transaction=True)
def test_reverse_does_not_drop_a_unique_composite_email_index():
    """CONTROL: the email composite must survive the reversal too."""
    _exec(f"DROP INDEX IF EXISTS {EMAIL_INDEX}")
    _exec(
        f"CREATE UNIQUE INDEX {EMAIL_INDEX} ON auth_user (lower(email), username) "
        "WHERE email IS NOT NULL AND email <> ''"
    )

    _run(mod.DROP_STATEMENTS)

    survivor = _structure(EMAIL_INDEX)
    assert survivor is not None, (
        "the reverse DELETED a same-named composite email index it never created"
    )
    assert survivor["nkeyatts"] == 2


# ---------------------------------------------------------------------------
# INCLUDE decoys — invisible to indexprs, so also invisible to the old check.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_an_include_column_variant_is_replaced_not_accepted():
    """`(lower(username)) INCLUDE (email)` — one key, but not our structure."""
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _exec(
        f"CREATE UNIQUE INDEX {USERNAME_INDEX} ON auth_user (lower(username)) "
        "INCLUDE (email)"
    )

    before = _structure(USERNAME_INDEX)
    assert before is not None and before["natts"] == 2, (
        f"precondition: the decoy should carry one INCLUDE column, got {before}"
    )

    _run(mod.CREATE_STATEMENTS)

    after = _structure(USERNAME_INDEX)
    assert after is not None
    assert after["natts"] == 1, (
        "an INCLUDE-column variant was accepted as ours, so the CREATE was skipped "
        f"and the INCLUDE index was left in place: {after['definition']}"
    )


@pytest.mark.django_db(transaction=True)
def test_reverse_does_not_drop_an_include_column_variant():
    """CONTROL: the INCLUDE variant survives the reversal."""
    _exec(f"DROP INDEX IF EXISTS {USERNAME_INDEX}")
    _exec(
        f"CREATE UNIQUE INDEX {USERNAME_INDEX} ON auth_user (lower(username)) "
        "INCLUDE (email)"
    )

    _run(mod.DROP_STATEMENTS)

    survivor = _structure(USERNAME_INDEX)
    assert survivor is not None, (
        "the reverse DELETED a same-named INCLUDE index it never created"
    )
    assert survivor["natts"] == 2
