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

CREATE_INDEXES = """
CREATE UNIQUE INDEX IF NOT EXISTS auth_user_username_lower_uniq
    ON auth_user (lower(username));

CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_lower_uniq
    ON auth_user (lower(email))
    WHERE email IS NOT NULL AND email <> '';
"""

DROP_INDEXES = """
DROP INDEX IF EXISTS auth_user_email_lower_uniq;
DROP INDEX IF EXISTS auth_user_username_lower_uniq;
"""


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("auth_app", "0008_pendingsignup"),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE_INDEXES, reverse_sql=DROP_INDEXES),
    ]
