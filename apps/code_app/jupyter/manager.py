#!/usr/bin/env python3
"""Jupyter notebook management utilities."""
import os
import json
from pathlib import Path
from typing import Optional
import logging

from django.conf import settings
from django.utils import timezone

from ..models import Notebook
from .validator import NotebookValidator

logger = logging.getLogger(__name__)


class NotebookManager:
    """Manages Jupyter notebook operations."""

    def __init__(self, user):
        self.user = user
        self.base_path = Path(settings.MEDIA_ROOT) / "notebooks" / str(user.id)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def create_notebook(self, title: str, description: str = "") -> Notebook:
        """Create a new empty notebook."""
        # Create basic notebook structure
        nb_content = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        f"# {title}\n",
                        f"\n{description}\n" if description else "\n",
                        "This notebook was created with SciTeX-Code.\n",
                    ],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Welcome to SciTeX-Code!\n",
                        "# Start coding your analysis here\n",
                        'print("Hello, SciTeX!")',
                    ],
                },
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python", "version": "3.11.0"},
            },
            "nbformat": 4,
            "nbformat_minor": 4,
        }

        # Save to database
        notebook = Notebook.objects.create(
            user=self.user,
            title=title,
            description=description,
            content=nb_content,
            status="draft",
        )

        # Save to file system
        notebook_path = self.base_path / f"{notebook.notebook_id}.ipynb"
        with open(notebook_path, "w") as f:
            json.dump(nb_content, f, indent=2)

        notebook.file_path = str(notebook_path)
        notebook.save()

        logger.info(f"Created notebook '{title}' for user {self.user.username}")
        return notebook

    def load_notebook(self, notebook_id: str) -> Optional[Notebook]:
        """Load notebook from database."""
        try:
            return Notebook.objects.get(notebook_id=notebook_id, user=self.user)
        except Notebook.DoesNotExist:
            return None

    def save_notebook(self, notebook_id: str, content: dict) -> bool:
        """Save notebook content."""
        try:
            notebook = self.load_notebook(notebook_id)
            if not notebook:
                return False

            # Validate content
            is_valid, errors = NotebookValidator.validate_notebook(content)
            if not is_valid:
                logger.error(f"Invalid notebook content: {errors}")
                return False

            # Sanitize content
            sanitized_content = NotebookValidator.sanitize_notebook(content)

            # Update database
            notebook.content = sanitized_content
            notebook.updated_at = timezone.now()
            notebook.save()

            # Save to file system
            if notebook.file_path and os.path.exists(notebook.file_path):
                with open(notebook.file_path, "w") as f:
                    json.dump(sanitized_content, f, indent=2)

            logger.info(f"Saved notebook {notebook_id} for user {self.user.username}")
            return True

        except Exception as e:
            logger.error(f"Error saving notebook {notebook_id}: {e}")
            return False

    def duplicate_notebook(
        self, notebook_id: str, new_title: str
    ) -> Optional[Notebook]:
        """Create a copy of an existing notebook."""
        try:
            original = self.load_notebook(notebook_id)
            if not original:
                return None

            # Create new notebook with copied content
            new_notebook = Notebook.objects.create(
                user=self.user,
                title=new_title,
                description=f"Copy of {original.title}",
                content=original.content,
                status="draft",
            )

            # Save to file system
            notebook_path = self.base_path / f"{new_notebook.notebook_id}.ipynb"
            with open(notebook_path, "w") as f:
                json.dump(original.content, f, indent=2)

            new_notebook.file_path = str(notebook_path)
            new_notebook.save()

            return new_notebook

        except Exception as e:
            logger.error(f"Error duplicating notebook {notebook_id}: {e}")
            return None


# EOF
