"""
DOI utility functions for validation, formatting, and metadata retrieval.
Provides helper functions for DOI operations across the service layer.
"""

import logging
import re
import requests
from typing import Optional, Dict

from django.core.exceptions import ValidationError

from ...models import Dataset
from .doi_manager import DOIManager
from .doi_exceptions import DOIAssignmentError

logger = logging.getLogger(__name__)


def auto_assign_doi_on_publish(dataset: Dataset) -> Optional[str]:
    """Automatically assign DOI when dataset is published"""

    if dataset.repository_doi:
        logger.info(f"Dataset {dataset.id} already has DOI: {dataset.repository_doi}")
        return dataset.repository_doi

    if not dataset.repository_connection:
        logger.warning(f"Dataset {dataset.id} has no repository connection")
        return None

    try:
        doi_manager = DOIManager(dataset.repository_connection)
        doi = doi_manager.assign_doi_to_dataset(dataset, publish=True)

        logger.info(f"Auto-assigned DOI {doi} to dataset {dataset.id}")
        return doi

    except Exception as e:
        logger.error(f"Failed to auto-assign DOI to dataset {dataset.id}: {e}")
        return None


def validate_and_format_doi(doi_string: str) -> Optional[str]:
    """Validate and format a DOI string"""

    if not doi_string:
        return None

    # Remove common prefixes
    doi_string = doi_string.strip()
    doi_string = doi_string.replace("https://doi.org/", "")
    doi_string = doi_string.replace("http://doi.org/", "")
    doi_string = doi_string.replace("doi:", "")
    doi_string = doi_string.replace("DOI:", "")

    # Basic DOI format validation
    doi_pattern = r"^10\.\d{4,}\/[-._;()\/:a-zA-Z0-9]+$"

    if re.match(doi_pattern, doi_string):
        return doi_string
    else:
        raise ValidationError(f"Invalid DOI format: {doi_string}")


def get_doi_metadata(doi: str) -> Optional[Dict]:
    """Retrieve metadata for a DOI from CrossRef or DataCite"""

    try:
        # Try CrossRef first
        response = requests.get(
            f"https://api.crossref.org/works/{doi}",
            headers={"Accept": "application/json"},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "source": "crossref",
                "title": data["message"].get("title", [""])[0],
                "authors": [
                    f"{author.get('given', '')} {author.get('family', '')}"
                    for author in data["message"].get("author", [])
                ],
                "publisher": data["message"].get("publisher"),
                "published_date": data["message"]
                .get("published-print", {})
                .get("date-parts", [[None]])[0][0],
                "type": data["message"].get("type"),
                "url": data["message"].get("URL"),
                "abstract": data["message"].get("abstract"),
            }

    except Exception as e:
        logger.warning(f"Failed to get metadata from CrossRef for DOI {doi}: {e}")

    try:
        # Try DataCite
        response = requests.get(
            f"https://api.datacite.org/dois/{doi}",
            headers={"Accept": "application/json"},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            attributes = data["data"]["attributes"]

            return {
                "source": "datacite",
                "title": attributes.get("titles", [{}])[0].get("title"),
                "authors": [
                    creator.get("name") for creator in attributes.get("creators", [])
                ],
                "publisher": attributes.get("publisher"),
                "published_date": attributes.get("published"),
                "type": attributes.get("resourceTypeGeneral"),
                "url": attributes.get("url"),
                "description": attributes.get("descriptions", [{}])[0].get(
                    "description"
                ),
            }

    except Exception as e:
        logger.warning(f"Failed to get metadata from DataCite for DOI {doi}: {e}")

    return None
