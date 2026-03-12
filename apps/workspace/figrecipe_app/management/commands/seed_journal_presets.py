"""
Seed journal presets for scientific figure editor
Based on official journal submission guidelines
"""

from django.core.management.base import BaseCommand
from apps.workspace.figrecipe_app.models import JournalPreset


class Command(BaseCommand):
    help = "Seed journal presets for scientific figures"

    def handle(self, *args, **options):
        presets = [
            # Simplified standard sizes: 90mm (single) / 180mm (double)
            # Works for Nature, Science, Cell, PNAS, and most major journals
            {
                "name": "Standard",
                "column_type": "single",
                "width_mm": 90,
                "height_mm": None,  # Auto
                "dpi": 300,
                "font_family": "Arial",
                "font_size_pt": 7,
                "line_width_pt": 0.5,
            },
            {
                "name": "Standard",
                "column_type": "double",
                "width_mm": 180,
                "height_mm": None,
                "dpi": 300,
                "font_family": "Arial",
                "font_size_pt": 7,
                "line_width_pt": 0.5,
            },
        ]

        created_count = 0
        updated_count = 0

        for preset_data in presets:
            preset, created = JournalPreset.objects.update_or_create(
                name=preset_data["name"],
                column_type=preset_data["column_type"],
                defaults=preset_data,
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Created: {preset.name} - {preset.get_column_type_display()}"
                    )
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"⟳ Updated: {preset.name} - {preset.get_column_type_display()}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Done: {created_count} created, {updated_count} updated"
            )
        )
