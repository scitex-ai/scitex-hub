#!/usr/bin/env python3
"""Jupyter notebook execution utilities."""
import json
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from django.utils import timezone

from ..models import Notebook, CodeExecutionJob

logger = logging.getLogger(__name__)


class NotebookExecutor:
    """Executes Jupyter notebooks safely."""

    def __init__(self, timeout: int = 300, memory_limit: int = 512):
        self.timeout = timeout
        self.memory_limit = memory_limit

    def execute_notebook(
        self, notebook: Notebook, execution_job: Optional[CodeExecutionJob] = None
    ) -> Tuple[bool, Dict]:
        """
        Execute a Jupyter notebook safely.

        Returns:
            (success, result_data)
        """
        if execution_job:
            execution_job.status = "running"
            execution_job.started_at = timezone.now()
            execution_job.save()

        try:
            # Load notebook content
            nb_content = notebook.content
            nb = nbformat.from_dict(nb_content)

            # Create execution environment
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Set up execution preprocessor
                ep = ExecutePreprocessor(
                    timeout=self.timeout, kernel_name="python3", allow_errors=True
                )

                # Execute notebook
                start_time = timezone.now()
                executed_nb, resources = ep.preprocess(
                    nb, {"metadata": {"path": str(temp_path)}}
                )
                end_time = timezone.now()

                # Extract results
                execution_time = (end_time - start_time).total_seconds()
                outputs = []
                errors = []

                for cell in executed_nb.cells:
                    if cell.cell_type == "code" and cell.outputs:
                        for output in cell.outputs:
                            if output.output_type == "stream":
                                outputs.append(
                                    {
                                        "type": "stream",
                                        "name": output.name,
                                        "text": "".join(output.text),
                                    }
                                )
                            elif output.output_type == "execute_result":
                                outputs.append(
                                    {
                                        "type": "result",
                                        "execution_count": output.execution_count,
                                        "data": output.data,
                                    }
                                )
                            elif output.output_type == "display_data":
                                outputs.append({"type": "display", "data": output.data})
                            elif output.output_type == "error":
                                errors.append(
                                    {
                                        "ename": output.ename,
                                        "evalue": output.evalue,
                                        "traceback": output.traceback,
                                    }
                                )

                # Update notebook with execution results
                notebook.content = nbformat.to_dict(executed_nb)
                notebook.last_executed = timezone.now()
                notebook.execution_count += 1
                notebook.status = "completed" if not errors else "failed"
                notebook.save()

                # Update execution job if provided
                if execution_job:
                    execution_job.status = "completed" if not errors else "failed"
                    execution_job.completed_at = timezone.now()
                    execution_job.execution_time = execution_time
                    execution_job.output = json.dumps(outputs, indent=2)
                    if errors:
                        execution_job.error_output = json.dumps(errors, indent=2)
                    execution_job.save()

                result_data = {
                    "execution_time": execution_time,
                    "outputs": outputs,
                    "errors": errors,
                    "cells_executed": len(
                        [c for c in executed_nb.cells if c.cell_type == "code"]
                    ),
                }

                logger.info(f"Successfully executed notebook {notebook.notebook_id}")
                return True, result_data

        except Exception as e:
            logger.error(f"Error executing notebook {notebook.notebook_id}: {e}")

            # Update job status
            if execution_job:
                execution_job.status = "failed"
                execution_job.completed_at = timezone.now()
                execution_job.error_output = str(e)
                execution_job.save()

            # Update notebook status
            notebook.status = "failed"
            notebook.save()

            return False, {"error": str(e)}

    def execute_cell(self, notebook: Notebook, cell_index: int) -> Tuple[bool, Dict]:
        """Execute a single cell in the notebook."""
        try:
            nb_content = notebook.content
            if cell_index >= len(nb_content.get("cells", [])):
                return False, {"error": "Cell index out of range"}

            cell = nb_content["cells"][cell_index]
            if cell.get("cell_type") != "code":
                return False, {"error": "Can only execute code cells"}

            # Create a temporary notebook with just this cell
            temp_nb_content = {
                "cells": [cell],
                "metadata": nb_content.get("metadata", {}),
                "nbformat": nb_content.get("nbformat", 4),
                "nbformat_minor": nb_content.get("nbformat_minor", 4),
            }

            temp_nb = nbformat.from_dict(temp_nb_content)

            # Execute
            ep = ExecutePreprocessor(
                timeout=60,  # Shorter timeout for single cell
                kernel_name="python3",
                allow_errors=True,
            )

            executed_nb, _ = ep.preprocess(temp_nb)
            executed_cell = executed_nb.cells[0]

            # Extract outputs
            outputs = []
            errors = []

            for output in executed_cell.outputs:
                if output.output_type == "stream":
                    outputs.append(
                        {
                            "type": "stream",
                            "name": output.name,
                            "text": "".join(output.text),
                        }
                    )
                elif output.output_type == "execute_result":
                    outputs.append(
                        {
                            "type": "result",
                            "execution_count": output.execution_count,
                            "data": output.data,
                        }
                    )
                elif output.output_type == "error":
                    errors.append(
                        {
                            "ename": output.ename,
                            "evalue": output.evalue,
                            "traceback": output.traceback,
                        }
                    )

            # Update the cell in the original notebook
            nb_content["cells"][cell_index] = nbformat.to_dict(executed_cell)
            notebook.content = nb_content
            notebook.save()

            return True, {
                "outputs": outputs,
                "errors": errors,
                "execution_count": executed_cell.execution_count,
            }

        except Exception as e:
            logger.error(
                f"Error executing cell {cell_index} in notebook {notebook.notebook_id}: {e}"
            )
            return False, {"error": str(e)}


# EOF
