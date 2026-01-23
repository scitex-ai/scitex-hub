"""
Metadata generation functionality for manuscript repository integration.
"""

import logging
from typing import Dict, List

from apps.scholar_app.models import Dataset

logger = logging.getLogger(__name__)


def generate_dataset_description(manuscript) -> str:
    """Generate a description for the supplementary dataset"""

    description = f"Supplementary data and materials for the manuscript:\n\n"
    description += f"Title: {manuscript.title}\n"
    description += (
        f"Authors: {manuscript.owner.get_full_name() or manuscript.owner.username}"
    )

    collaborators = manuscript.collaborators.all()
    if collaborators:
        collab_names = [c.get_full_name() or c.username for c in collaborators]
        description += f", {', '.join(collab_names)}"

    description += f"\n\nAbstract:\n{manuscript.abstract}\n\n"
    description += f"Keywords: {manuscript.keywords}\n\n"
    description += (
        f"This dataset contains supplementary materials, data, and other resources "
    )
    description += f"that support the findings presented in the manuscript."

    if manuscript.target_journal:
        description += f"\n\nTarget Journal: {manuscript.target_journal}"

    return description


def generate_replication_description(manuscript) -> str:
    """Generate a description for the replication dataset"""

    description = f"Replication materials for the manuscript:\n\n"
    description += f"Title: {manuscript.title}\n"
    description += (
        f"Authors: {manuscript.owner.get_full_name() or manuscript.owner.username}"
    )

    collaborators = manuscript.collaborators.all()
    if collaborators:
        collab_names = [c.get_full_name() or c.username for c in collaborators]
        description += f", {', '.join(collab_names)}"

    description += f"\n\nAbstract:\n{manuscript.abstract}\n\n"
    description += (
        f"This dataset contains all the data, code, and analysis scripts needed "
    )
    description += f"to reproduce the results presented in the manuscript. It includes:\n\n"
    description += f"• Source code and analysis scripts\n"
    description += f"• Raw and processed data files\n"
    description += f"• Configuration files and parameters\n"
    description += f"• Documentation and README files\n"
    description += f"• Figures and visualization outputs\n\n"
    description += (
        f"The materials are organized to support computational reproducibility "
    )
    description += f"and enable other researchers to verify and build upon the findings."

    return description


def generate_arxiv_dataset_description(arxiv_submission) -> str:
    """Generate a description for the arXiv dataset"""

    description = f"Materials associated with arXiv submission:\n\n"
    description += f"Title: {arxiv_submission.title}\n"
    description += f"arXiv ID: {arxiv_submission.arxiv_id or 'Pending'}\n"
    description += f"Authors: {arxiv_submission.authors}\n"
    description += f"Primary Category: {arxiv_submission.primary_category.code}\n"

    if arxiv_submission.secondary_categories.exists():
        secondary = [cat.code for cat in arxiv_submission.secondary_categories.all()]
        description += f"Secondary Categories: {', '.join(secondary)}\n"

    description += f"\nAbstract:\n{arxiv_submission.abstract}\n\n"
    description += (
        f"This dataset contains the submission materials for this arXiv preprint, "
    )
    description += (
        f"including LaTeX source files, PDF, and any supplementary materials."
    )

    if arxiv_submission.comments:
        description += f"\n\nComments: {arxiv_submission.comments}"

    return description


def generate_keywords(manuscript) -> str:
    """Generate keywords for the dataset"""

    keywords = []

    if manuscript.keywords:
        keywords.extend(
            [k.strip() for k in manuscript.keywords.split(",") if k.strip()]
        )

    # Add manuscript-specific keywords
    keywords.extend(["manuscript", "research data", "supplementary materials"])

    if manuscript.target_journal:
        keywords.append(manuscript.target_journal.lower().replace(" ", "_"))

    return ", ".join(keywords[:10])  # Limit to 10 keywords


def generate_data_availability_statement_impl(manuscript) -> str:
    """Generate a data availability statement for the manuscript"""

    linked_datasets = Dataset.objects.filter(
        cited_in_manuscripts=manuscript
    ).select_related("repository_connection__repository")

    if not linked_datasets.exists():
        return "No datasets are associated with this manuscript."

    statement = "Data Availability Statement:\n\n"

    for dataset in linked_datasets:
        if dataset.repository_doi:
            statement += f"• {dataset.title}: {dataset.repository_doi}\n"
        elif dataset.repository_url:
            statement += f"• {dataset.title}: {dataset.repository_url}\n"
        else:
            statement += f"• {dataset.title}: Available in {dataset.repository_connection.repository.name}\n"

    statement += "\nAll datasets are made available under their respective licenses. "
    statement += "Please cite the datasets when reusing the data."

    return statement


def get_citation_entries_impl(manuscript) -> List[Dict]:
    """Generate citation entries for linked datasets"""

    linked_datasets = Dataset.objects.filter(
        cited_in_manuscripts=manuscript
    ).select_related("repository_connection__repository")

    citations = []

    for dataset in linked_datasets:
        citation = {
            "type": "dataset",
            "title": dataset.title,
            "author": dataset.owner.get_full_name() or dataset.owner.username,
            "year": dataset.published_at.year
            if dataset.published_at
            else dataset.created_at.year,
            "publisher": dataset.repository_connection.repository.name,
            "doi": dataset.repository_doi,
            "url": dataset.repository_url,
            "version": dataset.version,
            "keywords": dataset.keywords,
        }

        # Add collaborators as additional authors
        collaborators = dataset.collaborators.all()
        if collaborators:
            authors = [dataset.owner.get_full_name() or dataset.owner.username]
            authors.extend([c.get_full_name() or c.username for c in collaborators])
            citation["author"] = " and ".join(authors)

        citations.append(citation)

    return citations


def generate_replication_readme(manuscript) -> str:
    """Generate README for replication dataset"""

    readme = f"# Replication Materials\n\n"
    readme += f"## Manuscript Information\n\n"
    readme += f"**Title:** {manuscript.title}\n"
    readme += (
        f"**Authors:** {manuscript.owner.get_full_name() or manuscript.owner.username}"
    )

    collaborators = manuscript.collaborators.all()
    if collaborators:
        collab_names = [c.get_full_name() or c.username for c in collaborators]
        readme += f", {', '.join(collab_names)}"

    readme += f"\n**Status:** {manuscript.get_status_display()}\n"

    if manuscript.target_journal:
        readme += f"**Target Journal:** {manuscript.target_journal}\n"

    readme += f"\n## Abstract\n\n{manuscript.abstract}\n\n"

    readme += f"## Repository Contents\n\n"
    readme += f"This repository contains all materials needed to reproduce the results presented in the manuscript:\n\n"
    readme += f"### Directory Structure\n\n"
    readme += f"```\n"
    readme += f"├── manuscript/          # Manuscript files (PDF, LaTeX)\n"
    readme += f"├── replication/         # Replication materials\n"
    readme += f"│   ├── code_outputs/    # Code execution metadata\n"
    readme += f"│   └── analysis/        # Analysis results\n"
    readme += f"├── metadata/            # Dataset and manuscript metadata\n"
    readme += f"└── README.md           # This file\n"
    readme += f"```\n\n"

    readme += f"### Requirements\n\n"
    readme += f"To reproduce the results, you will need:\n\n"
    readme += f"- Python 3.8 or higher\n"
    readme += f"- Required packages (see requirements files in code directories)\n"
    readme += f"- LaTeX distribution for document compilation\n\n"

    readme += f"### Usage\n\n"
    readme += f"1. Download all files from this repository\n"
    readme += f"2. Install required dependencies\n"
    readme += f"3. Run analysis scripts in the order specified\n"
    readme += f"4. Compare outputs with published results\n\n"

    readme += f"### Citation\n\n"
    readme += f"If you use these materials, please cite the original manuscript:\n\n"
    readme += f"```\n"
    readme += f"[Citation will be added upon publication]\n"
    readme += f"```\n\n"

    readme += f"### Contact\n\n"
    readme += f"For questions about these replication materials, please contact:\n"
    readme += f"{manuscript.owner.get_full_name() or manuscript.owner.username}\n"

    if hasattr(manuscript.owner, "email"):
        readme += f"Email: {manuscript.owner.email}\n"

    readme += f"\n### License\n\n"
    readme += f"These materials are made available under the Creative Commons Attribution 4.0 License (CC-BY-4.0).\n"

    return readme
