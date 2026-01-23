"""
File operations for manuscript repository integration.
"""

import json
import logging
from typing import List

from django.core.files.base import ContentFile

from apps.scholar_app.models import DatasetFile
from .metadata import generate_replication_readme

logger = logging.getLogger(__name__)


def add_manuscript_files_to_dataset(dataset, manuscript):
    """Add manuscript files to the dataset"""

    # Add compiled PDF if available
    if manuscript.compiled_pdf:
        try:
            with manuscript.compiled_pdf.open("rb") as f:
                pdf_content = f.read()

            pdf_file = DatasetFile.objects.create(
                dataset=dataset,
                filename=f"{manuscript.slug}.pdf",
                file_path="manuscript/",
                file_type="documentation",
                file_format="pdf",
                size_bytes=len(pdf_content),
                description="Compiled manuscript PDF",
                local_file=ContentFile(pdf_content, name=f"{manuscript.slug}.pdf"),
            )

        except Exception as e:
            logger.error(f"Failed to add manuscript PDF to dataset: {e}")

    # Add LaTeX source if using modular structure
    if manuscript.is_modular:
        _add_modular_manuscript_files(dataset, manuscript)
    else:
        # Add main content as LaTeX file
        if manuscript.content:
            latex_content = manuscript.content.encode("utf-8")
            latex_file = DatasetFile.objects.create(
                dataset=dataset,
                filename=f"{manuscript.slug}.tex",
                file_path="manuscript/",
                file_type="documentation",
                file_format="tex",
                size_bytes=len(latex_content),
                description="Manuscript LaTeX source",
                local_file=ContentFile(latex_content, name=f"{manuscript.slug}.tex"),
            )

    # Add manuscript metadata
    add_manuscript_metadata_to_dataset(dataset, manuscript)

    # Update dataset stats
    update_dataset_stats(dataset)


def _add_modular_manuscript_files(dataset, manuscript):
    """Add modular manuscript files to dataset"""

    manuscript_info = {
        "title": manuscript.title,
        "abstract": manuscript.abstract,
        "keywords": manuscript.keywords,
        "is_modular": manuscript.is_modular,
        "paper_directory": manuscript.paper_directory,
        "word_counts": {
            "abstract": manuscript.word_count_abstract,
            "introduction": manuscript.word_count_introduction,
            "methods": manuscript.word_count_methods,
            "results": manuscript.word_count_results,
            "discussion": manuscript.word_count_discussion,
            "total": manuscript.word_count_total,
        },
        "citation_count": manuscript.citation_count,
        "created_at": manuscript.created_at.isoformat(),
        "updated_at": manuscript.updated_at.isoformat(),
    }

    info_content = json.dumps(manuscript_info, indent=2).encode("utf-8")
    info_file = DatasetFile.objects.create(
        dataset=dataset,
        filename="manuscript_info.json",
        file_path="metadata/",
        file_type="metadata",
        file_format="json",
        size_bytes=len(info_content),
        description="Manuscript structure and metadata",
        local_file=ContentFile(info_content, name="manuscript_info.json"),
    )


def add_replication_materials_to_dataset(
    dataset, manuscript, code_outputs: List = None, analysis_data: List = None
):
    """Add replication materials to dataset"""

    # Add linked code execution outputs
    if manuscript.project:
        from apps.code_app.models import CodeExecutionJob

        # Get code jobs from the project
        code_jobs = CodeExecutionJob.objects.filter(
            user=manuscript.owner, status="completed"
        )

        for job in code_jobs[:5]:  # Limit to recent jobs
            # Add job metadata
            job_info = {
                "job_id": str(job.job_id),
                "execution_type": job.execution_type,
                "execution_time": job.execution_time,
                "cpu_time": job.cpu_time,
                "memory_peak": job.memory_peak,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat()
                if job.completed_at
                else None,
                "output_files": job.output_files,
                "plot_files": job.plot_files,
            }

            job_content = json.dumps(job_info, indent=2).encode("utf-8")
            job_file = DatasetFile.objects.create(
                dataset=dataset,
                filename=f"code_job_{job.job_id}.json",
                file_path="replication/code_outputs/",
                file_type="metadata",
                file_format="json",
                size_bytes=len(job_content),
                description=f"Code execution job metadata for {job.job_id}",
                local_file=ContentFile(job_content, name=f"code_job_{job.job_id}.json"),
            )

    # Add manuscript metadata for replication
    add_manuscript_metadata_to_dataset(dataset, manuscript)

    # Create replication README
    readme_content = generate_replication_readme(manuscript)
    readme_file_content = readme_content.encode("utf-8")
    readme_file = DatasetFile.objects.create(
        dataset=dataset,
        filename="README.md",
        file_path="",
        file_type="readme",
        file_format="md",
        size_bytes=len(readme_file_content),
        description="Replication instructions and documentation",
        local_file=ContentFile(readme_file_content, name="README.md"),
    )

    # Update dataset stats
    update_dataset_stats(dataset)


def add_arxiv_files_to_dataset(dataset, arxiv_submission):
    """Add arXiv submission files to dataset"""

    # Add LaTeX source if available
    if arxiv_submission.latex_source:
        try:
            with arxiv_submission.latex_source.open("rb") as f:
                latex_content = f.read()

            latex_file = DatasetFile.objects.create(
                dataset=dataset,
                filename=f"arxiv_source_{arxiv_submission.submission_id}.zip",
                file_path="arxiv/",
                file_type="code",
                file_format="zip",
                size_bytes=len(latex_content),
                description="arXiv LaTeX source files",
                local_file=ContentFile(
                    latex_content,
                    name=f"arxiv_source_{arxiv_submission.submission_id}.zip",
                ),
            )

        except Exception as e:
            logger.error(f"Failed to add arXiv LaTeX source to dataset: {e}")

    # Add PDF if available
    if arxiv_submission.pdf_file:
        try:
            with arxiv_submission.pdf_file.open("rb") as f:
                pdf_content = f.read()

            pdf_file = DatasetFile.objects.create(
                dataset=dataset,
                filename=f"arxiv_manuscript_{arxiv_submission.submission_id}.pdf",
                file_path="arxiv/",
                file_type="documentation",
                file_format="pdf",
                size_bytes=len(pdf_content),
                description="arXiv submission PDF",
                local_file=ContentFile(
                    pdf_content,
                    name=f"arxiv_manuscript_{arxiv_submission.submission_id}.pdf",
                ),
            )

        except Exception as e:
            logger.error(f"Failed to add arXiv PDF to dataset: {e}")

    # Add arXiv metadata
    arxiv_metadata = {
        "submission_id": str(arxiv_submission.submission_id),
        "arxiv_id": arxiv_submission.arxiv_id,
        "title": arxiv_submission.title,
        "authors": arxiv_submission.authors,
        "abstract": arxiv_submission.abstract,
        "primary_category": arxiv_submission.primary_category.code,
        "secondary_categories": [
            cat.code for cat in arxiv_submission.secondary_categories.all()
        ],
        "comments": arxiv_submission.comments,
        "journal_reference": arxiv_submission.journal_reference,
        "doi": arxiv_submission.doi,
        "submission_type": arxiv_submission.submission_type,
        "status": arxiv_submission.status,
        "version": arxiv_submission.version,
        "submitted_at": arxiv_submission.submitted_at.isoformat()
        if arxiv_submission.submitted_at
        else None,
        "published_at": arxiv_submission.published_at.isoformat()
        if arxiv_submission.published_at
        else None,
    }

    metadata_content = json.dumps(arxiv_metadata, indent=2).encode("utf-8")
    metadata_file = DatasetFile.objects.create(
        dataset=dataset,
        filename="arxiv_metadata.json",
        file_path="metadata/",
        file_type="metadata",
        file_format="json",
        size_bytes=len(metadata_content),
        description="arXiv submission metadata",
        local_file=ContentFile(metadata_content, name="arxiv_metadata.json"),
    )

    # Update dataset stats
    update_dataset_stats(dataset)


def add_manuscript_metadata_to_dataset(dataset, manuscript):
    """Add manuscript metadata to dataset"""

    metadata = {
        "manuscript_id": str(manuscript.id),
        "title": manuscript.title,
        "slug": manuscript.slug,
        "abstract": manuscript.abstract,
        "keywords": manuscript.keywords,
        "owner": manuscript.owner.get_full_name() or manuscript.owner.username,
        "collaborators": [
            c.get_full_name() or c.username for c in manuscript.collaborators.all()
        ],
        "status": manuscript.status,
        "target_journal": manuscript.target_journal,
        "submission_deadline": manuscript.submission_deadline.isoformat()
        if manuscript.submission_deadline
        else None,
        "version": manuscript.version,
        "is_public": manuscript.is_public,
        "word_counts": {
            "abstract": manuscript.word_count_abstract,
            "introduction": manuscript.word_count_introduction,
            "methods": manuscript.word_count_methods,
            "results": manuscript.word_count_results,
            "discussion": manuscript.word_count_discussion,
            "total": manuscript.word_count_total,
        },
        "citation_count": manuscript.citation_count,
        "created_at": manuscript.created_at.isoformat(),
        "updated_at": manuscript.updated_at.isoformat(),
        "last_compiled": manuscript.last_compiled.isoformat()
        if manuscript.last_compiled
        else None,
    }

    metadata_content = json.dumps(metadata, indent=2).encode("utf-8")
    metadata_file = DatasetFile.objects.create(
        dataset=dataset,
        filename="manuscript_metadata.json",
        file_path="metadata/",
        file_type="metadata",
        file_format="json",
        size_bytes=len(metadata_content),
        description="Manuscript metadata and information",
        local_file=ContentFile(metadata_content, name="manuscript_metadata.json"),
    )


def update_dataset_stats(dataset):
    """Update dataset file count and total size"""

    files = dataset.files.all()
    dataset.file_count = files.count()
    dataset.total_size_bytes = sum(f.size_bytes for f in files)

    # Update file formats list
    formats = list(set(f.file_format for f in files if f.file_format))
    dataset.file_formats = formats

    dataset.save()
