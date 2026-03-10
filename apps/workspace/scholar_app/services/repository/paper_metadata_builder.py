"""
DataCite metadata builders for research papers.
Handles XML metadata generation for paper resources.
"""

import xml.etree.ElementTree as ET

from ...models import SearchIndex


class PaperMetadataBuilder:
    """Builder for DataCite metadata XML for research papers"""

    def build_metadata(self, paper: SearchIndex) -> str:
        """Build DataCite metadata XML for a research paper"""

        # Create root element
        root = ET.Element("resource")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        root.set("xmlns", "http://datacite.org/schema/kernel-4")
        root.set(
            "xsi:schemaLocation",
            "http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4.4/metadata.xsd",
        )

        # Identifier (DOI)
        if paper.doi:
            identifier = ET.SubElement(root, "identifier")
            identifier.set("identifierType", "DOI")
            identifier.text = paper.doi.replace("https://doi.org/", "").replace(
                "doi:", ""
            )

        # Creators
        self._add_creators(root, paper)

        # Titles
        titles = ET.SubElement(root, "titles")
        title = ET.SubElement(titles, "title")
        title.text = paper.title

        # Publisher
        publisher = ET.SubElement(root, "publisher")
        if paper.journal:
            publisher.text = paper.journal.name
        else:
            publisher.text = paper.get_source_display()

        # Publication year
        publication_year = ET.SubElement(root, "publicationYear")
        if paper.publication_date:
            publication_year.text = str(paper.publication_date.year)
        else:
            publication_year.text = str(paper.created_at.year)

        # Resource type
        resource_type = ET.SubElement(root, "resourceType")
        resource_type.set("resourceTypeGeneral", "Text")
        resource_type.text = paper.get_document_type_display()

        # Subjects (keywords)
        self._add_subjects(root, paper.keywords)

        # Descriptions
        if paper.abstract:
            descriptions = ET.SubElement(root, "descriptions")
            description = ET.SubElement(descriptions, "description")
            description.set("descriptionType", "Abstract")
            description.text = paper.abstract

        # Dates
        self._add_dates(root, paper)

        # Language
        language = ET.SubElement(root, "language")
        language.text = "en"  # Default to English

        # Related identifiers
        self._add_related_identifiers(root, paper)

        return ET.tostring(root, encoding="unicode")

    def _add_creators(self, root: ET.Element, paper: SearchIndex):
        """Add creator elements for paper authors"""
        creators = ET.SubElement(root, "creators")

        # Get authors through AuthorPaper relationship
        author_papers = paper.authors.through.objects.filter(paper=paper).order_by(
            "author_order"
        )

        for author_paper in author_papers:
            creator = ET.SubElement(creators, "creator")
            creator_name = ET.SubElement(creator, "creatorName")
            creator_name.set("nameType", "Personal")
            creator_name.text = author_paper.author.full_name

            if author_paper.author.orcid:
                name_identifier = ET.SubElement(creator, "nameIdentifier")
                name_identifier.set("schemeURI", "https://orcid.org")
                name_identifier.set("nameIdentifierScheme", "ORCID")
                name_identifier.text = author_paper.author.orcid

            if author_paper.author.affiliation:
                affiliation = ET.SubElement(creator, "affiliation")
                affiliation.text = author_paper.author.affiliation

    def _add_subjects(self, root: ET.Element, keywords: str):
        """Add subject (keyword) elements"""
        if keywords:
            subjects = ET.SubElement(root, "subjects")
            for keyword in keywords.split(","):
                keyword = keyword.strip()
                if keyword:
                    subject = ET.SubElement(subjects, "subject")
                    subject.text = keyword

    def _add_dates(self, root: ET.Element, paper: SearchIndex):
        """Add date elements"""
        dates = ET.SubElement(root, "dates")

        if paper.publication_date:
            pub_date = ET.SubElement(dates, "date")
            pub_date.set("dateType", "Issued")
            pub_date.text = paper.publication_date.strftime("%Y-%m-%d")

    def _add_related_identifiers(self, root: ET.Element, paper: SearchIndex):
        """Add related identifiers for paper"""
        related_identifiers = ET.SubElement(root, "relatedIdentifiers")

        if paper.pmid:
            related_identifier = ET.SubElement(related_identifiers, "relatedIdentifier")
            related_identifier.set("relatedIdentifierType", "PMID")
            related_identifier.set("relationType", "IsIdenticalTo")
            related_identifier.text = paper.pmid

        if paper.arxiv_id:
            related_identifier = ET.SubElement(related_identifiers, "relatedIdentifier")
            related_identifier.set("relatedIdentifierType", "arXiv")
            related_identifier.set("relationType", "IsIdenticalTo")
            related_identifier.text = paper.arxiv_id
