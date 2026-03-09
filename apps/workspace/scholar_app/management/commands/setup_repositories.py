"""
Management command to set up default research data repositories.
This creates Repository instances for common data repositories like Zenodo, Figshare, etc.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.workspace.scholar_app.models import Repository


class Command(BaseCommand):
    help = "Set up default research data repositories"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing repositories before creating new ones",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write(
                self.style.WARNING("Deleting all existing repositories...")
            )
            Repository.objects.all().delete()

        self.stdout.write("Setting up default research data repositories...")

        repositories_data = [
            {
                "name": "Zenodo",
                "repository_type": "zenodo",
                "description": "Open science repository for research data, publications, and software",
                "api_base_url": "https://zenodo.org",
                "api_version": "v1",
                "api_documentation_url": "https://developers.zenodo.org/",
                "website_url": "https://zenodo.org",
                "supports_doi": True,
                "supports_versioning": True,
                "supports_private_datasets": True,
                "max_file_size_mb": 50000,  # 50GB
                "max_dataset_size_mb": 50000,
                "requires_authentication": True,
                "supports_metadata_formats": ["dublin_core", "datacite", "marc21"],
                "supported_file_formats": [
                    ".pdf",
                    ".txt",
                    ".doc",
                    ".docx",
                    ".csv",
                    ".xlsx",
                    ".json",
                    ".xml",
                    ".zip",
                    ".tar.gz",
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".svg",
                    ".py",
                    ".r",
                    ".m",
                    ".ipynb",
                    ".h5",
                    ".hdf5",
                    ".nc",
                    ".mat",
                ],
                "license_options": [
                    "CC-BY-4.0",
                    "CC-BY-SA-4.0",
                    "CC-BY-NC-4.0",
                    "CC-BY-NC-SA-4.0",
                    "CC-BY-ND-4.0",
                    "CC-BY-NC-ND-4.0",
                    "CC0-1.0",
                    "MIT",
                    "Apache-2.0",
                    "GPL-3.0",
                    "BSD-3-Clause",
                ],
                "is_open_access": True,
                "is_default": True,
                "status": "active",
            },
            {
                "name": "Figshare",
                "repository_type": "figshare",
                "description": "Repository for research outputs including datasets, figures, and publications",
                "api_base_url": "https://api.figshare.com",
                "api_version": "v2",
                "api_documentation_url": "https://docs.figshare.com/",
                "website_url": "https://figshare.com",
                "supports_doi": True,
                "supports_versioning": True,
                "supports_private_datasets": True,
                "max_file_size_mb": 20000,  # 20GB
                "max_dataset_size_mb": 20000,
                "requires_authentication": True,
                "supports_metadata_formats": ["dublin_core", "datacite"],
                "supported_file_formats": [
                    ".pdf",
                    ".txt",
                    ".doc",
                    ".docx",
                    ".csv",
                    ".xlsx",
                    ".json",
                    ".xml",
                    ".zip",
                    ".tar.gz",
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".svg",
                    ".py",
                    ".r",
                    ".m",
                    ".ipynb",
                    ".h5",
                    ".hdf5",
                    ".nc",
                ],
                "license_options": [
                    "CC-BY-4.0",
                    "CC-BY-SA-4.0",
                    "CC-BY-NC-4.0",
                    "CC-BY-NC-SA-4.0",
                    "CC0-1.0",
                    "MIT",
                    "Apache-2.0",
                    "GPL-3.0",
                ],
                "is_open_access": True,
                "is_default": False,
                "status": "active",
            },
            {
                "name": "Dryad",
                "repository_type": "dryad",
                "description": "Repository for data underlying scientific publications",
                "api_base_url": "https://datadryad.org/api/v2",
                "api_version": "v2",
                "api_documentation_url": "https://datadryad.org/docs/api",
                "website_url": "https://datadryad.org",
                "supports_doi": True,
                "supports_versioning": True,
                "supports_private_datasets": True,
                "max_file_size_mb": 300000,  # 300GB
                "max_dataset_size_mb": 300000,
                "requires_authentication": True,
                "supports_metadata_formats": ["datacite", "dublin_core"],
                "supported_file_formats": [
                    ".csv",
                    ".xlsx",
                    ".txt",
                    ".json",
                    ".xml",
                    ".zip",
                    ".tar.gz",
                    ".h5",
                    ".hdf5",
                    ".nc",
                    ".mat",
                    ".sav",
                    ".dta",
                    ".rdata",
                ],
                "license_options": ["CC0-1.0", "CC-BY-4.0"],
                "is_open_access": True,
                "is_default": False,
                "status": "active",
            },
            {
                "name": "Harvard Dataverse",
                "repository_type": "harvard_dataverse",
                "description": "Research data repository hosted by Harvard University",
                "api_base_url": "https://dataverse.harvard.edu/api",
                "api_version": "v1",
                "api_documentation_url": "https://guides.dataverse.org/en/latest/api/",
                "website_url": "https://dataverse.harvard.edu",
                "supports_doi": True,
                "supports_versioning": True,
                "supports_private_datasets": True,
                "max_file_size_mb": 2048,  # 2GB per file
                "max_dataset_size_mb": 10000,  # 10GB total
                "requires_authentication": True,
                "supports_metadata_formats": ["datacite", "dublin_core", "ddi"],
                "supported_file_formats": [
                    ".txt",
                    ".csv",
                    ".xlsx",
                    ".json",
                    ".xml",
                    ".zip",
                    ".tar.gz",
                    ".pdf",
                    ".doc",
                    ".docx",
                    ".h5",
                    ".hdf5",
                    ".nc",
                    ".dta",
                    ".sav",
                ],
                "license_options": [
                    "CC0-1.0",
                    "CC-BY-4.0",
                    "CC-BY-SA-4.0",
                    "CC-BY-NC-4.0",
                ],
                "is_open_access": True,
                "is_default": False,
                "status": "active",
            },
            {
                "name": "Open Science Framework (OSF)",
                "repository_type": "osf",
                "description": "Open source scholarly commons for research materials and collaboration",
                "api_base_url": "https://api.osf.io/v2",
                "api_version": "v2",
                "api_documentation_url": "https://developer.osf.io/",
                "website_url": "https://osf.io",
                "supports_doi": True,
                "supports_versioning": True,
                "supports_private_datasets": True,
                "max_file_size_mb": 5000,  # 5GB per file
                "max_dataset_size_mb": 50000,  # 50GB total
                "requires_authentication": True,
                "supports_metadata_formats": ["dublin_core"],
                "supported_file_formats": [
                    ".txt",
                    ".csv",
                    ".xlsx",
                    ".json",
                    ".xml",
                    ".zip",
                    ".tar.gz",
                    ".pdf",
                    ".doc",
                    ".docx",
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".py",
                    ".r",
                    ".m",
                    ".ipynb",
                    ".h5",
                    ".hdf5",
                    ".nc",
                ],
                "license_options": [
                    "No license",
                    "CC0-1.0",
                    "CC-BY-4.0",
                    "MIT",
                    "Apache-2.0",
                ],
                "is_open_access": True,
                "is_default": False,
                "status": "active",
            },
            {
                "name": "Mendeley Data",
                "repository_type": "mendeley_data",
                "description": "Research data repository by Mendeley",
                "api_base_url": "https://api.mendeley.com",
                "api_version": "v1",
                "api_documentation_url": "https://dev.mendeley.com/",
                "website_url": "https://data.mendeley.com",
                "supports_doi": True,
                "supports_versioning": True,
                "supports_private_datasets": True,
                "max_file_size_mb": 10000,  # 10GB per dataset
                "max_dataset_size_mb": 10000,
                "requires_authentication": True,
                "supports_metadata_formats": ["dublin_core"],
                "supported_file_formats": [
                    ".txt",
                    ".csv",
                    ".xlsx",
                    ".json",
                    ".xml",
                    ".zip",
                    ".tar.gz",
                    ".pdf",
                    ".doc",
                    ".docx",
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                ],
                "license_options": [
                    "CC-BY-4.0",
                    "CC0-1.0",
                    "CC-BY-SA-4.0",
                    "CC-BY-NC-4.0",
                ],
                "is_open_access": True,
                "is_default": False,
                "status": "active",
            },
        ]

        with transaction.atomic():
            created_count = 0
            updated_count = 0

            for repo_data in repositories_data:
                repository, created = Repository.objects.get_or_create(
                    name=repo_data["name"],
                    repository_type=repo_data["repository_type"],
                    defaults=repo_data,
                )

                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Created repository: {repository.name}")
                    )
                else:
                    # Update existing repository with new data
                    for key, value in repo_data.items():
                        if key not in ["name", "repository_type"]:
                            setattr(repository, key, value)
                    repository.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f"↻ Updated repository: {repository.name}")
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nRepository setup complete! "
                f"Created: {created_count}, Updated: {updated_count}"
            )
        )

        # Show summary
        self.stdout.write("\nAvailable repositories:")
        for repo in Repository.objects.filter(status="active").order_by("name"):
            default_marker = " (DEFAULT)" if repo.is_default else ""
            self.stdout.write(
                f"  • {repo.name} ({repo.get_repository_type_display()}){default_marker}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\nRepositories are ready for use. Users can now create connections "
                "to these repositories through the Scholar module."
            )
        )
