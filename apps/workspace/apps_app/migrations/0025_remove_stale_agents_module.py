"""Delete the stale pre-slug-rename "agents" catalog row (Agent Container duplicate tile).

Root cause (prod DB, 2026-10-23): two public AppsModule rows describe the
same board — ("agents", "SciTeX Agent Container", ...) [stale legacy] and
("agent-container", "Agent Container", ...) [plugin, from the leaf's own
manifest]. The launcher's step 2 re-adds every public row the registry does
not know, so the stale "agents" row rendered a second tile next to the
plugin one.

Mirrors 0023's remove_stale_todo_module: delete the catalog row (dependent
installation state cascades) and strip the retired id from per-user
launcher configs so no dangling dock/order entry survives. The hub-owned
/apps/agents/ -> /apps/agent-container/ legacy redirect (config/urls.py,
pinned by tests/config/test_todo_mount.py's sibling) is untouched.
"""

from django.db import migrations

_RETIRED = {"agents"}


def remove_stale_agents_module(apps, schema_editor):
    """Delete the stale "agents" row and scrub it from user launcher configs."""
    AppsModule = apps.get_model("apps_app", "AppsModule")
    ModuleInstallation = apps.get_model("apps_app", "ModuleInstallation")
    PlannedAppInterest = apps.get_model("apps_app", "PlannedAppInterest")

    AppsModule.objects.filter(module_name__in=_RETIRED).delete()
    PlannedAppInterest.objects.filter(app_id__in=_RETIRED).delete()

    for installation in ModuleInstallation.objects.all().iterator():
        config = installation.config
        if not isinstance(config, dict):
            continue
        updated = dict(config)
        dock = updated.get("launcher_dock")
        if isinstance(dock, list):
            updated["launcher_dock"] = [name for name in dock if name not in _RETIRED]
        order = updated.get("launcher_link_order")
        if isinstance(order, dict):
            updated["launcher_link_order"] = {
                name: value for name, value in order.items() if name not in _RETIRED
            }
        if updated != config:
            installation.config = updated
            installation.save(update_fields=["config"])


class Migration(migrations.Migration):
    dependencies = [("apps_app", "0024_add_pinned_version")]
    operations = [
        migrations.RunPython(remove_stale_agents_module, migrations.RunPython.noop),
    ]
