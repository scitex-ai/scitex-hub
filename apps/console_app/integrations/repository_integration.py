"""
Repository integration for Code execution results.
Automatically sync code outputs, datasets, and analysis results to research data repositories.

Re-exports from specialized submodules:
- repository_dataset_creators: Dataset creation functions
- repository_file_handlers: File handling functions
"""

import logging
from typing import Any, Dict, Optional

from django.db import transaction

from apps.scholar_app.models import Dataset, RepositoryConnection
from apps.scholar_app.services.repository.services import upload_dataset_to_repository

from ..models import CodeExecutionJob, DataAnalysisJob, Notebook
from .repository_dataset_creators import (
    create_dataset_from_analysis_job,
    create_dataset_from_code_job,
    create_dataset_from_notebook,
)
from .repository_file_handlers import (
    add_analysis_outputs_to_dataset,
    add_code_outputs_to_dataset,
    add_notebook_to_dataset,
    update_dataset_stats,
)

logger = logging.getLogger(__name__)


class CodeRepositoryIntegrator:
    """Service for integrating code execution results with data repositories."""

    def __init__(
        self, user, repository_connection: Optional[RepositoryConnection] = None
    ):
        self.user = user
        self.repository_connection = (
            repository_connection or self._get_default_connection()
        )

    def _get_default_connection(self) -> Optional[RepositoryConnection]:
        """Get user's default repository connection."""
        return RepositoryConnection.objects.filter(
            user=self.user, is_default=True, status="active"
        ).first()

    def sync_code_execution_results(
        self, job: CodeExecutionJob, auto_upload: bool = True
    ) -> Optional[Dataset]:
        """Sync code execution results to repository."""
        if not self.repository_connection:
            logger.warning(f"No repository connection for user {self.user.username}")
            return None

        try:
            with transaction.atomic():
                dataset = create_dataset_from_code_job(
                    job, self.user, self.repository_connection
                )
                add_code_outputs_to_dataset(job, dataset)

                if auto_upload and job.status == "completed":
                    upload_dataset_to_repository(dataset)

                logger.info(f"Created dataset {dataset.id} for code job {job.job_id}")
                return dataset

        except Exception as e:
            logger.error(f"Failed to sync code execution results: {e}")
            return None

    def sync_analysis_results(
        self, analysis_job: DataAnalysisJob, auto_upload: bool = True
    ) -> Optional[Dataset]:
        """Sync data analysis results to repository."""
        if not self.repository_connection:
            logger.warning(f"No repository connection for user {self.user.username}")
            return None

        try:
            with transaction.atomic():
                dataset = create_dataset_from_analysis_job(
                    analysis_job, self.user, self.repository_connection
                )
                add_analysis_outputs_to_dataset(analysis_job, dataset)

                if auto_upload:
                    upload_dataset_to_repository(dataset)

                logger.info(
                    f"Created dataset {dataset.id} for analysis {analysis_job.analysis_id}"
                )
                return dataset

        except Exception as e:
            logger.error(f"Failed to sync analysis results: {e}")
            return None

    def sync_notebook_results(
        self, notebook: Notebook, auto_upload: bool = False
    ) -> Optional[Dataset]:
        """Sync notebook execution results to repository."""
        if not self.repository_connection:
            logger.warning(f"No repository connection for user {self.user.username}")
            return None

        try:
            with transaction.atomic():
                dataset = create_dataset_from_notebook(
                    notebook, self.user, self.repository_connection
                )
                add_notebook_to_dataset(notebook, dataset)

                if auto_upload:
                    upload_dataset_to_repository(dataset)

                logger.info(
                    f"Created dataset {dataset.id} for notebook {notebook.notebook_id}"
                )
                return dataset

        except Exception as e:
            logger.error(f"Failed to sync notebook results: {e}")
            return None


def auto_sync_code_completion(job: CodeExecutionJob) -> Dict[str, Any]:
    """Automatically sync code execution results on job completion."""
    default_connection = RepositoryConnection.objects.filter(
        user=job.user, is_default=True, auto_sync_enabled=True, status="active"
    ).first()

    if not default_connection:
        logger.info(f"No auto-sync repository connection for user {job.user.username}")
        return {"auto_sync": False, "reason": "no_auto_sync_connection"}

    try:
        integrator = CodeRepositoryIntegrator(job.user, default_connection)
        dataset = integrator.sync_code_execution_results(job, auto_upload=True)

        if dataset:
            return {
                "auto_sync": True,
                "dataset_id": str(dataset.id),
                "dataset_title": dataset.title,
                "repository_name": default_connection.repository.name,
                "files_synced": dataset.file_count,
                "total_size": dataset.total_size_bytes,
            }
        else:
            return {"auto_sync": False, "reason": "sync_failed"}

    except Exception as e:
        logger.error(f"Auto-sync failed for job {job.job_id}: {e}")
        return {"auto_sync": False, "reason": "sync_error", "error": str(e)}


def sync_project_data_to_repository(
    project, repository_connection: RepositoryConnection
) -> Optional[Dataset]:
    """Sync all project data to a repository."""
    try:
        dataset = Dataset.objects.create(
            title=f"Project Data - {project.name}",
            description=(
                f"Complete data and outputs from project: {project.name}\n\n"
                f"{project.description}"
            ),
            dataset_type="supplementary",
            owner=project.owner,
            repository_connection=repository_connection,
            project=project,
            keywords=f"project data, {project.name}, computational results",
            status="draft",
        )

        # Add all code execution results from this project
        code_jobs = CodeExecutionJob.objects.filter(user=project.owner)
        for job in code_jobs:
            if job.status == "completed":
                add_code_outputs_to_dataset(job, dataset)

        # Add all analysis results from this project
        analysis_jobs = DataAnalysisJob.objects.filter(user=project.owner)
        for analysis_job in analysis_jobs:
            add_analysis_outputs_to_dataset(analysis_job, dataset)

        update_dataset_stats(dataset)

        logger.info(f"Created project dataset {dataset.id} for project {project.name}")
        return dataset

    except Exception as e:
        logger.error(f"Failed to sync project data: {e}")
        return None
