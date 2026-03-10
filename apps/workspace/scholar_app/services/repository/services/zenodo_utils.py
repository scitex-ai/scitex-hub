"""Utility functions for Zenodo service."""

from typing import Dict


def format_zenodo_metadata(metadata: Dict) -> Dict:
    """Format metadata for Zenodo API"""
    zenodo_metadata = {
        "title": metadata.get("title", ""),
        "description": metadata.get("description", ""),
        "upload_type": "dataset",
        "creators": metadata.get("creators", []),
    }

    # Add optional fields
    if "keywords" in metadata:
        zenodo_metadata["keywords"] = (
            metadata["keywords"].split(",")
            if isinstance(metadata["keywords"], str)
            else metadata["keywords"]
        )

    if "license" in metadata:
        zenodo_metadata["license"] = metadata["license"]

    if "access_right" in metadata:
        zenodo_metadata["access_right"] = metadata["access_right"]

    if "embargo_date" in metadata:
        zenodo_metadata["embargo_date"] = metadata["embargo_date"]

    if "communities" in metadata:
        zenodo_metadata["communities"] = metadata["communities"]

    return zenodo_metadata


# EOF
