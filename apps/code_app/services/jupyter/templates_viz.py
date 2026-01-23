#!/usr/bin/env python3
"""
Data visualization notebook template.
"""


class VizTemplate:
    """Data visualization notebook template."""

    @staticmethod
    def get_visualization_template() -> dict:
        """Get data visualization notebook template."""
        return {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        "# Data Visualization Project\n",
                        "\n",
                        "Create publication-ready visualizations with this template.\n",
                    ],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Import visualization libraries\n",
                        "import matplotlib.pyplot as plt\n",
                        "import seaborn as sns\n",
                        "import plotly.express as px\n",
                        "import plotly.graph_objects as go\n",
                        "import pandas as pd\n",
                        "import numpy as np\n",
                        "\n",
                        "# Set style for publication-ready plots\n",
                        'plt.rcParams["figure.figsize"] = (10, 6)\n',
                        'plt.rcParams["font.size"] = 12\n',
                        'plt.rcParams["axes.linewidth"] = 1.5\n',
                    ],
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["## Static Plots with Matplotlib/Seaborn\n"],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": ["# Create static visualizations\n"],
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["## Interactive Plots with Plotly\n"],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": ["# Create interactive visualizations\n"],
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
