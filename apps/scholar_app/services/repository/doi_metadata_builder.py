"""
DataCite metadata builders for datasets.
Handles XML metadata generation for dataset resources.
"""

import xml.etree.ElementTree as ET

from ...models import Dataset


class DatasetMetadataBuilder:
    """Builder for DataCite metadata XML for datasets"""

    def build_metadata(self, dataset: Dataset) -> str:
        """Build DataCite metadata XML for a dataset"""

        # Create root element
        root = ET.Element("resource")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        root.set("xmlns", "http://datacite.org/schema/kernel-4")
        root.set(
            "xsi:schemaLocation",
            "http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4.4/metadata.xsd",
        )

        # Identifier (DOI)
        if dataset.repository_doi:
            identifier = ET.SubElement(root, "identifier")
            identifier.set("identifierType", "DOI")
            identifier.text = dataset.repository_doi.replace(
                "https://doi.org/", ""
            ).replace("doi:", "")

        # Creators
        self._add_creators(root, dataset)

        # Titles
        titles = ET.SubElement(root, "titles")
        title = ET.SubElement(titles, "title")
        title.text = dataset.title

        # Publisher
        publisher = ET.SubElement(root, "publisher")
        publisher.text = dataset.repository_connection.repository.name

        # Publication year
        publication_year = ET.SubElement(root, "publicationYear")
        if dataset.published_at:
            publication_year.text = str(dataset.published_at.year)
        else:
            publication_year.text = str(dataset.created_at.year)

        # Resource type
        resource_type = ET.SubElement(root, "resourceType")
        resource_type.set("resourceTypeGeneral", "Dataset")
        resource_type.text = dataset.get_dataset_type_display()

        # Subjects (keywords)
        self._add_subjects(root, dataset.keywords)

        # Descriptions
        descriptions = ET.SubElement(root, "descriptions")
        description = ET.SubElement(descriptions, "description")
        description.set("descriptionType", "Abstract")
        description.text = dataset.description

        # Dates
        self._add_dates(root, dataset)

        # Language
        language = ET.SubElement(root, "language")
        language.text = "en"  # Default to English

        # Version
        version = ET.SubElement(root, "version")
        version.text = dataset.version

        # Rights
        self._add_rights(root, dataset.license)

        # Related identifiers
        self._add_related_identifiers_dataset(root, dataset)

        # Formats
        self._add_formats(root, dataset.file_formats)

        # Size
        if dataset.total_size_bytes > 0:
            sizes = ET.SubElement(root, "sizes")
            size = ET.SubElement(sizes, "size")
            size.text = dataset.get_file_size_display()

        return ET.tostring(root, encoding="unicode")

    def _add_creators(self, root: ET.Element, dataset: Dataset):
        """Add creator elements for owner and collaborators"""
        creators = ET.SubElement(root, "creators")

        # Main creator (owner)
        creator = ET.SubElement(creators, "creator")
        creator_name = ET.SubElement(creator, "creatorName")
        creator_name.set("nameType", "Personal")
        creator_name.text = dataset.owner.get_full_name() or dataset.owner.username

        if hasattr(dataset.owner, "orcid_id") and dataset.owner.orcid_id:
            name_identifier = ET.SubElement(creator, "nameIdentifier")
            name_identifier.set("schemeURI", "https://orcid.org")
            name_identifier.set("nameIdentifierScheme", "ORCID")
            name_identifier.text = dataset.owner.orcid_id

        if hasattr(dataset.owner, "affiliation") and dataset.owner.affiliation:
            affiliation = ET.SubElement(creator, "affiliation")
            affiliation.text = dataset.owner.affiliation

        # Additional creators (collaborators)
        for collaborator in dataset.collaborators.all():
            creator = ET.SubElement(creators, "creator")
            creator_name = ET.SubElement(creator, "creatorName")
            creator_name.set("nameType", "Personal")
            creator_name.text = (
                collaborator.get_full_name() or collaborator.username
            )

            if hasattr(collaborator, "orcid_id") and collaborator.orcid_id:
                name_identifier = ET.SubElement(creator, "nameIdentifier")
                name_identifier.set("schemeURI", "https://orcid.org")
                name_identifier.set("nameIdentifierScheme", "ORCID")
                name_identifier.text = collaborator.orcid_id

            if hasattr(collaborator, "affiliation") and collaborator.affiliation:
                affiliation = ET.SubElement(creator, "affiliation")
                affiliation.text = collaborator.affiliation

    def _add_subjects(self, root: ET.Element, keywords: str):
        """Add subject (keyword) elements"""
        if keywords:
            subjects = ET.SubElement(root, "subjects")
            for keyword in keywords.split(","):
                keyword = keyword.strip()
                if keyword:
                    subject = ET.SubElement(subjects, "subject")
                    subject.text = keyword

    def _add_dates(self, root: ET.Element, dataset: Dataset):
        """Add date elements"""
        dates = ET.SubElement(root, "dates")

        # Created date
        created_date = ET.SubElement(dates, "date")
        created_date.set("dateType", "Created")
        created_date.text = dataset.created_at.strftime("%Y-%m-%d")

        # Updated date
        if dataset.updated_at != dataset.created_at:
            updated_date = ET.SubElement(dates, "date")
            updated_date.set("dateType", "Updated")
            updated_date.text = dataset.updated_at.strftime("%Y-%m-%d")

        # Available date
        if dataset.published_at:
            available_date = ET.SubElement(dates, "date")
            available_date.set("dateType", "Available")
            available_date.text = dataset.published_at.strftime("%Y-%m-%d")

    def _add_rights(self, root: ET.Element, license: str):
        """Add rights (license) elements"""
        if license:
            rights_list = ET.SubElement(root, "rightsList")
            rights = ET.SubElement(rights_list, "rights")
            rights.text = license

            # Add common license URIs
            license_uris = {
                "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
                "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
                "CC-BY-NC-4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
                "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
                "MIT": "https://opensource.org/licenses/MIT",
                "Apache-2.0": "https://opensource.org/licenses/Apache-2.0",
            }

            if license in license_uris:
                rights.set("rightsURI", license_uris[license])

    def _add_related_identifiers_dataset(self, root: ET.Element, dataset: Dataset):
        """Add related identifiers for dataset"""
        if dataset.related_papers.exists():
            related_identifiers = ET.SubElement(root, "relatedIdentifiers")

            for paper in dataset.related_papers.all():
                if paper.doi:
                    related_identifier = ET.SubElement(
                        related_identifiers, "relatedIdentifier"
                    )
                    related_identifier.set("relatedIdentifierType", "DOI")
                    related_identifier.set("relationType", "IsSupplementTo")
                    related_identifier.text = paper.doi

    def _add_formats(self, root: ET.Element, file_formats: list):
        """Add format elements"""
        if file_formats:
            formats = ET.SubElement(root, "formats")
            for file_format in file_formats:
                format_elem = ET.SubElement(formats, "format")
                format_elem.text = file_format
