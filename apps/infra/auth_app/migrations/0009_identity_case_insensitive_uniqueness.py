"""Case-insensitive identity uniqueness, enforced BY THE DATABASE.

OPERATOR RULE: this project is PostgreSQL-only, so a functional unique index is
available and is the right tool. We deliberately do NOT swap AUTH_USER_MODEL for
this — that is an architectural change far larger than the constraint it buys.

WHY THE DATABASE AND NOT THE APPLICATION
The signup policy is case-INSENSITIVE (``iexact``), but the only constraint the
database had was a case-SENSITIVE unique on ``username``, and none at all on
``email``. So the application's promise ("this username is taken") and the
database's guarantee disagreed: a concurrent pair of signups could land
``Foo`` and ``foo`` and BOTH succeed, because the constraint that fired was not
the one the policy meant. Catching ``IntegrityError`` in the view does not close
that, because no error is raised.

A functional index on ``lower(...)`` is what makes the two agree. PostgreSQL
gives that for free; it is exactly why the operator rule matters here.

A PREEXISTING INDEX UNDER THE SAME NAME IS NOT ASSUMED TO BE OURS
``CREATE UNIQUE INDEX IF NOT EXISTS`` checks the NAME only. A preexisting index
carrying one of these names with a DIFFERENT definition would therefore make this
migration report success while the policy it exists to enforce was never created
— silently unguarded, which is the worst of the outcomes. So before creating, any
same-named index whose definition does not match is dropped, and the CREATE
follows.

HOW "IS IT OURS" IS DECIDED — and the trap in it. PostgreSQL does NOT render the
definition the way it was written. ``ON auth_user (lower(username))`` comes back
as::

    ... USING btree (lower((username)::text))

so a guard searching for the literal ``lower(username)`` matches NEITHER our own
index NOR a wrong one — it answers "not ours" for everything, which silently
turns the reversal into a no-op and, worse, would make the CREATE path drop an
index it had just built. The match is therefore on the two things that survive
rendering: the presence of ``lower(`` and the column name.

The REVERSE is guarded in the same spirit: it drops an index ONLY when that index
IS the one this migration created, so reversing cannot remove an unrelated index
that merely happens to share the name.

STATEMENTS ARE A LIST, deliberately. Each entry is executed on its own, so a
failure names the exact statement that failed and no multi-statement string has
to be passed through a driver in one call.

PREFLIGHT, AND WHY THIS MIGRATION FAILS LOUD
``CREATE UNIQUE INDEX`` ERRORS if existing rows already collide. That is
INTENDED, not a defect: silently skipping the index would leave production
unguarded while reporting a successful migration, which is the worst of the
three outcomes. So the policy is:

  1. PREFLIGHT — run the read-only audit first:
         python manage.py audit_identity_duplicates
     It writes NOTHING and lists every colliding group, so a human decides.
  2. RECONCILE — merge or rename the colliding rows. There is no automatic
     reconciliation on purpose: two accounts that differ only in case are two
     real people or one duplicated person, and only a human can tell which.
     Merging accounts is a destructive, judgement-bearing act; it must not be
     something a migration does to production unattended.
  3. MIGRATE — apply this migration. If a duplicate was missed it FAILS with
     PostgreSQL's own error naming the offending value, which is the loudest
     and most precise signal available.

``email`` is indexed ``WHERE email <> ''`` because blank is the legitimate
absence of an address, not a value two users may not share.
"""

from django.conf import settings
from django.db import migrations

USERNAME_INDEX = "auth_user_username_lower_uniq"
EMAIL_INDEX = "auth_user_email_lower_uniq"

USERNAME_COLUMN = "username"
EMAIL_COLUMN = "email"


def looks_like_ours(definition: str, column: str) -> bool:
    """Is ``definition`` the lower()-based index this migration builds for ``column``?

    Deliberately NOT a check for ``lower(column)``: PostgreSQL renders the index as
    ``lower((username)::text)``, so the written form does not appear in its own
    ``pg_get_indexdef`` output. Requiring ``lower(`` AND the column survives that
    rendering, and still rejects a plain case-sensitive index on the same column.
    """
    return "lower(" in definition and column in definition


def _is_ours_sql(column: str) -> str:
    """The same decision expressed in SQL, over the ``existing_def`` variable."""
    return f"(position('lower(' in existing_def) > 0 AND position('{column}' in existing_def) > 0)"


def _drop_if_not_ours(name: str, column: str) -> str:
    """Drop ``name`` only when it exists and is NOT the index we are about to build."""
    return f"""
DO $$
DECLARE
    existing_def text;
BEGIN
    SELECT pg_get_indexdef(c.oid)
      INTO existing_def
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE c.relname = '{name}'
       AND n.nspname = current_schema();

    IF existing_def IS NOT NULL
       AND NOT {_is_ours_sql(column)} THEN
        RAISE NOTICE 'replacing same-named but non-matching index {name}: %', existing_def;
        DROP INDEX {name};
    END IF;
END $$;
"""


def _drop_only_if_ours(name: str, column: str) -> str:
    """Drop ``name`` only when it IS the index this migration creates."""
    return f"""
DO $$
DECLARE
    existing_def text;
BEGIN
    SELECT pg_get_indexdef(c.oid)
      INTO existing_def
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE c.relname = '{name}'
       AND n.nspname = current_schema();

    IF existing_def IS NOT NULL
       AND {_is_ours_sql(column)} THEN
        DROP INDEX {name};
    END IF;
END $$;
"""


#: Each entry runs on its own. Order matters: clear a foreign index out of the
#: way, then create ours.
CREATE_STATEMENTS = [
    _drop_if_not_ours(USERNAME_INDEX, USERNAME_COLUMN),
    f"""
CREATE UNIQUE INDEX IF NOT EXISTS {USERNAME_INDEX}
    ON auth_user (lower(username));
""",
    _drop_if_not_ours(EMAIL_INDEX, EMAIL_COLUMN),
    f"""
CREATE UNIQUE INDEX IF NOT EXISTS {EMAIL_INDEX}
    ON auth_user (lower(email))
    WHERE email IS NOT NULL AND email <> '';
""",
]

#: Reversal removes only what this migration built. A same-named index belonging
#: to something else is left alone — removing a stranger's index is not this
#: migration's business.
DROP_STATEMENTS = [
    _drop_only_if_ours(EMAIL_INDEX, EMAIL_COLUMN),
    _drop_only_if_ours(USERNAME_INDEX, USERNAME_COLUMN),
]

# Back-compat for callers that referenced the single-string form.
CREATE_INDEXES = "\n".join(CREATE_STATEMENTS)
DROP_INDEXES = "\n".join(DROP_STATEMENTS)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("auth_app", "0008_pendingsignup"),
    ]

    operations = [
        migrations.RunSQL(sql=statement, reverse_sql=migrations.RunSQL.noop)
        for statement in CREATE_STATEMENTS
    ] + [
        migrations.RunSQL(sql=migrations.RunSQL.noop, reverse_sql=statement)
        for statement in DROP_STATEMENTS
    ]
