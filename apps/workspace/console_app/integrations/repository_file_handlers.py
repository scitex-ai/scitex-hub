"""
Repository File Handlers - Functions to add files to datasets.
"""

import json
import logging
import os

from django.core.files.base import ContentFile

from apps.workspace.scholar_app.models import DatasetFile

logger = logging.getLogger(__name__)


def add_code_outputs_to_dataset(job, dataset):
    """Add code execution outputs to dataset."""
    # Add source code as a file
    if job.source_code:
        source_file_content = job.source_code.encode("utf-8")
        DatasetFile.objects.create(
            dataset=dataset,
            filename=f"source_code_{job.job_id}.py",
            file_path="code/",
            file_type="code",
            file_format="py",
            size_bytes=len(source_file_content),
            description="Source code executed in this job",
            local_file=ContentFile(
                source_file_content, name=f"source_code_{job.job_id}.py"
            ),
        )

    # Add execution log
    if job.output:
        log_content = f"Job ID: {job.job_id}\n"
        log_content += f"Status: {job.status}\n"
        log_content += f"Execution Time: {job.execution_time}s\n"
        log_content += f"CPU Time: {job.cpu_time}s\n"
        log_content += f"Memory Peak: {job.memory_peak} bytes\n\n"
        log_content += "=== OUTPUT ===\n"
        log_content += job.output

        if job.error_output:
            log_content += "\n\n=== ERRORS ===\n"
            log_content += job.error_output

        log_file_content = log_content.encode("utf-8")
        DatasetFile.objects.create(
            dataset=dataset,
            filename=f"execution_log_{job.job_id}.txt",
            file_path="logs/",
            file_type="documentation",
            file_format="txt",
            size_bytes=len(log_file_content),
            description="Execution log with output and errors",
            local_file=ContentFile(
                log_file_content, name=f"execution_log_{job.job_id}.txt"
            ),
        )

    # Add output files
    for file_path in job.output_files:
        add_output_file_to_dataset(dataset, file_path, "data")

    # Add plot files
    for file_path in job.plot_files:
        add_output_file_to_dataset(dataset, file_path, "figure")

    update_dataset_stats(dataset)


def add_analysis_outputs_to_dataset(analysis_job, dataset):
    """Add analysis outputs to dataset."""
    # Add analysis results as JSON
    if analysis_job.results:
        results_content = json.dumps(analysis_job.results, indent=2).encode("utf-8")
        DatasetFile.objects.create(
            dataset=dataset,
            filename=f"analysis_results_{analysis_job.analysis_id}.json",
            file_path="results/",
            file_type="data",
            file_format="json",
            size_bytes=len(results_content),
            description="Analysis results in JSON format",
            local_file=ContentFile(
                results_content,
                name=f"analysis_results_{analysis_job.analysis_id}.json",
            ),
        )

    # Add analysis parameters
    if analysis_job.parameters:
        params_content = json.dumps(analysis_job.parameters, indent=2).encode("utf-8")
        DatasetFile.objects.create(
            dataset=dataset,
            filename=f"analysis_parameters_{analysis_job.analysis_id}.json",
            file_path="metadata/",
            file_type="metadata",
            file_format="json",
            size_bytes=len(params_content),
            description="Analysis parameters and configuration",
            local_file=ContentFile(
                params_content,
                name=f"analysis_parameters_{analysis_job.analysis_id}.json",
            ),
        )

    # Add summary as README
    if analysis_job.summary:
        readme_content = "# Analysis Results\n\n"
        readme_content += f"**Analysis ID:** {analysis_job.analysis_id}\n"
        readme_content += (
            f"**Analysis Type:** {analysis_job.get_analysis_type_display()}\n"
        )
        readme_content += f"**Figures Generated:** {analysis_job.figures_generated}\n\n"
        readme_content += f"## Summary\n\n{analysis_job.summary}\n"

        readme_file_content = readme_content.encode("utf-8")
        DatasetFile.objects.create(
            dataset=dataset,
            filename="README.md",
            file_path="",
            file_type="readme",
            file_format="md",
            size_bytes=len(readme_file_content),
            description="Analysis summary and documentation",
            local_file=ContentFile(readme_file_content, name="README.md"),
        )

    update_dataset_stats(dataset)


def add_notebook_to_dataset(notebook, dataset):
    """Add notebook to dataset."""
    # Add notebook content as JSON
    if notebook.content:
        notebook_content = json.dumps(notebook.content, indent=2).encode("utf-8")
        DatasetFile.objects.create(
            dataset=dataset,
            filename=f"{notebook.title.replace(' ', '_')}.ipynb",
            file_path="notebooks/",
            file_type="code",
            file_format="ipynb",
            size_bytes=len(notebook_content),
            description=f"Jupyter notebook: {notebook.title}",
            local_file=ContentFile(notebook_content, name=f"{notebook.title}.ipynb"),
        )

    # Add notebook metadata
    metadata = {
        "notebook_id": str(notebook.notebook_id),
        "title": notebook.title,
        "description": notebook.description,
        "status": notebook.status,
        "is_public": notebook.is_public,
        "last_executed": (
            notebook.last_executed.isoformat() if notebook.last_executed else None
        ),
        "execution_count": notebook.execution_count,
        "created_at": notebook.created_at.isoformat(),
        "updated_at": notebook.updated_at.isoformat(),
    }

    metadata_content = json.dumps(metadata, indent=2).encode("utf-8")
    DatasetFile.objects.create(
        dataset=dataset,
        filename="notebook_metadata.json",
        file_path="metadata/",
        file_type="metadata",
        file_format="json",
        size_bytes=len(metadata_content),
        description="Notebook metadata and execution information",
        local_file=ContentFile(metadata_content, name="notebook_metadata.json"),
    )

    update_dataset_stats(dataset)


def add_output_file_to_dataset(dataset, file_path, file_type):
    """Add an output file to the dataset."""
    try:
        if os.path.exists(file_path):
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)

            with open(file_path, "rb") as f:
                file_content = f.read()

            file_format = file_name.split(".")[-1] if "." in file_name else ""

            DatasetFile.objects.create(
                dataset=dataset,
                filename=file_name,
                file_path=f"{file_type}s/",
                file_type=file_type,
                file_format=file_format,
                size_bytes=file_size,
                description=f"Generated {file_type} from code execution",
                local_file=ContentFile(file_content, name=file_name),
            )

            logger.info(f"Added {file_type} file {file_name} to dataset {dataset.id}")

    except Exception as e:
        logger.error(f"Failed to add output file {file_path} to dataset: {e}")


def update_dataset_stats(dataset):
    """Update dataset file count and total size."""
    files = dataset.files.all()
    dataset.file_count = files.count()
    dataset.total_size_bytes = sum(f.size_bytes for f in files)

    # Update file formats list
    formats = list({f.file_format for f in files if f.file_format})
    dataset.file_formats = formats

    dataset.save()
