#!/usr/bin/env python3
"""
Notebook templates dispatcher.
"""

from .templates_data import DataTemplate
from .templates_ml import MLTemplate
from .templates_viz import VizTemplate


class NotebookTemplates:
    """Provides pre-built notebook templates."""

    @staticmethod
    def get_data_analysis_template() -> dict:
        """Get data analysis notebook template."""
        return DataTemplate.get_data_analysis_template()

    @staticmethod
    def get_machine_learning_template() -> dict:
        """Get machine learning notebook template."""
        return MLTemplate.get_machine_learning_template()

    @staticmethod
    def get_visualization_template() -> dict:
        """Get data visualization notebook template."""
        return VizTemplate.get_visualization_template()
