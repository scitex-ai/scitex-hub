"""Unified visualization generator with mixin composition."""

from .base_generator import *
from .basic_plots_mixin import BasicPlotsMixin
from .stats_plots_mixin import StatsPlotsMixin
from .publication_mixin import PublicationMixin


class VisualizationGenerator(BasicPlotsMixin, StatsPlotsMixin, PublicationMixin):
    """
    Complete visualization generator combining all plot types.
    
    Inherits methods from:
    - BasicPlotsMixin: Line, scatter plots
    - StatsPlotsMixin: Bar, histogram, boxplot, heatmap, violin, pair plots
    - PublicationMixin: Publication-quality figures
    """
    pass


# EOF
