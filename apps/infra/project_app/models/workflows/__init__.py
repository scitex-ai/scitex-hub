"""
Workflows module - CI/CD workflow and automation models

Refactored from monolithic models.py into modular structure:
- workflow.py: Workflow model (workflow definition)
- run.py: WorkflowRun model (workflow execution)
- job.py: WorkflowJob model (job within a run)
- step.py: WorkflowStep model (step within a job)
- workflow_secret.py: WorkflowSecret model (encrypted secrets)
- artifact.py: WorkflowArtifact model (build artifacts)
"""

from .workflow import Workflow
from .run import WorkflowRun
from .job import WorkflowJob
from .step import WorkflowStep
from .workflow_secret import WorkflowSecret
from .artifact import WorkflowArtifact

__all__ = [
    "Workflow",
    "WorkflowRun",
    "WorkflowJob",
    "WorkflowStep",
    "WorkflowSecret",
    "WorkflowArtifact",
]
