#!/usr/bin/env python3
"""
Data Visualization Pipeline for SciTeX-Code
Integrates with Viz Module for publication-ready figure generation.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Any
import logging

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User


logger = logging.getLogger(__name__)



from .generator import VisualizationGenerator

class VisualizationPipeline:
    """Orchestrates data visualization workflows."""

    def __init__(self, user: User):
        self.user = user
        self.generator = VisualizationGenerator(user)

    def process_data_and_visualize(
        self, data_source: str, visualization_specs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process data and generate visualizations."""
        try:
            # Load data (simplified - could support multiple formats)
            if data_source.endswith(".csv"):
                df = pd.read_csv(data_source)
            elif data_source.endswith(".json"):
                with open(data_source) as f:
                    data = json.load(f)
                df = pd.DataFrame(data)
            else:
                return {"error": "Unsupported data format"}

            results = []

            for spec in visualization_specs:
                plot_type = spec["type"]

                # Extract data based on specification
                if plot_type in ["line", "scatter"]:
                    x_col = spec.get("x_column")
                    y_col = spec.get("y_column")

                    if x_col not in df.columns or y_col not in df.columns:
                        results.append({"error": f"Columns {x_col}, {y_col} not found"})
                        continue

                    plot_data = {"x": df[x_col].tolist(), "y": df[y_col].tolist()}

                elif plot_type == "histogram":
                    col = spec.get("column")
                    if col not in df.columns:
                        results.append({"error": f"Column {col} not found"})
                        continue

                    plot_data = {"values": df[col].tolist()}

                elif plot_type == "heatmap":
                    # Correlation heatmap
                    numeric_cols = df.select_dtypes(include=[np.number]).columns
                    correlation_matrix = df[numeric_cols].corr()

                    plot_data = {
                        "matrix": correlation_matrix.values,
                        "x_labels": correlation_matrix.columns.tolist(),
                        "y_labels": correlation_matrix.index.tolist(),
                    }

                else:
                    results.append({"error": f"Unsupported plot type: {plot_type}"})
                    continue

                # Generate visualization
                success, result = self.generator.generate_plot(
                    plot_type, plot_data, spec.get("options", {})
                )

                results.append(result)

            return {
                "success": True,
                "visualizations": results,
                "data_shape": df.shape,
                "data_columns": df.columns.tolist(),
            }

        except Exception as e:
            logger.error(f"Error in visualization pipeline: {e}")
            return {"error": str(e)}

    def create_research_report(self, title: str, sections: List[Dict[str, Any]]) -> str:
        """Create a research report with embedded visualizations."""
        from datetime import datetime

        report_content = f"""
# {title}

Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Author: {self.user.get_full_name() or self.user.username}

---

"""

        for section in sections:
            section_title = section.get("title", "Untitled Section")
            section_text = section.get("text", "")
            visualizations = section.get("visualizations", [])

            report_content += f"## {section_title}\n\n"

            if section_text:
                report_content += f"{section_text}\n\n"

            for viz in visualizations:
                if viz.get("filename"):
                    report_content += f"![{viz.get('plot_type', 'Visualization')}](visualizations/{self.user.id}/{viz['filename']})\n\n"
                    if viz.get("caption"):
                        report_content += f"*Figure: {viz['caption']}*\n\n"

        # Save report
        report_dir = Path(settings.MEDIA_ROOT) / "reports" / str(self.user.id)
        report_dir.mkdir(parents=True, exist_ok=True)

        report_filename = f"report_{uuid.uuid4().hex[:8]}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path = report_dir / report_filename

        with open(report_path, "w") as f:
            f.write(report_content)

        return str(report_path)

# EOF
