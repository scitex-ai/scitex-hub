"""
Management command to fix missing compile scripts for existing manuscripts.
Usage: python manage.py fix_compile_scripts
"""

from django.core.management.base import BaseCommand
from apps.workspace.writer_app.models import Manuscript


class Command(BaseCommand):
    help = "Create missing compile scripts for existing manuscripts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recreate compile scripts even if they exist",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        self.stdout.write(
            self.style.SUCCESS("Checking manuscripts for missing compile scripts...")
        )

        manuscripts = Manuscript.objects.filter(is_modular=True)
        fixed_count = 0
        skipped_count = 0
        error_count = 0

        for manuscript in manuscripts:
            paper_path = manuscript.get_project_paper_path()

            if not paper_path or not paper_path.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping {manuscript.title}: paper path not found ({paper_path})"
                    )
                )
                skipped_count += 1
                continue

            # Check for compile script
            compile_script = paper_path / "compile.sh"
            compile_link = paper_path / "compile"

            if compile_script.exists() and not force:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"OK: {manuscript.title} already has compile script"
                    )
                )
                skipped_count += 1
                continue

            # Need to create compile script
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"Would create compile script for: {manuscript.title} at {paper_path}"
                    )
                )
                fixed_count += 1
            else:
                try:
                    # Use the model's fallback method
                    success = manuscript._create_fallback_compile_script(paper_path)

                    if success:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Created compile script for: {manuscript.title}"
                            )
                        )
                        fixed_count += 1
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Failed to create compile script for: {manuscript.title}"
                            )
                        )
                        error_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error processing {manuscript.title}: {e}")
                    )
                    error_count += 1

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.SUCCESS(f"Total manuscripts checked: {manuscripts.count()}")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Compile scripts created/would create: {fixed_count}")
        )
        self.stdout.write(self.style.WARNING(f"Skipped: {skipped_count}"))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"Errors: {error_count}"))

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nThis was a dry run. Use without --dry-run to make changes."
                )
            )
