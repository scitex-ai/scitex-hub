"""
Dev App Views - Design System Views

Exports all views for backward compatibility:
    from apps.dev_app.views import DesignSystemView, DesignSectionView, ...
"""

from .base import (
    DESIGN_SECTIONS,
    DesignSectionView,
    DesignSystemView,
    _load_components,
    index,
)
from .combined import DesignAllView
from .sections import (
    DesignAlertsView,
    DesignBadgeView,
    DesignBreadcrumbView,
    DesignButtonView,
    DesignCardView,
    DesignCheckboxView,
    DesignCodeBlocksView,
    DesignColorsView,
    DesignDropdownMenuView,
    DesignFileUploadView,
    DesignFormInputView,
    DesignGuidelinesView,
    DesignHeroView,
    DesignIconsView,
    DesignNavbarView,
    DesignResizerView,
    DesignSegmentedRadioControlView,
    DesignSelectDropdownView,
    DesignSpacingView,
    DesignTabsView,
    DesignTerminalLogView,
    DesignTerminalView,
    DesignThemeView,
    DesignToggleButtonCheckboxView,
    DesignTypographyView,
    DesignVisitorSystemView,
    DesignWorkspaceColorsView,
    DesignWorkspaceIconsView,
    DesignWorkspaceLayoutView,
)
from .slurm import cancel_all_jobs_api
from .tests import TestMonitorView, run_tests_api

__all__ = [
    # base.py
    "index",
    "_load_components",
    "DESIGN_SECTIONS",
    "DesignSystemView",
    "DesignSectionView",
    # sections.py - Foundation
    "DesignColorsView",
    "DesignWorkspaceColorsView",
    "DesignWorkspaceIconsView",
    "DesignTypographyView",
    "DesignCodeBlocksView",
    "DesignSpacingView",
    "DesignThemeView",
    "DesignGuidelinesView",
    "DesignTerminalLogView",
    "DesignTerminalView",
    "DesignIconsView",
    # sections.py - Components
    "DesignBadgeView",
    "DesignButtonView",
    "DesignCardView",
    "DesignCheckboxView",
    "DesignFormInputView",
    "DesignToggleButtonCheckboxView",
    "DesignSelectDropdownView",
    "DesignTabsView",
    "DesignBreadcrumbView",
    "DesignDropdownMenuView",
    "DesignFileUploadView",
    "DesignSegmentedRadioControlView",
    "DesignNavbarView",
    "DesignAlertsView",
    "DesignHeroView",
    "DesignResizerView",
    "DesignWorkspaceLayoutView",
    "DesignVisitorSystemView",
    # combined.py
    "DesignAllView",
    # tests.py
    "TestMonitorView",
    "run_tests_api",
    # slurm.py
    "cancel_all_jobs_api",
]
