#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/code_app/repository_integration.py"""

import pytest

# from apps.code_app.repository_integration import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")

if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/code_app/repository_integration.py
# --------------------------------------------------------------------------------
# """
# Repository integration for Code execution results.
# Automatically sync code outputs, datasets, and analysis results to research data repositories.
# """
# 
# import os
# import json
# import logging
# from typing import Dict, Optional, Any
# from django.core.files.base import ContentFile
# from django.db import transaction
# 
# from .models import CodeExecutionJob, DataAnalysisJob, Notebook
# from apps.scholar_app.models import (
#     Dataset,
#     DatasetFile,
#     RepositoryConnection,
# )
# from apps.scholar_app.repository_services import (
#     upload_dataset_to_repository,
# )
# 
# logger = logging.getLogger(__name__)
# 
# 
# class CodeRepositoryIntegrator:
#     """Service for integrating code execution results with data repositories"""
# 
#     def __init__(
#         self, user, repository_connection: Optional[RepositoryConnection] = None
#     ):
#         self.user = user
#         self.repository_connection = (
#             repository_connection or self._get_default_connection()
#         )
# 
#     def _get_default_connection(self) -> Optional[RepositoryConnection]:
#         """Get user's default repository connection"""
#         return RepositoryConnection.objects.filter(
#             user=self.user, is_default=True, status="active"
#         ).first()
# 
#     def sync_code_execution_results(
#         self, job: CodeExecutionJob, auto_upload: bool = True
#     ) -> Optional[Dataset]:
#         """Sync code execution results to repository"""
# 
#         if not self.repository_connection:
#             logger.warning(
#                 f"No repository connection available for user {self.user.username}"
#             )
#             return None
# 
#         try:
#             with transaction.atomic():
#                 # Create dataset
#                 dataset = self._create_dataset_from_code_job(job)
# 
#                 # Add output files
#                 self._add_code_outputs_to_dataset(job, dataset)
# 
#                 # Auto-upload if requested and job completed successfully
#                 if auto_upload and job.status == "completed":
#                     upload_dataset_to_repository(dataset)
# 
#                 logger.info(f"Created dataset {dataset.id} for code job {job.job_id}")
#                 return dataset
# 
#         except Exception as e:
#             logger.error(f"Failed to sync code execution results: {e}")
#             return None
# 
#     def sync_analysis_results(
#         self, analysis_job: DataAnalysisJob, auto_upload: bool = True
#     ) -> Optional[Dataset]:
#         """Sync data analysis results to repository"""
# 
#         if not self.repository_connection:
#             logger.warning(
#                 f"No repository connection available for user {self.user.username}"
#             )
#             return None
# 
#         try:
#             with transaction.atomic():
#                 # Create dataset
#                 dataset = self._create_dataset_from_analysis_job(analysis_job)
# 
#                 # Add analysis outputs
#                 self._add_analysis_outputs_to_dataset(analysis_job, dataset)
# 
#                 # Auto-upload if requested
#                 if auto_upload:
#                     upload_dataset_to_repository(dataset)
# 
#                 logger.info(
#                     f"Created dataset {dataset.id} for analysis job {analysis_job.analysis_id}"
#                 )
#                 return dataset
# 
#         except Exception as e:
#             logger.error(f"Failed to sync analysis results: {e}")
#             return None
# 
#     def sync_notebook_results(
#         self, notebook: Notebook, auto_upload: bool = False
#     ) -> Optional[Dataset]:
#         """Sync notebook execution results to repository"""
# 
#         if not self.repository_connection:
#             logger.warning(
#                 f"No repository connection available for user {self.user.username}"
#             )
#             return None
# 
#         try:
#             with transaction.atomic():
#                 # Create dataset
#                 dataset = self._create_dataset_from_notebook(notebook)
# 
#                 # Add notebook file
#                 self._add_notebook_to_dataset(notebook, dataset)
# 
#                 # Auto-upload if requested
#                 if auto_upload:
#                     upload_dataset_to_repository(dataset)
# 
#                 logger.info(
#                     f"Created dataset {dataset.id} for notebook {notebook.notebook_id}"
#                 )
#                 return dataset
# 
#         except Exception as e:
#             logger.error(f"Failed to sync notebook results: {e}")
#             return None
# 
#     def _create_dataset_from_code_job(self, job: CodeExecutionJob) -> Dataset:
#         """Create a dataset from a code execution job"""
# 
#         title = f"Code Execution Results - {job.job_id}"
#         description = f"""
#         Results from code execution job {job.job_id}.
#         
#         Execution Type: {job.get_execution_type_display()}
#         Status: {job.get_status_display()}
#         Execution Time: {job.execution_time}s
#         CPU Time: {job.cpu_time}s
#         Memory Peak: {job.memory_peak / (1024 * 1024):.1f} MB
#         
#         Generated on: {job.created_at}
#         """.strip()
# 
#         dataset = Dataset.objects.create(
#             title=title,
#             description=description,
#             dataset_type="code_output",
#             owner=self.user,
#             repository_connection=self.repository_connection,
#             keywords=f"code execution, {job.execution_type}, computational results",
#             generated_by_job=job,
#             status="draft",
#         )
# 
#         return dataset
# 
#     def _create_dataset_from_analysis_job(
#         self, analysis_job: DataAnalysisJob
#     ) -> Dataset:
#         """Create a dataset from a data analysis job"""
# 
#         title = f"Analysis Results - {analysis_job.analysis_type}"
#         description = f"""
#         Results from data analysis job {analysis_job.analysis_id}.
#         
#         Analysis Type: {analysis_job.get_analysis_type_display()}
#         Input Data: {analysis_job.input_data_path}
#         Figures Generated: {analysis_job.figures_generated}
#         
#         Analysis Summary:
#         {analysis_job.summary}
#         
#         Generated on: {analysis_job.created_at}
#         """.strip()
# 
#         dataset = Dataset.objects.create(
#             title=title,
#             description=description,
#             dataset_type="analysis_results",
#             owner=self.user,
#             repository_connection=self.repository_connection,
#             keywords=f"data analysis, {analysis_job.analysis_type}, computational results",
#             status="draft",
#         )
# 
#         return dataset
# 
#     def _create_dataset_from_notebook(self, notebook: Notebook) -> Dataset:
#         """Create a dataset from a notebook"""
# 
#         title = f"Notebook - {notebook.title}"
#         description = f"""
#         Jupyter notebook: {notebook.title}
#         
#         {notebook.description}
#         
#         Status: {notebook.get_status_display()}
#         Last Executed: {notebook.last_executed}
#         Execution Count: {notebook.execution_count}
#         
#         Created on: {notebook.created_at}
#         """.strip()
# 
#         dataset = Dataset.objects.create(
#             title=title,
#             description=description,
#             dataset_type="code_output",
#             owner=self.user,
#             repository_connection=self.repository_connection,
#             keywords=f"jupyter notebook, computational notebook, {notebook.status}",
#             status="draft",
#         )
# 
#         # Associate notebook with dataset
#         dataset.associated_notebooks.add(notebook)
# 
#         return dataset
# 
#     def _add_code_outputs_to_dataset(self, job: CodeExecutionJob, dataset: Dataset):
#         """Add code execution outputs to dataset"""
# 
#         # Add source code as a file
#         if job.source_code:
#             source_file_content = job.source_code.encode("utf-8")
#             source_file = DatasetFile.objects.create(
#                 dataset=dataset,
#                 filename=f"source_code_{job.job_id}.py",
#                 file_path="code/",
#                 file_type="code",
#                 file_format="py",
#                 size_bytes=len(source_file_content),
#                 description="Source code executed in this job",
#                 local_file=ContentFile(
#                     source_file_content, name=f"source_code_{job.job_id}.py"
#                 ),
#             )
# 
#         # Add execution log
#         if job.output:
#             log_content = f"Job ID: {job.job_id}\n"
#             log_content += f"Status: {job.status}\n"
#             log_content += f"Execution Time: {job.execution_time}s\n"
#             log_content += f"CPU Time: {job.cpu_time}s\n"
#             log_content += f"Memory Peak: {job.memory_peak} bytes\n\n"
#             log_content += "=== OUTPUT ===\n"
#             log_content += job.output
# 
#             if job.error_output:
#                 log_content += "\n\n=== ERRORS ===\n"
#                 log_content += job.error_output
# 
#             log_file_content = log_content.encode("utf-8")
#             log_file = DatasetFile.objects.create(
#                 dataset=dataset,
#                 filename=f"execution_log_{job.job_id}.txt",
#                 file_path="logs/",
#                 file_type="documentation",
#                 file_format="txt",
#                 size_bytes=len(log_file_content),
#                 description="Execution log with output and errors",
#                 local_file=ContentFile(
#                     log_file_content, name=f"execution_log_{job.job_id}.txt"
#                 ),
#             )
# 
#         # Add output files
#         for file_path in job.output_files:
#             self._add_output_file_to_dataset(dataset, file_path, "data")
# 
#         # Add plot files
#         for file_path in job.plot_files:
#             self._add_output_file_to_dataset(dataset, file_path, "figure")
# 
#         # Update dataset file count and size
#         self._update_dataset_stats(dataset)
# 
#     def _add_analysis_outputs_to_dataset(
#         self, analysis_job: DataAnalysisJob, dataset: Dataset
#     ):
#         """Add analysis outputs to dataset"""
# 
#         # Add analysis results as JSON
#         if analysis_job.results:
#             results_content = json.dumps(analysis_job.results, indent=2).encode("utf-8")
#             results_file = DatasetFile.objects.create(
#                 dataset=dataset,
#                 filename=f"analysis_results_{analysis_job.analysis_id}.json",
#                 file_path="results/",
#                 file_type="data",
#                 file_format="json",
#                 size_bytes=len(results_content),
#                 description="Analysis results in JSON format",
#                 local_file=ContentFile(
#                     results_content,
#                     name=f"analysis_results_{analysis_job.analysis_id}.json",
#                 ),
#             )
# 
#         # Add analysis parameters
#         if analysis_job.parameters:
#             params_content = json.dumps(analysis_job.parameters, indent=2).encode(
#                 "utf-8"
#             )
#             params_file = DatasetFile.objects.create(
#                 dataset=dataset,
#                 filename=f"analysis_parameters_{analysis_job.analysis_id}.json",
#                 file_path="metadata/",
#                 file_type="metadata",
#                 file_format="json",
#                 size_bytes=len(params_content),
#                 description="Analysis parameters and configuration",
#                 local_file=ContentFile(
#                     params_content,
#                     name=f"analysis_parameters_{analysis_job.analysis_id}.json",
#                 ),
#             )
# 
#         # Add summary as README
#         if analysis_job.summary:
#             readme_content = f"# Analysis Results\n\n"
#             readme_content += f"**Analysis ID:** {analysis_job.analysis_id}\n"
#             readme_content += (
#                 f"**Analysis Type:** {analysis_job.get_analysis_type_display()}\n"
#             )
#             readme_content += (
#                 f"**Figures Generated:** {analysis_job.figures_generated}\n\n"
#             )
#             readme_content += f"## Summary\n\n{analysis_job.summary}\n"
# 
#             readme_file_content = readme_content.encode("utf-8")
#             readme_file = DatasetFile.objects.create(
#                 dataset=dataset,
#                 filename="README.md",
#                 file_path="",
#                 file_type="readme",
#                 file_format="md",
#                 size_bytes=len(readme_file_content),
#                 description="Analysis summary and documentation",
#                 local_file=ContentFile(readme_file_content, name="README.md"),
#             )
# 
#         # Update dataset file count and size
#         self._update_dataset_stats(dataset)
# 
#     def _add_notebook_to_dataset(self, notebook: Notebook, dataset: Dataset):
#         """Add notebook to dataset"""
# 
#         # Add notebook content as JSON
#         if notebook.content:
#             notebook_content = json.dumps(notebook.content, indent=2).encode("utf-8")
#             notebook_file = DatasetFile.objects.create(
#                 dataset=dataset,
#                 filename=f"{notebook.title.replace(' ', '_')}.ipynb",
#                 file_path="notebooks/",
#                 file_type="code",
#                 file_format="ipynb",
#                 size_bytes=len(notebook_content),
#                 description=f"Jupyter notebook: {notebook.title}",
#                 local_file=ContentFile(
#                     notebook_content, name=f"{notebook.title}.ipynb"
#                 ),
#             )
# 
#         # Add notebook metadata
#         metadata = {
#             "notebook_id": str(notebook.notebook_id),
#             "title": notebook.title,
#             "description": notebook.description,
#             "status": notebook.status,
#             "is_public": notebook.is_public,
#             "last_executed": notebook.last_executed.isoformat()
#             if notebook.last_executed
#             else None,
#             "execution_count": notebook.execution_count,
#             "created_at": notebook.created_at.isoformat(),
#             "updated_at": notebook.updated_at.isoformat(),
#         }
# 
#         metadata_content = json.dumps(metadata, indent=2).encode("utf-8")
#         metadata_file = DatasetFile.objects.create(
#             dataset=dataset,
#             filename="notebook_metadata.json",
#             file_path="metadata/",
#             file_type="metadata",
#             file_format="json",
#             size_bytes=len(metadata_content),
#             description="Notebook metadata and execution information",
#             local_file=ContentFile(metadata_content, name="notebook_metadata.json"),
#         )
# 
#         # Update dataset file count and size
#         self._update_dataset_stats(dataset)
# 
#     def _add_output_file_to_dataset(
#         self, dataset: Dataset, file_path: str, file_type: str
#     ):
#         """Add an output file to the dataset"""
# 
#         try:
#             if os.path.exists(file_path):
#                 file_name = os.path.basename(file_path)
#                 file_size = os.path.getsize(file_path)
# 
#                 with open(file_path, "rb") as f:
#                     file_content = f.read()
# 
#                 # Determine file format
#                 file_format = file_name.split(".")[-1] if "." in file_name else ""
# 
#                 dataset_file = DatasetFile.objects.create(
#                     dataset=dataset,
#                     filename=file_name,
#                     file_path=f"{file_type}s/",
#                     file_type=file_type,
#                     file_format=file_format,
#                     size_bytes=file_size,
#                     description=f"Generated {file_type} from code execution",
#                     local_file=ContentFile(file_content, name=file_name),
#                 )
# 
#                 logger.info(
#                     f"Added {file_type} file {file_name} to dataset {dataset.id}"
#                 )
# 
#         except Exception as e:
#             logger.error(f"Failed to add output file {file_path} to dataset: {e}")
# 
#     def _update_dataset_stats(self, dataset: Dataset):
#         """Update dataset file count and total size"""
# 
#         files = dataset.files.all()
#         dataset.file_count = files.count()
#         dataset.total_size_bytes = sum(f.size_bytes for f in files)
# 
#         # Update file formats list
#         formats = list(set(f.file_format for f in files if f.file_format))
#         dataset.file_formats = formats
# 
#         dataset.save()
# 
# 
# # Utility functions for automatic integration
# def auto_sync_code_completion(job: CodeExecutionJob) -> Dict[str, Any]:
#     """Automatically sync code execution results on job completion"""
# 
#     # Check if user has auto-sync enabled
#     default_connection = RepositoryConnection.objects.filter(
#         user=job.user, is_default=True, auto_sync_enabled=True, status="active"
#     ).first()
# 
#     if not default_connection:
#         logger.info(f"No auto-sync repository connection for user {job.user.username}")
#         return {"auto_sync": False, "reason": "no_auto_sync_connection"}
# 
#     try:
#         integrator = CodeRepositoryIntegrator(job.user, default_connection)
#         dataset = integrator.sync_code_execution_results(job, auto_upload=True)
# 
#         if dataset:
#             return {
#                 "auto_sync": True,
#                 "dataset_id": str(dataset.id),
#                 "dataset_title": dataset.title,
#                 "repository_name": default_connection.repository.name,
#                 "files_synced": dataset.file_count,
#                 "total_size": dataset.total_size_bytes,
#             }
#         else:
#             return {"auto_sync": False, "reason": "sync_failed"}
# 
#     except Exception as e:
#         logger.error(f"Auto-sync failed for job {job.job_id}: {e}")
#         return {"auto_sync": False, "reason": "sync_error", "error": str(e)}
# 
# 
# def sync_project_data_to_repository(
#     project, repository_connection: RepositoryConnection
# ) -> Optional[Dataset]:
#     """Sync all project data to a repository"""
# 
#     try:
#         # Create a project-wide dataset
#         dataset = Dataset.objects.create(
#             title=f"Project Data - {project.name}",
#             description=f"Complete data and outputs from project: {project.name}\n\n{project.description}",
#             dataset_type="supplementary",
#             owner=project.owner,
#             repository_connection=repository_connection,
#             project=project,
#             keywords=f"project data, {project.name}, computational results",
#             status="draft",
#         )
# 
#         integrator = CodeRepositoryIntegrator(project.owner, repository_connection)
# 
#         # Add all code execution results from this project
#         code_jobs = CodeExecutionJob.objects.filter(
#             user=project.owner
#         )  # Filter by project if available
#         for job in code_jobs:
#             if job.status == "completed":
#                 integrator._add_code_outputs_to_dataset(job, dataset)
# 
#         # Add all analysis results from this project
#         analysis_jobs = DataAnalysisJob.objects.filter(
#             user=project.owner
#         )  # Filter by project if available
#         for analysis_job in analysis_jobs:
#             integrator._add_analysis_outputs_to_dataset(analysis_job, dataset)
# 
#         # Update dataset stats
#         integrator._update_dataset_stats(dataset)
# 
#         logger.info(f"Created project dataset {dataset.id} for project {project.name}")
#         return dataset
# 
#     except Exception as e:
#         logger.error(f"Failed to sync project data: {e}")
#         return None

# --------------------------------------------------------------------------------
# End of Source Code from: apps/code_app/repository_integration.py
# --------------------------------------------------------------------------------
