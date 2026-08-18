# Hand-written 2026-07-18 — undo the seed's display-column self-pollution.
# seed_apps iterated EVERY registered module (not just builtins) and copied
# each runtime-registered user app's registry label — the raw repo slug —
# into the new AppsModule.label column (and the generic puzzle icon into
# .icon). A populated column wins over the prettified fallback, so the
# operator kept seeing "scitex-agentic-journal-app" on the grid. Blank the
# exact self-pollution signature (label == module_name) so the honest
# fallback engages; a real manifest label repopulates on the next publish.

from django.db import migrations


def _blank_selfnamed(apps, schema_editor):
    AppsModule = apps.get_model("apps_app", "AppsModule")
    from django.db.models import F

    polluted = AppsModule.objects.filter(label=F("module_name"))
    for row in polluted:
        row.label = ""
        if row.icon == "fas fa-puzzle-piece":
            row.icon = ""
        row.save(update_fields=["label", "icon"])


class Migration(migrations.Migration):

    dependencies = [
        ("apps_app", "0015_appsmodule_label_icon"),
    ]

    operations = [
        migrations.RunPython(_blank_selfnamed, migrations.RunPython.noop),
    ]
