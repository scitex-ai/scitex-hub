"""
Utility functions for Scholar module citation export functionality.
"""

import re
from datetime import datetime
from typing import List, Dict, Any
from ..models import SearchIndex, Author, LibraryExport


class CitationExporter:
    """Handle citation exports in various formats"""

    @staticmethod
    def clean_string(text: str) -> str:
        """Clean string for citation format compatibility"""
        if not text:
            return ""
        # Remove special characters that could break citation formats
        text = re.sub(r"[{}\[\]\\]", "", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def format_authors_bibtex(authors: List[Author]) -> str:
        """Format authors for BibTeX"""
        if not authors:
            return ""

        author_strings = []
        for author in authors:
            if author.last_name and author.first_name:
                # BibTeX format: "Last, First Middle"
                name_parts = [author.last_name]
                if author.first_name:
                    name_parts.append(author.first_name)
                if author.middle_name:
                    name_parts.append(author.middle_name)
                author_strings.append(f"{name_parts[0]}, {' '.join(name_parts[1:])}")
            elif author.last_name:
                author_strings.append(author.last_name)

        return " and ".join(author_strings)

    @staticmethod
    def format_authors_ris(authors: List[Author]) -> List[str]:
        """Format authors for RIS format"""
        if not authors:
            return []

        author_lines = []
        for author in authors:
            if author.last_name and author.first_name:
                # RIS format: "Last, First Middle"
                name_parts = [author.last_name]
                if author.first_name:
                    name_parts.append(author.first_name)
                if author.middle_name:
                    name_parts.append(author.middle_name)
                author_lines.append(
                    f"AU  - {name_parts[0]}, {' '.join(name_parts[1:])}"
                )
            elif author.last_name:
                author_lines.append(f"AU  - {author.last_name}")

        return author_lines

    @staticmethod
    def format_authors_endnote(authors: List[Author]) -> str:
        """Format authors for EndNote"""
        if not authors:
            return ""

        author_strings = []
        for author in authors:
            if author.last_name and author.first_name:
                # EndNote format: "Last, First Middle"
                name_parts = [author.last_name]
                if author.first_name:
                    name_parts.append(author.first_name)
                if author.middle_name:
                    name_parts.append(author.middle_name)
                author_strings.append(f"{name_parts[0]}, {' '.join(name_parts[1:])}")
            elif author.last_name:
                author_strings.append(author.last_name)

        return "\n".join(author_strings)

    @staticmethod
    def generate_bibtex_key(paper: SearchIndex) -> str:
        """Generate BibTeX citation key"""
        key_parts = []

        # Get first author's last name
        first_author = paper.authors.first()
        if first_author:
            last_name = re.sub(r"[^a-zA-Z]", "", first_author.last_name.lower())
            key_parts.append(last_name)
        else:
            key_parts.append("visitor")

        # Add year
        if paper.publication_date:
            key_parts.append(str(paper.publication_date.year))
        else:
            key_parts.append(str(datetime.now().year))

        # Add title words (first 2-3 significant words)
        title_words = re.findall(r"\b[a-zA-Z]{3,}\b", paper.title.lower())
        key_parts.extend(title_words[:2])

        return "".join(key_parts)

    @classmethod
    def to_bibtex(cls, papers: List[SearchIndex]) -> str:
        """Export papers to BibTeX format"""
        bibtex_entries = []

        for paper in papers:
            # Get authors
            authors = list(paper.authors.all().order_by("authorpaper__author_order"))
            authors_str = cls.format_authors_bibtex(authors)

            # Generate citation key
            key = cls.generate_bibtex_key(paper)

            # Determine entry type
            entry_type = "article"
            if paper.document_type == "book":
                entry_type = "book"
            elif paper.document_type == "chapter":
                entry_type = "inbook"
            elif paper.document_type == "conference":
                entry_type = "inproceedings"
            elif paper.document_type == "thesis":
                entry_type = "phdthesis"
            elif paper.document_type == "preprint":
                entry_type = "misc"

            # Build BibTeX entry
            entry_lines = [f"@{entry_type}{{{key},"]

            # Required fields
            if paper.title:
                title = cls.clean_string(paper.title)
                entry_lines.append(f"  title={{{title}}},")

            if authors_str:
                entry_lines.append(f"  author={{{authors_str}}},")

            # Journal/venue
            if paper.journal:
                journal_name = cls.clean_string(paper.journal.name)
                entry_lines.append(f"  journal={{{journal_name}}},")

            # Year
            if paper.publication_date:
                entry_lines.append(f"  year={{{paper.publication_date.year}}},")

            # Optional fields
            if paper.doi:
                entry_lines.append(f"  doi={{{paper.doi}}},")

            if paper.pmid:
                entry_lines.append(f"  pmid={{{paper.pmid}}},")

            if paper.arxiv_id:
                entry_lines.append(f"  eprint={{{paper.arxiv_id}}},")
                entry_lines.append(f"  archivePrefix={{arXiv}},")

            if paper.external_url:
                entry_lines.append(f"  url={{{paper.external_url}}},")

            if paper.abstract:
                abstract = cls.clean_string(paper.abstract)
                if len(abstract) > 500:
                    abstract = abstract[:500] + "..."
                entry_lines.append(f"  abstract={{{abstract}}},")

            # Remove trailing comma from last line and close entry
            if entry_lines[-1].endswith(","):
                entry_lines[-1] = entry_lines[-1][:-1]
            entry_lines.append("}")

            bibtex_entries.append("\n".join(entry_lines))

        return "\n\n".join(bibtex_entries)

    @classmethod
    def to_ris(cls, papers: List[SearchIndex]) -> str:
        """Export papers to RIS format"""
        ris_entries = []

        for paper in papers:
            # Get authors
            authors = list(paper.authors.all().order_by("authorpaper__author_order"))

            # Start RIS entry
            entry_lines = []

            # Document type
            if paper.document_type == "article":
                entry_lines.append("TY  - JOUR")
            elif paper.document_type == "book":
                entry_lines.append("TY  - BOOK")
            elif paper.document_type == "chapter":
                entry_lines.append("TY  - CHAP")
            elif paper.document_type == "conference":
                entry_lines.append("TY  - CONF")
            elif paper.document_type == "thesis":
                entry_lines.append("TY  - THES")
            else:
                entry_lines.append("TY  - GEN")

            # Title
            if paper.title:
                title = cls.clean_string(paper.title)
                entry_lines.append(f"TI  - {title}")

            # Authors
            author_lines = cls.format_authors_ris(authors)
            entry_lines.extend(author_lines)

            # Journal
            if paper.journal:
                journal_name = cls.clean_string(paper.journal.name)
                entry_lines.append(f"JO  - {journal_name}")

            # Publication year
            if paper.publication_date:
                entry_lines.append(f"PY  - {paper.publication_date.year}")

            # DOI
            if paper.doi:
                entry_lines.append(f"DO  - {paper.doi}")

            # URL
            if paper.external_url:
                entry_lines.append(f"UR  - {paper.external_url}")

            # Abstract
            if paper.abstract:
                abstract = cls.clean_string(paper.abstract)
                if len(abstract) > 1000:
                    abstract = abstract[:1000] + "..."
                entry_lines.append(f"AB  - {abstract}")

            # End of record
            entry_lines.append("ER  - ")

            ris_entries.append("\n".join(entry_lines))

        return "\n\n".join(ris_entries)

    @classmethod
    def to_endnote(cls, papers: List[SearchIndex]) -> str:
        """Export papers to EndNote format"""
        endnote_entries = []

        for paper in papers:
            # Get authors
            authors = list(paper.authors.all().order_by("authorpaper__author_order"))

            entry_lines = []

            # Reference type
            if paper.document_type == "article":
                entry_lines.append("%0 Journal Article")
            elif paper.document_type == "book":
                entry_lines.append("%0 Book")
            elif paper.document_type == "chapter":
                entry_lines.append("%0 Book Section")
            elif paper.document_type == "conference":
                entry_lines.append("%0 Conference Paper")
            elif paper.document_type == "thesis":
                entry_lines.append("%0 Thesis")
            else:
                entry_lines.append("%0 Generic")

            # Title
            if paper.title:
                title = cls.clean_string(paper.title)
                entry_lines.append(f"%T {title}")

            # Authors
            if authors:
                authors_str = cls.format_authors_endnote(authors)
                for author_line in authors_str.split("\n"):
                    if author_line.strip():
                        entry_lines.append(f"%A {author_line.strip()}")

            # Journal
            if paper.journal:
                journal_name = cls.clean_string(paper.journal.name)
                entry_lines.append(f"%J {journal_name}")

            # Publication date
            if paper.publication_date:
                entry_lines.append(f"%D {paper.publication_date.year}")

            # DOI
            if paper.doi:
                entry_lines.append(f"%R {paper.doi}")

            # URL
            if paper.external_url:
                entry_lines.append(f"%U {paper.external_url}")

            # Abstract
            if paper.abstract:
                abstract = cls.clean_string(paper.abstract)
                if len(abstract) > 1000:
                    abstract = abstract[:1000] + "..."
                entry_lines.append(f"%X {abstract}")

            endnote_entries.append("\n".join(entry_lines))

        return "\n\n".join(endnote_entries)

    @classmethod
    def to_csv(cls, papers: List[SearchIndex]) -> str:
        """Export papers to CSV format"""
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        # Header
        headers = [
            "Title",
            "Authors",
            "Journal",
            "Year",
            "DOI",
            "PMID",
            "ArXiv ID",
            "Document Type",
            "Citation Count",
            "URL",
            "Abstract",
        ]
        writer.writerow(headers)

        # Data rows
        for paper in papers:
            authors = list(paper.authors.all().order_by("authorpaper__author_order"))
            authors_str = "; ".join(
                [f"{a.first_name} {a.last_name}".strip() for a in authors]
            )

            row = [
                cls.clean_string(paper.title) if paper.title else "",
                authors_str,
                paper.journal.name if paper.journal else "",
                paper.publication_date.year if paper.publication_date else "",
                paper.doi if paper.doi else "",
                paper.pmid if paper.pmid else "",
                paper.arxiv_id if paper.arxiv_id else "",
                paper.get_document_type_display(),
                paper.citation_count,
                paper.external_url if paper.external_url else "",
                cls.clean_string(paper.abstract) if paper.abstract else "",
            ]
            writer.writerow(row)

        return output.getvalue()

    @classmethod
    def log_export(
        cls,
        user,
        export_format: str,
        papers: List[SearchIndex],
        collection_name: str = "",
        filter_criteria: Dict[str, Any] = None,
    ):
        """Log export activity for analytics"""
        LibraryExport.objects.create(
            user=user,
            export_format=export_format,
            paper_count=len(papers),
            collection_name=collection_name,
            filter_criteria=filter_criteria or {},
        )
