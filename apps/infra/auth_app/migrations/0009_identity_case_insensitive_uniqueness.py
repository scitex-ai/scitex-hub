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

OWNERSHIP IS DECIDED STRUCTURALLY, NOT BY NAME OR BY A SUBSTRING
``CREATE UNIQUE INDEX IF NOT EXISTS`` checks the NAME only. So a preexisting
index carrying one of our names but NOT being our index would make this migration
report success while the policy it exists to enforce was never created — silently
unguarded — and the reversal would then DELETE AN INDEX THAT IS NOT OURS.

Earlier revisions of this file matched on a substring of ``pg_get_indexdef``
(``lower(`` plus the column name). That is not ownership, and it accepted exactly
the two shapes that matter:

  * a same-named **NON-UNIQUE** index on ``lower(username)`` — matches the
    substring, so the CREATE is skipped and uniqueness stays UNENFORCED while the
    migration reports success;
  * the email index with a **wrong predicate** — e.g. one that does not exclude
    blanks, so the index does not mean what this migration promises.

Ownership now requires ALL of the following, read from the system catalogs:
  1. it is UNIQUE (``pg_index.indisunique``);
  2. it is on ``auth_user`` (not another table that happens to share the name);
  3. its expression is exactly ``lower(<column>)``;
  4. for ``email`` only, its predicate is exactly the not-blank one;
     for ``username``, it has no predicate at all.
Comparisons are on a NORMALISED rendering, because PostgreSQL rewrites what it
was given — ``ON auth_user (lower(username))`` comes back as
``lower((username)::text)`` — so the normalisation strips casts, punctuation and
whitespace from BOTH sides.

STATEMENTS ARE A LIST, deliberately. Each entry is executed on its own, so a
failure names the exact statement that failed.

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
  3. MIGRATE — apply this migration. If a duplicate was missed it FAILS with
     PostgreSQL's own error naming the offending value.
"""

from django.conf import settings
from django.db import migrations

USERNAME_INDEX = "auth_user_username_lower_uniq"
EMAIL_INDEX = "auth_user_email_lower_uniq"

USERNAME_COLUMN = "username"
EMAIL_COLUMN = "email"

#: PostgreSQL's own rendering of our predicates, normalised the same way the
#: check normalises the candidate. ``''::text`` collapses to nothing and the
#: casts disappear, hence ``emailisnotnullandemail<>``.
USERNAME_EXPRESSION = "lowerusername"
EMAIL_EXPRESSION = "loweremail"
EMAIL_PREDICATE = "emailisnotnullandemail<>"

#: Strip casts, then everything that is not a letter, digit or angle bracket.
#: Applied identically on both sides of the comparison.
NORMALISE = "regexp_replace(regexp_replace(lower({value}), '::text', '', 'g'), '[^a-z0-9<>]', '', 'g')"


def normalise(text: str | None) -> str | None:
    """The same normalisation in Python, so tests compare on identical terms."""
    if text is None:
        return None
    return "".join(
        ch for ch in text.lower().replace("::text", "") if ch.isalnum() or ch in "<>"
    )


def _ownership_sql(column: str) -> str:
    """SQL for "the index under this name IS the one this migration builds".

    Structure is checked with the catalog fields, not only the expression text.
    ``pg_get_expr(indexprs, indrelid)`` renders ONLY the expression columns, so a
    UNIQUE COMPOSITE ``(lower(username), email)`` renders exactly
    ``lower((username)::text)`` — indistinguishable from ours by expression alone.
    It would be accepted as ours, the CREATE would be skipped (leaving weaker
    composite uniqueness, i.e. the policy unenforced), and the reversal would then
    DELETE it. ``INCLUDE`` columns are invisible to ``indexprs`` for the same
    reason. Hence:

      * ``indnkeyatts = 1`` — exactly ONE key column;
      * ``indnatts = 1`` — no INCLUDE columns either;
      * ``indkey::text = '0'`` — that single key is an EXPRESSION (0 means
        "expression", per indexprs), not a plain column. A composite renders
        ``'0 2'``, so it is rejected here;
      * ``indisvalid`` — the index is actually USABLE. A failed
        ``CREATE UNIQUE INDEX CONCURRENTLY`` leaves the index in place with the
        name and shape we build but flagged invalid, enforcing NOTHING. Without
        this, that wreckage is accepted as ours: the CREATE is skipped (policy
        silently unenforced) and the reversal deletes an index it did not create.
    """
    if column == EMAIL_COLUMN:
        expression, predicate = EMAIL_EXPRESSION, f"= '{EMAIL_PREDICATE}'"
    else:
        expression, predicate = USERNAME_EXPRESSION, "IS NULL"
    return f"""(
            i.indisvalid
        AND i.indisunique
        AND t.relname = 'auth_user'
        AND i.indnkeyatts = 1
        AND i.indnatts = 1
        AND i.indkey::text = '0'
        AND {NORMALISE.format(value="pg_get_expr(i.indexprs, i.indrelid)")} = '{expression}'
        AND {NORMALISE.format(value="pg_get_expr(i.indpred, i.indrelid)")} {predicate}
    )"""


_LOOKUP = """
    SELECT {ownership} INTO is_ours
      FROM pg_index i
      JOIN pg_class c ON c.oid = i.indexrelid
      JOIN pg_class t ON t.oid = i.indrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE c.relname = '{name}'
       AND n.nspname = current_schema();
"""


def _drop_if_not_ours(name: str, column: str) -> str:
    """Drop ``name`` only when it exists and is NOT the index we are about to build."""
    lookup = _LOOKUP.format(ownership=_ownership_sql(column), name=name)
    return f"""
DO $$
DECLARE
    is_ours boolean;
BEGIN
    {lookup}
    IF is_ours IS FALSE THEN
        RAISE NOTICE 'replacing index {name}: it exists but is not the unique lower({column}) index on auth_user';
        DROP INDEX {name};
    END IF;
END $$;
"""


def _drop_only_if_ours(name: str, column: str) -> str:
    """Drop ``name`` only when it IS the index this migration creates."""
    lookup = _LOOKUP.format(ownership=_ownership_sql(column), name=name)
    return f"""
DO $$
DECLARE
    is_ours boolean;
BEGIN
    {lookup}
    IF is_ours IS TRUE THEN
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
