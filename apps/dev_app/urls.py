#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-10-25 09:45:25 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/dev_app/urls.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/dev_app/urls.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

from django.urls import path

from apps.core_app.views.console_logger import get_console_logs, log_console

from . import views

app_name = "dev_app"

urlpatterns = [
    path("", views.index, name="index"),
    path("tests/", views.TestMonitorView.as_view(), name="tests"),
    path(
        "tests/<str:category>/", views.TestMonitorView.as_view(), name="tests_category"
    ),
    path("api/tests/run/<str:category>/", views.run_tests_api, name="tests_run_api"),
    path("api/console/", log_console, name="console_log"),
    path("api/console/logs/", get_console_logs, name="console_logs_get"),
    path("api/cancel-all-jobs/", views.cancel_all_jobs_api, name="cancel_all_jobs_api"),
    path("design/", views.DesignGuidelinesView.as_view(), name="design"),
    path(
        "design/typography/",
        views.DesignTypographyView.as_view(),
        name="design_typography",
    ),
    path(
        "design/colors/",
        views.DesignColorsView.as_view(),
        name="design_colors",
    ),
    path(
        "design/workspace-colors/",
        views.DesignWorkspaceColorsView.as_view(),
        name="design_workspace_colors",
    ),
    path(
        "design/workspace-icons/",
        views.DesignWorkspaceIconsView.as_view(),
        name="design_workspace_icons",
    ),
    path(
        "design/code-blocks/",
        views.DesignCodeBlocksView.as_view(),
        name="design_code_blocks",
    ),
    path(
        "design/terminal-log/",
        views.DesignTerminalLogView.as_view(),
        name="design_terminal_log",
    ),
    path(
        "design/terminal/",
        views.DesignTerminalView.as_view(),
        name="design_terminal",
    ),
    path(
        "design/spacing/",
        views.DesignSpacingView.as_view(),
        name="design_spacing",
    ),
    path("design/theme/", views.DesignThemeView.as_view(), name="design_theme"),
    path(
        "design/guidelines/",
        views.DesignGuidelinesView.as_view(),
        name="design_guidelines",
    ),
    # Component pages
    path(
        "design/hero/",
        views.DesignHeroView.as_view(),
        name="design_hero",
    ),
    path(
        "design/badge/",
        views.DesignBadgeView.as_view(),
        name="design_badge",
    ),
    path(
        "design/button/",
        views.DesignButtonView.as_view(),
        name="design_button",
    ),
    path(
        "design/card/",
        views.DesignCardView.as_view(),
        name="design_card",
    ),
    path(
        "design/checkbox/",
        views.DesignCheckboxView.as_view(),
        name="design_checkbox",
    ),
    path(
        "design/form-input/",
        views.DesignFormInputView.as_view(),
        name="design_form_input",
    ),
    path(
        "design/toggle-button-checkbox/",
        views.DesignToggleButtonCheckboxView.as_view(),
        name="design_toggle_button_checkbox",
    ),
    path(
        "design/select-dropdown/",
        views.DesignSelectDropdownView.as_view(),
        name="design_select_dropdown",
    ),
    path(
        "design/tabs/",
        views.DesignTabsView.as_view(),
        name="design_tabs",
    ),
    path(
        "design/breadcrumb/",
        views.DesignBreadcrumbView.as_view(),
        name="design_breadcrumb",
    ),
    path(
        "design/dropdown-menu/",
        views.DesignDropdownMenuView.as_view(),
        name="design_dropdown_menu",
    ),
    path(
        "design/file-upload/",
        views.DesignFileUploadView.as_view(),
        name="design_file_upload",
    ),
    path(
        "design/segmented-radio-control/",
        views.DesignSegmentedRadioControlView.as_view(),
        name="design_segmented_radio_control",
    ),
    path(
        "design/navbar/",
        views.DesignNavbarView.as_view(),
        name="design_navbar",
    ),
    path(
        "design/alerts/",
        views.DesignAlertsView.as_view(),
        name="design_alerts",
    ),
    path(
        "design/resizer/",
        views.DesignResizerView.as_view(),
        name="design_resizer",
    ),
    path(
        "design/icons/",
        views.DesignIconsView.as_view(),
        name="design_icons",
    ),
    path(
        "design/workspace-layout/",
        views.DesignWorkspaceLayoutView.as_view(),
        name="design_workspace_layout",
    ),
    path(
        "design/visitor-system/",
        views.DesignVisitorSystemView.as_view(),
        name="design_visitor_system",
    ),
    path(
        "design/all/",
        views.DesignAllView.as_view(),
        name="design_all",
    ),
]

# EOF
