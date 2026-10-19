# Generated on 2026-10-19: track whether the user explicitly saved a theme.
# get-theme must serve source "profile" only for an explicit choice;
# auto-created rows carry the dark default and must stay source "default"
# so they never clobber an explicit localStorage choice (card
# stats-dark-theme-forced-20261018).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth_app", "0013_alter_pendingsignup_plan"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="theme_explicit",
            field=models.BooleanField(
                default=False,
                help_text="True only after the user explicitly saved a theme via "
                "the save-theme endpoint. Distinguishes a real choice from the "
                "auto-created row default so get-theme never serves an unchosen "
                "default as source 'profile' (it would clobber an explicit "
                "localStorage choice on every load).",
            ),
        ),
    ]
