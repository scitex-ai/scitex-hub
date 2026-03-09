"""
Combined Design System Views

View for displaying all design system sections in a single page.
"""

from django.shortcuts import render
from django.views import View

from .base import _load_components


class DesignAllView(View):
    """Design system - All sections combined for printing/reference."""

    template_name = "dev_app/design_all.html"

    def get(self, request):
        components_data = _load_components()
        # All section partials in logical order
        sections = [
            {"title": "Colors", "partial": "dev_app/design_partial/colors.html"},
            {
                "title": "Workspace Colors",
                "partial": "dev_app/design_partial/workspace_colors.html",
            },
            {
                "title": "Typography",
                "partial": "dev_app/design_partial/typography.html",
            },
            {"title": "Spacing", "partial": "dev_app/design_partial/spacing.html"},
            {"title": "Icons", "partial": "dev_app/design_partial/icons.html"},
            {
                "title": "Workspace Icons",
                "partial": "dev_app/design_partial/workspace_icons.html",
            },
            {"title": "Theme", "partial": "dev_app/design_partial/theme.html"},
            {"title": "Code Blocks", "partial": "dev_app/design_partial/code.html"},
            {"title": "Terminal", "partial": "dev_app/design_partial/terminal.html"},
            {
                "title": "Terminal Log",
                "partial": "dev_app/design_partial/terminal-log.html",
            },
            {"title": "Button", "partial": "dev_app/design_partial/button.html"},
            {"title": "Badge", "partial": "dev_app/design_partial/badge.html"},
            {"title": "Card", "partial": "dev_app/design_partial/card.html"},
            {
                "title": "Form Input",
                "partial": "dev_app/design_partial/form-input.html",
            },
            {"title": "Checkbox", "partial": "dev_app/design_partial/checkbox.html"},
            {
                "title": "Toggle Button Checkbox",
                "partial": "dev_app/design_partial/toggle-button-checkbox.html",
            },
            {
                "title": "Select Dropdown",
                "partial": "dev_app/design_partial/select-dropdown.html",
            },
            {
                "title": "File Upload",
                "partial": "dev_app/design_partial/file-upload.html",
            },
            {
                "title": "Segmented Radio Control",
                "partial": "dev_app/design_partial/segmented-radio-control.html",
            },
            {"title": "Tabs", "partial": "dev_app/design_partial/tabs.html"},
            {
                "title": "Breadcrumb",
                "partial": "dev_app/design_partial/breadcrumb.html",
            },
            {
                "title": "Dropdown Menu",
                "partial": "dev_app/design_partial/dropdown-menu.html",
            },
            {"title": "Navbar", "partial": "dev_app/design_partial/navbar.html"},
            {"title": "Alerts", "partial": "dev_app/design_partial/alerts.html"},
            {"title": "Hero", "partial": "dev_app/design_partial/hero-guideline.html"},
            {
                "title": "Panel Resizer",
                "partial": "dev_app/design_partial/resizer.html",
            },
            {
                "title": "Guidelines",
                "partial": "dev_app/design_partial/guidelines.html",
            },
        ]
        context = {
            "components": components_data.get("components", []),
            "metadata": components_data.get("metadata", {}),
            "sections": sections,
        }
        return render(request, self.template_name, context)
