#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helper functions for workflow management."""

from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def get_workflow_template(template_name):
    """Get workflow template YAML content"""
    templates = {
        "python-test": """name: Python Tests
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run tests
        run: |
          pytest tests/ -v
""",
        "latex-build": """name: LaTeX Build
on:
  push:
    branches: [ main ]
    paths:
      - '**.tex'
      - 'scitex/writer/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Compile LaTeX
        run: |
          cd scitex/writer/00_shared
          pdflatex main.tex
          bibtex main
          pdflatex main.tex
          pdflatex main.tex

      - name: Upload PDF
        uses: actions/upload-artifact@v3
        with:
          name: manuscript
          path: scitex/writer/00_shared/main.pdf
""",
        "code-lint": """name: Code Linting
on:
  push:
    branches: [ main, develop ]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install linting tools
        run: |
          pip install black flake8 mypy

      - name: Run black
        run: black --check .

      - name: Run flake8
        run: flake8 .

      - name: Run mypy
        run: mypy . --ignore-missing-imports
""",
        "docker-build": """name: Docker Build
on:
  push:
    branches: [ main ]
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Build Docker image
        run: |
          docker build -t myapp:latest .

      - name: Test Docker image
        run: |
          docker run myapp:latest pytest
""",
    }

    return templates.get(template_name, "")


def get_available_templates():
    """Get list of available workflow templates"""
    return [
        {
            "id": "python-test",
            "name": "Python Tests",
            "description": "Run pytest tests on push and pull requests",
            "icon": "python",
        },
        {
            "id": "latex-build",
            "name": "LaTeX Build",
            "description": "Compile LaTeX documents and generate PDFs",
            "icon": "document",
        },
        {
            "id": "code-lint",
            "name": "Code Linting",
            "description": "Run black, flake8, and mypy for code quality",
            "icon": "check",
        },
        {
            "id": "docker-build",
            "name": "Docker Build",
            "description": "Build and test Docker images",
            "icon": "container",
        },
    ]


def save_workflow_to_filesystem(workflow):
    """Save workflow YAML to project filesystem"""
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    try:
        manager = get_project_filesystem_manager(workflow.project.owner)
        project_path = manager.get_project_root_path(workflow.project)

        if not project_path:
            logger.error(f"Project path not found for {workflow.project.name}")
            return False

        # Create .scitex/workflows directory
        workflows_dir = project_path / ".scitex" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        # Save workflow YAML
        workflow_file = workflows_dir / Path(workflow.file_path).name
        workflow_file.write_text(workflow.yaml_content)

        logger.info(f"Saved workflow '{workflow.name}' to {workflow_file}")
        return True

    except Exception as e:
        logger.error(f"Failed to save workflow to filesystem: {e}")
        return False


def delete_workflow_from_filesystem(project, workflow):
    """Delete workflow YAML from project filesystem"""
    from apps.project_app.services.project_filesystem import (
        get_project_filesystem_manager,
    )

    try:
        manager = get_project_filesystem_manager(project.owner)
        project_path = manager.get_project_root_path(project)

        if not project_path:
            return False

        workflow_file = project_path / workflow.file_path
        if workflow_file.exists():
            workflow_file.unlink()
            logger.info(f"Deleted workflow file {workflow_file}")
            return True

        return False

    except Exception as e:
        logger.error(f"Failed to delete workflow from filesystem: {e}")
        return False


# EOF
