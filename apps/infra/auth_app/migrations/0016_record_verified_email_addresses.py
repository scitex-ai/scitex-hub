# Make existing e-mail proofs visible to allauth before verification becomes
# mandatory.
#
# Two kinds of proof had no verified allauth EmailAddress row:
#   1. a one-time code the account used (the hub's own signup / e-mail change);
#   2. a social identity whose provider vouched for the same address
#      (connected to an existing account by the adapter, which wrote no row).
# For every ACTIVE account whose current address carries such a proof, record
# it as a verified EmailAddress. Accounts with no proof are left as they are:
# they are asked to confirm their address the next time they sign in, and
# nobody is locked out.

from django.db import IntegrityError, migrations, transaction


def _truthy(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes")


def _proofs(apps):
    EmailVerification = apps.get_model("auth_app", "EmailVerification")
    SocialAccount = apps.get_model("socialaccount", "SocialAccount")

    proofs = {}
    for user_id, email in EmailVerification.objects.filter(
        is_verified=True
    ).values_list("user_id", "email"):
        proofs.setdefault(user_id, set()).add((email or "").strip().lower())
    for user_id, extra in SocialAccount.objects.values_list("user_id", "extra_data"):
        extra = extra if isinstance(extra, dict) else {}
        claimed = extra.get("email_verified", extra.get("verified_email"))
        if extra.get("email") and _truthy(claimed):
            proofs.setdefault(user_id, set()).add(str(extra["email"]).strip().lower())
    return proofs


def record_proven_addresses(apps, schema_editor):
    User = apps.get_model("auth", "User")
    EmailAddress = apps.get_model("account", "EmailAddress")

    proofs = _proofs(apps)
    for user in User.objects.filter(is_active=True, pk__in=proofs.keys()):
        address = (user.email or "").strip().lower()
        if not address or address not in proofs[user.pk]:
            continue
        try:
            with transaction.atomic():
                row = EmailAddress.objects.filter(
                    user=user, email__iexact=address
                ).first()
                if row is None:
                    has_primary = EmailAddress.objects.filter(
                        user=user, primary=True
                    ).exists()
                    EmailAddress.objects.create(
                        user=user, email=address, verified=True, primary=not has_primary
                    )
                elif not row.verified:
                    row.verified = True
                    row.save(update_fields=["verified"])
        except IntegrityError:
            # Another account already holds this address as verified; leave
            # this one to the confirm-on-sign-in path.
            continue


class Migration(migrations.Migration):
    dependencies = [
        ("auth_app", "0015_remove_device_accounts"),
        ("account", "0009_emailaddress_unique_primary_email"),
        ("socialaccount", "0006_alter_socialaccount_extra_data"),
    ]

    operations = [
        migrations.RunPython(record_proven_addresses, migrations.RunPython.noop),
    ]
