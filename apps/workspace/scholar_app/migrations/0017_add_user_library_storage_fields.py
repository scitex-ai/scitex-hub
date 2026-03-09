# Generated migration for user-level library storage
# Phase 1: Add new fields without removing old ones (backward compatible)

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("scholar_app", "0016_add_search_limits_to_userpreference"),
    ]

    operations = [
        # Add new storage mode field
        migrations.AddField(
            model_name="userlibrary",
            name="storage_mode",
            field=models.CharField(
                choices=[
                    ("django_media", "Django Media Storage"),
                    ("user_library", "User Library (Symlinks)"),
                ],
                default="django_media",
                help_text="Storage backend for this paper",
                max_length=20,
            ),
        ),
        # Add user library PDF path field
        migrations.AddField(
            model_name="userlibrary",
            name="user_library_pdf_path",
            field=models.CharField(
                blank=True,
                help_text="Relative path to PDF in user's scholar library (e.g., 'papers/doi/10.1000_example.pdf')",
                max_length=500,
            ),
        ),
        # Add user library BibTeX path field
        migrations.AddField(
            model_name="userlibrary",
            name="user_library_bibtex_path",
            field=models.CharField(
                blank=True,
                help_text="Relative path to BibTeX in user's scholar library",
                max_length=500,
            ),
        ),
        # Update help text for existing fields to indicate they are legacy
        migrations.AlterField(
            model_name="userlibrary",
            name="personal_pdf",
            field=models.FileField(
                blank=True,
                help_text="[Legacy] PDF file in Django media storage",
                null=True,
                upload_to="user_library/pdfs/",
            ),
        ),
        migrations.AlterField(
            model_name="userlibrary",
            name="personal_bibtex",
            field=models.FileField(
                blank=True,
                help_text="[Legacy] BibTeX file in Django media storage",
                null=True,
                upload_to="user_library/bibtex/",
            ),
        ),
    ]
