"""String catalog for the client-rendered Project Health page.

The page's list, dialogs and error messages are built in TypeScript
(apps/infra/project_app/static/project_app/ts/repository/admin/), so the
template alone cannot translate them. The view passes this dict to the
template, which emits it with ``json_script:"project-health-i18n"``; the TS
helper ``t(key, fallbackEnglish)`` in ``i18n.ts`` reads it once.

INTERIM: scitex-ui is building a shell-level i18n primitive. Keys are stable
dotted names mirrored 1:1 in the TS call sites, so moving to that primitive is
a mechanical swap — do not rename keys casually.

English msgids are the source; the Japanese msgstrs live in
``locale/ja/LC_MESSAGES/django.po``. Build the dict per request (gettext, not
gettext_lazy) so it follows the active language.
"""

from __future__ import annotations

from django.utils.translation import gettext


def project_health_catalog() -> dict[str, str]:
    """Return the translated Project Health strings for the active language."""
    return {
        # Summary cards
        "card.healthy.label": gettext("Healthy"),
        "card.healthy.title": gettext("Click to show only healthy projects"),
        "card.warnings.label": gettext("Warnings"),
        "card.warnings.title": gettext("Click to show only warnings"),
        "card.critical.label": gettext("Critical"),
        "card.critical.title": gettext("Click to show only critical issues"),
        "card.total.label": gettext("Total Projects"),
        "card.total.title": gettext("Click to show all projects"),
        # Issue cards
        "issue.unknown_name": gettext("Unknown"),
        "column.local": gettext("Local"),
        "column.project": gettext("Project"),
        "column.repository": gettext("Gitea Repository"),
        "value.local": gettext("Local"),
        "value.project": gettext("Project"),
        "value.repository": gettext("Repository"),
        "value.missing": gettext("Missing"),
        "type.healthy": gettext("In sync"),
        "type.orphaned_in_gitea": gettext("Orphaned in Gitea"),
        "type.missing_in_gitea": gettext("Repository missing"),
        "type.missing_directory": gettext("Local directory missing"),
        "message.healthy": gettext("Project healthy and in sync"),
        "message.orphaned_in_gitea": gettext(
            "Repository exists in Gitea but no project found"
        ),
        "message.missing_in_gitea": gettext(
            "Project exists but its Gitea repository was not found"
        ),
        "message.missing_directory": gettext("Local git directory missing"),
        "action.restore": gettext("Restore Project"),
        "action.sync": gettext("Sync Project"),
        # Empty state
        "empty.title": gettext("All projects are healthy!"),
        "empty.message": gettext("No synchronization issues detected"),
        # Confirmation dialogs
        "dialog.warning_label": gettext("Warning:"),
        "dialog.note_label": gettext("Note:"),
        "dialog.sync.question": gettext("Sync this project with Gitea?"),
        "dialog.sync.detail": gettext(
            "This will re-clone the repository from Gitea if the local directory is missing."
        ),
        "dialog.delete.question": gettext(
            "Are you sure you want to delete this orphaned repository?"
        ),
        "dialog.delete.warning": gettext(
            "This action cannot be undone. The repository will be permanently deleted from Gitea."
        ),
        "dialog.restore.question": gettext(
            "Restore this orphaned repository by creating a new project?"
        ),
        "dialog.restore.name_label": gettext("Project name for restored repository:"),
        "dialog.restore.note": gettext(
            "This will create a new project linked to the existing Gitea repository and clone it to your local filesystem."
        ),
        # Errors
        "error.load": gettext("Failed to load project health"),
        "error.connect": gettext("Failed to connect to server"),
        "error.sync": gettext("Failed to sync project"),
        "error.delete": gettext("Failed to delete repository"),
        "error.restore": gettext("Failed to restore project"),
    }
