#!/usr/bin/env python3
"""Jupyter notebook templates."""


class NotebookTemplates:
    """Provides pre-built notebook templates."""

    @staticmethod
    def get_data_analysis_template() -> dict:
        """Get data analysis notebook template."""
        return {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        "# Data Analysis with SciTeX\n",
                        "\n",
                        "This notebook template provides a structured approach to data analysis.\n",
                        "\n",
                        "## Objectives\n",
                        "- [ ] Data loading and exploration\n",
                        "- [ ] Data preprocessing\n",
                        "- [ ] Analysis and visualization\n",
                        "- [ ] Results and conclusions\n",
                    ],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Import required libraries\n",
                        "import pandas as pd\n",
                        "import numpy as np\n",
                        "import matplotlib.pyplot as plt\n",
                        "import seaborn as sns\n",
                        "\n",
                        "# Set plotting style\n",
                        'plt.style.use("default")\n',
                        'sns.set_palette("husl")\n',
                    ],
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["## 1. Data Loading\n"],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Load your data here\n",
                        '# df = pd.read_csv("your_data.csv")\n',
                        '# print(f"Data shape: {df.shape}")\n',
                    ],
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["## 2. Data Exploration\n"],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Explore your data\n",
                        "# df.head()\n",
                        "# df.info()\n",
                        "# df.describe()\n",
                    ],
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["## 3. Analysis and Results\n"],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": ["# Your analysis code here\n"],
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

    @staticmethod
    def get_machine_learning_template() -> dict:
        """Get machine learning notebook template."""
        return {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        "# Machine Learning Project\n",
                        "\n",
                        "This template provides a structured approach to machine learning projects.\n",
                    ],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Import ML libraries\n",
                        "import pandas as pd\n",
                        "import numpy as np\n",
                        "from sklearn.model_selection import train_test_split\n",
                        "from sklearn.preprocessing import StandardScaler\n",
                        "from sklearn.metrics import classification_report, confusion_matrix\n",
                        "import matplotlib.pyplot as plt\n",
                        "import seaborn as sns\n",
                    ],
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["## 1. Data Preparation\n"],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": ["# Load and prepare your data\n"],
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["## 2. Feature Engineering\n"],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": ["# Feature selection and engineering\n"],
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["## 3. Model Training\n"],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": ["# Train your models\n"],
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["## 4. Model Evaluation\n"],
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": ["# Evaluate model performance\n"],
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


# EOF
