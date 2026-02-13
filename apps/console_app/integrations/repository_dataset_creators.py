"""
Repository Dataset Creators - Functions to create datasets from various sources.
"""

from apps.scholar_app.models import Dataset


def create_dataset_from_code_job(job, user, repository_connection):
    """Create a dataset from a code execution job."""
    title = f"Code Execution Results - {job.job_id}"
    description = f"""
    Results from code execution job {job.job_id}.

    Execution Type: {job.get_execution_type_display()}
    Status: {job.get_status_display()}
    Execution Time: {job.execution_time}s
    CPU Time: {job.cpu_time}s
    Memory Peak: {job.memory_peak / (1024 * 1024):.1f} MB

    Generated on: {job.created_at}
    """.strip()

    dataset = Dataset.objects.create(
        title=title,
        description=description,
        dataset_type="code_output",
        owner=user,
        repository_connection=repository_connection,
        keywords=f"code execution, {job.execution_type}, computational results",
        generated_by_job=job,
        status="draft",
    )

    return dataset


def create_dataset_from_analysis_job(analysis_job, user, repository_connection):
    """Create a dataset from a data analysis job."""
    title = f"Analysis Results - {analysis_job.analysis_type}"
    description = f"""
    Results from data analysis job {analysis_job.analysis_id}.

    Analysis Type: {analysis_job.get_analysis_type_display()}
    Input Data: {analysis_job.input_data_path}
    Figures Generated: {analysis_job.figures_generated}

    Analysis Summary:
    {analysis_job.summary}

    Generated on: {analysis_job.created_at}
    """.strip()

    dataset = Dataset.objects.create(
        title=title,
        description=description,
        dataset_type="analysis_results",
        owner=user,
        repository_connection=repository_connection,
        keywords=f"data analysis, {analysis_job.analysis_type}, computational results",
        status="draft",
    )

    return dataset


def create_dataset_from_notebook(notebook, user, repository_connection):
    """Create a dataset from a notebook."""
    title = f"Notebook - {notebook.title}"
    description = f"""
    Jupyter notebook: {notebook.title}

    {notebook.description}

    Status: {notebook.get_status_display()}
    Last Executed: {notebook.last_executed}
    Execution Count: {notebook.execution_count}

    Created on: {notebook.created_at}
    """.strip()

    dataset = Dataset.objects.create(
        title=title,
        description=description,
        dataset_type="code_output",
        owner=user,
        repository_connection=repository_connection,
        keywords=f"jupyter notebook, computational notebook, {notebook.status}",
        status="draft",
    )

    # Associate notebook with dataset
    dataset.associated_notebooks.add(notebook)

    return dataset
