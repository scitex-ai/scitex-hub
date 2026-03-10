"""Sync publications from YAML/CrossRef to database."""

import re
from pathlib import Path

import requests
import yaml
from django.core.management.base import BaseCommand

from apps.infra.public_app.models import Publication


def strip_tags(text):
    """Strip HTML/JATS tags from text."""
    if not text:
        return ""
    # Remove JATS and HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Clean up whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def resolve_doi(doi):
    """Fetch paper metadata from CrossRef API."""
    try:
        resp = requests.get(
            f"https://api.crossref.org/works/{doi}",
            headers={"Accept": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            work = resp.json().get("message", {})
            authors = work.get("author", [])
            author_str = ", ".join(
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in authors[:5]
            )
            if len(authors) > 5:
                author_str += " et al."

            year = work.get("published", {}).get("date-parts", [[None]])[0][0]

            return {
                "title": work.get("title", [""])[0],
                "authors": author_str,
                "journal": work.get("container-title", [""])[0],
                "year": year,
                "volume": work.get("volume", ""),
                "page": work.get("page", ""),
                "abstract": strip_tags(work.get("abstract", "")),
                "paper_url": f"https://doi.org/{doi}",
            }
    except Exception as e:
        print(f"  Failed to resolve DOI {doi}: {e}")
    return None


class Command(BaseCommand):
    """Sync publications from YAML file to database."""

    help = "Sync publications from YAML/CrossRef to database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing publications before syncing",
        )

    def handle(self, *args, **options):
        data_file = (
            Path(__file__).parent.parent.parent.parent
            / "public_app"
            / "data"
            / "publications.yaml"
        )

        if not data_file.exists():
            self.stderr.write(f"YAML file not found: {data_file}")
            return

        with open(data_file) as f:
            data = yaml.safe_load(f)

        if options["clear"]:
            deleted, _ = Publication.objects.all().delete()
            self.stdout.write(f"Cleared {deleted} existing publications")

        # Process DOI-based papers
        for entry in data.get("papers_doi", []):
            doi = entry.get("doi")
            if not doi:
                continue

            # Check if already exists
            if Publication.objects.filter(doi=doi).exists():
                self.stdout.write(f"  Skipping existing DOI: {doi}")
                continue

            self.stdout.write(f"  Resolving DOI: {doi}")
            resolved = resolve_doi(doi)
            if resolved:
                Publication.objects.create(
                    doi=doi,
                    title=resolved["title"],
                    authors=resolved["authors"],
                    journal=resolved["journal"],
                    year=resolved["year"],
                    volume=resolved["volume"],
                    page=resolved["page"],
                    abstract=resolved["abstract"],
                    paper_url=resolved["paper_url"],
                    code_url=entry.get("code_url", ""),
                    status="published",
                )
                self.stdout.write(
                    self.style.SUCCESS(f"    Added: {resolved['title'][:50]}...")
                )

        # Process manual papers
        for entry in data.get("papers_manual", []):
            title = entry.get("title")
            if not title:
                continue

            # Check if already exists
            if Publication.objects.filter(title=title).exists():
                self.stdout.write(f"  Skipping existing: {title[:50]}...")
                continue

            # Determine status
            journal = entry.get("journal", "")
            if "preprint" in journal.lower():
                status = "preprint"
            elif "preparation" in journal.lower():
                status = "in_preparation"
            else:
                status = "published"

            Publication.objects.create(
                title=title,
                authors=entry.get("authors", ""),
                journal=journal,
                abstract=entry.get("abstract", ""),
                paper_url=entry.get("paper_url"),
                code_url=entry.get("code_url"),
                status=status,
            )
            self.stdout.write(self.style.SUCCESS(f"  Added manual: {title[:50]}..."))

        count = Publication.objects.count()
        self.stdout.write(self.style.SUCCESS(f"\nTotal publications: {count}"))
