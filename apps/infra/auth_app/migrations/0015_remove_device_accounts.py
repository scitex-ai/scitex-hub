# The multi-account switcher is retired: its routes and cookie are gone, so
# the device -> account mapping it kept has no reader. Drop both tables.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("auth_app", "0014_userprofile_theme_explicit"),
    ]

    operations = [
        migrations.DeleteModel(name="DeviceAccount"),
        migrations.DeleteModel(name="AuthenticatedDevice"),
    ]
