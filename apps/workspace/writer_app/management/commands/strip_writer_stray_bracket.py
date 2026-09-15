"""Remove the old template's stray 「」」 after ``%%%% EOF`` in every user workspace.

Usage: python manage.py strip_writer_stray_bracket [--root /app/data/users] [--dry-run]
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.workspace.writer_app.services.template_stray_bracket import (
    strip_stray_bracket_text,
    strip_stray_brackets,
)


class Command(BaseCommand):
    help = "Strip the stray template bracket from writer contents/*.tex files"

    def add_arguments(self, parser):
        default_root = Path(getattr(settings, "BASE_DIR", ".")) / "data" / "users"
        parser.add_argument("--root", default=str(default_root))
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        root = Path(options["root"])
        total = 0
        for writer_dir in root.glob("*/proj/*/.scitex/writer"):
            if options["dry_run"]:
                hits = [
                    p
                    for p in writer_dir.glob("*/contents/**/*.tex")
                    if p.is_file() and not p.is_symlink()
                    and strip_stray_bracket_text(p.read_text(encoding="utf-8", errors="replace"))
                    != p.read_text(encoding="utf-8", errors="replace")
                ]
            else:
                hits = strip_stray_brackets(writer_dir)
            for path in hits:
                self.stdout.write(str(path))
            total += len(hits)
        verb = "would fix" if options["dry_run"] else "fixed"
        self.stdout.write(self.style.SUCCESS(f"{verb} {total} file(s) under {root}"))
