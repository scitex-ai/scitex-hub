"""
Configuration File Generator Module

Handles creation of project configuration files including YAML/JSON configs,
paths.json, and environment templates.
"""

import json
from pathlib import Path
import logging

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from ...models import Project

logger = logging.getLogger(__name__)


class ConfigGeneratorManager:
    """Manages project configuration file creation."""

    def __init__(self, filesystem_manager):
        """
        Initialize ConfigGeneratorManager.

        Args:
            filesystem_manager: Parent ProjectFilesystemManager instance
        """
        self.manager = filesystem_manager

    def create_project_config_files(self, project: Project, project_path: Path):
        """Create essential configuration files for the project."""
        config_path = project_path / "config"

        project_config = {
            "project": {
                "name": project.name,
                "id": project.id,
                "description": project.description,
                "created": project.created_at.isoformat(),
                "owner": project.owner.username,
                "progress": getattr(project, "progress", 0),
            },
            "paths": {
                "data_raw": "./data/raw",
                "data_processed": "./data/processed",
                "data_figures": "./data/figures",
                "data_models": "./data/models",
                "scripts": "./scripts",
                "results": "./results",
                "docs": "./docs",
                "temp": "./temp",
            },
            "execution": {
                "python_version": "3.8+",
                "requirements_file": "../requirements.txt",
                "log_level": "INFO",
                "cache_enabled": True,
            },
            "research": {
                "hypotheses": getattr(project, "hypotheses", "") or "",
                "keywords": [],
                "collaborators": [],
            },
        }

        if HAS_YAML:
            with open(config_path / "project.yaml", "w") as f:
                yaml.dump(project_config, f, default_flow_style=False, indent=2)
        else:
            with open(config_path / "project.json", "w") as f:
                json.dump(project_config, f, indent=2)

        self._write_paths_config(project_path)
        self._write_env_template(project_path, project)

    def _write_paths_config(self, project_path: Path):
        """Write paths.json configuration file."""
        paths_config = {
            "data": {
                "raw": str(project_path / "data" / "raw"),
                "processed": str(project_path / "data" / "processed"),
                "figures": str(project_path / "data" / "figures"),
                "models": str(project_path / "data" / "models"),
            },
            "scripts": str(project_path / "scripts"),
            "results": {
                "outputs": str(project_path / "results" / "outputs"),
                "reports": str(project_path / "results" / "reports"),
                "analysis": str(project_path / "results" / "analysis"),
            },
            "docs": str(project_path / "docs"),
            "temp": {
                "cache": str(project_path / "temp" / "cache"),
                "logs": str(project_path / "temp" / "logs"),
                "tmp": str(project_path / "temp" / "tmp"),
            },
        }

        config_path = project_path / "config"
        with open(config_path / "paths.json", "w") as f:
            json.dump(paths_config, f, indent=2)

    def _write_env_template(self, project_path: Path, project: Project):
        """Write environment template file."""
        env_template = f"""# SciTeX Project Environment Configuration
# Project: {project.name}

# Python Environment
PYTHON_PATH=./scripts
PYTHONPATH=${{PYTHONPATH}}:./scripts

# Data Paths
DATA_RAW=./data/raw
DATA_PROCESSED=./data/processed
DATA_FIGURES=./data/figures
DATA_MODELS=./data/models

# Output Paths
RESULTS_OUTPUT=./results/outputs
RESULTS_REPORTS=./results/reports
RESULTS_ANALYSIS=./results/analysis

# Temporary Paths
TEMP_CACHE=./temp/cache
TEMP_LOGS=./temp/logs
TEMP_TMP=./temp/tmp

# Project Settings
PROJECT_NAME="{project.name}"
PROJECT_ID={project.id}
LOG_LEVEL=INFO
CACHE_ENABLED=true

# Add your custom environment variables below
# API_KEY=your_api_key_here
# SCITEX_CLOUD_POSTGRES_URL=your_database_url_here
"""

        config_path = project_path / "config"
        with open(config_path / ".env.template", "w") as f:
            f.write(env_template)

    def create_requirements_file(self, project: Project, project_path: Path):
        """Create requirements.txt with essential scientific packages."""
        requirements = """# SciTeX Project Requirements
# Core scientific computing packages
numpy>=1.21.0
pandas>=1.3.0
matplotlib>=3.4.0
seaborn>=0.11.0
scipy>=1.7.0

# Data processing and analysis
scikit-learn>=1.0.0
statsmodels>=0.12.0

# Visualization
plotly>=5.0.0
bokeh>=2.4.0

# Jupyter and interactive computing
jupyter>=1.0.0
ipykernel>=6.0.0
nbformat>=5.1.0

# File I/O and data formats
openpyxl>=3.0.0
xlrd>=2.0.0
h5py>=3.1.0

# Development and testing
pytest>=6.2.0
black>=21.0.0
flake8>=3.9.0

# Documentation
sphinx>=4.0.0
sphinx-rtd-theme>=0.5.0

# Add your project-specific requirements below:
# tensorflow>=2.6.0
# torch>=1.9.0
# transformers>=4.9.0
"""

        with open(project_path / "requirements.txt", "w") as f:
            f.write(requirements)
