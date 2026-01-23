"""
Vis App Models - Scientific Figure Editor

Exports all models for backward compatibility:
    from apps.vis_app.models import ScientificFigure, PltzBundle, ...
"""

from .bundles import (
    FigzBundle,
    FigzPanel,
    PltzBundle,
)
from .figures import (
    Annotation,
    FigureExport,
    FigurePanel,
    FigureVersion,
    JournalPreset,
    ScientificFigure,
)
from .presets import (
    UserStylePreset,
)

__all__ = [
    # figures.py
    "JournalPreset",
    "ScientificFigure",
    "FigurePanel",
    "Annotation",
    "FigureVersion",
    "FigureExport",
    # bundles.py
    "PltzBundle",
    "FigzBundle",
    "FigzPanel",
    # presets.py
    "UserStylePreset",
]
