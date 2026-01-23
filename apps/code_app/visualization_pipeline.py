#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualization Pipeline - Legacy import location.

This module has been refactored into services/visualization/.
Kept for backward compatibility.
"""

# Import from new location
from .services.visualization import VisualizationGenerator, VisualizationPipeline

__all__ = ["VisualizationGenerator", "VisualizationPipeline"]

# EOF
