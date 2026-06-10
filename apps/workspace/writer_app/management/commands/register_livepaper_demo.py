"""Register the grant-material live-paper demo Project in dev.

This management command wires the real research project that lives in the
sibling repository ``paper-scitex-clew`` (bind-mounted into the dev
container at ``/paper-scitex-clew/``) into the Hub as a Django
``Project`` record so that the standard ``/apps/writer/editor/`` and
``/apps/writer/viewer-v2/`` URLs render against the **real** clew claims
+ DAG + manuscript instead of the empty default project.

The command is intentionally a thin idempotent registration step rather
than data copy: ``Project.local_path`` is set to the bind-mounted source,
so ``project.get_local_path()`` (and downstream the auto-injected
``working_dir`` for ``scitex_writer._django.views.viewer_page``) resolves
directly to the live clew checkout.

Dev-mode only. Prod is deferred per operator policy; running this in
prod would point a hub Project at a host path that prod does not bind.

Usage::

    make ENV=dev exec-web
    python manage.py register_livepaper_demo

Re-run-safe: the command upserts on (owner=test-user, slug=
``live-paper-demo``). To remove the registration, pass ``--undo``.
"""

from __future__ import annotations

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

DEFAULT_LIVE_PAPER_PATH = (
    "/paper-scitex-clew/GITIGNORED/grant-materials/live-paper-demo/project"
)
DEFAULT_OWNER_USERNAME = "test-user"
DEFAULT_SLUG = "live-paper-demo"
DEFAULT_NAME = "SciTeX Live Paper Demo"
DEFAULT_DESCRIPTION = (
    "Grant-material live-paper demo. Reads claims.json, the verification "
    "DAG, and the LaTeX manuscript directly from the bind-mounted "
    "paper-scitex-clew repository so the Writer + /viewer-v2/ surfaces "
    "render real clew research data. Dev-mode only."
)


class Command(BaseCommand):
    help = (
        "Register (or remove) the live-paper grant-material demo as a "
        "Django Project pointing at the bind-mounted paper-scitex-clew "
        "live-paper-demo project."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--owner",
            default=DEFAULT_OWNER_USERNAME,
            help=(
                "Username of the project owner. Default: "
                f"'{DEFAULT_OWNER_USERNAME}'. Must already exist."
            ),
        )
        parser.add_argument(
            "--slug",
            default=DEFAULT_SLUG,
            help=f"Project slug. Default: '{DEFAULT_SLUG}'.",
        )
        parser.add_argument(
            "--name",
            default=DEFAULT_NAME,
            help=f"Project display name. Default: '{DEFAULT_NAME}'.",
        )
        parser.add_argument(
            "--local-path",
            default=DEFAULT_LIVE_PAPER_PATH,
            help=(
                "Absolute path (inside the Django container) to the live "
                "paper project. Default: '%(default)s'."
            ),
        )
        parser.add_argument(
            "--undo",
            action="store_true",
            help=(
                "Remove the registration instead of creating it. Does not "
                "touch any files on disk."
            ),
        )

    def handle(self, *args, **options):
        from apps.infra.project_app.models import Project

        owner_username = options["owner"]
        slug = options["slug"]
        name = options["name"]
        local_path = options["local_path"]
        undo = options["undo"]

        User = get_user_model()
        try:
            owner = User.objects.get(username=owner_username)
        except User.DoesNotExist as exc:
            raise CommandError(
                f"Owner user '{owner_username}' does not exist. Create it "
                "first (`python manage.py createsuperuser` or seed)."
            ) from exc

        if undo:
            deleted, _ = Project.objects.filter(owner=owner, slug=slug).delete()
            if deleted:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Removed Project owner={owner_username} slug={slug}"
                    )
                )
            else:
                self.stdout.write(
                    f"No Project owner={owner_username} slug={slug} to remove."
                )
            return

        path = Path(local_path)
        if not path.is_dir():
            raise CommandError(
                f"local_path does not exist or is not a directory: "
                f"{local_path}. Verify the bind mount "
                "(`docker-compose.yml`: `paper-scitex-clew:/paper-scitex-clew:ro`)."
            )

        # Spot-check the live-paper layout so a misconfigured path fails
        # loudly here rather than silently in the viewer.
        for required in ("00_shared/claims.json", "01_manuscript"):
            if not (path / required).exists():
                raise CommandError(
                    f"local_path is missing the expected live-paper layout: "
                    f"{required} not found under {local_path}"
                )

        project, created = Project.objects.update_or_create(
            owner=owner,
            slug=slug,
            defaults={
                "name": name,
                "description": DEFAULT_DESCRIPTION,
                "project_type": "local",
                "visibility": "public",
                "local_path": local_path,
                "source": "scitex",
            },
        )
        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} Project id={project.id} owner={owner_username} "
                f"slug={slug} local_path={local_path}"
            )
        )
        self.stdout.write(
            "Demo URL (when dev Django is up):\n"
            f"  http://localhost:8000/apps/writer/editor/?project_id={project.id}\n"
            f"  http://localhost:8000/apps/writer/viewer-v2/?working_dir={local_path}"
        )
